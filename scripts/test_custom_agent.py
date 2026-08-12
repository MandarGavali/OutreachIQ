"""
Manual integration demo for the OutreachIQ V2 custom agent loop.

Run:
    python -m scripts.test_custom_agent

This script demonstrates the custom tool-calling loop operating step-by-step.
It uses the FixtureProfileAdapter (no real LinkedIn scraping) and the real
Gemini LLM (requires GOOGLE_API_KEY in .env).

The script prints each turn and tool call so the agent loop is clearly visible.

Do NOT include this in pytest — it requires a real API key.
"""

import json
import logging

from app.agent.agent_core import OutreachAgent
from app.agent.tools import TOOL_LIST, AVAILABLE_TOOLS
from app.models.request_models import OutreachRequest, Tone
from app.scraper.acquisition import RawProfileData
from app.scraper.adapters import FixtureProfileAdapter
from app.scraper.cache import ProfileCache
from app.scraper.profile_scraper import ProfileScraper
from app.scraper.rate_limiter import RateLimiter

# Set up visible logging for this demo
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

PROFILE_URL = "https://linkedin.com/in/jane-demo"
PRODUCT_DESC = (
    "OutreachIQ is an AI-powered outreach assistant that generates personalized, "
    "non-spammy LinkedIn messages based on real profile data and your product context."
)


def main() -> None:
    print("=" * 60)
    print("  OutreachIQ V2 — Custom Agent Loop Demo")
    print("=" * 60)
    print()

    # Register a fixture profile so we don't need real LinkedIn access
    adapter = FixtureProfileAdapter()
    adapter.register(
        PROFILE_URL,
        RawProfileData(
            profile_url=PROFILE_URL,
            name="Jane Demo",
            headline="ML Engineer | Building AI evaluation frameworks",
            about=(
                "I help ML teams build reliable model evaluation pipelines. "
                "Currently working on automated drift detection."
            ),
            recent_activity=[
                "Shared a post about LLM evaluation metrics",
                "Commented on retrieval quality in RAG systems",
            ],
            source="demo_fixture",
        ),
    )

    test_scraper = ProfileScraper(
        acquisition=adapter,
        rate_limiter=RateLimiter(min_delay_seconds=0.0, max_delay_seconds=0.0),
        cache=ProfileCache(ttl_seconds=60),
    )

    # Patch the default scraper used by the tool
    import app.agent.tools as tools_module
    tools_module._default_scraper = test_scraper

    print(f"Profile URL : {PROFILE_URL}")
    print(f"Product     : {PRODUCT_DESC[:80]}...")
    print(f"Tone        : casual")
    print()
    print("Starting agent loop...")
    print("-" * 60)

    request = OutreachRequest(
        profile_url=PROFILE_URL,
        product_description=PRODUCT_DESC,
        tone=Tone.CASUAL,
    )

    try:
        agent = OutreachAgent(max_turns=6)
        result = agent.run(request)
    except Exception as exc:
        print(f"\n[AGENT ERROR] {type(exc).__name__}: {exc}")
        return

    print()
    print("=" * 60)
    print("  FINAL RESULT")
    print("=" * 60)
    print(f"Recipient       : {result.recipient_name}")
    print(f"Reason          : {result.reason_for_outreach}")
    print()
    print("Message:")
    print(result.message)
    print()


if __name__ == "__main__":
    main()
