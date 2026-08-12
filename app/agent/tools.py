"""
Tool definitions and registry for the OutreachIQ custom agent loop.

Two tools are registered:

1. scrape_profile  — thin wrapper around the Phase 1 ProfileScraper
2. generate_message — thin wrapper around the existing generator

Each tool is a plain Python callable.  The custom agent loop in
agent_core.py dispatches calls using AVAILABLE_TOOLS.

TOOL_SCHEMAS contains the JSON Schema descriptions sent to the LLM via
ChatGoogleGenerativeAI.bind_tools().  These are built from the tool
functions themselves using LangChain's StructuredTool helper so the
schema stays in sync with the implementation.

Nothing in this module makes direct network calls or launches browsers.
The acquisition path goes through ProfileScraper → acquisition adapter.
"""

from __future__ import annotations

import json
import logging

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError

from app.llm.gemini_client import generate_message as _generate_message_llm
from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone
from app.models.response_models import OutreachMessage
from app.scraper.adapters import FixtureProfileAdapter
from app.scraper.cache import ProfileCache
from app.scraper.exceptions import ProfileAcquisitionError
from app.scraper.profile_scraper import ProfileScraper
from app.scraper.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default ProfileScraper instance used by the scrape_profile tool.
#
# Uses the FixtureProfileAdapter.  In a real deployment this would be
# replaced by an authorized adapter.  Tests can override _default_scraper
# or pass a scraper directly to the tool functions via the helper below.
# ---------------------------------------------------------------------------

_default_scraper = ProfileScraper(
    acquisition=FixtureProfileAdapter(),
    rate_limiter=RateLimiter(
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
    ),
    cache=ProfileCache(ttl_seconds=300),
)


# ---------------------------------------------------------------------------
# Pydantic arg models (validated before tool execution)
# ---------------------------------------------------------------------------

class ScrapeProfileArgs(BaseModel):
    profile_url: str = Field(
        ...,
        description="The HTTPS URL of the LinkedIn profile to acquire.",
    )


class GenerateMessageArgs(BaseModel):
    profile_name: str = Field(
        ...,
        description="Full name of the profile owner.",
    )
    headline: str = Field(
        default="",
        description="Professional headline from the profile.",
    )
    about: str = Field(
        default="",
        description="About/summary section from the profile.",
    )
    recent_activity: list[str] = Field(
        default_factory=list,
        description="List of recent activity items from the profile.",
    )
    product_description: str = Field(
        ...,
        description="Description of the product or service to pitch.",
    )
    tone: str = Field(
        default="casual",
        description="Outreach tone: 'formal', 'casual', or 'technical'.",
    )


# ---------------------------------------------------------------------------
# Tool implementations — plain callables
# ---------------------------------------------------------------------------

def _run_scrape_profile(profile_url: str) -> dict:
    """
    Acquire and return structured profile data for the given URL.

    Uses the Phase 1 ProfileScraper pipeline:
      URL validation → cache → rate limiter → adapter → normalizer → ScrapedProfile

    Returns a JSON-serializable dict (profile.model_dump() with URL as str).
    On failure, returns a structured error dict so the agent can decide how to proceed.
    """
    logger.info("[Tool] scrape_profile called for %s", profile_url)
    try:
        profile: ScrapedProfile = _default_scraper.scrape(profile_url)
        result = profile.model_dump()
        # Ensure profile_url is a string (Pydantic HttpUrl → str)
        result["profile_url"] = str(result["profile_url"])
        logger.info("[Tool] scrape_profile succeeded for %s", profile_url)
        return {"success": True, "profile": result}
    except ProfileAcquisitionError as exc:
        logger.warning("[Tool] scrape_profile acquisition error: %s", exc)
        return {
            "success": False,
            "error": {"type": "profile_acquisition_error", "message": str(exc)},
        }
    except Exception as exc:
        logger.warning("[Tool] scrape_profile unexpected error: %s", type(exc).__name__)
        return {
            "success": False,
            "error": {"type": "unexpected_error", "message": str(exc)},
        }


def _run_generate_message(
    profile_name: str,
    headline: str,
    about: str,
    recent_activity: list[str],
    product_description: str,
    tone: str = "casual",
) -> dict:
    """
    Generate a personalized outreach message using the existing generator.

    Phase 3: routes through the self-correction service (generate → evaluate →
    optionally regenerate → return best result).  When self-correction is
    disabled via settings, falls back to single-generation behaviour.

    Returns a JSON-serializable dict on success.
    Returns a structured error dict on failure so the agent can recover.
    """
    logger.info("[Tool] generate_message called for profile_name=%s", profile_name)
    try:
        try:
            tone_enum = Tone(tone.lower())
        except ValueError:
            tone_enum = Tone.CASUAL

        profile = ScrapedProfile(
            profile_url="https://linkedin.com/in/unknown",
            name=profile_name,
            headline=headline,
            about=about,
            recent_activity=recent_activity if isinstance(recent_activity, list) else [],
        )

        # Lazy import to avoid circular imports at module load time
        from app.agent.evaluator import evaluate_message
        from app.agent.self_correction import run_self_correction

        sc_result = run_self_correction(
            profile=profile,
            product_description=product_description,
            tone=tone_enum,
            generate_fn=_generate_message_llm,
            evaluate_fn=evaluate_message,
        )

        logger.info(
            "[Tool] generate_message succeeded — attempts=%d improved=%s score=%.2f",
            sc_result.attempt_count,
            sc_result.improved,
            sc_result.final_evaluation.overall_score,
        )
        return {
            "success": True,
            "message": sc_result.final_message.model_dump(),
            "self_correction": {
                "attempt_count": sc_result.attempt_count,
                "improved": sc_result.improved,
                "final_score": sc_result.final_evaluation.overall_score,
                "passed": sc_result.final_evaluation.passed,
            },
        }

    except ValidationError as exc:
        logger.warning("[Tool] generate_message validation error: %s", exc)
        return {
            "success": False,
            "error": {"type": "validation_error", "message": str(exc)},
        }
    except Exception as exc:
        logger.warning("[Tool] generate_message unexpected error: %s", type(exc).__name__)
        return {
            "success": False,
            "error": {"type": "unexpected_error", "message": str(exc)},
        }



# ---------------------------------------------------------------------------
# StructuredTool wrappers — used to build LLM-compatible schemas
# ---------------------------------------------------------------------------

scrape_profile_tool = StructuredTool.from_function(
    func=_run_scrape_profile,
    name="scrape_profile",
    description=(
        "Acquire structured profile information from a profile URL. "
        "Call this FIRST before generate_message when a profile URL is supplied. "
        "Returns profile fields: name, headline, about, recent_activity. "
        "Never call generate_message with a profile URL you have not scraped first."
    ),
    args_schema=ScrapeProfileArgs,
)

generate_message_tool = StructuredTool.from_function(
    func=_run_generate_message,
    name="generate_message",
    description=(
        "Generate a personalized LinkedIn outreach message. "
        "Call this ONLY AFTER scrape_profile has returned the profile data. "
        "Pass the profile fields exactly as returned by scrape_profile. "
        "Returns a structured outreach message with recipient_name, message, "
        "and reason_for_outreach fields."
    ),
    args_schema=GenerateMessageArgs,
)

# ---------------------------------------------------------------------------
# AVAILABLE_TOOLS registry — maps name → callable (plain Python function)
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS: dict[str, callable] = {
    "scrape_profile": _run_scrape_profile,
    "generate_message": _run_generate_message,
}

# List of StructuredTool objects passed to llm.bind_tools()
TOOL_LIST: list[StructuredTool] = [
    scrape_profile_tool,
    generate_message_tool,
]
