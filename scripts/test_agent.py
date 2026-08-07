import sys
from pathlib import Path


# Add project root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agent_core import generate_outreach
from app.models.request_models import OutreachRequest

request = OutreachRequest(
    profile_url="""
John Doe
AI Engineer at OpenAI

About:
Building AI agents using LangChain and FastAPI.

Recent Activity:
Published a post about RAG pipelines.
""",
    product_description="An AI outreach platform that generates personalized LinkedIn messages.",
    tone="casual",
)

response = generate_outreach(request)

print("=" * 50)
print("Type:")
print(type(response))

print("\n" + "=" * 50)
print("Content:")
print(response.content)

print("\n" + "=" * 50)
print("Raw AIMessage:")
print(response)
