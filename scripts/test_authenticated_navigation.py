from app.scraper.browser_manager import browser_manager


FEED_URL = "https://www.linkedin.com/feed/"


def verify_navigation(headless: bool) -> None:
    print(f"\nTesting {'headless' if headless else 'headed'} mode...")

    try:
        with browser_manager(headless=headless) as page:
            page.goto(
                FEED_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            print("URL:", page.url)
            print("Title:", page.title())

            # Basic authentication check
            if "/login" in page.url:
                print("FAILED: Session is not authenticated.")
                return

            # Verify that the feed page loaded
            feed_element = page.locator("main").first

            if feed_element.count() > 0:
                print("Feed/main element found.")
                print("Authenticated navigation: PASSED")
            else:
                print("WARNING: Feed/main element not found.")

    except Exception as exc:
        print(f"Navigation failed: {exc}")


if __name__ == "__main__":
    verify_navigation(headless=False)
    verify_navigation(headless=True)