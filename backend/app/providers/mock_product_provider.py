from __future__ import annotations

from backend.app.models.domain import Product, ProductSearchResult
from backend.app.providers.product_provider import ProductProvider
from backend.app.utils.ids import new_id


class MockProductProvider(ProductProvider):
    name = "mock"

    async def search(self, query: str, max_results: int = 5) -> ProductSearchResult:
        products = [
            Product(
                id=new_id(),
                title="کیبورد گیمینگ مکانیکی ردراگون مدل K552 Kumara",
                title_en="Redragon K552 Kumara Mechanical Keyboard",
                image_url="https://placehold.co/480x480/png?text=Redragon+K552",
                price=2_850_000,
                currency="IRR",
                rating=4.5,
                review_count=234,
                product_url="https://www.digikala.com/product/dkp-mock-k552/",
                source="digikala",
                available=True,
                description="کیبورد مکانیکی گیمینگ با سوئیچ قرمز و نورپردازی — گزینه متعادل برای استفاده روزانه و بازی.",
                highlights=["گیمینگ", "مکانیکی", "RGB"],
            ),
            Product(
                id=new_id(),
                title="کیبورد گیمینگ گرین مدل GK601-RGB",
                title_en="Green GK601 RGB Gaming Keyboard",
                image_url="https://placehold.co/480x480/png?text=Green+GK601",
                price=1_950_000,
                currency="IRR",
                rating=4.2,
                review_count=118,
                product_url="https://www.digikala.com/product/dkp-mock-gk601/",
                source="digikala",
                available=True,
                description="گزینه اقتصادی با نورپردازی RGB برای بودجه‌های محدودتر.",
                highlights=["گیمینگ", "RGB", "اقتصادی"],
            ),
            Product(
                id=new_id(),
                title="کیبورد گیمینگ لاجیتک مدل G213 Prodigy",
                title_en="Logitech G213 Prodigy",
                image_url="https://placehold.co/480x480/png?text=Logitech+G213",
                price=3_400_000,
                currency="IRR",
                rating=4.6,
                review_count=310,
                product_url="https://www.digikala.com/product/dkp-mock-g213/",
                source="digikala",
                available=True,
                description="کیبورد پریمیوم‌تر با برند معتبر و امتیاز بالا برای استفاده طولانی.",
                highlights=["گیمینگ", "پریمیوم"],
            ),
            Product(
                id=new_id(),
                title="هدفون بی‌سیم سونی مدل WH-CH520",
                title_en="Sony WH-CH520 Wireless Headphones",
                image_url="https://placehold.co/480x480/png?text=Sony+WH-CH520",
                price=2_200_000,
                currency="IRR",
                rating=4.4,
                review_count=189,
                product_url="https://www.digikala.com/product/dkp-mock-whch520/",
                source="digikala",
                available=True,
                description="هدفون بی‌سیم سبک برای استفاده روزمره و هدیه.",
                highlights=["بی‌سیم", "هدیه"],
            ),
            Product(
                id=new_id(),
                title="ماوس گیمینگ ریزر مدل DeathAdder Essential",
                title_en="Razer DeathAdder Essential",
                image_url="https://placehold.co/480x480/png?text=Razer+DeathAdder",
                price=1_750_000,
                currency="IRR",
                rating=4.7,
                review_count=402,
                product_url="https://www.digikala.com/product/dkp-mock-deathadder/",
                source="digikala",
                available=True,
                description="ماوس گیمینگ محبوب با ارگونومی خوب و امتیاز بالا.",
                highlights=["گیمینگ", "ارگونومیک"],
            ),
        ]

        filtered = [
            p
            for p in products
            if any(token in (p.title + " " + p.title_en).lower() for token in query.lower().split())
        ]
        final = filtered[:max_results] if filtered else products[:max_results]
        return ProductSearchResult(
            products=final,
            query=query,
            provider=self.name,
            total_found=len(final),
        )
