"""
API tests for OutreachIQ V2.

Covers:
  POST /generate   — with profile_url (original) and profile_text (new)
  POST /generate-batch
  POST /generate-from-pdf  — new multipart endpoint
  Validation errors, oversized PDF, missing fields, partial batch failure
"""

from __future__ import annotations

import io
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import app
from app.models.request_models import Tone

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_text_pdf(text: str) -> bytes:
    """Build a minimal text-based PDF and return its bytes."""
    writer = PdfWriter()
    safe = (
        text
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )
    lines = safe.splitlines()
    stream_parts = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for line in lines:
        stream_parts.append(f"({line}) Tj T*")
    stream_parts.append("ET")
    content_stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

    page = writer.add_blank_page(width=612, height=792)
    resources = DictionaryObject()
    font_dict = DictionaryObject()
    font_ref = DictionaryObject()
    font_ref[NameObject("/Type")] = NameObject("/Font")
    font_ref[NameObject("/Subtype")] = NameObject("/Type1")
    font_ref[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_dict[NameObject("/F1")] = font_ref
    resources[NameObject("/Font")] = font_dict
    page[NameObject("/Resources")] = resources
    stream_obj = DecodedStreamObject()
    stream_obj.set_data(content_stream)
    stream_ref = writer._add_object(stream_obj)
    page[NameObject("/Contents")] = stream_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


VALID_PDF_BYTES = _build_text_pdf(
    "Alex Rivera\nHead of Growth\n\nAbout\nBuilds outbound pipelines.\n\nRecent Activity\n- Posted about SDR workflows"
)
PRODUCT_DESC = "OutreachIQ is an AI-powered platform for personalized outreach. " * 2


# ---------------------------------------------------------------------------
# /generate — health / existing tests
# ---------------------------------------------------------------------------

def test_health_check_not_found_but_api_up():
    response = client.get("/health")
    assert response.status_code in [200, 404]


def test_generate_invalid_request_missing_product():
    # profile_url provided but product_description missing
    response = client.post("/generate", json={"profile_url": "https://linkedin.com/in/test"})
    assert response.status_code == 422


def test_generate_invalid_request_no_profile_source():
    # Neither profile_url nor profile_text — should fail validation
    response = client.post(
        "/generate",
        json={"product_description": PRODUCT_DESC},
    )
    assert response.status_code == 422


def test_generate_valid_request_with_profile_url_mocked(monkeypatch):
    from app.models.response_models import OutreachMessage

    def mock_generate_outreach(request, pre_scraped_profile=None):
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint.",
        )

    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)

    response = client.post("/generate", json={
        "profile_url": "https://linkedin.com/in/test",
        "product_description": PRODUCT_DESC,
        "tone": "casual",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_name"] == "John"


def test_generate_valid_request_with_profile_text_mocked(monkeypatch):
    """New: POST /generate with profile_text instead of profile_url."""
    from app.models.response_models import OutreachMessage

    def mock_generate_outreach(request, pre_scraped_profile=None):
        return OutreachMessage(
            recipient_name="Alex Rivera",
            message="Hi Alex, saw your post on outreach. " + "A" * 50,
            reason_for_outreach="Connecting with a growth leader.",
        )

    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)

    response = client.post("/generate", json={
        "profile_text": "Alex Rivera\nHead of Growth\n\nAbout\nBuilds pipelines.\n\nRecent Activity\n- Post",
        "product_description": PRODUCT_DESC,
        "tone": "casual",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_name"] == "Alex Rivera"


# ---------------------------------------------------------------------------
# /generate-batch
# ---------------------------------------------------------------------------

def test_generate_batch_valid_mocked(monkeypatch):
    from app.models.response_models import OutreachMessage

    def mock_generate_outreach(request, pre_scraped_profile=None):
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint.",
        )

    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)

    response = client.post("/generate-batch", json={
        "requests": [
            {
                "profile_url": "https://linkedin.com/in/test1",
                "product_description": PRODUCT_DESC,
            },
            {
                "profile_text": "Sam Chen\nEngineer\n\nAbout\nBuilds things.",
                "product_description": PRODUCT_DESC,
            },
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2


def test_generate_batch_partial_failure(monkeypatch):
    from app.models.response_models import OutreachMessage

    call_count = [0]
    def mock_generate_outreach(request, pre_scraped_profile=None):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("Agent failed")
        return OutreachMessage(
            recipient_name="John",
            message="Hi John, this is a test message. " + "A" * 50,
            reason_for_outreach="Testing the API endpoint.",
        )

    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)

    response = client.post("/generate-batch", json={
        "requests": [
            {"profile_url": "https://linkedin.com/in/test1", "product_description": PRODUCT_DESC},
            {"profile_url": "https://linkedin.com/in/test2", "product_description": PRODUCT_DESC},
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1


# ---------------------------------------------------------------------------
# /generate-from-pdf
# ---------------------------------------------------------------------------

def test_generate_from_pdf_valid(monkeypatch):
    """Valid PDF + mocked agent → 200 with OutreachMessage."""
    from app.models.response_models import OutreachMessage

    def mock_generate_outreach(request, pre_scraped_profile=None):
        return OutreachMessage(
            recipient_name="Alex Rivera",
            message="Hi Alex, great post on outreach strategy. " + "A" * 50,
            reason_for_outreach="Connecting with a growth leader.",
        )

    monkeypatch.setattr("app.api.routes.generate_outreach", mock_generate_outreach)

    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.pdf", VALID_PDF_BYTES, "application/pdf")},
        data={"product_description": PRODUCT_DESC, "tone": "casual"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "recipient_name" in data


def test_generate_from_pdf_wrong_extension():
    """Non-PDF file extension → 422."""
    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.txt", b"some text", "text/plain")},
        data={"product_description": PRODUCT_DESC, "tone": "casual"},
    )
    assert response.status_code == 422


def test_generate_from_pdf_empty_file():
    """Empty PDF bytes → 422."""
    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.pdf", b"", "application/pdf")},
        data={"product_description": PRODUCT_DESC, "tone": "casual"},
    )
    assert response.status_code == 422


def test_generate_from_pdf_oversized():
    """Oversized PDF → 422."""
    # Patch the settings to use a very small size limit
    import app.config as cfg
    original = cfg.settings.PDF_MAX_FILE_SIZE_MB
    cfg.settings.PDF_MAX_FILE_SIZE_MB = 0  # 0 MB — everything is "too large"
    try:
        response = client.post(
            "/generate-from-pdf",
            files={"profile_pdf": ("profile.pdf", VALID_PDF_BYTES, "application/pdf")},
            data={"product_description": PRODUCT_DESC, "tone": "casual"},
        )
        assert response.status_code == 422
        assert "too large" in response.json()["detail"].lower()
    finally:
        cfg.settings.PDF_MAX_FILE_SIZE_MB = original


def test_generate_from_pdf_corrupt():
    """Corrupt PDF content → 400."""
    garbage = b"%PDF-1.4\nGARBAGE NOT A REAL PDF"
    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.pdf", garbage, "application/pdf")},
        data={"product_description": PRODUCT_DESC, "tone": "casual"},
    )
    assert response.status_code == 400


def test_generate_from_pdf_missing_product_description():
    """Missing product_description → 422."""
    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.pdf", VALID_PDF_BYTES, "application/pdf")},
        data={"tone": "casual"},  # no product_description
    )
    assert response.status_code == 422


def test_generate_from_pdf_invalid_tone(monkeypatch):
    """Invalid tone value → 422."""
    response = client.post(
        "/generate-from-pdf",
        files={"profile_pdf": ("profile.pdf", VALID_PDF_BYTES, "application/pdf")},
        data={"product_description": PRODUCT_DESC, "tone": "aggressively_pushy"},
    )
    assert response.status_code == 422
