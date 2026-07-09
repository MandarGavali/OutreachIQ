from app.scraper.profile_scraper import scrape_profile

profile_text = """
John Doe

AI Engineer at Google

About
Building AI-powered applications using LLMs and Cloud technologies.

Recent Activity
Published an article on AI Agents.
Spoke at PyCon 2026.
Open-sourced an AI project.
"""

profile = scrape_profile(profile_text)

print(profile)