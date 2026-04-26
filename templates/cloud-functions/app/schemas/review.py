from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    rating: int
    content: Optional[str] = None
    captcha_token: str
    captcha_answer: int


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    user_nickname: Optional[str] = None
    user_avatar: Optional[str] = None
    skill_id: str
    rating: int
    content: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
