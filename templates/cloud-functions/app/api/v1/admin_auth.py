"""Admin authentication: separate token scope from regular users.

Backed by KV. A first-run seed creates one admin from the
ADMIN_INIT_USERNAME / ADMIN_INIT_PASSWORD environment variables (set
during EdgeOne Pages deploy). Tokens issued here include scope="admin"
in the JWT payload so the user-facing /api/v1/* routes can reject them
and vice versa.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
# Use PyJWT (already pinned in requirements.txt). python-jose is intentionally
# NOT a dependency — importing it here used to crash the whole Cloud Function
# at module-load time and surfaced as the EdgeOne "544 Unknown Status" on
# /api/v1/admin/auth/login (because FastAPI never finished booting and KV seed
# never ran). See SKILL.md error-recovery table.
import jwt
from pydantic import BaseModel

from app.api.v1.deps import get_kv
from app.core.config import settings
from app.core.exceptions import AppException, ErrorCode, success_response
from app.core.security import hash_password, verify_password
from app.storage.kv import KVStore


router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


# JWT helpers — separate scope from user tokens
ADMIN_TOKEN_TTL_MIN = 60 * 4  # 4 hours


def issue_admin_token(admin_id: str) -> str:
    payload = {
        "sub": str(admin_id),
        "scope": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=ADMIN_TOKEN_TTL_MIN),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_admin_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("scope") != "admin":
        return None
    return payload


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
    rec = await kv.get(f"admin:user:{body.username.lower()}")
    if not rec or not verify_password(body.password, rec.get("password_hash", "")):
        raise AppException(ErrorCode.PASSWORD_ERROR, "用户名或密码错误")
    if rec.get("disabled"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "管理员账号已禁用")

    token = issue_admin_token(rec["username"])
    return success_response({
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": bool(rec.get("must_change_password")),
        "username": rec["username"],
    })


async def get_current_admin(request: Request, kv: KVStore = Depends(get_kv)) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise AppException(ErrorCode.NOT_AUTHENTICATED, "缺少管理员令牌", status_code=401)
    payload = verify_admin_token(auth.split(" ", 1)[1].strip())
    if not payload:
        raise AppException(ErrorCode.NOT_AUTHENTICATED, "管理员令牌无效或已过期", status_code=401)
    rec = await kv.get(f"admin:user:{payload['sub']}")
    if not rec or rec.get("disabled"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "管理员不存在或已禁用")
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
    admin["password_hash"] = hash_password(body.new_password)
    admin["must_change_password"] = False
    admin["password_changed_at"] = datetime.utcnow().isoformat()
    await kv.put(f"admin:user:{admin['username']}", admin)
    return success_response({"ok": True})


@router.get("/me")
async def me(admin: dict = Depends(get_current_admin)):
    return success_response({
        "username": admin["username"],
        "must_change_password": bool(admin.get("must_change_password")),
        "created_at": admin.get("created_at"),
    })


# First-run seed helper, called from main.py lifespan
async def seed_default_admin(kv: KVStore):
    """Create the bootstrap admin if none exists yet."""
    existing = await kv.get_list("admin:list")
    if existing:
        return

    username = os.getenv("ADMIN_INIT_USERNAME", "admin").lower()
    password = os.getenv("ADMIN_INIT_PASSWORD", "change_me_on_first_login")
    rec = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
        "must_change_password": True,
        "disabled": False,
    }
    await kv.put(f"admin:user:{username}", rec)
    await kv.add_to_list("admin:list", username)
    print(f"[Admin Seed] Bootstrap admin '{username}' created. CHANGE PASSWORD ON FIRST LOGIN.")
