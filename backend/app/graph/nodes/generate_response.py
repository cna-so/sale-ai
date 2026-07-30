from __future__ import annotations

import logging
from typing import Any

from backend.app.core.exceptions import LLMError
from backend.app.graph.state import AgentState
from backend.app.models.domain import Product, RetrievedDocument
from backend.app.prompts.recommendation import RECOMMENDATION_GUIDANCE_EN, RECOMMENDATION_GUIDANCE_FA
from backend.app.prompts.response import RESPONSE_SYSTEM_PROMPT_EN, RESPONSE_SYSTEM_PROMPT_FA
from backend.app.schemas.widgets import (
    ComparisonTableData,
    ComparisonTableWidget,
    ProductCarouselData,
    ProductCarouselWidget,
    ProductCardData,
    ProductCardWidget,
)
from backend.app.services.llm_service import LLMService
from backend.app.services.recommendation_service import RecommendationService
from backend.app.utils.language import format_price_toman

logger = logging.getLogger(__name__)


def _build_rag_context(docs: list[RetrievedDocument]) -> str:
    if not docs:
        return ""
    parts = [f"[{i+1}] ({d.source}) {d.content}" for i, d in enumerate(docs)]
    return "\n\n".join(parts)


def _build_product_context(products: list[Product], language: str) -> str:
    if not products:
        return ""
    lines = []
    for i, p in enumerate(products):
        price_str = format_price_toman(p.price) if p.price else "-"
        title = p.title if language == "fa" else (p.title_en or p.title)
        rating_label = "\u0627\u0645\u062a\u06cc\u0627\u0632" if language == "fa" else "Rating"
        lines.append(f"{i+1}. {title} | {price_str} | {rating_label}: {p.rating}")
    return "\n".join(lines)


def _build_widgets(intent: str, products: list[Product], language: str) -> list[Any]:
    if not products:
        return []

    if intent in {"recommendation", "gift_recommendation", "product_comparison"} and len(products) >= 2:
        title = "\u0645\u0642\u0627\u06cc\u0633\u0647 \u0645\u062d\u0635\u0648\u0644\u0627\u062a" if intent == "product_comparison" and language == "fa" else (
            "Product Comparison" if intent == "product_comparison" else (
                "\u0645\u062d\u0635\u0648\u0644\u0627\u062a \u067e\u06cc\u0634\u0646\u0647\u0627\u062f\u06cc" if language == "fa" else "Recommended Products"
            )
        )
        columns_fa = ["\u0645\u062d\u0635\u0648\u0644", "\u0642\u06cc\u0645\u062a", "\u0627\u0645\u062a\u06cc\u0627\u0632"]
        columns_en = ["Product", "Price", "Rating"]
        columns = columns_fa if language == "fa" else columns_en
        rows = [
            [p.title if language == "fa" else (p.title_en or p.title), format_price_toman(p.price) if p.price else "-", str(p.rating)]
            for p in products
        ]
        return [ComparisonTableWidget(data=ComparisonTableData(title=title, columns=columns, rows=rows))]

    if len(products) == 1 or intent == "product_detail":
        return [ProductCardWidget(data=ProductCardData(product=products[0]))]

    carousel_title = "\u0646\u062a\u0627\u06cc\u062c \u062c\u0633\u062a\u062c\u0648" if language == "fa" else "Search Results"
    return [ProductCarouselWidget(data=ProductCarouselData(title=carousel_title, products=products))]


def make_generate_response_node(llm_service: LLMService, recommendation_service: RecommendationService):
    async def generate_response(state: AgentState) -> AgentState:
        intent_result = state.get("intent")
        intent_label = intent_result.intent if intent_result else "general_chat"
        language = intent_result.detected_language if intent_result else "fa"
        products = state.get("products", [])
        retrieved_docs = state.get("retrieved_docs", [])
        image_analysis = state.get("image_analysis") or state.get("last_image_analysis")
        user_message = state["user_message"]
        history = state.get("history", [])
        preferences = state.get("preferences")

        recommendation_reasons: list[str] = []
        if intent_label in {"recommendation", "gift_recommendation"} and products:
            min_t = intent_result.filters.price.min_toman if intent_result else None
            max_t = intent_result.filters.price.max_toman if intent_result else None
            recommendations = recommendation_service.recommend(
                query=user_message,
                products=products,
                language=language,
                min_toman=min_t,
                max_toman=max_t,
            )
            products = [r.product for r in recommendations]
            recommendation_reasons = [r.reason for r in recommendations]

        system_prompt = RESPONSE_SYSTEM_PROMPT_FA if language == "fa" else RESPONSE_SYSTEM_PROMPT_EN
        if intent_label in {"recommendation", "gift_recommendation"}:
            system_prompt += "\n\n" + (
                RECOMMENDATION_GUIDANCE_FA if language == "fa" else RECOMMENDATION_GUIDANCE_EN
            )

        context_parts: list[str] = []
        if retrieved_docs:
            context_parts.append("---\n" + _build_rag_context(retrieved_docs) + "\n---")
        if products:
            label = "\u0645\u062d\u0635\u0648\u0644\u0627\u062a \u06cc\u0627\u0641\u062a \u0634\u062f\u0647" if language == "fa" else "Found products"
            context_parts.append(f"{label}:\n" + _build_product_context(products, language))
        elif state.get("error") and state.get("used_product_search"):
            if language == "fa":
                context_parts.append(
                    f"جستجوی دیجی\u200cکالا ناموفق بود: {state['error']}. "
                    "به کاربر بگو محصولی از دیجی\u200cکالا دریافت نشد و دوباره تلاش کند."
                )
            else:
                context_parts.append(
                    f"Digikala search failed: {state['error']}. "
                    "Tell the user no live Digikala products were retrieved and suggest retrying."
                )
        if recommendation_reasons:
            label = "\u062f\u0644\u0627\u06cc\u0644 \u0627\u0646\u062a\u062e\u0627\u0628" if language == "fa" else "Recommendation fit"
            context_parts.append(f"{label}:\n" + "\n".join(recommendation_reasons))
        if image_analysis:
            img_label = "\u062a\u062d\u0644\u06cc\u0644 \u062a\u0635\u0648\u06cc\u0631" if language == "fa" else "Image analysis"
            context_parts.append(f"{img_label}: {image_analysis.concise_description} | Query: {image_analysis.suggested_search_query}")
        elif state.get("image_data") is not None or state.get("used_image_analysis"):
            # Prevent the response model from wrongly claiming no image was uploaded.
            if language == "fa":
                context_parts.append(
                    "توجه: کاربر یک تصویر محصول آپلود کرده است. تحلیل بینایی موقتاً ناموفق بود. "
                    "هرگز نگو که تصویری آپلود نشده. اگر محصولی پیدا شد معرفی کن؛ وگرنه بخواه توضیح کوتاه متنی بدهد."
                )
            else:
                context_parts.append(
                    "Note: The user uploaded a product image. Vision analysis failed temporarily. "
                    "Do NOT say that no image was uploaded. If products were found, present them; "
                    "otherwise ask for a short text description of the product."
                )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Include prior turns already limited by load_context / chat_history_limit
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        user_content = user_message
        if context_parts:
            user_content = "\n\n".join(context_parts) + "\n\n" + user_message

        messages.append({"role": "user", "content": user_content})

        try:
            answer = await llm_service.chat(messages=messages, temperature=0.3)
        except LLMError as exc:
            logger.warning("LLM generation failed: %s", exc)
            if language == "fa":
                answer = "\u0645\u062a\u0623\u0633\u0641\u0627\u0646\u0647 \u062f\u0631 \u062d\u0627\u0644 \u062d\u0627\u0636\u0631 \u0642\u0627\u062f\u0631 \u0628\u0647 \u067e\u0627\u0633\u062e\u062f\u0647\u06cc \u0646\u06cc\u0633\u062a\u0645. \u0644\u0637\u0641\u0627\u064b \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f."
            else:
                answer = "Sorry, I'm unable to respond at the moment. Please try again."

        widgets = _build_widgets(intent_label, products, language)

        return {
            **state,
            "answer": answer,
            "widgets": widgets,
            "sources": retrieved_docs,
            "products": products,
            "recommendation_reasons": recommendation_reasons,
        }

    return generate_response
