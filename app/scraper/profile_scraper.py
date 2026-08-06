from app.models.profile_models import ScrapedProfile
from app.scraper.parser import parse_profile
from app.scraper.rate_limiter import RateLimiter

rate_limiter = RateLimiter(delay_seconds=2.0)
#single instance is created for every object - it will keep track of everything 
#unlike creating new instance of rate limiter for every new iteration of request 



def scrape_profile(profile_text: str) -> ScrapedProfile:
    rate_limiter.wait()
    """
    Process profile text and return a structured profile.
    """

    return parse_profile(profile_text)