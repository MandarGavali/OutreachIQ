from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


STORAGE_STATE_PATH = Path("app/auth/storage_state.json")


@contextmanager
def browser_manager(
    headless: bool = True,
) -> Generator[Page, None, None]:
    """
    Launch an authenticated Chromium browser and yield a page.

    The browser, context, and Playwright instance are cleaned up
    automatically when the context exits, including on exceptions.
    """

    if not STORAGE_STATE_PATH.exists():
        raise FileNotFoundError(
            f"Storage state not found: {STORAGE_STATE_PATH}"
        )

    playwright: Playwright | None = None
    browser: Browser | None = None
    context = None
    page: Page | None = None

    try:
        playwright = sync_playwright().start()

        browser = playwright.chromium.launch(
            headless=headless,
        )

        context = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH),
        )

        page = context.new_page()

        yield page

    finally:
        if page:
            page.close()

        if context:
            context.close()

        if browser:
            browser.close()

        if playwright:
            playwright.stop()