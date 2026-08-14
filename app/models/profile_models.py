# app/models/profile_models.py
"""
Canonical profile data model for OutreachIQ.

ScrapedProfile is the single shared representation consumed by the
Agent, Generator, and Evaluator.  All acquisition adapters must
eventually produce a ScrapedProfile (via RawProfileData → normalizer).

profile_url is optional: users may supply profile text or a PDF without
a corresponding URL.  When no URL is available, the field is None.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ScrapedProfile(BaseModel):
    # URL is optional — text/PDF inputs may not have a URL.
    # When present, it is stored as-is for metadata/traceability only.
    profile_url: Optional[str] = Field(
        default=None,
        description="Profile URL, if known.  None for text/PDF inputs.",
    )

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    headline: str = Field(
        default="",
        max_length=300,
    )

    about: str = Field(
        default="",
        max_length=3000,
    )

    recent_activity: list[str] = Field(
        default_factory=list,
    )