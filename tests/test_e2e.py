import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.models.response_models import OutreachMessage
from app.models.evaluation_models import EvaluationResult

client = TestClient(app)

@pytest.fixture
def mock_pipeline(monkeypatch):
    """
    Mock the lowest-level external boundaries (LLM calls and HTTP scraper calls)
    so the entire internal architecture (API -> Agent -> Tools -> Cache -> Generator -> Evaluator)
    runs end-to-end locally.
    """
    # 1. Mock the Scraper Adapter (so we don't actually fetch from LinkedIn or fail)
    # The default FixtureProfileAdapter already returns deterministic data for specific URLs,
    # but we can explicitly use it or just mock it. We will use the built-in fixture mechanism
    # by using the URL for John Doe from FixtureProfileAdapter.
    # "https://linkedin.com/in/johndoe" -> returns a valid ScrapedProfile.

    # 2. Mock the LLM Generator
    def mock_generate_message_llm(prompt: str) -> OutreachMessage:
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is an E2E generated message based on your profile. " + "A" * 50,
            reason_for_outreach="E2E test reason that meets validation."
        )

    monkeypatch.setattr("app.agent.tools._generate_message_llm", mock_generate_message_llm)
    # Also mock the raw gemini client just in case
    monkeypatch.setattr("app.llm.gemini_client.generate_message", mock_generate_message_llm)

    # 3. Mock the LLM Evaluator for self-correction
    def mock_evaluate_message(*args, **kwargs) -> EvaluationResult:
        return EvaluationResult(
            personalization=9.0,
            relevance=9.0,
            specificity=9.0,
            naturalness=9.0,
            non_spamminess=9.0,
            factuality=9.0,
            feedback="Great E2E message.",
            improvement_suggestions=[],
            evidence_used=["E2E evidence"],
            passed=True
        )

    monkeypatch.setattr("app.agent.evaluator.evaluate_message", mock_evaluate_message)
    
    # 4. Mock the agent's LLM routing so it automatically decides to call the tools in sequence.
    # The custom agent loop calls ChatGoogleGenerativeAI. We need to mock its behavior.
    from langchain_core.messages import AIMessage, ToolCall
    
    call_counts = {"invoke": 0}
    def mock_agent_invoke(*args, **kwargs):
        call_counts["invoke"] += 1
        turn = call_counts["invoke"]
        
        if turn == 1:
            # Turn 1: LLM decides to call scrape_profile
            return AIMessage(
                content="",
                tool_calls=[ToolCall(name="scrape_profile", args={"profile_url": "https://linkedin.com/in/johndoe"}, id="call_1")]
            )
        elif turn == 2:
            # Turn 2: LLM decides to call generate_message
            return AIMessage(
                content="",
                tool_calls=[ToolCall(
                    name="generate_message", 
                    args={
                        "profile_name": "John Doe",
                        "headline": "Software Engineer",
                        "about": "Likes coding.",
                        "recent_activity": [],
                        "product_description": "A very good product that requires a long description.",
                        "tone": "casual"
                    }, 
                    id="call_2"
                )]
            )
        else:
            # Turn 3: LLM provides final answer
            return AIMessage(
                content='{"recipient_name": "John", "message": "Hi John, this is an E2E generated message based on your profile. AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "reason_for_outreach": "E2E test reason that meets validation."}'
            )
            
    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI.invoke", mock_agent_invoke)

    return call_counts

def test_single_generation_e2e(mock_pipeline):
    """Test a full successful single request flow."""
    response = client.post("/generate", json={
        "profile_url": "https://linkedin.com/in/johndoe",
        "product_description": "A very good product that requires a long description.",
        "tone": "casual"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_name"] == "John"
    assert "E2E generated message" in data["message"]

def test_batch_generation_e2e(mock_pipeline):
    """Test a full successful batch request flow."""
    response = client.post("/generate-batch", json={
        "requests": [
            {
                "profile_url": "https://linkedin.com/in/johndoe",
                "product_description": "A very good product that requires a long description."
            },
            {
                "profile_url": "https://linkedin.com/in/johndoe",
                "product_description": "A very good product that requires a long description."
            }
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["recipient_name"] == "John"
    assert data["results"][1]["recipient_name"] == "John"

def test_failure_recovery_e2e(monkeypatch, mock_pipeline):
    """Test that a failure in one batch item doesn't fail the whole batch."""
    
    # We override the mock agent invoke to fail on the first request but succeed on the second
    from langchain_core.messages import AIMessage, ToolCall
    
    call_counts = {"invoke": 0}
    def mock_agent_invoke_flakey(*args, **kwargs):
        call_counts["invoke"] += 1
        turn = call_counts["invoke"]
        
        if turn == 1:
            # First batch item - fail it immediately
            raise RuntimeError("LLM is having a bad day")
        else:
            # Second batch item - succeed immediately
            return AIMessage(
                content='{"recipient_name": "John", "message": "Hi John, this is an E2E generated message based on your profile. AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "reason_for_outreach": "E2E test reason that meets validation."}'
            )
            
    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI.invoke", mock_agent_invoke_flakey)

    response = client.post("/generate-batch", json={
        "requests": [
            {
                "profile_url": "https://linkedin.com/in/johndoe",
                "product_description": "A very good product that requires a long description."
            },
            {
                "profile_url": "https://linkedin.com/in/johndoe",
                "product_description": "A very good product that requires a long description."
            }
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1 # Only one succeeded
    assert data["results"][0]["recipient_name"] == "John"

def test_api_validation_e2e():
    """Test that invalid requests are blocked at the API layer before hitting the agent."""
    response = client.post("/generate", json={
        "profile_url": "not-a-url",
        "product_description": "short",
        "tone": "invalid_tone"
    })
    
    assert response.status_code == 422
    data = response.json()
    # Expect 3 validation errors: url, product_description min_length, tone enum
    assert "detail" in data
