import os
import csv
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




