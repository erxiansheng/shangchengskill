import asyncio
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.api.v1.deps import get_kv, get_s3, get_current_user, get_current_user_optional, require_scope
from app.core.exceptions import success_response, AppException, ErrorCode, paginated_response
from app.core.levels import get_level_info
from app.core.skill_titles import assert_skill_title_unique, find_duplicate_skill_id_by_title, sync_skill_title_index
from app.schemas.skill import SkillCreate, SkillUpdate, VersionCreate
from app.storage.kv import KVStore
from app.storage.s3 import S3Storage

# ── 内存缓存：避免每次请求都重新从 KV 加载全部技能 ──
_skill_list_cache = {"data": None, "ids": None, "ts": 0}
_SKILL_CACHE_TTL = 120  # 秒（与 Edge Function 缓存 TTL 对齐）


def _invalidate_skill_cache():
    """技能创建/更新/上下线/删除时清除列表缓存"""
    _skill_list_cache["data"] = None
    _skill_list_cache["ts"] = 0

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    category_id: Optional[int] = None,
    sort: str = Query("newest"),
    keyword: Optional[str] = None,
    is_free: Optional[bool] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    min_rating: Optional[int] = None,
    kv: KVStore = Depends(get_kv),
):
    # 使用内存缓存：避免每次请求都重新从 KV 加载全部技能
    now = time.monotonic()
    if _skill_list_cache["data"] is not None and (now - _skill_list_cache["ts"]) < _SKILL_CACHE_TTL:
        items_raw = list(_skill_list_cache["data"])  # 浅拷贝
    else:
        skill_ids = await kv.get_list("skill:by_status:approved")
        if not skill_ids:
            return paginated_response([], 0, page, page_size)
        skills = await kv.batch_get([f"skill:{sid}" for sid in skill_ids])
        items_raw = [s for s in skills if s]
        _skill_list_cache["data"] = items_raw
        _skill_list_cache["ids"] = skill_ids
        _skill_list_cache["ts"] = now

    # Apply filters
    if category_id:
        items_raw = [s for s in items_raw if s.get("category_id") == category_id]
    if keyword:
        kw = keyword.lower()
        items_raw = [s for s in items_raw if kw in (s.get("title", "").lower()) or kw in (s.get("description", "").lower())]
    if is_free is not None:
        items_raw = [s for s in items_raw if s.get("is_free") == is_free]
    if price_min is not None:
        items_raw = [s for s in items_raw if s.get("price", 0) >= price_min]
    if price_max is not None:
        items_raw = [s for s in items_raw if s.get("price", 0) <= price_max]
    if min_rating is not None:
        items_raw = [s for s in items_raw if s.get("avg_rating", 0) >= min_rating]

    # Sort
    if sort == "hot":
        items_raw.sort(key=lambda s: s.get("download_count", 0), reverse=True)
    elif sort == "rating":
        items_raw.sort(key=lambda s: s.get("avg_rating", 0), reverse=True)
    else:
        items_raw.sort(key=lambda s: s.get("created_at", ""), reverse=True)

    total = len(items_raw)
    start = (page - 1) * page_size
    page_skills = items_raw[start:start + page_size]

    # 并行加载 author、category、site settings（原来是串行 3 次 HTTP）
    author_ids = list({s["user_id"] for s in page_skills})
    cat_ids = list({s["category_id"] for s in page_skills if s.get("category_id")})

    coros = [
        kv.batch_get([f"user:{uid}" for uid in author_ids]),
        kv.get("site:settings"),
    ]
    if cat_ids:
        coros.append(kv.batch_get([f"cat:{cid}" for cid in cat_ids]))

    results = await asyncio.gather(*coros)
    authors = results[0]
    site_settings = results[1] or {}
    cats = results[2] if cat_ids else []

    author_map = {a["id"]: a for a in authors if a}
    cat_map = {c["id"]: c for c in cats if c}
    cfg_levels = site_settings.get("levelsConfig") or None

    items = []
    for s in page_skills:
        author = author_map.get(s["user_id"], {})
        cat = cat_map.get(s.get("category_id"), {})
        items.append({
            "id": s["id"],
            "title": s["title"],
            "subtitle": s.get("subtitle") or "",
            "price": s["price"],
            "is_free": s.get("is_free", False),
            "cover_image": s.get("cover_image"),
            "version": s.get("version", "1.0.0"),
            "avg_rating": s.get("avg_rating", 0),
            "review_count": s.get("review_count", 0),
            "download_count": s.get("download_count", 0),
            "purchase_count": s.get("purchase_count", 0),
            "tags": s.get("tags") or [],
            "category_name": cat.get("name"),
            "author_id": s["user_id"],
            "author_name": author.get("nickname"),
            "author_avatar": author.get("avatar_url"),
            "author_role": author.get("role", "user"),
            "author_level_info": get_level_info(author.get("exp", 0), levels=cfg_levels),
            "status": s["status"],
            "created_at": s.get("created_at"),
        })

    return paginated_response(items, total, page, page_size)


@router.get("/my")
async def my_skills(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    start = (page - 1) * page_size
    skill_ids = await kv.get_list(f"skill:by_user:{user['id']}")
    if not skill_ids:
        return paginated_response([], 0, page, page_size)

    # by_user 列表按创建顺序追加，倒序即可得到最新发布优先的分页顺序
    ordered_skill_ids = list(reversed(skill_ids))

    if status and status != "all":
        skills = await kv.batch_get([f"skill:{sid}" for sid in ordered_skill_ids])
        items_raw = [s for s in skills if s and s.get("status") == status]
        total = len(items_raw)
        page_skills = items_raw[start:start + page_size]
    else:
        total = len(ordered_skill_ids)
        page_skill_ids = ordered_skill_ids[start:start + page_size]
        if not page_skill_ids:
            return paginated_response([], total, page, page_size)
        page_skills_raw = await kv.batch_get([f"skill:{sid}" for sid in page_skill_ids])
        page_skills = [s for s in page_skills_raw if s]

    items = [{
        "id": s["id"],
        "title": s["title"],
        "description": (s.get("description") or "")[:200],
        "price": s["price"],
        "is_free": s.get("is_free", False),
        "cover_image": s.get("cover_image"),
        "version": s.get("version", "1.0.0"),
        "avg_rating": s.get("avg_rating", 0),
        "download_count": s.get("download_count", 0),
        "status": s["status"],
        "reject_reason": s.get("reject_reason"),
        "offline_reason": s.get("offline_reason"),
        "tags": s.get("tags") or [],
        "created_at": s.get("created_at"),
        "updated_at": s.get("updated_at"),
    } for s in page_skills]

    return paginated_response(items, total, page, page_size)


@router.get("/{skill_id}")
async def get_skill_detail(skill_id: str, kv: KVStore = Depends(get_kv), user: Optional[dict] = Depends(get_current_user_optional)):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
    if skill.get("status") == "deleted":
        is_admin = user and user.get("role") == "admin"
        if not is_admin:
            raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    # 并行加载 author、category、site_settings、image ids、version ids（原来是 5 次串行 KV 请求）
    coros = [
        kv.get(f"user:{skill['user_id']}"),
        kv.get("site:settings"),
        kv.get_list(f"si:by_skill:{skill_id}"),
        kv.get_list(f"sv:by_skill:{skill_id}"),
    ]
    if skill.get("category_id"):
        coros.append(kv.get(f"cat:{skill['category_id']}"))

    results = await asyncio.gather(*coros)
    author = results[0]
    site_settings = results[1] or {}
    image_ids = results[2]
    version_ids = results[3]
    cat = results[4] if skill.get("category_id") else None

    cfg_levels = site_settings.get("levelsConfig") or None

    # 并行加载图片和版本数据
    images_data, versions_data = await asyncio.gather(
        kv.batch_get([f"si:{iid}" for iid in image_ids]),
        kv.batch_get([f"sv:{vid}" for vid in version_ids]),
    )
    images = sorted([i for i in images_data if i], key=lambda x: x.get("sort_order", 0))
    image_urls = [i["image_url"] for i in images]

    versions = sorted([v for v in versions_data if v], key=lambda x: x.get("created_at", ""), reverse=True)

    return success_response({
        "id": skill["id"],
        "title": skill["title"],
        "subtitle": skill.get("subtitle"),
        "description": skill.get("description"),
        "price": skill["price"],
        "is_free": skill.get("is_free", False),
        "cover_image": skill.get("cover_image"),
        "file_url": skill.get("file_url"),
        "file_size": skill.get("file_size"),
        "original_filename": skill.get("original_filename"),
        "version": skill.get("version", "1.0.0"),
        "avg_rating": skill.get("avg_rating", 0),
        "review_count": skill.get("review_count", 0),
        "download_count": skill.get("download_count", 0),
        "purchase_count": skill.get("purchase_count", 0),
        "tags": skill.get("tags") or [],
        "status": skill["status"],
        "category_name": cat.get("name") if cat else None,
        "category_id": skill.get("category_id"),
        "author_id": skill["user_id"],
        "author_name": author.get("nickname") if author else None,
        "author_avatar": author.get("avatar_url") if author else None,
        "author_role": author.get("role", "user") if author else "user",
        "author_level_info": get_level_info(author.get("exp", 0), levels=cfg_levels) if author else get_level_info(0, levels=cfg_levels),
        "images": image_urls,
        "screenshots": skill.get("screenshots") or [],
        "installation_guide": skill.get("installation_guide"),
        "versions": [{
            "id": v["id"], "version": v["version"],
            "changelog": v.get("changelog"),
            "created_at": v.get("created_at"),
        } for v in versions],
        "created_at": skill.get("created_at"),
        "published_at": skill.get("published_at"),
        "file_tree": skill.get("file_tree") or [],
    })


@router.get("/{skill_id}/file-tree")
async def get_file_tree(skill_id: str, kv: KVStore = Depends(get_kv), user: Optional[dict] = Depends(get_current_user_optional)):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
    if skill.get("status") == "deleted":
        is_admin = user and user.get("role") == "admin"
        if not is_admin:
            raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
    return success_response(skill.get("file_tree") or [])


@router.post("")
async def create_skill(
    data: SkillCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_scope("skill:publish")),
    kv: KVStore = Depends(get_kv),
    s3: S3Storage = Depends(get_s3),
):
    # 校验必填字段
    # 实体商品 (product_type=physical) 不要求上传文件；纯数字商品 (digital) 仍要求 file_url。
    is_physical = (data.product_type or "digital") == "physical"
    if not is_physical and not data.file_url:
        raise AppException(ErrorCode.PARAMS_ERROR, "请先上传技能包文件（file_url 不能为空）。流程：先调用 POST /upload/skill-package 上传 ZIP，再用返回的 url 创建技能")

    # 现金售卖必须有有效的 cash_price_yuan（除非显式标记免费）
    sale_mode = data.sale_mode or "points"
    if sale_mode in ("cash", "both") and not data.is_free and (data.cash_price_yuan or 0) <= 0:
        raise AppException(ErrorCode.PARAMS_ERROR, "启用现金售卖时必须设置 cash_price_yuan > 0")

    # 非管理员限制：每人最多发布 200 个技能（更新不计，已删除的不计）
    is_admin = user.get("role") == "admin"
    if not is_admin:
        user_skill_ids = await kv.get_list(f"skill:by_user:{user['id']}")
        if user_skill_ids:
            user_skills = await kv.batch_get([f"skill:{sid}" for sid in user_skill_ids])
            active_count = sum(1 for s in user_skills if s and s.get("status") != "deleted")
            if active_count >= 200:
                raise AppException(ErrorCode.PUBLISH_LIMIT_EXCEEDED, "每位用户最多发布 200 个技能，请删除不需要的技能后重试")

    await assert_skill_title_unique(kv, data.title)

    now = datetime.now(timezone.utc).isoformat()
    skill_id = secrets.token_hex(8)

    # 管理员发布直接通过审核，无需等待（is_admin 在上方发布限制检查中已确定）
    initial_status = "approved" if is_admin else "pending"

    skill = {
        "id": skill_id,
        "user_id": user["id"],
        "title": data.title,
        "subtitle": data.subtitle,
        "description": data.description,
        "category_id": data.category_id,
        "price": data.price,
        "tags": data.tags,
        "is_free": data.is_free or data.price == 0,
        "cover_image": data.cover_image,
        "file_url": data.file_url,
        "file_size": data.file_size,
        "file_hash": data.file_hash,
        "original_filename": data.original_filename,
        "version": data.version,
        "screenshots": data.screenshots or [],
        "installation_guide": data.installation_guide,
        "file_tree": data.file_tree or [],
        # Generic-product fields
        "product_type": data.product_type or "digital",
        "sale_mode": sale_mode,
        "cash_price_yuan": float(data.cash_price_yuan or 0),
        "stock": data.stock,
        "shipping_fee_yuan": float(data.shipping_fee_yuan or 0),
        "shipping_required": bool(data.shipping_required) or is_physical,
        "download_count": 0,
        "purchase_count": 0,
        "avg_rating": 0,
        "review_count": 0,
        "status": initial_status,
        "reject_reason": None,
        "created_at": now,
        "updated_at": now,
        "published_at": now if is_admin else None,
    }

    await kv.put(f"skill:{skill_id}", skill)
    await kv.add_to_list(f"skill:by_user:{user['id']}", skill_id)
    if data.category_id:
        await kv.add_to_list(f"skill:by_cat:{data.category_id}", skill_id)
    await kv.add_to_list(f"skill:by_status:{initial_status}", skill_id)
    await sync_skill_title_index(kv, skill)

    # Create initial version
    ver_id = await kv.next_id("sv")
    version = {
        "id": ver_id,
        "skill_id": skill_id,
        "version": data.version,
        "changelog": "初始版本",
        "file_url": data.file_url or "",
        "file_size": data.file_size,
        "file_hash": data.file_hash,
        "status": "approved",
        "created_at": now,
    }
    await kv.put(f"sv:{ver_id}", version)
    await kv.add_to_list(f"sv:by_skill:{skill_id}", ver_id)

    _invalidate_skill_cache()

    # 管理员直接通过：更新用户统计缓存
    if is_admin:
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, user["id"], skill_delta=1)

    # 管理员发布无需自动审核；普通用户触发 VirusTotal 审核
    if not is_admin:
        background_tasks.add_task(_auto_review_skill, skill_id, kv, s3)

    return success_response({"id": skill_id, "status": initial_status})


async def _auto_review_skill(skill_id: str, kv: KVStore, s3: S3Storage):
    """VirusTotal 自动审核引擎（异步后台运行）。

    流程：哈希查询 → 未收录则上传文件扫描 → 轮询结果 → 更新状态。
    若未配置 API Key 则拒绝。
    """
    import asyncio
    import httpx

    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill.get("status") != "pending":
        return

    reject_reason = None
    vt_result = None

    site_settings = await kv.get("site:settings") or {}
    s3.update_config(site_settings)
    vt_key = site_settings.get("vtApiKey", "")
    file_hash = skill.get("file_hash")
    file_url = skill.get("file_url")

    # 实体商品（physical）不上传 ZIP，无可扫描内容，直接放行 VT 阶段；
    # 仍走标题查重，且仍写一条 audit 记录，方便管理员追溯。
    is_physical = (skill.get("product_type") or "digital") == "physical"
    if is_physical:
        vt_result = "skipped_physical"
    elif not vt_key:
        reject_reason = "未配置 VirusTotal API Key，无法进行安全审核，请联系管理员"
        vt_result = "skipped"
    elif not file_hash and not file_url:
        reject_reason = "技能未提供文件，无法进行安全校验"
        vt_result = "skipped"
    else:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {"x-apikey": vt_key}

                # Step 1: Try hash lookup (fast path)
                if file_hash:
                    resp = await client.get(
                        f"https://www.virustotal.com/api/v3/files/{file_hash}",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        stats = resp.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                        malicious = stats.get("malicious", 0)
                        suspicious = stats.get("suspicious", 0)
                        if malicious > 0 or suspicious > 0:
                            reject_reason = f"VirusTotal 检测到安全风险（{malicious} 个引擎报告恶意，{suspicious} 个引擎报告可疑）"
                            vt_result = "malicious"
                        else:
                            vt_result = "clean"
                    elif resp.status_code == 429:
                        reject_reason = "VirusTotal API 频率限制，请稍后重新提交"
                        vt_result = "rate_limited"
                    elif resp.status_code in (401, 403):
                        reject_reason = "VirusTotal API Key 无效或已过期，请联系管理员"
                        vt_result = "error"
                    elif resp.status_code != 404:
                        reject_reason = f"VirusTotal 审核服务异常（HTTP {resp.status_code}），请稍后重试"
                        vt_result = "error"
                    # 404 = not found, proceed to upload

                # Step 2: Upload file to VT for scanning (if hash not found)
                if vt_result is None and file_url:
                    file_bytes = await asyncio.to_thread(s3.get_file_bytes, file_url)
                    if not file_bytes:
                        reject_reason = "无法从存储中获取技能包文件，请重新上传"
                        vt_result = "error"
                    else:
                        resp = await client.post(
                            "https://www.virustotal.com/api/v3/files",
                            headers=headers,
                            files={"file": ("skill.zip", file_bytes, "application/zip")},
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            analysis_id = resp.json().get("data", {}).get("id")
                            # Step 3: Poll for scan results (max ~3 min)
                            for _ in range(12):
                                await asyncio.sleep(15)
                                poll_resp = await client.get(
                                    f"https://www.virustotal.com/api/v3/analyses/{analysis_id}",
                                    headers=headers,
                                )
                                if poll_resp.status_code == 200:
                                    attrs = poll_resp.json().get("data", {}).get("attributes", {})
                                    if attrs.get("status") == "completed":
                                        stats = attrs.get("stats", {})
                                        malicious = stats.get("malicious", 0)
                                        suspicious = stats.get("suspicious", 0)
                                        if malicious > 0 or suspicious > 0:
                                            reject_reason = f"VirusTotal 检测到安全风险（{malicious} 个引擎报告恶意，{suspicious} 个引擎报告可疑）"
                                            vt_result = "malicious"
                                        else:
                                            vt_result = "clean"
                                        break
                            else:
                                reject_reason = "VirusTotal 扫描超时（超过 3 分钟），请稍后重试"
                                vt_result = "timeout"
                        elif resp.status_code == 429:
                            reject_reason = "VirusTotal API 频率限制，请稍后重新提交"
                            vt_result = "rate_limited"
                        else:
                            reject_reason = f"VirusTotal 文件上传失败（HTTP {resp.status_code}），请稍后重试"
                            vt_result = "error"
                elif vt_result is None:
                    reject_reason = "技能未提供文件，无法进行安全校验"
                    vt_result = "skipped"
        except Exception as e:
            print(f"[VT Review] Error for skill {skill_id}: {e}")
            reject_reason = "VirusTotal 审核服务连接失败，请稍后重试"
            vt_result = "error"

    # Re-read skill (may have been modified during polling)
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill.get("status") != "pending":
        return

    skill["vt_result"] = vt_result
    now = datetime.now(timezone.utc).isoformat()
    audit_id = await kv.next_id("audit")

    if not reject_reason:
        duplicate_skill_id = await find_duplicate_skill_id_by_title(kv, skill.get("title", ""), exclude_skill_id=skill_id)
        if duplicate_skill_id:
            reject_reason = f"技能名称“{skill['title']}”已存在，请修改后重新提交"

    if reject_reason:
        skill["status"] = "rejected"
        skill["reject_reason"] = reject_reason
        await kv.put(f"skill:{skill_id}", skill)
        await sync_skill_title_index(kv, skill, previous_status="pending", previous_title=skill.get("title", ""))
        await kv.remove_from_list("skill:by_status:pending", skill_id)
        await kv.add_to_list("skill:by_status:rejected", skill_id)

        await kv.put(f"audit:{audit_id}", {
            "id": audit_id,
            "skill_id": skill_id,
            "audit_type": "auto",
            "result": "failed",
            "details": {"reason": reject_reason, "vt_result": vt_result},
            "reviewer_id": None,
            "created_at": now,
        })
    else:
        skill["status"] = "approved"
        skill["published_at"] = now
        await kv.put(f"skill:{skill_id}", skill)
        await sync_skill_title_index(kv, skill, previous_status="pending", previous_title=skill.get("title", ""))
        await kv.remove_from_list("skill:by_status:pending", skill_id)
        await kv.add_to_list("skill:by_status:approved", skill_id)
        # 自动审核通过：更新用户统计缓存
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, skill["user_id"], skill_delta=1)

        await kv.put(f"audit:{audit_id}", {
            "id": audit_id,
            "skill_id": skill_id,
            "audit_type": "auto",
            "result": "passed",
            "details": {"reason": "VirusTotal 审核通过", "vt_result": vt_result},
            "reviewer_id": None,
            "created_at": now,
        })

    await kv.add_to_list(f"audit:by_skill:{skill_id}", audit_id)
    _invalidate_skill_cache()

    # Notify author
    msg_id = await kv.next_id("msg")
    status_text = "通过" if skill["status"] == "approved" else "未通过"
    content = "审核通过，已自动上架" if skill["status"] == "approved" else reject_reason
    await kv.put(f"msg:{msg_id}", {
        "id": msg_id,
        "user_id": skill["user_id"],
        "type": "audit",
        "title": f"技能「{skill['title']}」审核{status_text}",
        "content": content,
        "is_read": False,
        "related_type": "skill",
        "related_id": skill_id,
        "created_at": now,
    })
    await kv.add_to_list(f"msg:by_user:{skill['user_id']}", msg_id)
    await kv.add_to_list(f"msg:unread:{skill['user_id']}", msg_id)


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_scope("skill:update")),
    kv: KVStore = Depends(get_kv),
    s3: S3Storage = Depends(get_s3),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在或无权操作", 404)

    old_cat = skill.get("category_id")
    old_status = skill.get("status")
    old_title = skill.get("title", "")
    updates = data.model_dump(exclude_unset=True)
    await assert_skill_title_unique(kv, updates.get("title", old_title), exclude_skill_id=skill_id)
    for key, value in updates.items():
        skill[key] = value
    skill["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Re-submit for review on update
    skill["status"] = "pending"
    skill["reject_reason"] = None
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    # Move status list
    if old_status and old_status != "pending":
        await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list("skill:by_status:pending", skill_id)

    # Update category index if changed
    new_cat = skill.get("category_id")
    if old_cat != new_cat:
        if old_cat:
            await kv.remove_from_list(f"skill:by_cat:{old_cat}", skill_id)
        if new_cat:
            await kv.add_to_list(f"skill:by_cat:{new_cat}", skill_id)

    _invalidate_skill_cache()

    # Trigger auto-review in background
    background_tasks.add_task(_auto_review_skill, skill_id, kv, s3)

    return success_response({"id": skill_id, "status": "pending"})


@router.post("/{skill_id}/versions")
async def create_version(
    skill_id: str,
    data: VersionCreate,
    user: dict = Depends(require_scope("skill:update")),
    kv: KVStore = Depends(get_kv),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    now = datetime.now(timezone.utc).isoformat()
    ver_id = await kv.next_id("sv")
    version = {
        "id": ver_id,
        "skill_id": skill_id,
        "version": data.version,
        "changelog": data.changelog,
        "file_url": data.file_url,
        "file_size": data.file_size,
        "file_hash": data.file_hash,
        "status": "approved",
        "created_at": now,
    }
    await kv.put(f"sv:{ver_id}", version)
    await kv.add_to_list(f"sv:by_skill:{skill_id}", ver_id)

    # Update parent skill
    skill["version"] = data.version
    skill["file_url"] = data.file_url
    if data.file_size:
        skill["file_size"] = data.file_size
    if data.file_hash:
        skill["file_hash"] = data.file_hash
    skill["updated_at"] = now
    await kv.put(f"skill:{skill_id}", skill)

    return success_response({"version_id": ver_id})


@router.get("/{skill_id}/versions")
async def list_versions(skill_id: str, kv: KVStore = Depends(get_kv)):
    version_ids = await kv.get_list(f"sv:by_skill:{skill_id}")
    versions = await kv.batch_get([f"sv:{vid}" for vid in version_ids])
    items = sorted([v for v in versions if v], key=lambda x: x.get("created_at", ""), reverse=True)
    return success_response({"items": [{
        "id": v["id"], "version": v["version"],
        "changelog": v.get("changelog"),
        "status": v.get("status"),
        "created_at": v.get("created_at"),
    } for v in items]})


@router.get("/{skill_id}/audit-logs")
async def get_audit_logs(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    audit_ids = await kv.get_list(f"audit:by_skill:{skill_id}")
    audits = await kv.batch_get([f"audit:{aid}" for aid in audit_ids])
    items = sorted([a for a in audits if a], key=lambda x: x.get("created_at", ""), reverse=True)

    return success_response({"items": [{
        "id": a["id"],
        "audit_type": a.get("audit_type"),
        "result": a.get("result"),
        "details": a.get("details"),
        "created_at": a.get("created_at"),
    } for a in items]})


@router.post("/{skill_id}/offline")
async def offline_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    old_status = skill["status"]
    old_title = skill.get("title", "")
    skill["status"] = "offline"
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    # Move between status lists
    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list("skill:by_status:offline", skill_id)
    _invalidate_skill_cache()
    return success_response()


@router.post("/{skill_id}/online")
async def online_skill(
    skill_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
    s3: S3Storage = Depends(get_s3),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    old_status = skill["status"]
    old_title = skill.get("title", "")
    now = datetime.now(timezone.utc).isoformat()

    await assert_skill_title_unique(kv, old_title, exclude_skill_id=skill_id)

    # Set to pending for re-review
    skill["status"] = "pending"
    skill["reject_reason"] = None
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list("skill:by_status:pending", skill_id)
    _invalidate_skill_cache()

    # Trigger auto-review in background
    background_tasks.add_task(_auto_review_skill, skill_id, kv, s3)

    return success_response({"status": "pending"})


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill or skill["user_id"] != user["id"]:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在或无权操作", 404)

    # Soft delete: hide from user, keep data for admin
    old_status = skill.get("status", "approved")
    old_title = skill.get("title", "")
    skill["status"] = "deleted"
    skill["deleted_at"] = datetime.now(timezone.utc).isoformat()
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    # Move from old status list to deleted list
    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list("skill:by_status:deleted", skill_id)
    # Remove from user's visible list
    await kv.remove_from_list(f"skill:by_user:{user['id']}", skill_id)
    if skill.get("category_id"):
        await kv.remove_from_list(f"skill:by_cat:{skill['category_id']}", skill_id)

    # 若删除的是已上架技能，更新用户统计缓存
    if old_status == "approved":
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, user["id"], skill_delta=-1, downloads_delta=-skill.get("download_count", 0))

    _invalidate_skill_cache()
    return success_response({"message": "技能已删除"})
