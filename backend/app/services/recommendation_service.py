from __future__ import annotations

from backend.app.models.domain import Product, Recommendation
from backend.app.utils.language import detect_language, format_price_toman, parse_price_constraints


class RecommendationService:
    def recommend(
        self,
        query: str,
        products: list[Product],
        language: str,
        min_toman: int | None = None,
        max_toman: int | None = None,
    ) -> list[Recommendation]:
        scored: list[Recommendation] = []
        lowered = query.lower()

        for p in products:
            score = 0.5
            combined = f"{p.title} {p.title_en}".lower()
            for token in lowered.split():
                if token and token in combined:
                    score += 0.08

            if max_toman is not None and p.price <= max_toman:
                score += 0.15
            if min_toman is not None and p.price >= min_toman:
                score += 0.05

            # Prefer better rating and more reviews
            score += min(p.rating / 5.0, 1.0) * 0.15
            score += min(p.review_count / 500.0, 1.0) * 0.07
            score = min(score, 1.0)

            if language == "fa":
                reason = f"{p.title} با قیمت {format_price_toman(p.price)} و امتیاز {p.rating} گزینه مناسبی برای درخواست شماست."
            else:
                reason = f"{p.title_en or p.title} is a strong match with a price of {p.price:,} toman and rating {p.rating}."

            scored.append(Recommendation(product=p, score=score, reason=reason))

        return sorted(scored, key=lambda r: r.score, reverse=True)
