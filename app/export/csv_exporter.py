import csv
from pathlib import Path

from app.models.response_models import OutreachMessage


import io

def _write_csv_data(writer, messages: list[OutreachMessage]):
    writer.writerow([
        "Recipient Name",
        "Reason For Outreach",
        "Message",
    ])
    for message in messages:
        writer.writerow([
            message.recipient_name,
            message.reason_for_outreach,
            message.message,
        ])


def export_to_csv(
    messages: list[OutreachMessage],
    output_file: str = "outreach_messages.csv",
) -> str:
    """
    Export validated outreach messages to a CSV file.
    """
    output_path = Path(output_file)
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        _write_csv_data(writer, messages)
    return str(output_path)


def export_to_csv_string(messages: list[OutreachMessage]) -> str:
    """
    Export validated outreach messages to a CSV formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    _write_csv_data(writer, messages)
    return output.getvalue()