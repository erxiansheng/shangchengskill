"""Public asset streaming route.

GET /api/v1/assets/{asset_id}
    Stream a chunked-KV-stored binary back to the browser. Sets the
    original content-type and a long Cache-Control so the EdgeOne edge
    layer (and any downstream CDN) can cache aggressively. The asset id
    is opaque and unguessable (12-byte token), so this is suitable for
    public product images, 3D model files (.glb), and other shareable
    binaries. For paid downloads gated by purchase, prefer the existing
    /api/v1/purchases/{id}/download route which checks ownership.
"""

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_kv
from app.core.exceptions import AppException, ErrorCode
from app.storage.kv import KVStore
from app.storage import chunked_kv


router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/{asset_id}")
async def get_asset(asset_id: str, kv: KVStore = Depends(get_kv)):
    meta = await chunked_kv.get_asset_meta(kv, asset_id)
    if not meta:
        raise AppException(ErrorCode.NOT_FOUND, "asset 不存在")

    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Length": str(meta.get("size", 0)),
        "ETag": f'"{meta.get("sha256", "")[:16]}"',
    }
    return StreamingResponse(
        chunked_kv.stream_asset(kv, asset_id),
        media_type=meta.get("content_type", "application/octet-stream"),
        headers=headers,
    )
