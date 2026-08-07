import json

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.tools import (
    scrape_profile,
    generate_outreach as generate_outreach_tool,
)
from app.config import settings
from app.models.request_models import OutreachRequest
from app.models.response_models import OutreachMessage


llm = ChatGoogleGenerativeAI(
    model=settings.MODEL_NAME,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.3,
)


agent = create_agent(
    model=llm,
    tools=[
        scrape_profile,
        generate_outreach_tool,
    ],
    system_prompt="""
You are an expert LinkedIn outreach assistant.

You have access to two tools:

1. scrape_profile
   - Use this FIRST to extract structured information from the supplied profile.

2. generate_outreach
   - Use this ONLY AFTER scrape_profile.
   - Pass the extracted profile fields together with the product description and tone.

Always call the tools.
Never invent profile information.
Never skip scrape_profile.
""",
)


def generate_outreach(request: OutreachRequest) -> OutreachMessage:
    """
    Execute the LangChain agent and return the structured
    OutreachMessage produced by the generate_outreach tool.
    """

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Generate a personalized LinkedIn outreach message.

Profile:
{request.profile_url}

Product:
{request.product_description}

Tone:
{request.tone}
""",
                }
            ]
        }
    )

    # Traverse messages from newest to oldest and find the
    # output of the generate_outreach tool.
    for message in reversed(response["messages"]):

        if (
            isinstance(message, ToolMessage)
            and message.name == "generate_outreach"
        ):
            return OutreachMessage.model_validate_json(message.content)

    raise RuntimeError(
        "generate_outreach tool did not return a valid response."
    )