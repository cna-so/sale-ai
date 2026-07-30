from __future__ import annotations

import re

# Persian + English stop words that should not drive product matching.
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "for",
        "to",
        "of",
        "in",
        "on",
        "at",
        "is",
        "are",
        "be",
        "with",
        "under",
        "below",
        "above",
        "over",
        "best",
        "good",
        "recommend",
        "recommendation",
        "please",
        "want",
        "need",
        "looking",
        "buy",
        "find",
        "show",
        "give",
        "me",
        "my",
        "some",
        "any",
        "one",
        "million",
        "toman",
        "tomans",
        "irr",
        "یک",
        "برای",
        "میخوام",
        "می‌خوام",
        "میخواهم",
        "می‌خواهم",
        "دنبال",
        "لطفا",
        "لطفاً",
        "خوب",
        "بهترین",
        "پیشنهاد",
        "بده",
        "بدهید",
        "میخوام",
        "میخواهم",
        "چی",
        "چیزی",
        "چطور",
        "چند",
        "زیر",
        "بالای",
        "حدود",
        "تومان",
        "تومن",
        "میلیون",
        "هزار",
        "من",
        "ما",
        "تو",
        "شما",
        "این",
        "اون",
        "آن",
        "که",
        "از",
        "به",
        "در",
        "با",
        "یا",
        "و",
    }
)


def normalize_persian_text(text: str) -> str:
    """Normalize Persian text for fuzzy matching (half-space, nbsp)."""
    return text.replace("\u200c", "").replace("\xa0", " ")


def meaningful_search_tokens(query: str) -> list[str]:
    """Extract non-stop-word tokens long enough to match product text."""
    normalized = normalize_persian_text(query.lower())
    tokens = re.findall(r"[\w\u0600-\u06FF]+", normalized)
    return [token for token in tokens if len(token) >= 2 and token not in _STOP_WORDS and not token.isdigit()]


def normalize_search_query(query: str) -> str:
    """Collapse whitespace for provider calls."""
    return re.sub(r"\s+", " ", query.strip())
