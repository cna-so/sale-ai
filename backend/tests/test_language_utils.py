from __future__ import annotations

from backend.app.utils.language import (
    detect_language,
    format_price_toman,
    normalize_arabic_chars,
    normalize_persian_numerals,
    parse_price_constraints,
)


def test_detect_language_persian():
    assert detect_language("یک کیبورد گیمینگ می‌خوام") == "fa"


def test_detect_language_english():
    assert detect_language("I want to buy a keyboard") == "en"


def test_detect_language_mixed_prefers_persian():
    assert detect_language("کیبورد gaming می‌خوام") == "fa"


def test_normalize_persian_numerals():
    assert normalize_persian_numerals("۱۲۳") == "123"
    assert normalize_persian_numerals("۰۹") == "09"


def test_normalize_arabic_kaf_yeh():
    # Arabic Kaf U+0643 -> Persian Kaf U+06A9
    assert normalize_arabic_chars("\u0643") == "\u06a9"
    # Arabic Yeh U+064A -> Persian Yeh U+06CC
    assert normalize_arabic_chars("\u064a") == "\u06cc"


def test_format_price_toman_basic():
    result = format_price_toman(3_500_000)
    assert "تومان" in result
    assert "۳" in result


def test_format_price_toman_zero():
    result = format_price_toman(0)
    assert "تومان" in result


def test_parse_price_under_persian():
    min_t, max_t = parse_price_constraints("زیر ۳ میلیون")
    assert min_t is None
    assert max_t == 3_000_000


def test_parse_price_under_english():
    min_t, max_t = parse_price_constraints("under 2 million")
    assert max_t == 2_000_000


def test_parse_price_between_persian():
    min_t, max_t = parse_price_constraints("بین ۱ تا ۲ میلیون")
    assert min_t == 1_000_000
    assert max_t == 2_000_000


def test_parse_price_no_price():
    min_t, max_t = parse_price_constraints("یک هدفون خوب می‌خوام")
    assert min_t is None
    assert max_t is None
