from app.scraper.profile_scraper import scrape_profile


def test_scrape_profile():
    profile_text = """
John Doe
AI Engineer | Generative AI

About
Building AI agents and RAG systems.

Recent Activity
Published a post about RAG.
Discussed LangGraph.
"""

    profile = scrape_profile(
        profile_text=profile_text,
        profile_url="https://linkedin.com/in/john-doe",
    )

    assert profile.name == "John Doe"
    assert profile.headline == "AI Engineer | Generative AI"
    assert profile.about == "Building AI agents and RAG systems."
    assert len(profile.recent_activity) == 2