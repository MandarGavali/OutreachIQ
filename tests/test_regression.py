import os
import csv
import json
import tempfile
import pytest

from app.models.request_models import OutreachRequest, Tone
from app.models.response_models import OutreachMessage
from app.export.csv_exporter import export_to_csv


def test_csv_export_functionality():
    """Test the original CSV export functionality from main branch."""
    messages = [
        OutreachMessage(
            recipient_name="Alice",
            message="Hi Alice, this is message 1. " + "A" * 50,
            reason_for_outreach="Reason 1 is sufficiently long for validation."
        ),
        OutreachMessage(
            recipient_name="Bob",
            message="Hi Bob, this is message 2. " + "B" * 50,
            reason_for_outreach="Reason 2 is sufficiently long for validation."
        )
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_export.csv")
        result_path = export_to_csv(messages, output_file)
        
        assert os.path.exists(result_path)
        
        with open(result_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Headers
            assert rows[0] == ["Recipient Name", "Reason For Outreach", "Message"]
            
            # Row 1
            assert rows[1][0] == "Alice"
            assert rows[1][1] == "Reason 1 is sufficiently long for validation."
            assert rows[1][2].startswith("Hi Alice")
            
            # Row 2
            assert rows[2][0] == "Bob"
            assert rows[2][1] == "Reason 2 is sufficiently long for validation."
            assert rows[2][2].startswith("Hi Bob")


# ===========================================================================
# Regression: 'list' object has no attribute 'strip'
#
# ChatGoogleGenerativeAI can return response.content as a list of content-part
# dicts (e.g. [{'type': 'text', 'text': '...'}]) instead of a plain str.
# _parse_final_response previously called text.strip() unconditionally,
# crashing when content was a list.
# ===========================================================================

from app.agent.agent_core import OutreachAgent, _coerce_content_to_str
from app.agent.exceptions import AgentError


class _MockLLM:
    """Minimal mock chat model for regression tests."""

    def __init__(self, responses):
        self._responses = responses
        self._call_count = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        resp = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return resp


_VALID_MSG = OutreachMessage(
    recipient_name="Alex Rivera",
    message=(
        "Hi Alex, I read your article on outreach frameworks — really sharp thinking. "
        "Our platform uses AI to ground every message in real profile data so reps "
        "stop sending generic openers. Happy to share a quick walkthrough if useful."
    ),
    reason_for_outreach="Alex writes about outreach and leads growth; direct product fit.",
)

_VALID_REQ = OutreachRequest(
    profile_url="https://linkedin.com/in/alex-rivera",
    product_description="OutreachIQ AI platform for personalised non-spammy sales outreach." * 2,
    tone=Tone.CASUAL,
)


# ---- Unit tests for _coerce_content_to_str ----

def test_coerce_plain_str_unchanged():
    assert _coerce_content_to_str("hello") == "hello"


def test_coerce_empty_str():
    assert _coerce_content_to_str("") == ""


def test_coerce_list_of_text_parts():
    content = [{"type": "text", "text": "Hello, "}, {"type": "text", "text": "world!"}]
    assert _coerce_content_to_str(content) == "Hello, world!"


def test_coerce_list_with_non_text_parts_skipped():
    content = [
        {"type": "image_url", "image_url": "http://example.com/img.png"},
        {"type": "text", "text": "Only text matters."},
    ]
    assert _coerce_content_to_str(content) == "Only text matters."


def test_coerce_list_of_plain_strings():
    """list of bare strings (not dicts) should also be joined."""
    content = ["part one ", "part two"]
    assert _coerce_content_to_str(content) == "part one part two"


def test_coerce_empty_list():
    assert _coerce_content_to_str([]) == ""


def test_coerce_unexpected_type_falls_back_to_str():
    assert _coerce_content_to_str(42) == "42"


# ---- Integration: agent does not crash when LLM returns list content ----

def test_agent_handles_list_content_response():
    """
    Regression for: 'list' object has no attribute 'strip'

    When ChatGoogleGenerativeAI returns response.content as a list of
    content-part dicts, the agent must normalise it to a str and parse
    the OutreachMessage correctly — it must NOT raise AttributeError.
    """
    from langchain_core.messages import AIMessage

    valid_json = _VALID_MSG.model_dump_json()

    # Simulate a Gemini response where .content is a list of parts
    list_content_response = AIMessage(
        content=[{"type": "text", "text": valid_json}],
        tool_calls=[],
    )

    mock_llm = _MockLLM([list_content_response])
    agent = OutreachAgent(llm=mock_llm, max_turns=3)
    result = agent.run(_VALID_REQ)

    assert isinstance(result, OutreachMessage)
    assert result.recipient_name == "Alex Rivera"


def test_agent_handles_multipart_list_content():
    """
    When response.content is a list with multiple text parts,
    they should be joined and parsed correctly.
    """
    from langchain_core.messages import AIMessage

    # Split the JSON across two parts — unusual but must not crash
    full_json = _VALID_MSG.model_dump_json()
    half = len(full_json) // 2
    part1, part2 = full_json[:half], full_json[half:]

    list_content_response = AIMessage(
        content=[{"type": "text", "text": part1}, {"type": "text", "text": part2}],
        tool_calls=[],
    )

    mock_llm = _MockLLM([list_content_response])
    agent = OutreachAgent(llm=mock_llm, max_turns=3)
    result = agent.run(_VALID_REQ)

    assert isinstance(result, OutreachMessage)


def test_agent_raises_on_empty_list_content():
    """Empty list content → AgentError, not AttributeError."""
    from langchain_core.messages import AIMessage

    empty_response = AIMessage(content=[], tool_calls=[])
    mock_llm = _MockLLM([empty_response])
    agent = OutreachAgent(llm=mock_llm, max_turns=1)

    with pytest.raises(Exception):  # AgentError or AgentMaxTurnsError
        agent.run(_VALID_REQ)


# ---- DEMO_PROFILE_URL fixture is registered ----

def test_demo_profile_url_is_registered():
    """DEMO_PROFILE_URL must be resolvable by the default scraper without network."""
    from app.agent.tools import DEMO_PROFILE_URL, _run_scrape_profile
    result = _run_scrape_profile(profile_url=DEMO_PROFILE_URL)
    assert result["success"] is True
    assert result["profile"]["name"] == "Alex Rivera"
    assert result["profile"]["headline"] != ""
