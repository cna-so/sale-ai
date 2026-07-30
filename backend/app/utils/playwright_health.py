from __future__ import annotations

from backend.app.providers.digikala_playwright_provider import _CHROMIUM_ARGS


async def check_playwright_chromium() -> tuple[bool, str | None]:
    """Verify headless Chromium can launch (needed for live Digikala scraping)."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
            await browser.close()
        return True, None
    except Exception as exc:
        return False, str(exc)
