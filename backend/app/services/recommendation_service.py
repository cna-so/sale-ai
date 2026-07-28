from __future__ import annotations

import re

from backend.app.models.domain import Product, Recommendation
from backend.app.utils.language import detect_language, format_price_toman, parse_price_constraints

# Scoring weight rationale (all weights sum to 1.0 added on top of 0.5 base):
#   title_match  : 0.08 per token — query relevance, uncapped (dominant signal)
#   price_fit    : 0.15          — being within budget is a hard user constraint
#   above_min    : 0.05          — not below the minimum (weaker, rare constraint)
#   rating       : 0.15          — quality signal, normalised 0-5 → 0-0.15
#   popularity   : 0.07          — social proof, normalised 0-500 reviews → 0-0.07
#
# Total max (without title tokens): 0.5 + 0.15 + 0.05 + 0.15 + 0.07 = 0.92
# The remaining headroom (0.08 per token) lets well-matched titles reach 1.0.
_W_PRICE_FIT = 0.15
_W_ABOVE_MIN = 0.05
_W_RATING = 0.15
_W_POPULARITY = 0.07
_W_TOKEN = 0.08
_POPULARITY_CAP = 500  # review count at which popularity score is maxed


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
        tokens = [t for t in lowered.split() if t]

        for p in products:
            score = 0.5
            combined = f"{p.title} {p.title_en}".lower()

            # Use word-boundary matching to avoid partial hits
            # (e.g. "mouse" matching inside "mousepad").
            for token in tokens:
                pattern = rf"\b{re.escape(token)}\b"
                if re.search(pattern, combined):
                    score += _W_TOKEN

            if max_toman is not None and p.price <= max_toman:
                score += _W_PRICE_FIT
            if min_toman is not None and p.price >= min_toman:
                score += _W_ABOVE_MIN

            score += min(p.rating / 5.0, 1.0) * _W_RATING
            score += min(p.review_count / _POPULARITY_CAP, 1.0) * _W_POPULARITY
            score = min(score, 1.0)

            if language == "fa":
                reason = f"{p.title} با قیمت {format_price_toman(p.price)} و امتیاز {p.rating} گزینه مناسبی برای درخواست شماست."
            else:
                reason = f"{p.title_en or p.title} is a strong match with a price of {p.price:,} toman and rating {p.rating}."

            scored.append(Recommendation(product=p, score=score, reason=reason))

        return sorted(scored, key=lambda r: r.score, reverse=True)
