from pydantic import BaseModel, Field


class ScrapedProfile(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    headline: str = Field(..., min_length=5, max_length=200)
    about: str | None = Field(
        default=None,
        max_length=2000,
        description="Public profile summary or bio.",
    )
    recent_activity: list[str] = Field(
        default_factory=list,
        description="Recent public posts or activities.",
    )