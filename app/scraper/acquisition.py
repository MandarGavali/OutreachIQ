"""
Acquisition interface, data models, and ProfileInput for OutreachIQ V2.

Defines the contract that every profile data provider must satisfy.
The rest of the application depends on this interface, not on any
specific data source.

ProfileInput
------------
A typed representation of the user's acquisition request.  It tells
the acquisition layer *what* to fetch and *how* (source_type):

    "text"    — user pasted profile text (TextProfileAdapter)
    "pdf"     — user uploaded a PDF (PDFProfileAdapter)
    "fixture" — deterministic in-memory fixture (FixtureProfileAdapter)

RawProfileData
--------------
The internal intermediate representation produced by every adapter and
consumed by normalize_profile().  It must NOT travel beyond the normalizer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional, Protocol

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProfileInput — typed acquisition request
# ---------------------------------------------------------------------------

class ProfileInput(BaseModel):
    """
    Typed input for the acquisition layer.

    Exactly one data source must be supplied for each source_type:

      source_type="text"    → profile_text must be non-empty
      source_type="pdf"     → pdf_path must be non-empty
      source_type="fixture" → profile_url must be non-empty

    profile_url is always optional metadata; it is stored in RawProfileData
    for traceability but is never required for text or PDF inputs.
    """

    source_type: Literal["text", "pdf", "fixture"] = "fixture"
    profile_text: Optional[str] = Field(
        default=None,
        description="Raw pasted profile text. Required when source_type='text'.",
    )
    pdf_path: Optional[str] = Field(
        default=None,
        description="Absolute path to the uploaded PDF. Required when source_type='pdf'.",
    )
    profile_url: Optional[str] = Field(
        default=None,
        description=(
            "Profile URL, if known.  Required when source_type='fixture'. "
            "Optional metadata for text/PDF inputs."
        ),
    )

    @model_validator(mode="after")
    def _check_source_data(self) -> "ProfileInput":
        if self.source_type == "text" and not (self.profile_text or "").strip():
            raise ValueError(
                "profile_text must be provided and non-empty when source_type='text'."
            )
        if self.source_type == "pdf" and not (self.pdf_path or "").strip():
            raise ValueError(
                "pdf_path must be provided and non-empty when source_type='pdf'."
            )
        if self.source_type == "fixture" and not (self.profile_url or "").strip():
            raise ValueError(
                "profile_url must be provided and non-empty when source_type='fixture'."
            )
        return self


# ---------------------------------------------------------------------------
# Raw data model
# ---------------------------------------------------------------------------

class RawProfileData(BaseModel):
    """
    Internal representation of profile data before normalization.

    This is an acquisition-layer artifact and must NOT be passed beyond
    the normalizer.  Do not store passwords, cookies, or tokens here.
    """

    # profile_url is optional — text and PDF inputs may not have a URL.
    profile_url: Optional[str] = Field(
        default=None,
        description="Profile URL, if known. None for text/PDF inputs.",
    )
    name: str = ""
    headline: str = ""
    about: str = ""
    recent_activity: list[str] = Field(default_factory=list)

    # Optional metadata — useful for debugging and audit trails
    source: str = "unknown"
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = {"frozen": False}


# ---------------------------------------------------------------------------
# Acquisition interface (Protocol — structural subtyping)
# ---------------------------------------------------------------------------

class ProfileAcquisition(Protocol):
    """
    Contract every profile data provider must satisfy.

    Implementations may use user-supplied text, PDF files, or fixture data.
    They must never bypass platform access controls or automate LinkedIn login.
    """

    def acquire(self, profile_url: str) -> RawProfileData:
        """
        Acquire raw profile data for the given profile URL.

        Args:
            profile_url: A validated, normalized profile URL.

        Returns:
            RawProfileData populated from the provider.

        Raises:
            ProfileNotFoundError: The profile does not exist.
            ProfileTimeoutError: The acquisition timed out.
            ProfileAcquisitionError: Any other acquisition failure.
        """
        ...
