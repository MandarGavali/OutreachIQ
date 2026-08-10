from app.models.profile_models import ScrapedProfile
from app.scraper.parser import parse_profile
from app.scraper.rate_limiter import RateLimiter


rate_limiter = RateLimiter(delay_seconds=2.0)


def scrape_profile(
    profile_text: str,
    profile_url: str,
) -> ScrapedProfile:
    """
    Acquire profile data and convert it into a ScrapedProfile.

    For the MVP, profile_text is provided directly rather than
    performing authenticated LinkedIn scraping.
    """

    rate_limiter.wait()

    if not profile_text.strip():
        raise ValueError("Profile text cannot be empty")

    return parse_profile(
        profile_text,
        profile_url,
    )