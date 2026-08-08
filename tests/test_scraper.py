import pytest

from app.scraper.parser import parse_profile


def test_parse_valid_profile():
    profile_text = """
    John Doe
    AI Engineer at OpenAI
    About
    Building AI agents using LangChain.
    Recent Activity
    Published a post about RAG.
    """

    profile = parse_profile(profile_text)

    assert profile.name == "John Doe"
    assert profile.headline == "AI Engineer at OpenAI"
    assert profile.about == "Building AI agents using LangChain."
    assert profile.recent_activity == [
        "Published a post about RAG."
    ]


def test_missing_about_section():
    profile_text = """
    John Doe
    AI Engineer at OpenAI
    Recent Activity
    Published a post about RAG.
    """

    profile = parse_profile(profile_text)

    assert profile.name == "John Doe"
    assert profile.headline == "AI Engineer at OpenAI"
    assert profile.about is None
    assert profile.recent_activity == [
        "Published a post about RAG."
    ]


def test_missing_recent_activity():
    profile_text = """
    John Doe
    AI Engineer at OpenAI
    About
    Building AI agents using LangChain.
    """

    profile = parse_profile(profile_text)

    assert profile.name == "John Doe"
    assert profile.headline == "AI Engineer at OpenAI"
    assert profile.about == "Building AI agents using LangChain."
    assert profile.recent_activity == []


def test_empty_profile_raises_error():
    with pytest.raises(IndexError):
        parse_profile("")


def test_malformed_profile():
    profile_text = """
    John Doe
    """

    with pytest.raises(IndexError):
        parse_profile(profile_text)