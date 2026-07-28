from __future__ import annotations

import logging
from urllib.parse import quote_plus, urljoin

from playwright.async_api import Browser, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from backend.app.core.config import Settings
from backend.app.models.domain import Product, ProductSearchResult
from backend.app.providers.product_provider import ProductProvider
from backend.app.utils.ids import new_id

logger = logging.getLogger(__name__)

# User-agent used for all Playwright requests. Keep it realistic.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class DigikalaPlaywrightProvider(ProductProvider):
    """Playwright-based scraper for Digikala product search.

    A single Chromium browser instance is shared across all calls (pool of
    one) so the expensive launch only happens once — on the first search —
    and is reused for subsequent requests.  Call :meth:`aclose` (or use the
    FastAPI lifespan) to shut the browser down cleanly.
    """

    name = "digikala"
    BASE_URL = "https://www.digikala.com"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright = None
        self._browser: Browser | None = None

    async def _get_browser(self) -> Browser:
        """Return the shared browser, launching it on first call."""
        if self._browser is None or not self._browser.is_connected():
            logger.info("Launching Playwright Chromium browser")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        return self._browser

    async def aclose(self) -> None:
        """Shut down the shared browser and Playwright runtime."""
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as exc:
                logger.warning("Error closing Playwright browser: %s", exc)
            finally:
                self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.warning("Error stopping Playwright: %s", exc)
            finally:
                self._playwright = None

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        search_url = f"{self.BASE_URL}/search/?q={quote_plus(query)}"
        products: list[Product] = []

        try:
            browser = await self._get_browser()
            page = await browser.new_page(user_agent=_USER_AGENT)
            try:
                await page.goto(
                    search_url,
                    timeout=self._settings.product_search_timeout_seconds * 1000,
                )
                # Wait for actual product cards to appear instead of a fixed sleep.
                # Falls back gracefully if no products are rendered.
                try:
                    await page.wait_for_selector(
                        "a[href*='/product/']",
                        timeout=8_000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning("No product cards appeared for query='%s'", query)
                    return ProductSearchResult(
                        products=[], query=query, provider=self.name, total_found=0, error="no_results"
                    )

                # NOTE:
                # Digikala's public product card markup may change over time.
                # These selectors intentionally target common public listing
                # structures and should be revisited if Digikala updates its HTML.
                cards = await page.query_selector_all("a[href*='/product/']")
                seen_urls: set[str] = set()

                for card in cards:
                    if len(products) >= max_results:
                        break

                    href = await card.get_attribute("href")
                    if not href:
                        continue
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    text = (await card.inner_text()) or ""
                    title = " ".join(line.strip() for line in text.splitlines() if line.strip())
                    if not title:
                        continue

                    img = await card.query_selector("img")
                    image_url = ""
                    if img is not None:
                        image_url = (
                            (await img.get_attribute("src"))
                            or (await img.get_attribute("data-src"))
                            or ""
                        )

                    price = self._extract_price_toman(text)
                    rating = self._extract_rating(text)
                    review_count = self._extract_review_count(text)

                    products.append(
                        Product(
                            id=new_id(),
                            title=title[:180],
                            title_en="",
                            image_url=image_url,
                            price=price,
                            currency="IRR",
                            rating=rating,
                            review_count=review_count,
                            product_url=full_url,
                            source="digikala",
                        )
                    )
            finally:
                # Always close the page; the browser itself is kept alive for reuse.
                await page.close()

        except PlaywrightTimeoutError:
            logger.warning("Digikala search timed out for query='%s'", query)
            return ProductSearchResult(
                products=[], query=query, provider=self.name, total_found=0, error="timeout"
            )
        except Exception as exc:
            logger.warning("Digikala provider failed: %s", exc)
            return ProductSearchResult(
                products=[], query=query, provider=self.name, total_found=0, error=str(exc)
            )

        return ProductSearchResult(
            products=products, query=query, provider=self.name, total_found=len(products)
        )

    @staticmethod
    def _extract_price_toman(text: str) -> int:
        import re

        patterns = [
            r"([\d,]+)\s*تومان",
            r"([\d,]+)\s*تومن",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    return int(m.group(1).replace(",", ""))
                except ValueError:
                    continue
        return 0

    @staticmethod
    def _extract_rating(text: str) -> float:
        import re

        m = re.search(r"(\d(?:\.\d)?)\s*از\s*5", text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _extract_review_count(text: str) -> int:
        import re

        m = re.search(r"(\d+)\s*نظر", text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
        return 0
