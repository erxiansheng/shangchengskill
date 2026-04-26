# KV Storage (chunked_kv)

EdgeOne KV 单 value 上限较小（~1 MB 实际 base64 后约 700 KB 安全），不能直接
塞图片或 GLB。`chunked_kv.py` 用「**512 KB 切片 + base64 编码 + meta 索引**」把
KV 当成对象存储用，**完全不需要 S3**。

## 协议

- `CHUNK_SIZE = 512 * 1024` (raw bytes per chunk before base64)
- `MAX_ASSET_BYTES = 25 * 1024 * 1024` (硬上限 25 MB)
- 每个资产生成 12 字节随机 ID（urlsafe base64），形如 `asset_OabCdEfGhIjK`
- 写入：

  ```
  asset:{id}:meta            -> {content_type, size, sha256, chunks, created_at}
  asset:{id}:chunk:0         -> base64(<= 512KB raw)
  asset:{id}:chunk:1         -> ...
  ...
  ```

- 读取（流）：`stream_asset(kv, id)` 是 `async generator`，逐 chunk
  base64-decode 后 yield，配合 `StreamingResponse`，避免一次性把整个文件加载到
  Cloud Function 内存。
- 校验：写入时计算整体 SHA-256 存进 meta，读取端可选地核对。

## API surface

```python
from app.storage.chunked_kv import (
    put_asset, get_asset_meta, get_asset_bytes, stream_asset, delete_asset,
)

result = await put_asset(kv, content=bytes_obj, content_type="image/png")
# -> {"id": "...", "url": "/api/v1/assets/...", "size": ..., "sha256": "..."}
```

## 公开访问

`GET /api/v1/assets/{id}` 由 `cloud-functions/app/api/v1/assets.py` 实现：

- 返回 `Content-Type` 来自 meta
- `Cache-Control: public, max-age=31536000, immutable`
- `ETag: "{sha256}"`，命中 304 直接复用 CDN 缓存

## 切换到 S3

`upload.py` 顶部读 `site:settings.storage_mode`：

```python
def _storage_mode(settings) -> str:
    return (settings.get("storage_mode") or "kv").lower()
```

- `kv` → `chunked_kv.put_asset` → URL 形如 `/api/v1/assets/...`
- `s3` → `s3.upload_image / upload_skill_package` → URL 是 S3 公网/CDN

后台 `/admin/settings` 切换后，**新上传**走新存储；**旧资产**仍可访问（因为
URL 本身就指明了来源）。

## 不要做的事

- 不要把单个 chunk 写超 512 KB —— 部分 KV 区域 base64 后会触发 `value too
  large`。
- 不要在 `stream_asset` 内 `await asyncio.gather(*chunks)` —— 顺序 yield
  才能保证下游浏览器边收边渲染。
- 不要忘记 `MAX_ASSET_BYTES`，否则恶意用户能用单文件占满 KV 配额。
