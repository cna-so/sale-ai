from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urljoin

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from backend.app.core.config import Settings
from backend.app.models.domain import Product, ProductSearchResult
from backend.app.providers.product_provider import ProductProvider
from backend.app.utils.ids import new_id

logger = logging.getLogger(__name__)


class DigikalaPlaywrightProvider(ProductProvider):
    """Scrape Digikala public search pages into showcase-ready product cards."""

    name = "digikala"
    BASE_URL = "https://www.digikala.com"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        search_url = f"{self.BASE_URL}/search/?q={quote_plus(query)}"
        timeout_ms = self._settings.product_search_timeout_seconds * 1000

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    locale="fa-IR",
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1365, "height": 900},
                )
                page = await context.new_page()
                await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    await page.wait_for_selector("a[href*='/product/dkp-']", timeout=min(timeout_ms, 12000))
                except PlaywrightTimeoutError:
                    await page.wait_for_timeout(2000)

                raw_cards = await page.evaluate(
                    """() => {
                      const anchors = Array.from(document.querySelectorAll("a[href*='/product/dkp-']"));
                      const seen = new Set();
                      const cards = [];
                      for (const a of anchors) {
                        const href = a.getAttribute("href") || "";
                        if (!href.includes("/product/dkp-") || seen.has(href)) continue;
                        seen.add(href);
                        const img = a.querySelector("img");
                        let image = "";
                        if (img) {
                          const srcset = img.getAttribute("srcset") || img.getAttribute("data-srcset") || "";
                          if (srcset) {
                            const parts = srcset.split(",").map(s => s.trim().split(" ")[0]).filter(Boolean);
                            image = parts[parts.length - 1] || "";
                          }
                          image = image
                            || img.getAttribute("src")
                            || img.getAttribute("data-src")
                            || img.currentSrc
                            || "";
                        }
                        const text = (a.innerText || "").replace(/\\s+/g, " ").trim();
                        cards.push({ href, image, text, alt: (img && img.getAttribute("alt")) || "" });
                        if (cards.length >= 20) break;
                      }
                      return cards;
                    }"""
                )
                await browser.close()
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

        products: list[Product] = []
        for card in raw_cards or []:
            if len(products) >= max_results:
                break
            product = self._card_to_product(card)
            if product is not None:
                products.append(product)

        return ProductSearchResult(
            products=products,
            query=query,
            provider=self.name,
            total_found=len(products),
        )

    def _card_to_product(self, card: dict) -> Product | None:
        href = card.get("href") or ""
        full_url = urljoin(self.BASE_URL, href)
        text = (card.get("text") or "").strip()
        alt = (card.get("alt") or "").strip()
        title = self._clean_title(alt or text)
        if not title or len(title) < 8:
            return None

        image_url = self._normalize_image_url(card.get("image") or "")
        price = self._extract_price_toman(text)
        rating = self._extract_rating(text)
        review_count = self._extract_review_count(text)
        available = "ناموجود" not in text and "soon" not in text.lower()
        highlights = self._extract_highlights(text, title)
        description = self._build_description(title, price, rating, review_count, available)

        return Product(
            id=new_id(),
            title=title[:180],
            title_en="",
            image_url=image_url,
            price=price,
            currency="IRR",
            rating=rating,
            review_count=review_count,
            product_url=full_url.split("?")[0],
            source="digikala",
            available=available,
            description=description,
            highlights=highlights,
        )

    @staticmethod
    def _normalize_image_url(image_url: str) -> str:
        if not image_url:
            return ""
        if image_url.startswith("//"):
            return "https:" + image_url
        if image_url.startswith("/"):
            return urljoin(DigikalaPlaywrightProvider.BASE_URL, image_url)
        return image_url

    @staticmethod
    def _clean_title(text: str) -> str:
        lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]
        candidates = lines or [text]
        for candidate in candidates:
            cleaned = re.sub(r"\s+", " ", candidate).strip(" -|")
            if not cleaned:
                continue
            if re.search(r"تومان|تومن|نظر|از\s*5", cleaned):
                continue
            if len(cleaned) < 8:
                continue
            return cleaned
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = re.split(r"\d[\d,]+\s*توم", cleaned)[0].strip(" -|")
        return cleaned

    @staticmethod
    def _build_description(
        title: str,
        price: int,
        rating: float,
        review_count: int,
        available: bool,
    ) -> str:
        bits = [title]
        if price:
            bits.append(f"قیمت حدودی {price:,} تومان")
        if rating:
            bits.append(f"امتیاز {rating}")
        if review_count:
            bits.append(f"{review_count} نظر")
        bits.append("موجود در دیجی‌کالا" if available else "وضعیت موجودی نامشخص/ناموجود")
        return " — ".join(bits)

    @staticmethod
    def _extract_highlights(text: str, title: str) -> list[str]:
        highlights: list[str] = []
        if "گیمینگ" in title or "gaming" in title.lower():
            highlights.append("گیمینگ")
        if "بی‌سیم" in title or "wireless" in title.lower():
            highlights.append("بی‌سیم")
        if "مکانیکی" in title:
            highlights.append("مکانیکی")
        if "RGB" in title.upper():
            highlights.append("RGB")
        if "ناموجود" in text:
            highlights.append("ناموجود")
        return highlights[:4]

    @staticmethod
    def _extract_price_toman(text: str) -> int:
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
        m = re.search(r"(\d(?:\.\d)?)\s*از\s*5", text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _extract_review_count(text: str) -> int:
        m = re.search(r"(\d[\d,]*)\s*نظر", text)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                return 0
        return 0
