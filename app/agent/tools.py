from langchain.tools import tool 

from app.generator.message_builder import build_prompt
from app.generator.tone_templates import CASUAL
from app.llm.gemini_client import generate_message
from app.scraper.parser import parse_profile

@tool
def scrape_profile(profile_url: str) -> dict:
    """
    Temporary implementation:
    profile_url currently contains pasted profile text.
    Later it will contain the actual LinkedIn URL.
    """

    profile = parse_profile(profile_url)

    return profile.model_dump()


# @tool
# def scrape_profile(profile_url: str) -> dict:
#     """
#     Extract structured profile information from raw LinkedIn profile text 
#     """
#     profile = parse_profile(profile_url)
#     return profile.model_dump()
#     #This makes the tool output easy for the agent to consume. into json


from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone

@tool 
def generate_outreach(
    profile_name: str,
    headline: str,
    about: str,
    recent_activity: list[str],
    product_description: str,
    tone: str = "casual",
) -> str:
    """
    Generate a personalized LinkedIn outreach message.
    """
    profile = ScrapedProfile(
        name=profile_name,
        headline=headline,
        about=about,
        recent_activity=recent_activity if isinstance(recent_activity, list) else [],
    )

    try:
        tone_enum = Tone(tone.lower())
    except ValueError:
        tone_enum = Tone.CASUAL

    prompt = build_prompt(
        profile=profile,
        product_description=product_description,
        tone=tone_enum,
    )

    response = generate_message(prompt)
    return response.model_dump_json()
 

