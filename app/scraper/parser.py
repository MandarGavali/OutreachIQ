from app.models.profile_models import ScrapedProfile


def parse_profile(
    profile_text: str,
    profile_url: str,
) -> ScrapedProfile:
    """
    Convert raw profile text into a structured ScrapedProfile object.
    """

    # Remove empty lines and extra spaces
    lines = [
        line.strip()
        for line in profile_text.splitlines()
        if line.strip()
    ]

    # Validate minimum required data
    if len(lines) < 2:
        raise ValueError(
            "Profile text must contain at least name and headline"
        )

    # Basic extraction
    name = lines[0]
    headline = lines[1]

    about = None
    recent_activity = []

    # Extract "About" section
    if "About" in lines:
        about_index = lines.index("About") + 1

        about_lines = []

        while (
            about_index < len(lines)
            and lines[about_index] != "Recent Activity"
        ):
            about_lines.append(lines[about_index])
            about_index += 1

        if about_lines:
            about = "\n".join(about_lines)

    # Extract "Recent Activity" section
    if "Recent Activity" in lines:
        activity_index = lines.index("Recent Activity")

        recent_activity = lines[activity_index + 1:]

    return ScrapedProfile(
        profile_url=profile_url,
        name=name,
        headline=headline,
        about=about,
        recent_activity=recent_activity,
    )