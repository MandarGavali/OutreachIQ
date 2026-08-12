"""
Acquisition interface and RawProfileData for OutreachIQ V2.

Defines the contract that every profile data provider must satisfy.
The rest of the application depends on this interface, not on any
specific LinkedIn scraper, API client, or fixture loader.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Raw data model
# ---------------------------------------------------------------------------

class RawProfileData(BaseModel):
    """
    Internal representation of profile data before normalization.

    This is an acquisition-layer artifact and must NOT be passed beyond
    the normalizer.  Do not store passwords, cookies, or tokens here.
    """

    profile_url: str
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

    Implementations may use HTTP APIs, authorized browser sessions,
    user-supplied fixture files, or any other permitted source.
    They must never bypass platform access controls.
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
