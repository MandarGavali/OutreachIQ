"""
Tests for the final_demo.py CLI behavior.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch
from app.scraper.exceptions import ProfileAcquisitionError
from scripts import final_demo

# We need to mock the actual run functions so we don't trigger the real LLM or adapter processing in CLI tests.
@pytest.fixture
def mock_run_text(monkeypatch):
    with patch("scripts.final_demo._run_text_demo") as mock:
        yield mock

@pytest.fixture
def mock_run_fixture(monkeypatch):
    with patch("scripts.final_demo._run_fixture_demo") as mock:
        yield mock

@pytest.fixture
def mock_run_pdf(monkeypatch):
    with patch("scripts.final_demo._run_pdf_demo") as mock:
        yield mock


def test_cli_default_is_text(mock_run_text, capsys):
    test_args = ["final_demo.py"]
    with patch.object(sys, "argv", test_args):
        final_demo.main()
    mock_run_text.assert_called_once()


def test_cli_text_source_works_without_pdf(mock_run_text, capsys):
    test_args = ["final_demo.py", "--source", "text"]
    with patch.object(sys, "argv", test_args):
        final_demo.main()
    mock_run_text.assert_called_once()


def test_cli_fixture_source_works_without_pdf(mock_run_fixture, capsys):
    test_args = ["final_demo.py", "--source", "fixture"]
    with patch.object(sys, "argv", test_args):
        final_demo.main()
    mock_run_fixture.assert_called_once()


def test_cli_pdf_source_requires_pdf_arg(capsys):
    test_args = ["final_demo.py", "--source", "pdf"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc:
            final_demo.main()
        assert exc.value.code == 1
    
    captured = capsys.readouterr()
    assert "PDF source requires --pdf PATH" in captured.out


def test_cli_pdf_source_rejects_nonexistent_file(capsys):
    # This tests _run_pdf_demo logic specifically
    with pytest.raises(SystemExit) as exc:
        final_demo._run_pdf_demo(["nonexistent_fake_path.pdf"])
    assert exc.value.code == 1
    
    captured = capsys.readouterr()
    assert "PDF file not found: nonexistent_fake_path.pdf" in captured.out


def test_cli_pdf_source_accepts_valid_pdf_path(monkeypatch, tmp_path):
    # Create a dummy pdf file
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.touch()

    # Mock adapter to avoid actual PDF extraction logic
    class FakeAdapter:
        def acquire_from_pdf(self, path):
            from app.scraper.acquisition import RawProfileData
            return RawProfileData(name="Fake", headline="Fake", source="pdf")

    monkeypatch.setattr("app.scraper.pdf_adapter.PDFProfileAdapter", FakeAdapter)
    
    # Mock generate_outreach to avoid LLM call
    with patch("scripts.final_demo.generate_outreach") as mock_generate:
        from app.models.response_models import OutreachMessage
        mock_generate.return_value = OutreachMessage(
            recipient_name="Fake", 
            message="This is a valid mock message that is long enough to pass validation rules.", 
            reason_for_outreach="Valid reason that passes the ten character minimum"
        )
        
        # Should not raise SystemExit
        final_demo._run_pdf_demo([str(dummy_pdf)])
        
        mock_generate.assert_called_once()


def test_cli_pdf_source_surfaces_acquisition_error(monkeypatch, tmp_path, capsys):
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.touch()

    class ErrorAdapter:
        def acquire_from_pdf(self, path):
            raise ProfileAcquisitionError("Simulated extraction error")

    monkeypatch.setattr("app.scraper.pdf_adapter.PDFProfileAdapter", ErrorAdapter)
    
    # In batch mode, errors don't exit, they just log and continue. So it shouldn't raise SystemExit anymore.
    final_demo._run_pdf_demo([str(dummy_pdf)])
    
    captured = capsys.readouterr()
    assert "Acquisition Error: Simulated extraction error" in captured.out
