"""
Concrete profile acquisition adapters for OutreachIQ V2.

This module ships three adapters:

1. FixtureProfileAdapter
   A deterministic, in-memory adapter for testing and development.
   Register fixture profiles by URL and it returns them instantly.

2. TextProfileAdapter
   Accepts user-pasted profile text and converts it into RawProfileData
   via the shared parse_profile_text() parser.
   No network calls.  No LinkedIn access required.

3. PDFProfileAdapter
   Accepts a path to a user-uploaded PDF and extracts text using pypdf.
   The extracted text is then parsed by parse_profile_text().
   See app/scraper/pdf_adapter.py.

IMPORTANT — What is NOT here:
  - No CAPTCHA bypass
  - No anti-bot browser fingerprint spoofing
  - No automated session harvesting
  - No proxy rotation for evasion
  - No unauthorized LinkedIn DOM scraping at scale

The browser_manager / Playwright infrastructure in the repository is
preserved for historical/experimental purposes only.  It is NOT required
by the production acquisition path (text or PDF inputs).

Production profile acquisition does not use LinkedIn DOM scraping.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.scraper.acquisition import ProfileAcquisition, RawProfileData
from app.scraper.exceptions import (
    ProfileAcquisitionError,
    ProfileNotFoundError,
    ProfileTimeoutError,
)
from app.scraper.parser import parse_profile_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixture adapter — deterministic, for tests and development
# ---------------------------------------------------------------------------

class FixtureProfileAdapter:
    """
    In-memory adapter that returns pre-registered RawProfileData objects.

    This satisfies the ProfileAcquisition protocol and allows the full
    acquisition pipeline (validation → cache → rate limiter → adapter →
    normalizer → ScrapedProfile) to be exercised without any network calls.

    Usage::

        adapter = FixtureProfileAdapter()
        adapter.register(
            "https://linkedin.com/in/jane-doe",
            RawProfileData(
                profile_url="https://linkedin.com/in/jane-doe",
                name="Jane Doe",
                headline="ML Engineer",
                source="fixture",
            ),
        )
        raw = adapter.acquire("https://linkedin.com/in/jane-doe")

    Error simulation::

        adapter.register_error(
            "https://linkedin.com/in/ghost",
            ProfileNotFoundError("Profile not found"),
        )
    """

    def __init__(self) -> None:
        self._fixtures: dict[str, RawProfileData] = {}
        self._errors: dict[str, ProfileAcquisitionError] = {}

    def register(self, profile_url: str, raw: RawProfileData) -> None:
        """Register a fixture profile for the given URL."""
        self._fixtures[profile_url.strip().rstrip("/")] = raw

    def register_error(
        self, profile_url: str, error: ProfileAcquisitionError
    ) -> None:
        """Register an error to be raised when the URL is acquired."""
        self._errors[profile_url.strip().rstrip("/")] = error

    def acquire(self, profile_url: str) -> RawProfileData:
        """Return a registered fixture or raise the registered error."""
        key = profile_url.strip().rstrip("/")

        if key in self._errors:
            logger.debug("Fixture adapter raising error for %s", key)
            raise self._errors[key]

        if key not in self._fixtures:
            logger.debug("Fixture adapter: not found for %s", key)
            raise ProfileNotFoundError(
                f"No fixture registered for URL: {profile_url!r}"
            )

        logger.debug("Fixture adapter: returning fixture for %s", key)
        return self._fixtures[key]


# ---------------------------------------------------------------------------
# Text adapter — user-pasted profile text
# ---------------------------------------------------------------------------

class TextProfileAdapter:
    """
    Adapter that accepts user-pasted profile text.

    Converts free-form text into RawProfileData using the shared
    parse_profile_text() parser.  No network calls are made.

    This adapter does NOT satisfy the ProfileAcquisition URL-based protocol
    because it does not take a URL as its primary input.  Use
    ProfileScraper.acquire_from_input(ProfileInput(..., source_type="text"))
    as the entry point.

    Usage::

        adapter = TextProfileAdapter()
        raw = adapter.acquire_from_text(
            profile_text="Alex Rivera\\nAI Engineer...",
            profile_url="https://linkedin.com/in/alex",  # optional
        )
    """

    def acquire_from_text(
        self,
        profile_text: str,
        profile_url: Optional[str] = None,
    ) -> RawProfileData:
        """
        Parse pasted profile text and return RawProfileData.

        Args:
            profile_text: Raw pasted text from the profile.
            profile_url: Optional URL for metadata/traceability.

        Returns:
            RawProfileData populated from the parsed text.

        Raises:
            ProfileAcquisitionError: If parsing fails or text is empty.
        """
        if not profile_text or not profile_text.strip():
            raise ProfileAcquisitionError("Profile text must not be empty.")

        try:
            raw = parse_profile_text(
                profile_text,
                profile_url=profile_url,
                source="text",
            )
        except ValueError as exc:
            raise ProfileAcquisitionError(
                f"Failed to parse profile text: {exc}"
            ) from exc
        except Exception as exc:
            raise ProfileAcquisitionError(
                f"Unexpected error parsing profile text: {exc}"
            ) from exc

        logger.debug(
            "TextProfileAdapter: parsed profile name=%r url=%s",
            raw.name,
            profile_url or "(none)",
        )
        return raw

    # Satisfy the ProfileAcquisition protocol by delegating acquire()
    # to acquire_from_text with an empty text body.  In practice callers
    # should always use acquire_from_text; this exists for type-system
    # compatibility only.
    def acquire(self, profile_url: str) -> RawProfileData:  # pragma: no cover
        raise ProfileAcquisitionError(
            "TextProfileAdapter.acquire() requires profile text. "
            "Use acquire_from_text(profile_text, profile_url) instead."
        )
