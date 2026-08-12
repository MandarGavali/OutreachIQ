from app.scraper.browser_manager import browser_manager


PROFILE_URL = "https://www.linkedin.com/in/williamhgates/"


with browser_manager(headless=False) as page:
    page.goto(PROFILE_URL, wait_until="domcontentloaded")

    print("URL:", page.url)
    print("Title:", page.title())

    input("Inspect the profile in DevTools, then press ENTER...")