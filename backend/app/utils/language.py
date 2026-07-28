from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Persian / Arabic character normalization maps
# ---------------------------------------------------------------------------

_PERSIAN_DIGITS = str.maketrans("\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9", "0123456789")
_ARABIC_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669", "0123456789")

# Arabic Kaf (\u0643) -> Persian Kaf (\u06a9)
# Arabic Yeh (\u064a) -> Persian Yeh (\u06cc)
_ARABIC_NORM = str.maketrans("\u0643\u064a", "\u06a9\u06cc")

# Rough threshold: if > 20% of alpha chars are Arabic/Persian, classify as 'fa'
_FA_RANGE = re.compile(r"[\u0600-\u06ff]")
_EN_RANGE = re.compile(r"[a-zA-Z]")


def normalize_persian_numerals(text: str) -> str:
    """Convert Persian and Arabic-Indic digit characters to ASCII digits."""
    return text.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def normalize_arabic_chars(text: str) -> str:
    """Normalize Arabic Kaf/Yeh variants to their Persian equivalents."""
    return text.translate(_ARABIC_NORM)


def normalize_text(text: str) -> str:
    """Apply all normalizations."""
    return normalize_arabic_chars(normalize_persian_numerals(text))


def detect_language(text: str) -> str:
    """Return 'fa' if the text is predominantly Persian/Arabic, else 'en'."""
    fa_count = len(_FA_RANGE.findall(text))
    en_count = len(_EN_RANGE.findall(text))
    if fa_count == 0 and en_count == 0:
        return "fa"  # default to Persian for the app context
    return "fa" if fa_count >= en_count else "en"


def format_price_toman(amount: int) -> str:
    """
    Format an integer Toman price with Persian thousands separators.
    Example: 3_500_000 -> '\u06f3\u066c\u06f5\u06f0\u06f0\u066c\u06f0\u06f0\u06f0 \u062a\u0648\u0645\u0627\u0646'
    """
    # Format with regular comma separators first
    formatted = f"{amount:,}"
    # Convert ASCII digits to Persian digits
    _to_persian = str.maketrans("0123456789,", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u066c")
    persian_formatted = formatted.translate(_to_persian)
    return f"{persian_formatted} \u062a\u0648\u0645\u0627\u0646"


# ---------------------------------------------------------------------------
# Price constraint parsing
# ---------------------------------------------------------------------------

_MILLION_FA = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:\u0645\u06cc\u0644\u06cc\u0648\u0646|\u0645\u06cc\u0644\u06cc\u0648\u0646)",  # میلیون
    re.IGNORECASE,
)
_UNDER_FA = re.compile(
    r"\u0632\u06cc\u0631\s*([\u06f0-\u06f9\d\u0660-\u0669]+(?:[.,]\d+)?)\s*(?:\u0645\u06cc\u0644\u06cc\u0648\u0646)?"  # زیر
)
_BETWEEN_FA = re.compile(
    r"\u0628\u06cc\u0646\s*([\u06f0-\u06f9\d]+)\s*\u062a\u0627\s*([\u06f0-\u06f9\d]+)\s*(?:\u0645\u06cc\u0644\u06cc\u0648\u0646)?"  # بین X تا Y
)


def parse_price_constraints(text: str) -> tuple[int | None, int | None]:
    """
    Parse Persian/English price constraints from natural language.
    Returns (min_toman, max_toman) — either can be None.
    """
    normalized = normalize_persian_numerals(text)

    # English patterns
    under_en = re.search(r"under\s+([\d,]+)", normalized, re.IGNORECASE)
    below_en = re.search(r"below\s+([\d,]+)", normalized, re.IGNORECASE)
    between_en = re.search(r"between\s+([\d,]+)\s+(?:and|to)\s+([\d,]+)", normalized, re.IGNORECASE)
    million_en = re.search(r"([\d.]+)\s*million", normalized, re.IGNORECASE)

    if between_en:
        lo = int(between_en.group(1).replace(",", ""))
        hi = int(between_en.group(2).replace(",", ""))
        # If values look like they are in millions already (< 1000), scale up
        if hi < 1000:
            lo *= 1_000_000
            hi *= 1_000_000
        return lo, hi

    if under_en or below_en:
        m = under_en or below_en
        val = int(m.group(1).replace(",", ""))  # type: ignore[union-attr]
        if val < 1000:
            val *= 1_000_000
        return None, val

    if million_en:
        val = int(float(million_en.group(1)) * 1_000_000)
        return None, val

    # Persian patterns
    between_fa = _BETWEEN_FA.search(normalized)
    if between_fa:
        lo = int(normalize_persian_numerals(between_fa.group(1)))
        hi = int(normalize_persian_numerals(between_fa.group(2)))
        if hi < 1000:
            lo *= 1_000_000
            hi *= 1_000_000
        return lo, hi

    under_fa = _UNDER_FA.search(normalized)
    if under_fa:
        raw = normalize_persian_numerals(under_fa.group(1))
        val = int(raw)
        if val < 1000:
            val *= 1_000_000
        return None, val

    million_fa = _MILLION_FA.search(normalized)
    if million_fa:
        val = int(float(million_fa.group(1).replace(",", "."))) * 1_000_000
        return None, val

    return None, None
