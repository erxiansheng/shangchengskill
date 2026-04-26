"""
KV Storage client for EdgeOne Pages KV.

Production mode: calls the Edge Function's KV proxy endpoint via HTTP.
MY_KV binding is only available in Edge Functions (JS), so the Python
Cloud Function accesses KV through an internal HTTP proxy exposed by
the Edge Function at /api/_internal/kv.

The Edge Function passes X-Internal-Origin on every forwarded request,
which is used to derive the proxy URL.
"""

from __future__ import annotations

import os
import json
import asyncio
import urllib.request
import urllib.error
from typing import Any, Optional

# 与 Edge Function 二者都从 Pages 环境变量 `INTERNAL_KEY` 读取。
# fallback 仅用于本地开发。生产环境未设置会被 Edge Function 拒绝。
_INTERNAL_KEY = os.environ.get("INTERNAL_KEY", "EdgeOneMall_internal_2026")


class KVStore:
    """HTTP-based KV storage client that proxies through the Edge Function."""

    def __init__(self):
        self._origin: Optional[str] = None

    def set_origin(self, origin: str):
        """Set the origin URL for the KV proxy (e.g. https://YOUR_DOMAIN_HERE)."""
        self._origin = origin.rstrip("/")
        print(f"[KV] Origin set to {self._origin}")

    @property
    def ready(self) -> bool:
        return self._origin is not None

    # ------------------------------------------------------------------
    # Internal HTTP call
    # ------------------------------------------------------------------

    def _post_sync(self, payload: dict, timeout: int = 15) -> Any:
        if not self._origin:
            raise RuntimeError(
                "[KV] 未配置 KV 代理地址。"
                "请确保请求经过 Edge Function 转发并携带 X-Internal-Origin 头。"
            )
        url = f"{self._origin}/api/_internal/kv"
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": _INTERNAL_KEY,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                return data.get("result")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"[KV] 代理返回 HTTP {e.code}: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"[KV] 访问 KV 代理失败: {e}") from e

    async def _post(self, payload: dict, timeout: int = 15) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._post_sync, payload, timeout)

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[dict | list | str | int]:
        return await self._post({"action": "get", "key": key})

    async def get_fresh(self, key: str) -> Optional[dict | list | str | int]:
        """强制跳过边缘缓存读取，用于注册等需要强一致性的场景"""
        return await self._post({"action": "get_fresh", "key": key})

    async def claim_register(self, openid_key: str) -> bool:
        """边缘侧注册去重锁，返回 True 表示成功获取锁（允许注册）"""
        result = await self._post({"action": "claim_register", "key": openid_key})
        return bool(result)

    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self._post({"action": "put", "key": key, "value": value})

    async def delete(self, key: str) -> None:
        await self._post({"action": "delete", "key": key})

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def batch_get(self, keys: list[str], timeout: int = 15) -> list[Optional[dict]]:
        if not keys:
            return []
        result = await self._post({"action": "batch_get", "keys": keys}, timeout=timeout)
        return list(result) if result else []

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    async def get_list(self, key: str) -> list:
        result = await self._post({"action": "get_list", "key": key})
        return list(result) if isinstance(result, list) else []

    async def add_to_list(self, key: str, item_id: int | str) -> None:
        await self._post({"action": "add_to_list", "key": key, "item_id": item_id})

    async def remove_from_list(self, key: str, item_id: int | str) -> None:
        await self._post({"action": "remove_from_list", "key": key, "item_id": item_id})

    # ------------------------------------------------------------------
    # Auto-increment ID
    # ------------------------------------------------------------------

    async def next_id(self, entity: str) -> int:
        result = await self._post({"action": "next_id", "entity": entity})
        return int(result)

    # ------------------------------------------------------------------
    # Key listing & bulk ops (for backup/restore)
    # ------------------------------------------------------------------

    async def list_all_keys(self) -> list[str]:
        """List ALL keys in the KV store (paginated internally)."""
        return await self.list_keys(prefix=None)

    async def list_keys(self, prefix: Optional[str] = None, limit: int = 256, timeout: int = 30) -> list[str]:
        """List keys by optional prefix (paginated internally)."""
        all_keys = []
        cursor = None
        while True:
            payload = {"action": "list_keys", "limit": min(limit, 256)}  # EdgeOne KV max limit is 256
            if prefix:
                payload["prefix"] = prefix
            if cursor:
                payload["cursor"] = cursor
            result = await self._post(payload, timeout=timeout)
            all_keys.extend(result.get("keys", []))
            if result.get("list_complete", True):
                break
            cursor = result.get("cursor")
            if not cursor:
                break
        return all_keys

    async def dump_all(self, timeout: int = 120) -> dict:
        """一次性导出所有 KV 数据（边缘直读，无多次 HTTP 往返）"""
        raw = await self._post({"action": "dump_all"}, timeout=timeout)
        # The edge function may return {result: data, errors: [...]}
        # _post extracts .result, but we need errors separately
        return raw if isinstance(raw, dict) else {}

    async def dump_all_with_errors(self, timeout: int = 120) -> tuple:
        """导出所有 KV 数据，同时返回错误列表"""
        if not self._origin:
            raise RuntimeError("[KV] 未配置 KV 代理地址。")
        url = f"{self._origin}/api/_internal/kv"
        payload = {"action": "dump_all"}
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": _INTERNAL_KEY,
            },
        )
        loop = asyncio.get_running_loop()
        def _do():
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        raw = await loop.run_in_executor(None, _do)
        data = raw.get("result", {})
        errors = raw.get("errors", [])
        return (data if isinstance(data, dict) else {}, errors)

    async def bulk_put(self, pairs: list[dict]) -> int:
        """Bulk put key-value pairs. pairs = [{"key": "...", "value": ...}, ...]"""
        # Split into batches of 50 to avoid timeouts
        count = 0
        for i in range(0, len(pairs), 50):
            batch = pairs[i:i + 50]
            await self._post({"action": "bulk_put", "pairs": batch})
            count += len(batch)
        return count

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        pass
