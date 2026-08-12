from app.scraper.browser_manager import browser_manager


with browser_manager(headless=False) as page:
    page.goto("https://www.linkedin.com/feed/")

    print("Title:", page.title())
    print("URL:", page.url)

    input("Press ENTER to close the browser...")