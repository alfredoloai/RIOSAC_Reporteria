from __future__ import annotations

from dataclasses import dataclass
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@dataclass(frozen=True)
class BrowserSession:
    browser: Browser
    context: BrowserContext
    page: Page

    def close(self) -> None:
        try:
            self.context.close()
        finally:
            self.browser.close()


def create_session(
    pw: Playwright,
    *,
    headless: bool,
    slow_mo_ms: int,
    timeout_ms: int,
) -> BrowserSession:
    # Si NO es headless, abrimos DevTools automáticamente para inspección/selectores.
    launch_args = ["--auto-open-devtools-for-tabs"] if not headless else None

    browser = pw.chromium.launch(
        headless=headless,
        slow_mo=slow_mo_ms,
        args=launch_args,
    )
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(timeout_ms)

    return BrowserSession(browser=browser, context=context, page=page)