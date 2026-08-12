from pathlib import Path

from playwright.sync_api import sync_playwright


STORAGE_STATE_PATH = Path("app/auth/storage_state.json")
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"


def main() -> None:
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
        )

        context = browser.new_context()

        page = context.new_page()

        print("Opening LinkedIn login...")
        page.goto(LINKEDIN_LOGIN_URL)

        print("\nLog into LinkedIn manually in the browser.")
        print("Complete any verification steps if LinkedIn asks for them.")
        input("\nAfter you are fully logged in, press ENTER here...")

        context.storage_state(path=str(STORAGE_STATE_PATH))

        print(f"\nSession saved to: {STORAGE_STATE_PATH}")

        browser.close()
        print("Browser closed.")


if __name__ == "__main__":
    main()

# Tech@5666 -> 56 tech fury 