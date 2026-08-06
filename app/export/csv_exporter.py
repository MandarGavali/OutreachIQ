import csv
from pathlib import Path

from app.models.response_models import OutreachMessage


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

        writer.writerow(
            [
                "Recipient Name",
                "Reason For Outreach",
                "Message",
            ]
        )

        for message in messages:
            writer.writerow(
                [
                    message.recipient_name,
                    message.reason_for_outreach,
                    message.message,
                ]
            )

    return str(output_path)