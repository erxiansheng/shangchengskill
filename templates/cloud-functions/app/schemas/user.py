from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    username: str
    password: str
    nickname: str
    phone: Optional[str] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: "UserBrief"


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    points_balance: int = 0
    level: int = 1
    role: str = "user"

    class Config:
        from_attributes = True


class UserProfile(UserBrief):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    total_earned: int = 0
    status: str = "active"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


TokenResponse.model_rebuild()
