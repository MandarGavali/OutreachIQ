from app.models.response_models import OutreachMessage

response = OutreachMessage(
    recipient_name="John Doe",
    message=(
        "Hi John, I noticed your recent work on AI systems and really liked "
        "your approach to building production-ready applications. I thought "
        "our AI outreach platform could be valuable for your workflow."
    ),
    reason_for_outreach="Recipient actively works on AI engineering.",
)

print(response.model_dump(mode="json"))