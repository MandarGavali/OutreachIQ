from app.agent.prompts import (
    SYSTEM_PROMPT,
    GOOD_EXAMPLES,
    BAD_EXAMPLES,
)


def build_prompt(
    *,
    profile_name: str,
    headline: str,
    about: str,
    recent_activity: list[str],
    product_description: str,
    tone_instruction: str,
) -> str:
    activity = "\n".join(f"- {item}" for item in recent_activity)

    return f"""
{SYSTEM_PROMPT}

{GOOD_EXAMPLES}

{BAD_EXAMPLES}

Tone Instructions:
{tone_instruction}

Profile Information

Name:
{profile_name}

Headline:
{headline}

About:
{about}

Recent Activity:
{activity}

Product / Service:
{product_description}

Write one personalized LinkedIn outreach message.
"""