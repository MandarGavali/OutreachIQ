import pytest
from pydantic import ValidationError

from app.models.profile_models import ScrapedProfile


def test_complete_profile():
    profile = ScrapedProfile(
        profile_url="https://linkedin.com/in/john-doe",
        name="John Doe",
        headline="AI Engineer | Generative AI | RAG",
        about="Building AI agents and production RAG systems.",
        recent_activity=[
            "Published a post about RAG evaluation",
            "Discussed agentic workflows with LangGraph",
        ],
    )

    assert profile.name == "John Doe"
    assert profile.headline == "AI Engineer | Generative AI | RAG"
    assert len(profile.recent_activity) == 2


def test_profile_with_missing_optional_fields():
    profile = ScrapedProfile(
        profile_url="https://linkedin.com/in/john-doe",
        name="John Doe",
    )

    assert profile.name == "John Doe"
    assert profile.headline == ""
    assert profile.about == ""
    assert profile.recent_activity == []


def test_profile_rejects_invalid_name():
    with pytest.raises(ValidationError):
        ScrapedProfile(
            profile_url="https://linkedin.com/in/john-doe",
            name="",
        )


def test_profile_rejects_long_name():
    with pytest.raises(ValidationError):
        ScrapedProfile(
            profile_url="https://linkedin.com/in/john-doe",
            name="A" * 101,
        )


def test_profile_rejects_long_headline():
    with pytest.raises(ValidationError):
        ScrapedProfile(
            profile_url="https://linkedin.com/in/john-doe",
            name="John Doe",
            headline="A" * 301,
        )


def test_profile_rejects_long_about():
    with pytest.raises(ValidationError):
        ScrapedProfile(
            profile_url="https://linkedin.com/in/john-doe",
            name="John Doe",
            about="A" * 3001,
        )