"""Admin login compatibility endpoint.

The admin console uses the same account system as the storefront. The first
registered user is promoted to role="admin" and can log in here with the same
username/password. No bootstrap admin account or secondary admin password is
created.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.v1.deps import get_kv
from app.core.exceptions import AppException, ErrorCode, success_response
from app.core.security import create_access_token, decode_token, verify_password
from app.storage.kv import KVStore


router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


# Schemas
class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# Routes
@router.post("/login")
async def admin_login(body: AdminLoginRequest, kv: KVStore = Depends(get_kv)):
    user_id = await kv.get(f"user:idx:username:{body.username}")
    if user_id is None:
        raise AppException(ErrorCode.PASSWORD_ERROR, "用户名或密码错误")
    rec = await kv.get(f"user:{user_id}")
    if not rec or not verify_password(body.password, rec.get("password_hash", "")):
        raise AppException(ErrorCode.PASSWORD_ERROR, "用户名或密码错误")
    if rec.get("id") != 1 and rec.get("role") != "admin":
        raise AppException(ErrorCode.PERMISSION_DENIED, "需要管理员权限")
    if rec.get("status") == "banned" or rec.get("is_banned"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁")

    token = create_access_token(rec["id"])
    return success_response({
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": False,
        "username": rec["username"],
        "user": {"id": rec["id"], "role": rec.get("role", "user"), "nickname": rec.get("nickname")},
    })


async def get_current_admin(request: Request, kv: KVStore = Depends(get_kv)) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise AppException(ErrorCode.NOT_AUTHENTICATED, "缺少管理员令牌", status_code=401)
    payload = decode_token(auth.split(" ", 1)[1].strip())
    if not payload or payload.get("type") != "access":
        raise AppException(ErrorCode.NOT_AUTHENTICATED, "管理员令牌无效或已过期", status_code=401)
    rec = await kv.get(f"user:{payload['sub']}")
    if not rec or (rec.get("id") != 1 and rec.get("role") != "admin"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "需要管理员权限")
    return rec


@router.post("/change-password")
async def change_password(
    body: AdminChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    if not verify_password(body.old_password, admin["password_hash"]):
        raise AppException(ErrorCode.PASSWORD_ERROR, "原密码不正确")
    if len(body.new_password) < 8:
        raise AppException(ErrorCode.PARAMS_ERROR, "新密码至少 8 位")
    from app.core.security import hash_password
    admin["password_hash"] = hash_password(body.new_password)
    admin["updated_at"] = datetime.utcnow().isoformat()
    await kv.put(f"user:{admin['id']}", admin)
    return success_response({"ok": True})


@router.get("/me")
async def me(admin: dict = Depends(get_current_admin)):
    return success_response({
        "username": admin["username"],
        "must_change_password": False,
        "created_at": admin.get("created_at"),
    })


# First-run seed helper, called from main.py lifespan
async def seed_default_admin(kv: KVStore):
    """No-op: the first registered storefront user becomes admin."""
    return
