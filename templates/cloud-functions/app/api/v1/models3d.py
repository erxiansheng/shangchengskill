"""3D model management for the homepage Logo3D component.

State is stored entirely in KV:

  models3d:list                -> [model_id, ...] (ordering = display order)
  models3d:item:{id}           -> {id, name, asset_id, scale, speed, bounds,
                                   enabled, order, created_at}

Binary .glb files live in chunked KV (asset:{id}:meta + chunks). The
public Logo3D component fetches /api/v1/models3d/active to learn which
models are currently enabled and their parameters; the actual mesh
bytes load from /api/v1/assets/{asset_id}.

Constraint: at most 5 enabled models at a time. Trying to enable a 6th
returns 400. Disabling/reordering is unrestricted.
"""

from __future__ import annotations

import time
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.api.v1.admin_auth import get_current_admin
from app.api.v1.deps import get_kv
from app.core.exceptions import AppException, ErrorCode, success_response
from app.storage import chunked_kv
from app.storage.kv import KVStore


MAX_ENABLED = 5
ALLOWED_TYPES = {"model/gltf-binary", "application/octet-stream"}
MAX_MODEL_BYTES = 8 * 1024 * 1024  # 8 MB per .glb


admin_router = APIRouter(prefix="/admin/models3d", tags=["admin-models3d"])
public_router = APIRouter(prefix="/models3d", tags=["models3d"])


class ModelParams(BaseModel):
    scale: float = Field(default=1.0, gt=0, le=20)
    speed_x: float = 0.5
    speed_y: float = 0.3
    speed_z: float = 0.4
    bounds_x: float = Field(default=2.0, gt=0, le=20)
    bounds_y: float = Field(default=1.5, gt=0, le=20)
    bounds_z: float = Field(default=1.5, gt=0, le=20)


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    order: Optional[int] = None
    params: Optional[ModelParams] = None


async def _load(kv: KVStore) -> list[dict]:
    ids = await kv.get_list("models3d:list") or []
    out: list[dict] = []
    for mid in ids:
        rec = await kv.get(f"models3d:item:{mid}")
        if rec:
            out.append(rec)
    out.sort(key=lambda r: (r.get("order", 999), r.get("created_at", 0)))
    return out


@public_router.get("/active")
async def list_active(kv: KVStore = Depends(get_kv)):
    """Public: enabled models for the Logo3D component to render."""
    items = await _load(kv)
    return success_response([
        {
            "id": r["id"],
            "name": r.get("name"),
            "asset_url": f"/api/v1/assets/{r['asset_id']}",
            "params": r.get("params", {}),
        }
        for r in items
        if r.get("enabled")
    ])


@admin_router.get("")
async def admin_list(_: dict = Depends(get_current_admin), kv: KVStore = Depends(get_kv)):
    return success_response(await _load(kv))


@admin_router.post("/upload")
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    enabled: bool = Form(False),
    _: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    if not file.filename.lower().endswith((".glb", ".gltf")):
        raise AppException(ErrorCode.PARAMS_ERROR, "仅支持 .glb / .gltf 文件")
    content = await file.read()
    if len(content) > MAX_MODEL_BYTES:
        raise AppException(
            ErrorCode.FILE_TOO_LARGE,
            f"模型文件超过 {MAX_MODEL_BYTES // (1024*1024)} MB",
        )

    if enabled:
        await _ensure_enable_quota(kv)

    asset = await chunked_kv.put_asset(kv, content, "model/gltf-binary")
    mid = secrets.token_urlsafe(8)
    rec = {
        "id": mid,
        "name": name,
        "asset_id": asset["id"],
        "size": len(content),
        "enabled": enabled,
        "order": int(time.time()),
        "params": ModelParams().model_dump(),
        "created_at": int(time.time()),
    }
    await kv.put(f"models3d:item:{mid}", rec)
    await kv.add_to_list("models3d:list", mid)
    return success_response(rec)


@admin_router.put("/{model_id}")
async def update_model(
    model_id: str,
    body: ModelUpdate,
    _: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    rec = await kv.get(f"models3d:item:{model_id}")
    if not rec:
        raise AppException(ErrorCode.NOT_FOUND, "模型不存在")

    if body.enabled is True and not rec.get("enabled"):
        await _ensure_enable_quota(kv)
    if body.enabled is not None:
        rec["enabled"] = bool(body.enabled)
    if body.name is not None:
        rec["name"] = body.name
    if body.order is not None:
        rec["order"] = body.order
    if body.params is not None:
        rec["params"] = body.params.model_dump()

    await kv.put(f"models3d:item:{model_id}", rec)
    return success_response(rec)


@admin_router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    _: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    rec = await kv.get(f"models3d:item:{model_id}")
    if not rec:
        raise AppException(ErrorCode.NOT_FOUND, "模型不存在")
    await chunked_kv.delete_asset(kv, rec["asset_id"])
    await kv.delete(f"models3d:item:{model_id}")
    await kv.remove_from_list("models3d:list", model_id)
    return success_response({"ok": True})


async def _ensure_enable_quota(kv: KVStore) -> None:
    items = await _load(kv)
    enabled_count = sum(1 for r in items if r.get("enabled"))
    if enabled_count >= MAX_ENABLED:
        raise AppException(
            ErrorCode.PARAMS_ERROR,
            f"最多同时启用 {MAX_ENABLED} 个 3D 模型，请先禁用其他模型",
        )
