import pytest
from langchain_core.messages import ToolMessage

from app.agent import agent_core
from app.models.request_models import OutreachRequest, Tone
from app.models.response_models import OutreachMessage


def test_generate_outreach_returns_outreach_message(monkeypatch):
    request = OutreachRequest(
        profile_url="John Doe\nAI Engineer at OpenAI\nBuilding AI agents using LangChain.",
        product_description="AI automation platform for building intelligent business workflows.",
        tone=Tone.CASUAL,
    )

    expected_message = OutreachMessage(
        recipient_name="John Doe",
        message=(
            "Hi John, I noticed your work building AI agents with LangChain. "
            "I thought our AI automation platform might be relevant to the "
            "kind of workflows you're working on."
        ),
        reason_for_outreach=(
            "Their work with AI agents is relevant."
        ),
    )

    tool_message = ToolMessage(
        content=expected_message.model_dump_json(),
        name="generate_outreach",
        tool_call_id="test-call",
    )

    def mock_invoke(_):
        return {
            "messages": [
                tool_message
            ]
        }

    monkeypatch.setattr(
        agent_core.agent,
        "invoke",
        mock_invoke,
    )

    result = agent_core.generate_outreach(request)

    assert isinstance(result, OutreachMessage)
    assert result.recipient_name == "John Doe"
    assert result.message == expected_message.message


def test_generate_outreach_raises_when_tool_output_missing(monkeypatch):
    request = OutreachRequest(
        profile_url="John Doe\nAI Engineer",
        product_description="AI automation platform for building intelligent business workflows.",
        tone=Tone.CASUAL,
    )

    def mock_invoke(_):
        return {
            "messages": []
        }

    monkeypatch.setattr(
        agent_core.agent,
        "invoke",
        mock_invoke,
    )

    with pytest.raises(RuntimeError):
        agent_core.generate_outreach(request)


def test_generate_outreach_propagates_agent_error(monkeypatch):
    request = OutreachRequest(
        profile_url="John Doe\nAI Engineer",
        product_description="AI automation platform for building intelligent business workflows.",
        tone=Tone.CASUAL,
    )

    def mock_invoke(_):
        raise RuntimeError("Agent failed")

    monkeypatch.setattr(
        agent_core.agent,
        "invoke",
        mock_invoke,
    )

    with pytest.raises(RuntimeError, match="Agent failed"):
        agent_core.generate_outreach(request)