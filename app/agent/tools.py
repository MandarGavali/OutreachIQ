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

from datetime import datetime, timezone

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError

from app.llm.gemini_client import generate_message as _generate_message_llm
from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone
from app.models.response_models import OutreachMessage
from app.scraper.acquisition import ProfileInput, RawProfileData
from app.scraper.adapters import FixtureProfileAdapter, TextProfileAdapter
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
#
# The adapter is pre-loaded with a demo profile so the final_demo script
# (and any other caller that uses DEMO_PROFILE_URL) can run the complete
# pipeline without network access.
# ---------------------------------------------------------------------------

# Public constant so callers (demo scripts, tests) can reference the
# pre-registered URL without hard-coding it in multiple places.
DEMO_PROFILE_URL: str = "https://linkedin.com/in/alex-rivera"

_fixture_adapter = FixtureProfileAdapter()
_fixture_adapter.register(
    DEMO_PROFILE_URL,
    RawProfileData(
        profile_url=DEMO_PROFILE_URL,
        name="Alex Rivera",
        headline="Head of Growth at TechScale — B2B SaaS | Revenue & Pipeline Strategy",
        about=(
            "I lead growth at TechScale, where I help B2B SaaS companies "
            "build scalable outbound pipelines without burning out their SDR teams. "
            "Previously scaled GTM at two Y Combinator companies from $0 to Series B. "
            "Passionate about data-driven personalization and cutting through inbox noise."
        ),
        recent_activity=[
            "Shared a post on why spray-and-pray cold outreach is dead in 2025",
            "Commented on a LinkedIn thread about AI-assisted SDR workflows",
            "Published an article: '5 outreach frameworks that actually get replies'",
        ],
        source="demo_fixture",
        fetched_at=datetime(2025, 8, 14, 0, 0, 0, tzinfo=timezone.utc),
    ),
)

_default_scraper = ProfileScraper(
    acquisition=_fixture_adapter,
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
    profile_source: str = Field(
        default="fixture",
        description=(
            "Acquisition source type. "
            "'fixture' — look up a pre-registered profile by URL (requires profile_url). "
            "'text' — parse user-pasted profile text (requires profile_text). "
            "Default: 'fixture'."
        ),
    )
    profile_url: str = Field(
        default="",
        description=(
            "The HTTPS URL of the LinkedIn profile. "
            "Required when profile_source='fixture'."
        ),
    )
    profile_text: str = Field(
        default="",
        description=(
            "Raw user-pasted profile text. "
            "Required when profile_source='text'. "
            "Include Name, Headline, About, and Recent Activity sections."
        ),
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

def _run_scrape_profile(
    profile_source: str = "fixture",
    profile_url: str = "",
    profile_text: str = "",
) -> dict:
    """
    Acquire and return structured profile data.

    Two acquisition modes:

      profile_source='fixture' (default)
        Look up a pre-registered profile by profile_url.
        Pipeline: URL validation → cache → adapter → normalizer → ScrapedProfile

      profile_source='text'
        Parse user-pasted profile text via TextProfileAdapter.
        No network calls.  No rate limiting.  No cache.
        Requires profile_text to be non-empty.

    Returns a JSON-serializable dict on success.
    Returns a structured error dict on failure so the agent can recover.
    """
    logger.info(
        "[Tool] scrape_profile called  source=%s  url=%r",
        profile_source,
        profile_url or "(none)",
    )
    try:
        source = (profile_source or "fixture").strip().lower()

        if source == "text":
            if not profile_text or not profile_text.strip():
                return {
                    "success": False,
                    "error": {
                        "type": "missing_profile_text",
                        "message": (
                            "profile_text must be non-empty when "
                            "profile_source='text'."
                        ),
                    },
                }
            profile_input = ProfileInput(
                source_type="text",
                profile_text=profile_text,
                profile_url=profile_url or None,
            )
            profile: ScrapedProfile = _default_scraper.acquire_from_input(profile_input)
        else:
            # 'fixture' (default) — URL-based lookup
            if not profile_url or not profile_url.strip():
                return {
                    "success": False,
                    "error": {
                        "type": "missing_profile_url",
                        "message": (
                            "profile_url must be non-empty when "
                            "profile_source='fixture'."
                        ),
                    },
                }
            logger.info("[Tool] scrape_profile called for %s", profile_url)
            profile = _default_scraper.scrape(profile_url)

        result = profile.model_dump()
        # Ensure profile_url is a plain string (may be None)
        if result.get("profile_url") is not None:
            result["profile_url"] = str(result["profile_url"])
        logger.info("[Tool] scrape_profile succeeded for %s", profile_url or profile.name)
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
            profile_url=None,  # generate_message does not require a URL
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
        "Acquire structured profile information from a profile source. "
        "Supports two modes: "
        "(1) profile_source='fixture' (default): look up a pre-registered profile "
        "by profile_url — call this FIRST when a URL is supplied; "
        "(2) profile_source='text': parse user-pasted profile text via profile_text — "
        "call this when the user has pasted their profile text directly. "
        "Returns profile fields: name, headline, about, recent_activity. "
        "Never call generate_message without first calling scrape_profile."
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
