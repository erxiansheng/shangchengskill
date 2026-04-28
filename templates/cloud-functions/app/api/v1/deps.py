from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import decode_token, hash_api_token
from app.storage.kv import KVStore
from app.storage.s3 import S3Storage

security = HTTPBearer(auto_error=False)

# Module-level singletons (initialised once)
_kv_store: Optional[KVStore] = None
_s3_storage: Optional[S3Storage] = None


def init_storage():
    """Call once at app startup to initialise storage singletons."""
    global _kv_store, _s3_storage
    if _kv_store is not None:
        return  # Already initialised
    _kv_store = KVStore()
    _s3_storage = S3Storage()


def get_kv() -> KVStore:
    assert _kv_store is not None, "KVStore not initialised. Call init_storage() first."
    return _kv_store


def get_s3() -> S3Storage:
    assert _s3_storage is not None, "S3Storage not initialised. Call init_storage() first."
    return _s3_storage


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_token: Optional[str] = Header(None, alias="X-API-Token"),
    kv: KVStore = Depends(get_kv),
) -> dict:
    """Authenticate via JWT Bearer *or* API Token. Returns a user dict."""

    # --- Path 1: API Token (X-API-Token header or Bearer oc_xxx) ---
    token_str = x_api_token
    if not token_str and credentials:
        if credentials.credentials.startswith(settings.API_TOKEN_PREFIX):
            token_str = credentials.credentials

    if token_str:
        th = hash_api_token(token_str)
        token_id = await kv.get(f"token:idx:hash:{th}")
        if token_id is not None:
            token_data = await kv.get(f"token:{token_id}")
            if token_data and token_data.get("is_active"):
                # Check expiry
                if token_data.get("expires_at"):
                    exp = datetime.fromisoformat(token_data["expires_at"])
                    if exp < datetime.now(timezone.utc):
                        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API 令牌已过期")
                # Update last_used
                token_data["last_used"] = datetime.now(timezone.utc).isoformat()
                await kv.put(f"token:{token_id}", token_data)
                user = await kv.get(f"user:{token_data['user_id']}")
                if user and user.get("status") != "banned" and not user.get("is_banned"):
                    user["_token_scopes"] = token_data.get("scopes", [])
                    return user
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效的 API 令牌")

    # --- Path 2: JWT Bearer ---
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已过期")

    user_id = int(payload["sub"])
    user = await kv.get(f"user:{user_id}")
    if not user or user.get("status") == "banned" or user.get("is_banned"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已被封禁")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_token: Optional[str] = Header(None, alias="X-API-Token"),
    kv: KVStore = Depends(get_kv),
) -> Optional[dict]:
    """Same as get_current_user but returns None when not authenticated."""
    if not credentials and not x_api_token:
        return None
    try:
        return await get_current_user(credentials, x_api_token, kv)
    except HTTPException:
        return None


async def get_current_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    # 第一个注册用户(id=1)自动为管理员
    if user.get("id") != 1 and user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


def require_scope(scope: str):
    """Return a dependency that checks the token carries *scope*.
    JWT-authenticated users always pass (they have full access)."""

    async def _check(user: dict = Depends(get_current_user)):
        scopes = user.get("_token_scopes")
        if scopes is not None and scope not in scopes:
            from app.core.exceptions import AppException, ErrorCode
            raise AppException(
                ErrorCode.PERMISSION_DENIED,
                f"API 令牌缺少权限: {scope}。请使用网页/小程序登录，或创建包含该权限的新令牌",
                status_code=403
            )
        return user

    return _check
