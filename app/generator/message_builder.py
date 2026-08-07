# from app.agent.prompts import (
#     SYSTEM_PROMPT,
#     GOOD_EXAMPLES,
#     BAD_EXAMPLES,
# )


# def build_prompt(
#     *,
#     profile_name: str,
#     headline: str,
#     about: str,
#     recent_activity: list[str],
#     product_description: str,
#     tone_instruction: str,
# ) -> str:
#     activity = "\n".join(f"- {item}" for item in recent_activity)

#     return f"""
# {SYSTEM_PROMPT}

# {GOOD_EXAMPLES}

# {BAD_EXAMPLES}

# Tone Instructions:
# {tone_instruction}

# Profile Information

# Name:
# {profile_name}

# Headline:
# {headline}

# About:
# {about}

# Recent Activity:
# {activity}

# Product / Service:
# {product_description}

# Write one personalized LinkedIn outreach message.
# """
from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone


def build_prompt(
    profile: ScrapedProfile,
    product_description: str,
    tone: Tone,
) -> str:
    """
    Builds the complete prompt for generating a personalized
    outreach message.
    """

    return f"""
You are an expert sales copywriter.

Generate a personalized LinkedIn outreach message.

PROFILE INFORMATION
-------------------
Name: {profile.name}
Headline: {profile.headline}
Summary:
{profile.about or ''}

Recent Activity:
{profile.recent_activity}

PRODUCT / SERVICE
-----------------
{product_description}

TONE
----
{tone.value}

INSTRUCTIONS
------------
- Personalize the opening using the profile information.
- Mention something specific from the profile.
- Keep the message concise (100-150 words).
- Avoid generic compliments.
- End with a soft call-to-action.

Return ONLY valid JSON in the following format:

{{
    "recipient_name": "...",
    "message": "...",
    "reason_for_outreach": "..."
}}
"""