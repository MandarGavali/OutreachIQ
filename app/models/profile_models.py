# app/models/profile_models.py

from pydantic import BaseModel, Field, HttpUrl


class ScrapedProfile(BaseModel):
    profile_url: HttpUrl

    name: str = Field(
        min_length=1,
        max_length=100
    )

    headline: str = Field(
        default="",
        max_length=300
    )

    about: str = Field(
        default="",
        max_length=3000
    )

    recent_activity: list[str] = Field(
        default_factory=list
    )