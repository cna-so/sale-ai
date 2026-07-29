from __future__ import annotations

from typing import Any, Sequence

from backend.app.models.domain import Product
from backend.app.utils.language import format_price_toman


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {}


def _product_title(product: dict[str, Any], language: str) -> str:
    if language == "fa":
        return product.get("title") or product.get("title_en") or ""
    return product.get("title_en") or product.get("title") or ""


def _format_price(price: Any, language: str) -> str:
    if not isinstance(price, int) or price <= 0:
        return "-"
    if language == "fa":
        return format_price_toman(price)
    return f"{price:,} toman"


def _labels(language: str) -> dict[str, str]:
    if language == "fa":
        return {
            "price": "قیمت",
            "rating": "امتیاز",
            "reviews": "نظرها",
            "availability": "موجودی",
            "in_stock": "موجود",
            "out_of_stock": "ناموجود / نامشخص",
            "details": "جزئیات",
            "highlights": "ویژگی‌ها",
            "why": "چرا مناسب است",
            "view": "مشاهده و خرید در دیجی‌کالا",
            "follow_up": "اگر بخواهید می‌توانم گزینه‌های ارزان‌تر، پریمیوم‌تر یا مشابه را هم مقایسه کنم.",
            "comparison": "مقایسه سریع",
            "picks": "ویترین محصولات",
            "source": "منبع",
        }
    return {
        "price": "Price",
        "rating": "Rating",
        "reviews": "Reviews",
        "availability": "Availability",
        "in_stock": "In stock",
        "out_of_stock": "Unavailable / unknown",
        "details": "Details",
        "highlights": "Highlights",
        "why": "Why it fits",
        "view": "View & buy on Digikala",
        "follow_up": "I can also narrow this to cheaper, premium, or more similar options.",
        "comparison": "Quick comparison",
        "picks": "Product showcase",
        "source": "Source",
    }


def format_product_card(
    product: Product | dict[str, Any],
    *,
    language: str = "fa",
    reason: str | None = None,
    include_image: bool = True,
    index: int | None = None,
) -> str:
    """Render one product as a LibreChat-friendly showcase card."""
    data = _as_dict(product)
    labels = _labels(language)
    title = _product_title(data, language)
    heading = f"### {index}. {title}" if index is not None and title else (f"### {title}" if title else "### Product")
    lines = [heading]

    image_url = data.get("image_url") or ""
    if include_image and image_url:
        lines.append(f"![{title}]({image_url})")

    lines.append(f"- **{labels['price']}:** {_format_price(data.get('price'), language)}")

    rating = data.get("rating")
    review_count = data.get("review_count") or 0
    if rating not in (None, "", 0, 0.0):
        rating_line = f"- **{labels['rating']}:** {rating}"
        if review_count:
            rating_line += f" ({review_count} {labels['reviews']})"
        lines.append(rating_line)
    elif review_count:
        lines.append(f"- **{labels['reviews']}:** {review_count}")

    available = data.get("available", True)
    lines.append(
        f"- **{labels['availability']}:** "
        f"{labels['in_stock'] if available else labels['out_of_stock']}"
    )

    highlights = data.get("highlights") or []
    if highlights:
        lines.append(f"- **{labels['highlights']}:** " + " · ".join(str(h) for h in highlights[:4]))

    description = (data.get("description") or "").strip()
    if description:
        lines.append(f"- **{labels['details']}:** {description}")

    if reason:
        lines.append(f"- **{labels['why']}:** {reason}")

    source = data.get("source") or ""
    if source:
        lines.append(f"- **{labels['source']}:** {source}")

    product_url = data.get("product_url") or ""
    if product_url:
        lines.append(f"- [{labels['view']}]({product_url})")

    return "\n".join(lines)


def format_product_cards(
    products: Sequence[Product | dict[str, Any]],
    *,
    language: str = "fa",
    reasons: Sequence[str] | None = None,
    include_image: bool = True,
    title: str | None = None,
) -> str:
    """Render multiple products as an image-forward showcase."""
    if not products:
        return ""

    labels = _labels(language)
    parts: list[str] = [f"**{title or labels['picks']}**"]

    for index, product in enumerate(products, start=1):
        reason = None
        if reasons and index - 1 < len(reasons):
            reason = reasons[index - 1]
        parts.append(
            format_product_card(
                product,
                language=language,
                reason=reason,
                include_image=include_image,
                index=index,
            )
        )
    return "\n\n".join(parts)


def format_comparison_table(
    products: Sequence[Product | dict[str, Any]],
    *,
    language: str = "fa",
    title: str | None = None,
) -> str:
    """Render a compact markdown comparison table from grounded product fields."""
    if not products:
        return ""

    labels = _labels(language)
    heading = title or labels["comparison"]
    columns = (
        ["محصول", "قیمت", "امتیاز", "نظرها"]
        if language == "fa"
        else ["Product", "Price", "Rating", "Reviews"]
    )
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join([" --- "] * len(columns)) + "|"
    rows = []
    for product in products:
        data = _as_dict(product)
        rows.append(
            "| "
            + " | ".join(
                [
                    _product_title(data, language),
                    _format_price(data.get("price"), language),
                    str(data.get("rating", "-")),
                    str(data.get("review_count", "-")),
                ]
            )
            + " |"
        )
    return "\n".join([f"**{heading}**", header, separator, *rows])


def format_widget_markdown(
    widget: Any,
    *,
    language: str = "fa",
    include_image: bool = True,
) -> str:
    """Convert an internal widget payload into chat-safe markdown."""
    data = _as_dict(widget)
    wtype = data.get("type", "")
    payload = data.get("data", {})

    if wtype == "product_card":
        product = payload.get("product", payload)
        return format_product_card(product, language=language, include_image=include_image)

    if wtype == "product_carousel":
        return format_product_cards(
            payload.get("products", []),
            language=language,
            include_image=include_image,
            title=payload.get("title"),
        )

    if wtype == "comparison_table":
        columns = payload.get("columns") or []
        rows = payload.get("rows") or []
        if not columns or not rows:
            return ""
        header = "| " + " | ".join(str(c) for c in columns) + " |"
        separator = "|" + "|".join([" --- "] * len(columns)) + "|"
        body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
        title = payload.get("title")
        parts = [f"**{title}**"] if title else []
        return "\n".join(parts + [header, separator, *body])

    return ""


def build_shopping_chat_content(
    answer: str,
    *,
    products: Sequence[Product | dict[str, Any]] | None = None,
    widgets: Sequence[Any] | None = None,
    reasons: Sequence[str] | None = None,
    language: str = "fa",
    render_mode: str = "markdown",
    include_image: bool = True,
    intent: str | None = None,
) -> str:
    """
    Dual-path chat content for LibreChat / OpenAI-compatible clients.

    - markdown: image-forward product showcase (default)
    - plain: compact text bullets
    - widgets: still flatten to markdown for OpenAI clients (widgets stay internal)
    """
    products = list(products or [])
    widgets = list(widgets or [])
    labels = _labels(language)
    intro = (answer or "").strip()
    mode = (render_mode or "markdown").lower()

    if mode == "plain":
        product_block = _format_plain_products(products, language=language, reasons=reasons)
    else:
        product_block = _format_markdown_products(
            products=products,
            widgets=widgets,
            reasons=reasons,
            language=language,
            include_image=include_image,
            intent=intent,
        )

    parts = [part for part in (intro, product_block) if part]
    if products:
        parts.append(labels["follow_up"])
    return "\n\n".join(parts)


def _format_markdown_products(
    *,
    products: list[Any],
    widgets: list[Any],
    reasons: Sequence[str] | None,
    language: str,
    include_image: bool,
    intent: str | None,
) -> str:
    # Showcase cards first so LibreChat always shows images/details.
    showcase_products = products[:5] if products else []
    if showcase_products:
        cards = format_product_cards(
            showcase_products,
            language=language,
            reasons=reasons,
            include_image=include_image,
        )
        if intent in {"product_comparison", "recommendation", "gift_recommendation"} and len(products) >= 2:
            table = format_comparison_table(products[:5], language=language)
            return "\n\n".join(part for part in (cards, table) if part)
        return cards

    if widgets:
        rendered = [
            format_widget_markdown(widget, language=language, include_image=include_image)
            for widget in widgets
        ]
        return "\n\n".join(part for part in rendered if part)

    return ""


def _format_plain_products(
    products: Sequence[Any],
    *,
    language: str,
    reasons: Sequence[str] | None,
) -> str:
    if not products:
        return ""
    labels = _labels(language)
    lines = []
    for index, product in enumerate(products):
        data = _as_dict(product)
        title = _product_title(data, language)
        price = _format_price(data.get("price"), language)
        rating = data.get("rating", "-")
        reason = reasons[index] if reasons and index < len(reasons) else ""
        line = f"- {title} | {labels['price']}: {price} | {labels['rating']}: {rating}"
        if reason:
            line += f" | {reason}"
        url = data.get("product_url") or ""
        if url:
            line += f" | {url}"
        lines.append(line)
    return "\n".join(lines)
