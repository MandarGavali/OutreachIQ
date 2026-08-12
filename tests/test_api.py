import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.request_models import Tone

client = TestClient(app)

def test_health_check_not_found_but_api_up():
    # If /health doesn't exist, we just want to ensure the app is running
    # but we can try generating a 404
    response = client.get("/health")
    # if it's 404, it means it's not implemented, which is fine, but app is up
    assert response.status_code in [200, 404]

def test_generate_invalid_request():
    response = client.post("/generate", json={"profile_url": "invalid"})
    assert response.status_code == 422 # Validation error for missing product_description

def test_generate_valid_request_mocked(monkeypatch):
    from app.models.response_models import OutreachMessage
    
    def mock_generate_outreach(request):
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint."
        )
    
    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)
    
    response = client.post("/generate", json={
        "profile_url": "https://linkedin.com/in/test",
        "product_description": "A test product that is sufficiently long.",
        "tone": "casual"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_name"] == "John"

def test_generate_batch_valid_mocked(monkeypatch):
    from app.models.response_models import OutreachMessage
    
    def mock_generate_outreach(request):
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint."
        )
    
    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)
    
    response = client.post("/generate-batch", json={
        "requests": [
            {
                "profile_url": "https://linkedin.com/in/test1",
                "product_description": "A test product that is sufficiently long."
            },
            {
                "profile_url": "https://linkedin.com/in/test2",
                "product_description": "A test product that is sufficiently long."
            }
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["recipient_name"] == "John"

def test_generate_batch_partial_failure(monkeypatch):
    from app.models.response_models import OutreachMessage
    
    call_count = [0]
    def mock_generate_outreach(request):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("Agent failed")
            
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint."
        )
    
    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)
    
    response = client.post("/generate-batch", json={
        "requests": [
            {
                "profile_url": "https://linkedin.com/in/test1",
                "product_description": "A test product that is sufficiently long."
            },
            {
                "profile_url": "https://linkedin.com/in/test2",
                "product_description": "A test product that is sufficiently long."
            }
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    # Should only contain the successful result, batch shouldn't fail completely
    assert len(data["results"]) == 1
