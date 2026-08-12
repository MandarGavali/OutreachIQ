from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Tone(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"


class OutreachRequest(BaseModel):
    profile_url: str
    product_description: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Description of the product or service.",
    )
    tone: Tone = Tone.CASUAL


class BatchRequest(BaseModel):
    requests: list[OutreachRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of outreach requests. Maximum 10 per batch.",
    )