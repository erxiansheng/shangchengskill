from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.exceptions import success_response
from app.core.security import generate_api_token
from app.schemas.token import TokenCreate, TokenUpdate
from app.storage.kv import KVStore
from app.api.v1.deps import get_kv, get_current_user

router = APIRouter(prefix="/tokens", tags=["tokens"])

VALID_SCOPES = {"skill:publish", "skill:update", "skill:read", "skill:purchase", "skill:download"}


@router.post("")
async def create_token(
    body: TokenCreate,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Create a new API token. The plaintext token is only shown once."""
    # Validate scopes
    invalid = set(body.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(400, f"无效的权限范围: {invalid}")

    plaintext, token_hash = generate_api_token()
    token_id = await kv.next_id("token")
    now = datetime.now(timezone.utc).isoformat()

    expires_at = None
    if body.expires_in_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()

    token_data = {
        "id": token_id,
        "user_id": user["id"],
        "name": body.name,
        "token_hash": token_hash,
        "scopes": body.scopes,
        "is_active": True,
        "last_used": None,
        "created_at": now,
        "expires_at": expires_at,
    }

    await kv.put(f"token:{token_id}", token_data)
    await kv.put(f"token:idx:hash:{token_hash}", token_id)
    await kv.add_to_list(f"token:by_user:{user['id']}", token_id)

    return success_response({
        "id": token_id,
        "name": body.name,
        "token": plaintext,
        "scopes": body.scopes,
        "is_active": True,
        "created_at": now,
        "expires_at": expires_at,
        "last_used": None,
    })


@router.get("")
async def list_tokens(
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """List all tokens for the current user (no plaintext)."""
    ids = await kv.get_list(f"token:by_user:{user['id']}")
    tokens = await kv.batch_get([f"token:{tid}" for tid in ids])
    result = []
    for t in tokens:
        if t:
            result.append({
                "id": t["id"],
                "name": t["name"],
                "scopes": t["scopes"],
                "is_active": t["is_active"],
                "created_at": t["created_at"],
                "expires_at": t.get("expires_at"),
                "last_used": t.get("last_used"),
            })
    return success_response(result)


@router.put("/{token_id}")
async def update_token(
    token_id: int,
    body: TokenUpdate,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Update a token's name or scopes."""
    token_data = await kv.get(f"token:{token_id}")
    if not token_data or token_data["user_id"] != user["id"]:
        raise HTTPException(404, "令牌不存在")

    if body.name is not None:
        token_data["name"] = body.name
    if body.scopes is not None:
        invalid = set(body.scopes) - VALID_SCOPES
        if invalid:
            raise HTTPException(400, f"无效的权限范围: {invalid}")
        token_data["scopes"] = body.scopes

    await kv.put(f"token:{token_id}", token_data)
    return success_response({
        "id": token_data["id"],
        "name": token_data["name"],
        "scopes": token_data["scopes"],
        "is_active": token_data["is_active"],
        "created_at": token_data["created_at"],
        "expires_at": token_data.get("expires_at"),
        "last_used": token_data.get("last_used"),
    })


@router.delete("/{token_id}")
async def revoke_token(
    token_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Delete a token permanently."""
    token_data = await kv.get(f"token:{token_id}")
    if not token_data or token_data.get("user_id") != user["id"]:
        raise HTTPException(404, "令牌不存在")

    # Remove hash index (may already be gone if token was disabled)
    try:
        token_hash = token_data.get("token_hash")
        if token_hash:
            await kv.delete(f"token:idx:hash:{token_hash}")
    except Exception:
        pass

    # Remove from user list (may fail if already removed)
    try:
        await kv.remove_from_list(f"token:by_user:{user['id']}", token_id)
    except Exception:
        pass

    # Delete the token data entirely
    try:
        await kv.delete(f"token:{token_id}")
    except Exception:
        pass

    return success_response({"message": "令牌已删除"})


@router.patch("/{token_id}/toggle")
async def toggle_token(
    token_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Toggle a token's active status (enable/disable)."""
    token_data = await kv.get(f"token:{token_id}")
    if not token_data or token_data["user_id"] != user["id"]:
        raise HTTPException(404, "令牌不存在")

    new_status = not token_data.get("is_active", True)
    token_data["is_active"] = new_status

    if new_status:
        # Re-enable: restore hash index
        await kv.put(f"token:idx:hash:{token_data['token_hash']}", token_id)
    else:
        # Disable: remove hash index so it can't be used
        try:
            await kv.delete(f"token:idx:hash:{token_data['token_hash']}")
        except Exception:
            # KV delete may fail on some platforms; clear by setting empty value
            await kv.put(f"token:idx:hash:{token_data['token_hash']}", "")

    await kv.put(f"token:{token_id}", token_data)

    return success_response({
        "id": token_data["id"],
        "name": token_data["name"],
        "is_active": new_status,
        "scopes": token_data["scopes"],
        "created_at": token_data["created_at"],
        "expires_at": token_data.get("expires_at"),
        "last_used": token_data.get("last_used"),
    })
