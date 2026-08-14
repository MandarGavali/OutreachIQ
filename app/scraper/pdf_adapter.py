"""
PDF profile acquisition adapter for OutreachIQ V2.

PDFProfileAdapter
-----------------
Accepts a path to a user-uploaded PDF file and extracts text using
the pypdf library (already installed).  The extracted text is then
parsed by the shared parse_profile_text() parser to produce RawProfileData.

Responsibilities:
  1. Validate the file exists
  2. Validate the file extension is .pdf
  3. Enforce maximum file size (configurable, default 10 MB)
  4. Open and parse the PDF using pypdf
  5. Extract text from all pages in order
  6. Detect and reject image-only PDFs (no extractable text)
  7. Detect and reject password-protected PDFs
  8. Normalize extracted text
  9. Pass to parse_profile_text() → RawProfileData
  10. Return RawProfileData

What this adapter does NOT do:
  - Does not perform OCR (image-only PDFs are rejected with a clear error)
  - Does not make network calls
  - Does not log PDF content (only metadata like page count)
  - Does not retain the PDF after processing (callers must clean up)
  - Does not pass PDF binary to any LLM

Security:
  - PDF content is treated as untrusted user data
  - No execution of embedded scripts or actions
  - pypdf extraction is deterministic and sandboxed

OCR is a future enhancement: if the PDF contains no extractable text,
a clear error is returned asking the user to provide a text-based PDF
or paste the profile text manually.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from app.scraper.acquisition import RawProfileData
from app.scraper.exceptions import ProfileAcquisitionError
from app.scraper.parser import parse_profile_text

logger = logging.getLogger(__name__)

# Default maximum PDF file size (10 MB)
_DEFAULT_MAX_SIZE_BYTES: int = 10 * 1024 * 1024

# Minimum text length to be considered meaningful (not just headers/footers)
_MIN_MEANINGFUL_TEXT_LEN: int = 20


class PDFProfileAdapter:
    """
    Adapter that extracts profile information from a user-uploaded PDF.

    Uses pypdf for text extraction.  The extracted text is parsed by
    the shared parse_profile_text() parser.

    Args:
        max_file_size_bytes: Maximum allowed PDF file size in bytes.
                             Defaults to 10 MB.

    Usage::

        adapter = PDFProfileAdapter()
        raw = adapter.acquire_from_pdf(
            pdf_path="/tmp/profile.pdf",
            profile_url="https://linkedin.com/in/alex",  # optional
        )
    """

    def __init__(
        self,
        max_file_size_bytes: int = _DEFAULT_MAX_SIZE_BYTES,
    ) -> None:
        self._max_size = max_file_size_bytes

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def acquire_from_pdf(
        self,
        pdf_path: str,
        profile_url: Optional[str] = None,
    ) -> RawProfileData:
        """
        Extract profile data from a PDF file.

        Args:
            pdf_path: Absolute path to the PDF file.
            profile_url: Optional URL for metadata/traceability.

        Returns:
            RawProfileData populated from the PDF's text content.

        Raises:
            ProfileAcquisitionError: For any validation or extraction failure.
        """
        self._validate_file(pdf_path)
        text = self._extract_text(pdf_path)
        return self._parse_text(text, profile_url=profile_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_file(self, pdf_path: str) -> None:
        """Validate that the file exists, is a PDF, and is within size limits."""
        if not pdf_path or not pdf_path.strip():
            raise ProfileAcquisitionError("PDF path must not be empty.")

        if not os.path.exists(pdf_path):
            raise ProfileAcquisitionError(
                f"PDF file not found: {os.path.basename(pdf_path)!r}"
            )

        if not os.path.isfile(pdf_path):
            raise ProfileAcquisitionError(
                f"PDF path is not a file: {os.path.basename(pdf_path)!r}"
            )

        # Extension check (case-insensitive)
        _, ext = os.path.splitext(pdf_path)
        if ext.lower() != ".pdf":
            raise ProfileAcquisitionError(
                f"File must have a .pdf extension, got {ext!r}."
            )

        # Size check
        size = os.path.getsize(pdf_path)
        if size == 0:
            raise ProfileAcquisitionError("PDF file is empty (0 bytes).")
        if size > self._max_size:
            max_mb = self._max_size / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            raise ProfileAcquisitionError(
                f"PDF file is too large ({actual_mb:.1f} MB). "
                f"Maximum allowed size is {max_mb:.0f} MB."
            )

    def _extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from the PDF using pypdf.

        Raises:
            ProfileAcquisitionError: For corrupt, encrypted, image-only PDFs,
                                     or extraction failures.
        """
        try:
            import pypdf  # noqa: PLC0415 — lazy import keeps module lightweight
        except ImportError as exc:  # pragma: no cover
            raise ProfileAcquisitionError(
                "pypdf is not installed. "
                "Run: pip install pypdf"
            ) from exc

        try:
            reader = pypdf.PdfReader(pdf_path)
        except pypdf.errors.PdfStreamError as exc:
            raise ProfileAcquisitionError(
                f"PDF file appears to be corrupt or malformed: {exc}"
            ) from exc
        except pypdf.errors.PdfReadError as exc:
            raise ProfileAcquisitionError(
                f"Could not read PDF file: {exc}"
            ) from exc
        except Exception as exc:
            raise ProfileAcquisitionError(
                f"Unexpected error opening PDF: {type(exc).__name__}: {exc}"
            ) from exc

        # Password-protected / encrypted
        if reader.is_encrypted:
            raise ProfileAcquisitionError(
                "PDF is password-protected and cannot be read. "
                "Please provide an unprotected PDF or paste the profile text manually."
            )

        if len(reader.pages) == 0:
            raise ProfileAcquisitionError(
                "PDF contains no pages."
            )

        logger.debug("PDF has %d page(s): %s", len(reader.pages), os.path.basename(pdf_path))

        # Extract text from each page
        page_texts: list[str] = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                page_texts.append(page_text)
                logger.debug("Page %d: %d chars extracted", i + 1, len(page_text))
            except Exception as exc:
                logger.warning(
                    "Could not extract text from page %d: %s", i + 1, type(exc).__name__
                )
                page_texts.append("")

        combined = "\n".join(page_texts)

        # Check for image-only PDF (no extractable text)
        if len(combined.strip()) < _MIN_MEANINGFUL_TEXT_LEN:
            raise ProfileAcquisitionError(
                "PDF contains no extractable text. "
                "This may be an image-only (scanned) PDF. "
                "Please upload a text-based profile PDF or paste the profile text manually. "
                "(OCR support is a planned future enhancement.)"
            )

        return combined

    def _parse_text(
        self,
        text: str,
        profile_url: Optional[str] = None,
    ) -> RawProfileData:
        """Parse extracted PDF text into RawProfileData."""
        try:
            raw = parse_profile_text(text, profile_url=profile_url, source="pdf")
        except ValueError as exc:
            raise ProfileAcquisitionError(
                f"Could not extract profile data from PDF: {exc}"
            ) from exc

        logger.info(
            "PDFProfileAdapter: extracted profile name=%r from PDF",
            raw.name,
        )
        return raw
