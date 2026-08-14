"""
Profile normalization layer for OutreachIQ V2.

Takes a RawProfileData object (from any acquisition adapter) and
produces the canonical ScrapedProfile Pydantic model consumed by the
agent and generator.

Normalization responsibilities:
  - Strip leading/trailing whitespace
  - Collapse repeated internal whitespace where safe
  - Enforce field-length limits from the ScrapedProfile schema
  - Deduplicate activity entries while preserving order
  - Remove empty activity entries
  - Validate that name is present and non-empty
  - Return the canonical ScrapedProfile

Normalization is data cleaning, not content generation.
Missing fields become their schema defaults; nothing is invented.
"""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

from app.models.profile_models import ScrapedProfile
from app.scraper.acquisition import RawProfileData
from app.scraper.exceptions import ProfileValidationError

logger = logging.getLogger(__name__)

# Match ScrapedProfile field limits
_MAX_NAME_LEN = 100
_MAX_HEADLINE_LEN = 300
_MAX_ABOUT_LEN = 3000
_MAX_ACTIVITY_ITEMS = 20
_MAX_ACTIVITY_ITEM_LEN = 500


def _clean(text: str) -> str:
    """Strip whitespace and collapse internal runs of whitespace."""
    text = text.strip()
    # Collapse multiple spaces/tabs on the same line (not newlines)
    text = re.sub(r"[^\S\n]+", " ", text)
    return text


def _truncate(text: str, max_len: int) -> str:
    """Hard-truncate text to max_len characters."""
    if len(text) > max_len:
        logger.warning(
            "Field truncated from %d to %d characters", len(text), max_len
        )
    return text[:max_len]


def normalize_profile(raw: RawProfileData) -> ScrapedProfile:
    """
    Convert RawProfileData into the canonical ScrapedProfile.

    Args:
        raw: Raw data from an acquisition adapter.

    Returns:
        A validated ScrapedProfile instance.

    Raises:
        ProfileValidationError: If the name is missing or normalization
                                 produces invalid output.
    """
    logger.debug(
        "Normalizing profile from source=%s url=%s",
        raw.source,
        raw.profile_url or "(none)",
    )

    # --- name ---
    name = _clean(raw.name)
    if not name:
        raise ProfileValidationError(
            "Profile name is required but was empty after normalization."
        )
    name = _truncate(name, _MAX_NAME_LEN)

    # --- headline ---
    headline = _clean(raw.headline)
    headline = _truncate(headline, _MAX_HEADLINE_LEN)

    # --- about ---
    about_raw = raw.about.strip()
    if about_raw:
        # Preserve paragraph boundaries; only collapse intra-line spaces
        about_lines = [_clean(line) for line in about_raw.splitlines()]
        about = "\n".join(about_lines).strip()
    else:
        about = ""
    about = _truncate(about, _MAX_ABOUT_LEN)

    # --- recent_activity ---
    seen: set[str] = set()
    activities: list[str] = []
    for item in raw.recent_activity:
        cleaned = _clean(item)
        if not cleaned:
            continue  # drop empty entries
        truncated = _truncate(cleaned, _MAX_ACTIVITY_ITEM_LEN)
        if truncated in seen:
            continue  # deduplicate
        seen.add(truncated)
        activities.append(truncated)
        if len(activities) >= _MAX_ACTIVITY_ITEMS:
            break

    try:
        profile = ScrapedProfile(
            profile_url=raw.profile_url,  # Optional[str] — may be None for text/PDF
            name=name,
            headline=headline,
            about=about,
            recent_activity=activities,
        )
    except ValidationError as exc:
        raise ProfileValidationError(
            f"Profile failed Pydantic validation: {exc}"
        ) from exc

    logger.debug("Normalization complete for url=%s", raw.profile_url or "(none)")
    return profile
