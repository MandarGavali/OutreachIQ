from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.tools import (
    scrape_profile,
    generate_outreach,
)
from app.config import settings


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.3,
)

agent = create_agent(
    model=llm,
    tools=[
        scrape_profile,
        generate_outreach,
    ],
    system_prompt="""
You are an expert LinkedIn outreach assistant.

Always use the available tools.

Never invent profile information.

Generate only personalized outreach messages.
""",
)