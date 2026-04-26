from pydantic import BaseModel
from typing import Optional, List


class TokenCreate(BaseModel):
    name: str
    scopes: List[str] = ["skill:publish", "skill:update"]
    expires_in_days: Optional[int] = 90


class TokenUpdate(BaseModel):
    name: Optional[str] = None
    scopes: Optional[List[str]] = None


class TokenResponse(BaseModel):
    id: int
    name: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    is_active: bool = True


class TokenCreated(TokenResponse):
    """Returned only at creation time — includes the plaintext token."""
    token: str
