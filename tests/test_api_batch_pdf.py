from fastapi.testclient import TestClient
import io
import pytest
from app.main import app
from app.models.response_models import OutreachMessage

client = TestClient(app)

@pytest.fixture
def mock_pipeline(monkeypatch):
    class MockProfile:
        name = "Mock User"
        headline = "Mock Headline"
        about = "Mock About"
        recent_activity = ["Mock Activity"]

    class MockScraper:
        def acquire_from_input(self, profile_input):
            return MockProfile()
            
    monkeypatch.setattr("app.api.routes._scraper", MockScraper())
    
    def mock_generate(*args, **kwargs):
        return OutreachMessage(
            recipient_name="Mock User",
            message="This is a mock message that passes the minimum length of fifty characters requirement easily.",
            reason_for_outreach="Valid reason that is long enough"
        )
    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate)

def test_batch_pdf_success(mock_pipeline):
    files = [
        ("files", ("profile1.pdf", b"fake pdf content", "application/pdf")),
        ("files", ("profile2.pdf", b"fake pdf content", "application/pdf"))
    ]
    data = {
        "product_description": "We sell a fantastic B2B product for generating leads.",
        "tone": "casual"
    }
    response = client.post("/generate-batch-from-pdf", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["total"] == 2
    assert res["successful"] == 2
    assert res["failed"] == 0
    assert len(res["results"]) == 2
    assert res["results"][0]["filename"] == "profile1.pdf"
    assert res["results"][0]["status"] == "success"
    assert res["results"][0]["result"]["recipient_name"] == "Mock User"

def test_batch_pdf_exceeds_limit(mock_pipeline):
    # 11 files
    files = [
        ("files", (f"profile{i}.pdf", b"fake pdf content", "application/pdf")) for i in range(11)
    ]
    data = {
        "product_description": "We sell a fantastic B2B product for generating leads."
    }
    response = client.post("/generate-batch-from-pdf", files=files, data=data)
    assert response.status_code == 422
    assert "Exceeded maximum batch size" in response.json()["detail"]

def test_batch_pdf_mixed_failures(mock_pipeline, monkeypatch):
    class MixedScraper:
        def acquire_from_input(self, profile_input):
            if "bad" in profile_input.pdf_path:
                from app.scraper.exceptions import ProfileAcquisitionError
                raise ProfileAcquisitionError("Simulated parse error")
            class MockProfile:
                name = "Mock User"
                headline = "Mock Headline"
                about = "Mock About"
                recent_activity = ["Mock Activity"]
            return MockProfile()
            
    monkeypatch.setattr("app.api.routes._scraper", MixedScraper())
    
    files = [
        ("files", ("good.pdf", b"fake pdf content", "application/pdf")),
        ("files", ("bad.txt", b"fake txt content", "text/plain")), # Fails validation
        ("files", ("empty.pdf", b"", "application/pdf")) # Empty file
    ]
    data = {
        "product_description": "We sell a fantastic B2B product for generating leads."
    }
    response = client.post("/generate-batch-from-pdf", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["total"] == 3
    assert res["successful"] == 1
    assert res["failed"] == 2
    
    results_by_name = {r["filename"]: r for r in res["results"]}
    
    assert results_by_name["good.pdf"]["status"] == "success"
    assert results_by_name["bad.txt"]["status"] == "error"
    assert "extension" in results_by_name["bad.txt"]["error"]
    assert results_by_name["empty.pdf"]["status"] == "error"
    assert "empty" in results_by_name["empty.pdf"]["error"]

def test_export_csv():
    payload = [
        {
            "recipient_name": "Alice",
            "message": "Message for Alice that is long enough to pass validation rules.",
            "reason_for_outreach": "Reason for Alice is here"
        },
        {
            "recipient_name": "Bob",
            "message": "Message for Bob that is long enough to pass validation rules.",
            "reason_for_outreach": "Reason for Bob is here"
        }
    ]
    response = client.post("/export-csv", json=payload)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Alice" in response.text
    assert "Bob" in response.text
    assert "Message for Alice" in response.text
