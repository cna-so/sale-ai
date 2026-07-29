from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from backend.app.models.domain import IntentFilters, IntentResult, PriceFilter
from backend.app.prompts.intent import INTENT_SYSTEM_PROMPT_EN, INTENT_SYSTEM_PROMPT_FA
from backend.app.services.llm_service import LLMService
from backend.app.utils.language import detect_language, parse_price_constraints


class IntentService:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm = llm_service

    async def detect_intent(self, message: str, conversation_messages: list[str] | None = None) -> IntentResult:
        language = detect_language(message)

        if self._llm is not None:
            try:
                system_prompt = INTENT_SYSTEM_PROMPT_FA if language == "fa" else INTENT_SYSTEM_PROMPT_EN
                history = conversation_messages or []
                history_block = ""
                if history:
                    clipped = history[-6:]
                    history_block = "Recent conversation:\n" + "\n".join(f"- {item}" for item in clipped) + "\n\n"
                content = await self._llm.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{history_block}Current message:\n{message}"},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    max_tokens=300,
                )
                parsed = json.loads(content)
                return IntentResult.model_validate(parsed)
            except Exception:
                pass

        return self._fallback_detect(message, language, conversation_messages or [])

    def _fallback_detect(self, message: str, language: str, history: list[str]) -> IntentResult:
        normalized = message.lower()
        min_price, max_price = parse_price_constraints(message)

        rag_keywords_fa = ["سیاست بازگشت", "گارانتی", "راهنمای خرید", "سند", "مدرک"]
        rag_keywords_en = ["return policy", "warranty", "buying guide", "document", "policy"]
        recommendation_keywords_fa = ["بهترین", "پیشنهاد", "زیر", "ارزان", "ارزان‌ترین"]
        recommendation_keywords_en = ["best", "recommend", "under", "below", "cheapest"]
        gift_keywords_fa = ["هدیه", "کادو", "تولد", "سالگرد", "برای مادرم", "برای دوستم"]
        gift_keywords_en = ["gift", "present", "birthday", "anniversary", "for my mom", "for my friend"]
        comparison_keywords_fa = ["مقایسه", "تفاوت", "فرق", "بین", "کدوم بهتره"]
        comparison_keywords_en = ["compare", "difference", "versus", " vs ", "which is better"]
        detail_keywords_fa = ["مشخصات", "جزئیات", "درباره", "نظرها", "گزینه اول", "این محصول"]
        detail_keywords_en = ["details", "specs", "reviews", "tell me about", "first option", "this product"]
        product_keywords_fa = ["می‌خوام", "میخوام", "دنبال", "خرید", "کیبورد", "هدفون", "ماوس", "لپتاپ", "لپ‌تاپ"]
        product_keywords_en = ["looking for", "buy", "keyboard", "headphone", "mouse", "laptop", "monitor"]
        follow_up_keywords_fa = ["همون", "این یکی", "گزینه اول", "کدوم بهتره", "مقایسه‌شون", "ارزان‌تر", "رسمی‌تر"]
        follow_up_keywords_en = ["that one", "first one", "which is better", "compare them", "what about", "cheaper", "more formal"]

        def has_any(tokens: list[str]) -> bool:
            return any(token in normalized for token in tokens)

        if has_any(rag_keywords_fa if language == "fa" else rag_keywords_en):
            return IntentResult(
                intent="rag_query",
                confidence=0.82,
                search_query=message,
                filters=IntentFilters(price=PriceFilter(min_toman=min_price, max_toman=max_price)),
                requires_rag=True,
                requires_product_search=False,
                detected_language=language,
            )

        filters = IntentFilters(
            price=PriceFilter(min_toman=min_price, max_toman=max_price),
        )
        active_gift_keywords = gift_keywords_fa if language == "fa" else gift_keywords_en
        active_comparison_keywords = comparison_keywords_fa if language == "fa" else comparison_keywords_en
        active_detail_keywords = detail_keywords_fa if language == "fa" else detail_keywords_en

        if has_any(active_gift_keywords):
            return IntentResult(
                intent="gift_recommendation",
                confidence=0.86,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        if has_any(active_comparison_keywords):
            return IntentResult(
                intent="product_comparison",
                confidence=0.84,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        if has_any(active_detail_keywords) and history:
            return IntentResult(
                intent="product_detail",
                confidence=0.78,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        if has_any(follow_up_keywords_fa if language == "fa" else follow_up_keywords_en) and history:
            return IntentResult(
                intent="follow_up",
                confidence=0.76,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        if has_any(recommendation_keywords_fa if language == "fa" else recommendation_keywords_en) or min_price is not None or max_price is not None:
            return IntentResult(
                intent="recommendation",
                confidence=0.84,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        if has_any(product_keywords_fa if language == "fa" else product_keywords_en):
            return IntentResult(
                intent="product_search",
                confidence=0.78,
                search_query=message,
                filters=filters,
                requires_rag=False,
                requires_product_search=True,
                detected_language=language,
            )

        return IntentResult(
            intent="general_chat",
            confidence=0.60,
            search_query=message,
            filters=filters,
            requires_rag=False,
            requires_product_search=False,
            detected_language=language,
        )
