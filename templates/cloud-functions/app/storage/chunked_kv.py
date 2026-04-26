"""Chunked binary storage on top of EdgeOne KV.

EdgeOne KV's per-value sweet spot is < 1 MB. To safely store binary assets
(product cover images, screenshots, GLB 3D models, miniprogram QR codes,
etc.) directly in KV without an object storage dependency, we slice the
payload into 512 KB chunks and persist:

  asset:{id}:meta         -> {content_type, size, sha256, chunk_count, created_at}
  asset:{id}:chunk:{n}    -> base64-encoded raw bytes (one slice)

A single asset id is exposed publicly via /api/v1/assets/{id}; the
streaming route concatenates chunks in order. When the operator switches
storage_mode to "s3" via the admin Settings panel, new uploads bypass
chunked KV and go straight to S3Storage; previously stored KV-resident
assets remain readable through the same /assets/{id} URL.

This module is dependency-free (only stdlib + KVStore) so it works
inside the EdgeOne Pages Python Cloud Function runtime without extra
requirements.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from typing import AsyncIterator, Optional

from app.storage.kv import KVStore


CHUNK_SIZE = 512 * 1024  # 512 KB per slice
MAX_ASSET_BYTES = 25 * 1024 * 1024  # hard cap: 25 MB per asset


def _new_asset_id() -> str:
    # 16-char url-safe id, collision-resistant enough for KV namespace
    return secrets.token_urlsafe(12)


async def put_asset(
    kv: KVStore,
    content: bytes,
    content_type: str,
    *,
    asset_id: Optional[str] = None,
) -> dict:
    """Store binary content as KV chunks. Returns {id, url, size, sha256}."""
    if not content:
        raise ValueError("empty content")
    if len(content) > MAX_ASSET_BYTES:
        raise ValueError(f"asset exceeds {MAX_ASSET_BYTES // (1024*1024)} MB cap")

    aid = asset_id or _new_asset_id()
    sha = hashlib.sha256(content).hexdigest()

    # Slice and write chunks
    chunks = [content[i : i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
    for idx, chunk in enumerate(chunks):
        encoded = base64.b64encode(chunk).decode("ascii")
        await kv.put(f"asset:{aid}:chunk:{idx}", encoded)

    meta = {
        "id": aid,
        "content_type": content_type or "application/octet-stream",
        "size": len(content),
        "sha256": sha,
        "chunk_count": len(chunks),
        "chunk_size": CHUNK_SIZE,
        "created_at": int(time.time()),
    }
    await kv.put(f"asset:{aid}:meta", meta)

    return {
        "id": aid,
        "url": f"/api/v1/assets/{aid}",
        "size": len(content),
        "sha256": sha,
        "content_type": meta["content_type"],
    }


async def get_asset_meta(kv: KVStore, asset_id: str) -> Optional[dict]:
    return await kv.get(f"asset:{asset_id}:meta")


async def get_asset_bytes(kv: KVStore, asset_id: str) -> Optional[tuple[bytes, dict]]:
    """Read the entire asset back into memory. Returns (bytes, meta) or None."""
    meta = await get_asset_meta(kv, asset_id)
    if not meta:
        return None
    parts: list[bytes] = []
    for idx in range(int(meta.get("chunk_count", 0))):
        encoded = await kv.get(f"asset:{asset_id}:chunk:{idx}")
        if not encoded:
            raise RuntimeError(f"asset {asset_id} missing chunk {idx}")
        parts.append(base64.b64decode(encoded))
    return b"".join(parts), meta


async def stream_asset(kv: KVStore, asset_id: str) -> AsyncIterator[bytes]:
    """Generator yielding chunks in order. Use for FastAPI StreamingResponse."""
    meta = await get_asset_meta(kv, asset_id)
    if not meta:
        return
    for idx in range(int(meta.get("chunk_count", 0))):
        encoded = await kv.get(f"asset:{asset_id}:chunk:{idx}")
        if encoded:
            yield base64.b64decode(encoded)


async def delete_asset(kv: KVStore, asset_id: str) -> bool:
    meta = await get_asset_meta(kv, asset_id)
    if not meta:
        return False
    for idx in range(int(meta.get("chunk_count", 0))):
        await kv.delete(f"asset:{asset_id}:chunk:{idx}")
    await kv.delete(f"asset:{asset_id}:meta")
    return True
