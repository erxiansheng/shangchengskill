"""Generic-product schema for the EdgeOne Mall template.

We keep the "skill" naming for backwards-compat in KV (the existing
storage layer references `skill:*` keys), but expose a product-flavoured
domain at the API surface. Two new fields make this template cover any
e-commerce vertical instead of an AI-skill marketplace specifically:

* ``sale_mode`` — points / cash / both. Drives the checkout flow.
* ``cash_price_yuan`` — required when sale_mode in ("cash", "both").
* ``stock`` — None means unlimited; otherwise integer with concurrency
  decrement at order placement.
* ``sku_list`` — optional list of {name, price_delta, stock} variants
  for products with size / color / spec selection.

Field names that map 1:1 to the legacy SkillCreate schema are kept so
that the existing KV records remain readable; renamed fields fall back
to the legacy name on read.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


SaleMode = Literal["points", "cash", "both"]


class SkuItem(BaseModel):
    name: str
    price_delta: int = 0          # extra points if sale_mode includes points
    cash_delta_yuan: float = 0    # extra yuan if sale_mode includes cash
    stock: Optional[int] = None   # None = unlimited


class ProductCreate(BaseModel):
    title: str
    description: str
    category_id: Optional[int] = None
    price: int = 0                                 # points price
    cash_price_yuan: float = 0.0
    sale_mode: SaleMode = "points"
    stock: Optional[int] = None
    sku_list: Optional[List[SkuItem]] = None

    tags: Optional[List[str]] = None
    is_free: bool = False
    cover_image: Optional[str] = None
    file_url: Optional[str] = None                 # downloadable goods (optional)
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    original_filename: Optional[str] = None
    subtitle: Optional[str] = None
    version: str = "1.0.0"
    screenshots: Optional[List[str]] = None
    installation_guide: Optional[str] = Field(
        default=None, description="后台叫'商品说明 / 使用教程'，复用 Markdown 渲染"
    )
    file_tree: Optional[List[dict]] = None

    @model_validator(mode="after")
    def _check_pricing(self):
        if self.sale_mode in ("cash", "both") and self.cash_price_yuan <= 0 and not self.is_free:
            raise ValueError("启用现金售卖时必须设置 cash_price_yuan > 0")
        if self.sale_mode in ("points", "both") and self.price < 0:
            raise ValueError("price 不能为负")
        return self


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = None
    cash_price_yuan: Optional[float] = None
    sale_mode: Optional[SaleMode] = None
    stock: Optional[int] = None
    sku_list: Optional[List[SkuItem]] = None
    tags: Optional[List[str]] = None
    is_free: Optional[bool] = None
    cover_image: Optional[str] = None
    subtitle: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    original_filename: Optional[str] = None
    version: Optional[str] = None
    screenshots: Optional[List[str]] = None
    installation_guide: Optional[str] = None
    file_tree: Optional[List[dict]] = None


class ProductListItem(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    price: int = 0
    cash_price_yuan: float = 0.0
    sale_mode: SaleMode = "points"
    stock: Optional[int] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    cover_image: Optional[str] = None
    icon: Optional[str] = None
    version: str = "1.0.0"
    avg_rating: float = 0.0
    review_count: int = 0
    download_count: int = 0
    purchase_count: int = 0
    favorite_count: int = 0
    is_free: bool = False
    tags: Optional[List[str]] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None
    author_role: Optional[str] = None
    author_level_info: Optional[dict] = None
    status: str = "pending"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductDetail(ProductListItem):
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    reject_reason: Optional[str] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    images: Optional[List[str]] = None
    versions: Optional[List[dict]] = None
    screenshots: Optional[List[str]] = None
    installation_guide: Optional[str] = None
    sku_list: Optional[List[SkuItem]] = None

    class Config:
        from_attributes = True
