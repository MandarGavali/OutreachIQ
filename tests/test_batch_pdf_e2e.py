from fastapi.testclient import TestClient
import io
import pytest
from app.main import app
from app.models.response_models import OutreachMessage
from pathlib import Path

client = TestClient(app)

@pytest.fixture
def mock_llm(monkeypatch):
    from app.models.response_models import OutreachMessage
    def mock_generate(*args, **kwargs):
        return OutreachMessage(
            recipient_name="Alex Rivera",
            message="This is a valid mock message that is long enough to pass validation rules.",
            reason_for_outreach="Valid reason that passes the ten character minimum"
        )
    monkeypatch.setattr("app.agent.agent_core.generate_outreach", mock_generate)

def test_batch_pdf_e2e_flow(mock_llm, tmp_path):
    # This relies on the examples/sample_profile.pdf
    pdf_path = Path("examples/sample_profile.pdf")
    
    if not pdf_path.exists():
        pytest.skip("sample_profile.pdf not found in examples/")
        
    pdf_bytes = pdf_path.read_bytes()

    # Step 1: Upload batch of PDFs
    files = [
        ("files", ("profile1.pdf", pdf_bytes, "application/pdf")),
        ("files", ("profile2.pdf", pdf_bytes, "application/pdf")),
        ("files", ("bad.pdf", b"corrupted pdf data", "application/pdf"))
    ]
    data = {
        "product_description": "We sell a fantastic B2B product for generating leads."
    }
    response = client.post("/generate-batch-from-pdf", files=files, data=data)
    
    assert response.status_code == 200
    res = response.json()
    assert res["total"] == 3
    assert res["successful"] == 2
    assert res["failed"] == 1
    
    # Step 2: Extract successful results
    success_results = [item["result"] for item in res["results"] if item["status"] == "success"]
    assert len(success_results) == 2
    assert success_results[0]["recipient_name"] == "Alex Rivera"

    # Step 3: Export to CSV
    csv_response = client.post("/export-csv", json=success_results)
    assert csv_response.status_code == 200
    assert "Alex Rivera" in csv_response.text
