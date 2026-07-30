from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from backend.app.core.config import Settings
from backend.app.models.domain import Product, ProductSearchResult
from backend.app.providers.product_provider import ProductProvider
from backend.app.utils.ids import new_id
from backend.app.utils.search_query import meaningful_search_tokens, normalize_persian_text, normalize_search_query

logger = logging.getLogger(__name__)

# Required for headless Chromium inside Docker (slim images have no sandbox user).
_CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]

_SEARCH_API_FRAGMENT = "/discovery/api/v2/search"


class DigikalaPlaywrightProvider(ProductProvider):
    """Fetch live Digikala search results via the site's discovery search API."""

    name = "digikala"
    BASE_URL = "https://www.digikala.com"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        query = normalize_search_query(query)
        if not query:
            return ProductSearchResult(
                products=[], query=query, provider=self.name, total_found=0, error="empty query"
            )

        search_url = f"{self.BASE_URL}/search/?q={quote_plus(query)}"
        timeout_ms = self._settings.product_search_timeout_seconds * 1000
        api_payload: dict[str, Any] | None = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=_CHROMIUM_ARGS,
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

                async def capture_search_api(response) -> None:
                    nonlocal api_payload
                    if api_payload is not None:
                        return
                    if _SEARCH_API_FRAGMENT not in response.url:
                        return
                    if response.status != 200:
                        return
                    query_params = parse_qs(urlparse(response.url).query)
                    response_query = (query_params.get("q") or [""])[0].strip()
                    page_number = (query_params.get("page") or ["1"])[0]
                    if response_query != query or page_number != "1":
                        return
                    try:
                        api_payload = await response.json()
                    except Exception:
                        logger.debug("Failed to parse Digikala search API response")

                page.on("response", capture_search_api)
                await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
                for _ in range(30):
                    if api_payload is not None:
                        break
                    await page.wait_for_timeout(500)

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

        raw_products = self._extract_products_from_api(api_payload)
        if not raw_products:
            logger.warning("Digikala search API returned no products for query='%s'", query)
            return ProductSearchResult(
                products=[],
                query=query,
                provider=self.name,
                total_found=0,
                error="no products in search response",
            )

        raw_products = self._rank_api_products(raw_products, query)

        products: list[Product] = []
        for raw in raw_products:
            if len(products) >= max_results:
                break
            product = self._api_product_to_domain(raw)
            if product is not None:
                products.append(product)

        return ProductSearchResult(
            products=products,
            query=query,
            provider=self.name,
            total_found=len(products),
        )

    @staticmethod
    def _extract_products_from_api(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not payload:
            return []

        found: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                product_id = node.get("id")
                if (
                    isinstance(product_id, int)
                    and "title_fa" in node
                    and "default_variant" in node
                    and product_id not in seen_ids
                ):
                    seen_ids.add(product_id)
                    found.append(node)
                    return
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(payload)
        return found

    @staticmethod
    def _rank_api_products(raw_products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        tokens = meaningful_search_tokens(query)
        if not tokens:
            return raw_products

        def score(raw: dict[str, Any]) -> tuple[int, float, int]:
            title = normalize_persian_text(f"{raw.get('title_fa', '')} {raw.get('title_en', '')}").lower()
            token_hits = sum(1 for token in tokens if token in title)
            rating = float((raw.get("rating") or {}).get("rate") or 0)
            reviews = int((raw.get("rating") or {}).get("count") or 0)
            return (token_hits, rating, reviews)

        return sorted(raw_products, key=score, reverse=True)

    def _api_product_to_domain(self, raw: dict[str, Any]) -> Product | None:
        title = (raw.get("title_fa") or raw.get("title_en") or "").strip()
        if len(title) < 4:
            return None

        title_en = (raw.get("title_en") or "").strip()
        variant = raw.get("default_variant") or {}
        price_block = variant.get("price") or {}
        selling_price_rial = price_block.get("selling_price") or 0
        price_toman = int(selling_price_rial // 10) if selling_price_rial else 0

        rating_block = raw.get("rating") or {}
        rating = self._normalize_rating(rating_block.get("rate"))
        review_count = int(rating_block.get("count") or 0)

        image_url = self._extract_image_url(raw.get("images") or {})
        product_url = self._extract_product_url(raw)
        status = (variant.get("status") or raw.get("status") or "").lower()
        available = status == "marketable"

        highlights = self._extract_highlights(title, raw)
        description = self._build_description(title, price_toman, rating, review_count, available)

        return Product(
            id=str(raw.get("id") or new_id()),
            title=title[:180],
            title_en=title_en[:180],
            image_url=image_url,
            price=price_toman,
            currency="IRR",
            rating=rating,
            review_count=review_count,
            product_url=product_url,
            source="digikala",
            available=available,
            description=description,
            highlights=highlights,
        )

    def _extract_product_url(self, raw: dict[str, Any]) -> str:
        url_obj = raw.get("url") or {}
        uri = url_obj.get("uri") or ""
        if uri:
            return urljoin(self.BASE_URL, uri.split("?")[0])
        product_id = raw.get("id")
        if product_id:
            return f"{self.BASE_URL}/product/dkp-{product_id}/"
        return ""

    @staticmethod
    def _extract_image_url(images: dict[str, Any]) -> str:
        main = images.get("main") or {}
        for key in ("webp_url", "url"):
            urls = main.get(key) or []
            if urls and isinstance(urls[0], str):
                return urls[0]
        return ""

    @staticmethod
    def _normalize_rating(raw_rate: Any) -> float:
        try:
            rate = float(raw_rate or 0)
        except (TypeError, ValueError):
            return 0.0
        if rate <= 0:
            return 0.0
        # Digikala discovery API uses a 0-100 satisfaction score.
        if rate > 5:
            return min(round(rate / 20, 1), 5.0)
        return min(rate, 5.0)

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
    def _extract_highlights(title: str, raw: dict[str, Any]) -> list[str]:
        highlights: list[str] = []
        if "گیمینگ" in title or "gaming" in title.lower():
            highlights.append("گیمینگ")
        if "بی‌سیم" in title or "wireless" in title.lower():
            highlights.append("بی‌سیم")
        if "مکانیکی" in title:
            highlights.append("مکانیکی")
        if "RGB" in title.upper():
            highlights.append("RGB")

        data_layer = raw.get("data_layer") or {}
        category = data_layer.get("item_category4") or data_layer.get("item_category3")
        if category and isinstance(category, str):
            highlights.append(category)

        discount = (raw.get("default_variant") or {}).get("price", {}).get("discount_percent")
        if isinstance(discount, int) and discount > 0:
            highlights.append(f"{discount}% تخفیف")

        return highlights[:4]
