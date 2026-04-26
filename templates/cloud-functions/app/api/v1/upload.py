import asyncio
import io
import re
import zipfile

from fastapi import APIRouter, Depends, UploadFile, File

from app.api.v1.deps import get_current_user, get_s3, get_kv
from app.core.exceptions import success_response, AppException, ErrorCode
from app.storage.kv import KVStore
from app.storage.s3 import S3Storage
from app.storage import chunked_kv

router = APIRouter(prefix="/upload", tags=["upload"])


def _storage_mode(site_settings: dict) -> str:
    """Resolve effective upload backend.

    The admin Settings panel writes `storage_mode` into KV under
    site:settings. Default is 'kv' (chunked KV, no external dep). Set
    to 's3' to push uploads through S3Storage (requires S3 creds also
    in site:settings).
    """
    mode = (site_settings or {}).get("storage_mode", "kv")
    return "s3" if mode == "s3" else "kv"


def _parse_skill_md(content: str) -> dict:
    """Parse SKILL.md content, extracting YAML front-matter and body."""
    result = {"title": None, "description": None, "full_description": content, "version": None, "tags": None}

    # Try to extract YAML front-matter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = fm_match.group(2).strip()
        result["full_description"] = body if body else content

        # Simple line-by-line YAML parsing (no pyyaml dependency)
        for line in fm_text.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip().strip('"').strip("'")
            if not val:
                continue
            if key in ('title', 'name'):
                result["title"] = val
            elif key == 'description':
                result["description"] = val
            elif key == 'version':
                result["version"] = val
            elif key == 'tags':
                # Handle comma-separated or YAML list on same line
                result["tags"] = [t.strip().strip('-').strip() for t in val.split(',') if t.strip()]

    # Fallback: extract description from first paragraph if not in front-matter
    if not result["description"] and result["full_description"]:
        lines = result["full_description"].strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                result["description"] = line[:200]
                break

    return result


def _process_zip_package(content: bytes) -> dict:
    """Open ZIP once to extract both SKILL.md metadata and file tree structure."""
    result: dict = {"skill_md": None, "file_tree": []}
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            md_path = None
            seen_dirs: set = set()
            entries = []

            for info in zf.infolist():
                name = info.filename
                if '/__MACOSX' in name or name.startswith('__MACOSX'):
                    continue
                is_dir = name.endswith('/')
                if is_dir:
                    seen_dirs.add(name.rstrip('/'))
                basename = name.split('/')[-1]
                depth = len(name.split('/')) - 1
                if basename.upper() == 'SKILL.MD' and depth <= 1:
                    md_path = name
                entries.append({
                    "name": name.rstrip('/'),
                    "is_dir": is_dir,
                    "size": info.file_size if not is_dir else 0,
                })

            if md_path:
                md_content = zf.read(md_path).decode('utf-8', errors='replace')
                result["skill_md"] = _parse_skill_md(md_content)

            # Synthesize missing directory entries from file paths
            implicit_dirs: set = set()
            for entry in entries:
                parts = entry["name"].split('/')
                for i in range(1, len(parts)):
                    parent = '/'.join(parts[:i])
                    if parent not in seen_dirs and parent not in implicit_dirs:
                        implicit_dirs.add(parent)
            for d in sorted(implicit_dirs):
                entries.append({"name": d, "is_dir": True, "size": 0})

            entries.sort(key=lambda e: (e["name"].count('/'), not e["is_dir"], e["name"].lower()))
            result["file_tree"] = entries
    except Exception:
        pass
    return result


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    s3: S3Storage = Depends(get_s3),
    kv: KVStore = Depends(get_kv),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise AppException(ErrorCode.FILE_TYPE_ERROR, "仅支持图片文件")
    content = await file.read()

    site_settings = await kv.get("site:settings") or {}
    s3.update_config(site_settings)
    max_size = int(site_settings.get("maxImageSize") or 5 * 1024 * 1024)
    if len(content) > max_size:
        raise AppException(ErrorCode.FILE_TOO_LARGE, f"图片过大（最大 {max_size // 1024 // 1024}MB）")

    mode = _storage_mode(site_settings)
    try:
        if mode == "s3":
            url = s3.upload_image(content, file.filename or "image.png", file.content_type)
        else:
            asset = await chunked_kv.put_asset(
                kv,
                content,
                file.content_type or "image/png",
            )
            url = asset["url"]
    except Exception as e:
        print(f"[Upload] Image upload failed (mode={mode}): {e}")
        raise AppException(ErrorCode.FILE_TYPE_ERROR, f"图片上传失败: {e}")
    return success_response({"url": url, "storage": mode})


@router.post("/skill-package")
async def upload_skill_package(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    s3: S3Storage = Depends(get_s3),
    kv: KVStore = Depends(get_kv),
):
    if not file.filename or not file.filename.endswith(".zip"):
        raise AppException(ErrorCode.FILE_TYPE_ERROR, "仅支持 .zip 格式文件")
    content = await file.read()

    # 并行：加载 site_settings + 单次打开 ZIP 解析（skill_md + file_tree），均不阻塞事件循环
    site_settings, zip_result = await asyncio.gather(
        kv.get("site:settings"),
        asyncio.to_thread(_process_zip_package, content),
    )
    site_settings = site_settings or {}
    s3.update_config(site_settings)

    max_size = int(site_settings.get("maxSkillPackageSize") or 50 * 1024 * 1024)
    if len(content) > max_size:
        raise AppException(ErrorCode.FILE_TOO_LARGE, f"文件过大（最大 {max_size // 1024 // 1024}MB）")

    if not zip_result.get("skill_md"):
        raise AppException(ErrorCode.SKILL_MD_MISSING,
            "技能包内未找到 SKILL.md 文件，请在 ZIP 根目录或一级子目录放置 SKILL.md 后重新上传")

    mode = _storage_mode(site_settings)
    try:
        if mode == "s3":
            result = await asyncio.to_thread(s3.upload_skill_package, content, file.filename)
        else:
            asset = await chunked_kv.put_asset(kv, content, "application/zip")
            result = {
                "url": asset["url"],
                "size": asset["size"],
                "hash": asset["sha256"],
                "original_filename": file.filename,
            }
    except Exception as e:
        print(f"[Upload] Package upload failed (mode={mode}): {e}")
        raise AppException(ErrorCode.FILE_TYPE_ERROR, f"商品包上传失败: {e}")

    result["storage"] = mode
    result["skill_md"] = zip_result["skill_md"]
    result["file_tree"] = zip_result["file_tree"]
    return success_response(result)
