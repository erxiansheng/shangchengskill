from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


# Sale mode controls which checkout flows the storefront exposes.
# - "points": pay only with platform points (legacy default for digital goods)
# - "cash":   pay only via WeChat Pay / Alipay (works for both digital and
#             physical goods; physical goods rely exclusively on this branch)
# - "both":   buyer chooses on the detail page
SaleMode = Literal["points", "cash", "both"]
ProductType = Literal["digital", "physical"]


class SkillCreate(BaseModel):
    title: str
    description: str
    category_id: Optional[int] = None
    price: int = 0
    tags: Optional[List[str]] = None
    is_free: bool = False
    cover_image: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    original_filename: Optional[str] = None
    subtitle: Optional[str] = None
    version: str = "1.0.0"
    screenshots: Optional[List[str]] = None
    installation_guide: Optional[str] = None
    file_tree: Optional[List[dict]] = None

    # Generic-product extensions (entity / cash-payment support)
    product_type: ProductType = "digital"
    sale_mode: SaleMode = "points"
    cash_price_yuan: float = 0.0
    stock: Optional[int] = None  # None = unlimited
    shipping_fee_yuan: float = 0.0
    shipping_required: bool = False  # auto-true for physical goods


class SkillUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = None
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

    product_type: Optional[ProductType] = None
    sale_mode: Optional[SaleMode] = None
    cash_price_yuan: Optional[float] = None
    stock: Optional[int] = None
    shipping_fee_yuan: Optional[float] = None
    shipping_required: Optional[bool] = None


class SkillListItem(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    price: int
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


class SkillDetail(SkillListItem):
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

    class Config:
        from_attributes = True


class VersionCreate(BaseModel):
    version: str
    changelog: Optional[str] = None
    file_url: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
