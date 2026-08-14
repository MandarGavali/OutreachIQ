"""
Request models for the OutreachIQ API.

OutreachRequest
---------------
Accepts either a profile_url (for fixture-based lookup) or profile_text
(for user-pasted text input).  At least one must be provided.

PDF input uses a separate multipart endpoint (/generate-from-pdf) and
is not part of this JSON request model.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Tone(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"


class OutreachRequest(BaseModel):
    # profile_url is now optional — text input does not require a URL.
    # Still accepted for fixture-based lookups and backward compatibility.
    profile_url: Optional[str] = Field(
        default=None,
        description=(
            "LinkedIn profile URL. "
            "Used for fixture-based profile lookup. "
            "Either profile_url or profile_text must be provided."
        ),
    )

    # New: user-pasted profile text input.
    profile_text: Optional[str] = Field(
        default=None,
        min_length=10,
        description=(
            "Raw profile text pasted by the user. "
            "Either profile_url or profile_text must be provided."
        ),
    )

    product_description: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Description of the product or service.",
    )
    tone: Tone = Tone.CASUAL

    @model_validator(mode="after")
    def _require_profile_source(self) -> "OutreachRequest":
        has_url = bool(self.profile_url and self.profile_url.strip())
        has_text = bool(self.profile_text and self.profile_text.strip())
        if not has_url and not has_text:
            raise ValueError(
                "Either 'profile_url' or 'profile_text' must be provided."
            )
        return self


class BatchRequest(BaseModel):
    requests: list[OutreachRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of outreach requests. Maximum 10 per batch.",
    )