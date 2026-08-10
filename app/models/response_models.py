from pydantic import BaseModel, Field


class OutreachMessage(BaseModel):
    recipient_name: str = Field(..., min_length=2, max_length=100)
    message: str = Field(..., min_length=50, max_length=1000)
    reason_for_outreach: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Why this message fits the recipient.",
    )


class BatchResponse(BaseModel):
    results: list[OutreachMessage] = Field(
        default_factory=list
    )