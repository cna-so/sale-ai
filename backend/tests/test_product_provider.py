from __future__ import annotations

import pytest

from backend.app.providers.mock_product_provider import MockProductProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_products():
    provider = MockProductProvider()
    result = await provider.search("کیبورد")
    assert result.provider == "mock"
    assert len(result.products) > 0


@pytest.mark.asyncio
async def test_mock_provider_product_fields():
    provider = MockProductProvider()
    result = await provider.search("keyboard")
    for p in result.products:
        assert p.title
        assert p.currency == "IRR"
        assert p.source == "digikala"
        assert "digikala.com" in p.product_url


@pytest.mark.asyncio
async def test_mock_provider_max_results():
    provider = MockProductProvider()
    result = await provider.search("test", max_results=2)
    assert len(result.products) <= 2


@pytest.mark.asyncio
async def test_mock_provider_persian_titles():
    provider = MockProductProvider()
    result = await provider.search("هدفون")
    # At least one product should have a Persian title
    has_persian = any(
        any(ord(c) >= 0x0600 for c in p.title)
        for p in result.products
    )
    assert has_persian
