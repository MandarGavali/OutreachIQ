from app.models.request_models import OutreachRequest

request = OutreachRequest(
    profile_url="https://linkedin.com/in/johndoe",
    product_description="An AI tool that helps recruiters personalize LinkedIn outreach messages.",
    tone="casual",
)

print(request.model_dump(mode="json"))