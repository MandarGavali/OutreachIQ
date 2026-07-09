from app.models.profile_models import ScrapedProfile
from app.scraper.parser import parse_profile


def scrape_profile(profile_text: str) -> ScrapedProfile:
    """
    Process profile text and return a structured profile.
    """

    return parse_profile(profile_text)