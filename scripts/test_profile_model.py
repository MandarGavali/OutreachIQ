from app.models.profile_models import ScrapedProfile

profile = ScrapedProfile(
    name="John Doe",
    headline="AI Engineer | Building Production AI Systems",
    about="Passionate about AI agents and backend engineering.",
    recent_activity=[
        "Shared a post about LLMs",
        "Started a new AI project",
    ],
)

print(profile.model_dump(mode="json"))