from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from backend.app.models.domain import Product


class ProductCardData(BaseModel):
    product: Product


class ProductCardWidget(BaseModel):
    type: Literal["product_card"] = "product_card"
    data: ProductCardData


class ProductCarouselData(BaseModel):
    title: str
    products: list[Product]


class ProductCarouselWidget(BaseModel):
    type: Literal["product_carousel"] = "product_carousel"
    data: ProductCarouselData


class ComparisonTableData(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]


class ComparisonTableWidget(BaseModel):
    type: Literal["comparison_table"] = "comparison_table"
    data: ComparisonTableData


# Discriminated union for widget payloads
Widget = Annotated[
    Union[ProductCardWidget, ProductCarouselWidget, ComparisonTableWidget],
    Field(discriminator="type"),
]
