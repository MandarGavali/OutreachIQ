"""
Concrete profile acquisition adapters for OutreachIQ V2.

This module ships two adapters:

1. FixtureProfileAdapter
   A deterministic, in-memory adapter for testing and development.
   Register fixture profiles by URL and it returns them instantly.
   This is the *correct* adapter for the current phase: we do not
   have a permitted real-time data source, and we do NOT implement
   unauthorized scraping.

2. TextProfileAdapter
   Wraps the existing V1/parser.py pathway so legacy callers that
   supply pasted profile text can still flow through the new
   acquisition interface.

IMPORTANT — What is NOT here:
  - No CAPTCHA bypass
  - No anti-bot browser fingerprint spoofing
  - No automated session harvesting
  - No proxy rotation for evasion
  - No unauthorized LinkedIn DOM scraping at scale

The browser_manager / Playwright infrastructure in the repository is
preserved for authorized browser workflows (e.g., authenticated human-
assisted sessions) and can be injected into a future authorized adapter
when a permitted data source is available.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.scraper.acquisition import ProfileAcquisition, RawProfileData
from app.scraper.exceptions import (
    ProfileAcquisitionError,
    ProfileNotFoundError,
    ProfileTimeoutError,
)
from app.scraper.parser import parse_profile

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
# Text adapter — wraps the V1 parser pathway
# ---------------------------------------------------------------------------

class TextProfileAdapter:
    """
    Adapter that accepts pasted profile text and converts it via the
    existing parser.py into RawProfileData.

    This preserves the V1 / current API pathway where profile_url
    contains the LinkedIn URL and the caller supplies raw profile text.

    The adapter does NOT make any network requests.

    Usage::

        adapter = TextProfileAdapter()
        raw = adapter.acquire_from_text(
            profile_text="Jane Doe\\nML Engineer\\n...",
            profile_url="https://linkedin.com/in/jane-doe",
        )
    """

    def acquire_from_text(
        self, profile_text: str, profile_url: str
    ) -> RawProfileData:
        """
        Parse pasted profile text and return RawProfileData.

        Args:
            profile_text: Raw pasted text from the profile page.
            profile_url: The canonical profile URL.

        Returns:
            RawProfileData populated from the parsed text.

        Raises:
            ProfileAcquisitionError: If parsing fails.
        """
        try:
            scraped = parse_profile(profile_text, profile_url)
        except Exception as exc:
            raise ProfileAcquisitionError(
                f"Failed to parse profile text: {exc}"
            ) from exc

        return RawProfileData(
            profile_url=profile_url,
            name=scraped.name,
            headline=scraped.headline,
            about=scraped.about or "",
            recent_activity=list(scraped.recent_activity),
            source="text_paste",
            fetched_at=datetime.now(timezone.utc),
        )

    # Satisfy the ProfileAcquisition protocol by delegating acquire()
    # to acquire_from_text with an empty text body.  In practice callers
    # should always use acquire_from_text; this exists for type-system
    # compatibility only.
    def acquire(self, profile_url: str) -> RawProfileData:  # pragma: no cover
        raise ProfileAcquisitionError(
            "TextProfileAdapter.acquire() requires profile text. "
            "Use acquire_from_text(profile_text, profile_url) instead."
        )
