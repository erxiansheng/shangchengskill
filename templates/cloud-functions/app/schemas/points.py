from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PointsBalance(BaseModel):
    balance: int
    total_earned: int
    total_spent: int


class PointsRecordItem(BaseModel):
    id: int
    type: str
    amount: int
    balance_after: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RechargeRequest(BaseModel):
    amount_yuan: float
    payment_method: str = "wechat"
    client_type: str = ""  # "miniprogram" for JSAPI payment


class RechargePackage(BaseModel):
    amount_yuan: float
    points: int
