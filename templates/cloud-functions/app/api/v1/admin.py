import asyncio
from datetime import datetime, timezone
from typing import Optional
import json
import re
import io

from app.api.v1.skills import _invalidate_skill_cache, _time_sort_key
import zipfile
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel

from app.api.v1.deps import get_kv, get_current_admin
from app.core.exceptions import success_response, paginated_response, AppException, ErrorCode
from app.core.skill_titles import assert_skill_title_unique, rebuild_skill_title_indexes, remove_skill_title_index, sync_skill_title_index
from app.storage.kv import KVStore

router = APIRouter(prefix="/admin", tags=["admin"])

async def send_notify_email(kv: KVStore, subject: str, body: str):
    """根据管理后台 SMTP 配置发送通知邮件。配置缺失时静默跳过。"""
    settings = await kv.get("site:settings") or {}
    email_to = settings.get("notifyEmail")
    smtp_host = settings.get("smtpHost")
    smtp_port = settings.get("smtpPort", 465)
    smtp_user = settings.get("smtpUser")
    smtp_pass = settings.get("smtpPass")
    smtp_from = settings.get("smtpFrom") or smtp_user

    if not all([email_to, smtp_host, smtp_user, smtp_pass]):
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = email_to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if int(smtp_port) == 465:
            server = smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=10)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [email_to], msg.as_string())
        server.quit()
    except Exception:
        pass  # 静默失败，不影响主业务


# ========== Dashboard ==========

@router.get("/stats")
async def dashboard_stats(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Get overview statistics for admin dashboard."""
    approved_ids, pending_ids, rejected_ids, offline_ids, deleted_ids, user_count = await asyncio.gather(
        kv.get_list("skill:by_status:approved"),
        kv.get_list("skill:by_status:pending"),
        kv.get_list("skill:by_status:rejected"),
        kv.get_list("skill:by_status:offline"),
        kv.get_list("skill:by_status:deleted"),
        kv.get("user:_counter"),
    )
    user_count = user_count or 0

    # Validate pending skills actually exist (clean up orphaned IDs)
    if pending_ids:
        pending_skills = await kv.batch_get([f"skill:{sid}" for sid in pending_ids])
        valid_pending = [sid for sid, s in zip(pending_ids, pending_skills) if s and s.get("status") == "pending"]
        # Clean up orphaned pending IDs
        for sid in pending_ids:
            if sid not in valid_pending:
                await kv.remove_from_list("skill:by_status:pending", sid)
        pending_count = len(valid_pending)
    else:
        pending_count = 0

    return success_response({
        "skills_approved": len(approved_ids),
        "skills_pending": pending_count,
        "skills_rejected": len(rejected_ids),
        "skills_offline": len(offline_ids),
        "skills_deleted": len(deleted_ids),
        "skills_total": len(approved_ids) + pending_count + len(rejected_ids) + len(offline_ids),
        "user_count": user_count,
    })


# ========== User Management ==========

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    keyword: Optional[str] = None,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    user_count = int(await kv.get("user:_counter") or 0)

    def _build_user_item(u: dict) -> dict:
        return {
            "id": u["id"],
            "username": u.get("username"),
            "nickname": u.get("nickname"),
            "avatar_url": u.get("avatar_url"),
            "role": u.get("role", "user"),
            "points_balance": u.get("points_balance", 0),
            "level": u.get("level", 1),
            "is_banned": u.get("is_banned", False),
            "created_at": u.get("created_at"),
        }

    if not keyword:
        # 快速路径：用户 ID 是自增整数，直接在 ID 范围上分页（最新注册 = 最大 ID）
        total = user_count
        start = (page - 1) * page_size
        page_ids = list(range(user_count - start, max(0, user_count - start - page_size), -1))
        if not page_ids:
            return paginated_response([], total, page, page_size)
        users_raw = await kv.batch_get([f"user:{uid}" for uid in page_ids])
        items = [_build_user_item(u) for u in users_raw if u]
        return paginated_response(items, total, page, page_size)

    # 关键词搜索：需全量加载后过滤
    user_ids = list(range(1, user_count + 1))
    users = await kv.batch_get([f"user:{uid}" for uid in user_ids])
    items_raw = [u for u in users if u]
    kw = keyword.lower()
    items_raw = [u for u in items_raw if kw in (u.get("nickname", "").lower()) or kw in (u.get("username", "").lower())]
    items_raw.sort(key=_time_sort_key, reverse=True)
    total = len(items_raw)
    start = (page - 1) * page_size
    page_users = items_raw[start:start + page_size]
    return paginated_response([_build_user_item(u) for u in page_users], total, page, page_size)


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
    role: Optional[str] = Body(None),
    is_banned: Optional[bool] = Body(None),
    points_balance: Optional[int] = Body(None),
    nickname: Optional[str] = Body(None),
):
    user = await kv.get(f"user:{user_id}")
    if not user:
        raise AppException(ErrorCode.USER_NOT_FOUND, "用户不存在", 404)

    if role is not None:
        user["role"] = role
    if is_banned is not None:
        user["is_banned"] = is_banned
        user["status"] = "banned" if is_banned else "active"
        # 封禁时禁用该用户所有 API 令牌
        if is_banned:
            token_ids = await kv.get_list(f"token:by_user:{user_id}")
            tokens = await kv.batch_get([f"token:{tid}" for tid in token_ids])
            for t in tokens:
                if t and t.get("is_active"):
                    t["is_active"] = False
                    th = t.get("token_hash")
                    if th:
                        try:
                            await kv.delete(f"token:idx:hash:{th}")
                        except Exception:
                            pass
                    await kv.put(f"token:{t['id']}", t)
    if points_balance is not None:
        user["points_balance"] = points_balance
    if nickname is not None:
        user["nickname"] = nickname

    await kv.put(f"user:{user_id}", user)
    return success_response()


# ========== Skill Management ==========

@router.get("/skills")
async def list_all_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    all_statuses = ["approved", "pending", "rejected", "offline", "deleted"]
    if status and status in all_statuses:
        statuses = [status]
    else:
        # By default, show all except deleted
        statuses = ["approved", "pending", "rejected", "offline"]

    def _build_item(s: dict, author_map: dict) -> dict:
        return {
            "id": s["id"],
            "title": s["title"],
            "price": s.get("price", 0),
            "status": s["status"],
            "author_name": author_map.get(s["user_id"], {}).get("nickname", ""),
            "download_count": s.get("download_count", 0),
            "avg_rating": s.get("avg_rating", 0),
            "created_at": s.get("created_at"),
            "deleted_at": s.get("deleted_at"),
        }

    # 快速路径：单一状态 + 无关键词 → 直接在 ID 列表上分页，只加载当页数据
    if len(statuses) == 1 and not keyword:
        all_ids = await kv.get_list(f"skill:by_status:{statuses[0]}")
        all_ids = list(reversed(all_ids))  # 最新优先
        total = len(all_ids)
        start = (page - 1) * page_size
        page_skill_ids = all_ids[start:start + page_size]
        if not page_skill_ids:
            return paginated_response([], total, page, page_size)
        page_skills_raw = await kv.batch_get([f"skill:{sid}" for sid in page_skill_ids])
        page_skills = [s for s in page_skills_raw if s]
        author_ids = list({s["user_id"] for s in page_skills})
        authors = await kv.batch_get([f"user:{uid}" for uid in author_ids])
        author_map = {a["id"]: a for a in authors if a}
        return paginated_response([_build_item(s, author_map) for s in page_skills], total, page, page_size)

    # 通用路径：多状态或关键词搜索 → 并行加载所有 ID，批量获取数据
    id_lists = await asyncio.gather(*[kv.get_list(f"skill:by_status:{s}") for s in statuses])
    all_ids = [sid for ids in id_lists for sid in ids]

    skills = await kv.batch_get([f"skill:{sid}" for sid in all_ids])
    items_raw = [s for s in skills if s]

    if keyword:
        kw = keyword.lower()
        items_raw = [s for s in items_raw if kw in (s.get("title", "").lower())]

    items_raw.sort(key=_time_sort_key, reverse=True)
    total = len(items_raw)
    start = (page - 1) * page_size
    page_skills = items_raw[start:start + page_size]

    author_ids = list({s["user_id"] for s in page_skills})
    authors = await kv.batch_get([f"user:{uid}" for uid in author_ids])
    author_map = {a["id"]: a for a in authors if a}

    return paginated_response([_build_item(s, author_map) for s in page_skills], total, page, page_size)


@router.delete("/skills/{skill_id}")
async def admin_delete_skill(
    skill_id: str,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Admin physical delete: permanently removes the skill and all indexes."""
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    old_status = skill.get("status", "approved")
    await remove_skill_title_index(kv, old_status, skill.get("title", ""), skill_id)
    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.remove_from_list(f"skill:by_user:{skill['user_id']}", skill_id)
    if skill.get("category_id"):
        await kv.remove_from_list(f"skill:by_cat:{skill['category_id']}", skill_id)
    await kv.delete(f"skill:{skill_id}")
    # 若删除的是已上架技能，更新用户统计缓存
    if old_status == "approved":
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, skill["user_id"], skill_delta=-1, downloads_delta=-skill.get("download_count", 0))
    _invalidate_skill_cache()

    return success_response({"message": "技能已物理删除"})


@router.post("/skills/rebuild-title-indexes")
async def rebuild_title_indexes(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    summary = await rebuild_skill_title_indexes(kv)
    return success_response(summary, "技能标题索引重建完成")


@router.post("/system/reseed")
async def force_reseed(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """强制重新执行首次冷启动种子注入。
    适用于 CLI 部署后 KV 仍为空（seed 中间件需要请求触发）的场景。
    幂等：seed 内部对每个键先 get 再 put，已存在不会覆盖。
    """
    from app.seed.bootstrap import run_full_seed
    try:
        summary = await run_full_seed(kv)
        return success_response({"ok": True, "summary": summary}, "种子注入已完成")
    except Exception as e:
        raise AppException(ErrorCode.STORAGE_ERROR, f"种子注入失败：{e}")


@router.post("/skills/rebuild-aggregate")
async def rebuild_skill_aggregate(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """重建 Edge Function 聊合分片缓存（skill_listdata_s0-s9）。
    数据量超过 1 万时应先调用此接口初始化缓存，
    否则每次 Edge 冷启动都会全量扫描。
    """
    skill_ids = await kv.get_list("skill:by_status:approved")
    if not skill_ids:
        return success_response({"count": 0, "shards": 0}, "暂无已审核技能")

    # 分批读取技能数据，每次 200 个
    BATCH = 200
    all_skills = []
    for i in range(0, len(skill_ids), BATCH):
        batch = skill_ids[i:i + BATCH]
        items = await kv.batch_get([f"skill:{sid}" for sid in batch], timeout=30)
        all_skills.extend(s for s in items if s)

    # 分片写入 KV：与 Edge Function 的 skillShardIndex 哈希逻辑保持一致
    SHARD_COUNT = 10

    def _shard_index(skill_id: str) -> int:
        h = 0
        for ch in str(skill_id):
            h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
        # 模拟 JS 有符号整数运算
        if h >= 0x80000000:
            h -= 0x100000000
        return abs(h) % SHARD_COUNT

    LISTING_FIELDS = [
        "id", "title", "subtitle", "price", "is_free", "cover_image",
        "product_type", "sale_mode", "cash_price_yuan", "stock", "shipping_fee_yuan", "shipping_required",
        "version", "avg_rating", "review_count", "download_count",
        "purchase_count", "favorite_count", "tags", "category_id",
        "user_id", "status", "created_at",
    ]

    shards: dict[int, list] = {i: [] for i in range(SHARD_COUNT)}
    for s in all_skills:
        listing = {f: s.get(f) for f in LISTING_FIELDS}
        listing["is_free"] = bool(listing.get("is_free"))
        listing.setdefault("product_type", "digital")
        listing.setdefault("sale_mode", "points")
        listing.setdefault("cash_price_yuan", 0)
        listing.setdefault("stock", None)
        listing.setdefault("shipping_fee_yuan", 0)
        listing["shipping_required"] = bool(listing.get("shipping_required"))
        listing.setdefault("subtitle", "")
        listing.setdefault("cover_image", None)
        listing.setdefault("version", "1.0.0")
        listing.setdefault("avg_rating", 0)
        listing.setdefault("review_count", 0)
        listing.setdefault("download_count", 0)
        listing.setdefault("purchase_count", 0)
        listing.setdefault("favorite_count", 0)
        listing.setdefault("tags", [])
        listing.setdefault("created_at", None)
        si = _shard_index(str(s["id"]))
        shards[si].append(listing)

    for i, shard_data in shards.items():
        await kv.put(f"skill_listdata_s{i}", shard_data)

    # 删除旧的单条聚合缓存
    await kv.delete("skill_approved_listdata")

    return success_response(
        {"count": len(all_skills), "shards": SHARD_COUNT},
        f"已重建 {len(all_skills)} 条技能的分片缓存"
    )


@router.post("/users/rebuild-stats")
async def rebuild_user_stats(
    user_id: Optional[int] = Query(None, description="指定用户 ID，不填则重建所有用户"),
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """重建用户统计缓存（user:stats:{user_id}），包含 skill_count 和 total_downloads。

    首次部署或统计数据异常时调用；之后由各接口（发布 / 审核 / 删除 / 下载）增量维护。
    - 指定 user_id：只重建该用户（推荐，如管理员账号）
    - 不指定 user_id：重建所有用户（建议使用 ?user_id=N 逐个修复）
    """
    BATCH = 200           # EdgeOne KV 单次批量上限
    CONCURRENCY = 5       # 并发批次数，避免触发 KV 限流

    async def _rebuild_one(uid: int) -> dict:
        skill_ids = await kv.get_list(f"skill:by_user:{uid}")
        if not skill_ids:
            await kv.put(f"user:stats:{uid}", {"skill_count": 0, "total_downloads": 0})
            return {"user_id": uid, "skill_count": 0, "total_downloads": 0}

        # 将所有 batch keys 预先分组
        batches = [
            [f"skill:{sid}" for sid in skill_ids[i:i + BATCH]]
            for i in range(0, len(skill_ids), BATCH)
        ]

        skill_count = 0
        total_downloads = 0

        # 每次并发 CONCURRENCY 批，减少总耗时
        for group_start in range(0, len(batches), CONCURRENCY):
            group = batches[group_start: group_start + CONCURRENCY]
            results = await asyncio.gather(
                *[kv.batch_get(b, timeout=30) for b in group]
            )
            for items in results:
                for s in items:
                    if s and s.get("status") == "approved":
                        skill_count += 1
                        total_downloads += s.get("download_count", 0)

        await kv.put(f"user:stats:{uid}", {"skill_count": skill_count, "total_downloads": total_downloads})
        return {"user_id": uid, "skill_count": skill_count, "total_downloads": total_downloads}

    if user_id is not None:
        result = await _rebuild_one(user_id)
        return success_response({"rebuilt": 1, "detail": [result]})

    # 扫描所有 user:<整数> 格式的 key
    user_keys = await kv.list_keys(prefix="user:")
    user_ids = [
        int(k.split(":")[1])
        for k in user_keys
        if len(k.split(":")) == 2 and k.split(":")[1].isdigit()
    ]
    if not user_ids:
        return success_response({"rebuilt": 0, "detail": []})

    details = []
    for uid in user_ids:
        details.append(await _rebuild_one(uid))

    return success_response({"rebuilt": len(details), "detail": details})


# ========== Review Management ==========

@router.get("/reviews")
async def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    keyword: Optional[str] = None,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    review_count = int(await kv.get("review:_counter") or 0)

    if not keyword:
        # 快速路径：评论 ID 是自增整数，直接在 ID 范围上分页（最新 = 最大 ID）
        total = review_count
        start = (page - 1) * page_size
        page_ids = list(range(review_count - start, max(0, review_count - start - page_size), -1))
        if not page_ids:
            return paginated_response([], total, page, page_size)
        reviews_raw = await kv.batch_get([f"review:{rid}" for rid in page_ids])
        page_reviews = [r for r in reviews_raw if r]
        uid_set = list({r["user_id"] for r in page_reviews if r.get("user_id")})
        users_raw = await kv.batch_get([f"user:{uid}" for uid in uid_set])
        user_map = {u["id"]: u for u in users_raw if u}
        items = [{
            "id": r["id"],
            "skill_id": r.get("skill_id"),
            "user_nickname": user_map.get(r.get("user_id"), {}).get("nickname", "匿名"),
            "rating": r.get("rating"),
            "content": r.get("content"),
            "created_at": r.get("created_at"),
        } for r in page_reviews]
        return paginated_response(items, total, page, page_size)

    # 关键词搜索：需全量加载
    review_ids = list(range(1, review_count + 1))
    reviews = await kv.batch_get([f"review:{rid}" for rid in review_ids])
    items_raw = [r for r in reviews if r]
    items_raw.sort(key=_time_sort_key, reverse=True)

    all_user_ids = list({r["user_id"] for r in items_raw if r.get("user_id")})
    users = await kv.batch_get([f"user:{uid}" for uid in all_user_ids])
    user_map = {u["id"]: u for u in users if u}

    kw = keyword.lower()
    items_raw = [r for r in items_raw if
        kw in (r.get("content") or "").lower() or
        kw in user_map.get(r.get("user_id"), {}).get("nickname", "").lower()]

    total = len(items_raw)
    start = (page - 1) * page_size
    page_reviews = items_raw[start:start + page_size]

    items = [{
        "id": r["id"],
        "skill_id": r.get("skill_id"),
        "user_nickname": user_map.get(r.get("user_id"), {}).get("nickname", "匿名"),
        "rating": r.get("rating"),
        "content": r.get("content"),
        "created_at": r.get("created_at"),
    } for r in page_reviews]

    return paginated_response(items, total, page, page_size)


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    review = await kv.get(f"review:{review_id}")
    if not review:
        raise AppException(ErrorCode.NOT_FOUND, "评论不存在", 404)
        
    if not isinstance(review, dict):
        raise AppException(ErrorCode.PARAMS_ERROR, "评论数据结构异常", 500)

    # Soft delete
    review["status"] = "hidden"
    await kv.put(f"review:{review_id}", review)
    
    # Recalculate skill's rating
    skill_id = review.get("skill_id")
    if skill_id:
        skill = await kv.get(f"skill:{skill_id}")
        if skill and isinstance(skill, dict):
            all_review_ids = await kv.get_list(f"review:by_skill:{skill_id}")
            all_reviews = await kv.batch_get([f"review:{rid}" for rid in all_review_ids])
            visible_ratings = [r["rating"] for r in all_reviews if r and isinstance(r, dict) and r.get("status") == "visible"]
            if visible_ratings:
                skill["avg_rating"] = round(sum(visible_ratings) / len(visible_ratings), 1)
            else:
                skill["avg_rating"] = 0.0
            skill["review_count"] = len(visible_ratings)
            await kv.put(f"skill:{skill_id}", skill)

    return success_response({"message": "评论已删除"})


# ========== Pending Skill Audit ==========


@router.get("/skills/pending")
async def pending_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    skill_ids = await kv.get_list("skill:by_status:pending")
    skills = await kv.batch_get([f"skill:{sid}" for sid in skill_ids])
    # Only show skills that actually exist and are still pending
    items_raw = [s for s in skills if s and s.get("status") == "pending"]
    items_raw.sort(key=_time_sort_key, reverse=True)

    total = len(items_raw)
    start = (page - 1) * page_size
    page_skills = items_raw[start:start + page_size]

    # Get author names
    author_ids = list({s["user_id"] for s in page_skills})
    authors = await kv.batch_get([f"user:{uid}" for uid in author_ids])
    author_map = {a["id"]: a for a in authors if a}

    items = [{
        "id": s["id"], "title": s["title"],
        "author": author_map.get(s["user_id"], {}).get("nickname", ""),
        "created_at": s.get("created_at"),
    } for s in page_skills]

    return paginated_response(items, total, page, page_size)


@router.post("/skills/{skill_id}/audit")
async def audit_skill(
    skill_id: str,
    result: str = "approved",
    reason: str = "",
    force: bool = False,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    now = datetime.now(timezone.utc).isoformat()
    old_status = skill["status"]
    old_title = skill.get("title", "")

    if result == "approved":
        await assert_skill_title_unique(kv, old_title, exclude_skill_id=skill_id)

    skill["status"] = result
    if result == "approved":
        skill["published_at"] = now
        if force:
            skill["force_approved"] = True
        else:
            skill.pop("force_approved", None)
        # Award XP to author for publishing
        from app.core.levels import EXP_PUBLISH_SKILL
        from app.api.v1.users import add_exp
        settings = await kv.get("site:settings") or {}
        exp_pub = settings.get("expPublish", EXP_PUBLISH_SKILL)
        await add_exp(kv, skill["user_id"], exp_pub)
        # 审核通过：若之前不是 approved，计入 skill_count
        if old_status != "approved":
            from app.api.v1.users import update_user_stats
            await update_user_stats(kv, skill["user_id"], skill_delta=1)
    else:
        skill["reject_reason"] = reason
        # 审核拒绝：若之前是 approved，从统计中减去
        if old_status == "approved":
            from app.api.v1.users import update_user_stats
            await update_user_stats(kv, skill["user_id"], skill_delta=-1, downloads_delta=-skill.get("download_count", 0))
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    # Move between status lists
    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list(f"skill:by_status:{result}", skill_id)

    # Create audit log
    audit_id = await kv.next_id("audit")
    await kv.put(f"audit:{audit_id}", {
        "id": audit_id,
        "skill_id": skill_id,
        "audit_type": "manual",
        "result": "passed" if result == "approved" else "failed",
        "details": {"reason": reason},
        "reviewer_id": admin["id"],
        "created_at": now,
    })
    await kv.add_to_list(f"audit:by_skill:{skill_id}", audit_id)
    _invalidate_skill_cache()

    # Notify author
    msg_id = await kv.next_id("msg")
    status_text = "通过" if result == "approved" else "未通过"
    await kv.put(f"msg:{msg_id}", {
        "id": msg_id,
        "user_id": skill["user_id"],
        "type": "audit",
        "title": f"技能 {skill['title']} 审核{status_text}",
        "content": reason or (f"审核{status_text}，{'已上架' if result == 'approved' else '请修改后重新提交'}"),
        "is_read": False,
        "related_type": "skill",
        "related_id": skill_id,
        "created_at": now,
    })
    await kv.add_to_list(f"msg:by_user:{skill['user_id']}", msg_id)
    await kv.add_to_list(f"msg:unread:{skill['user_id']}", msg_id)

    return success_response()


@router.post("/skills/{skill_id}/offline")
async def offline_skill(
    skill_id: str,
    reason: str = "",
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Admin manually take a skill offline with a reason."""
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    now = datetime.now(timezone.utc).isoformat()
    old_status = skill["status"]
    old_title = skill.get("title", "")

    skill["status"] = "offline"
    skill["offline_reason"] = reason
    skill["offline_at"] = now
    await kv.put(f"skill:{skill_id}", skill)
    await sync_skill_title_index(kv, skill, previous_status=old_status, previous_title=old_title)

    # Move between status lists
    await kv.remove_from_list(f"skill:by_status:{old_status}", skill_id)
    await kv.add_to_list(f"skill:by_status:offline", skill_id)
    # 若之前是已上架，更新用户统计缓存
    if old_status == "approved":
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, skill["user_id"], skill_delta=-1, downloads_delta=-skill.get("download_count", 0))
    _invalidate_skill_cache()

    # Notify author
    msg_id = await kv.next_id("msg")
    await kv.put(f"msg:{msg_id}", {
        "id": msg_id,
        "user_id": skill["user_id"],
        "type": "audit",
        "title": f"技能 {skill['title']} 已被下架",
        "content": reason or "您的技能已被管理员下架",
        "is_read": False,
        "related_type": "skill",
        "related_id": skill_id,
        "created_at": now,
    })
    await kv.add_to_list(f"msg:by_user:{skill['user_id']}", msg_id)
    await kv.add_to_list(f"msg:unread:{skill['user_id']}", msg_id)

    return success_response()


# ========== Withdrawal Management ==========

@router.get("/withdrawals")
async def list_withdrawals(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """List withdrawal requests for admin review."""
    def _build_wd_item(w: dict, user_map: dict) -> dict:
        return {
            "id": w["id"],
            "user_id": w["user_id"],
            "user_name": user_map.get(w["user_id"], {}).get("nickname", ""),
            "amount": w["amount"],
            "fee_yuan": w.get("fee_yuan"),
            "actual_yuan": w.get("actual_yuan"),
            "alipay_account": w["alipay_account"],
            "alipay_name": w["alipay_name"],
            "status": w["status"],
            "reject_reason": w.get("reject_reason"),
            "created_at": w.get("created_at"),
            "completed_at": w.get("completed_at"),
        }

    if status == "pending":
        wd_ids = await kv.get_list("wd:pending")
        wd_ids_rev = list(reversed(wd_ids))
        wds = await kv.batch_get([f"wd:{wid}" for wid in wd_ids_rev])
        wds = [w for w in wds if w]
    else:
        wd_count = int(await kv.get("wd:_counter") or 0)
        if not keyword and not status:
            # 快速路径：直接在 ID 范围上分页
            total = wd_count
            start = (page - 1) * page_size
            page_ids = list(range(wd_count - start, max(0, wd_count - start - page_size), -1))
            if not page_ids:
                return paginated_response([], total, page, page_size)
            wds_raw = await kv.batch_get([f"wd:{wid}" for wid in page_ids])
            page_wds = [w for w in wds_raw if w]
            uid_set = list({w["user_id"] for w in page_wds})
            users_raw = await kv.batch_get([f"user:{uid}" for uid in uid_set])
            user_map_p = {u["id"]: u for u in users_raw if u}
            return paginated_response([_build_wd_item(w, user_map_p) for w in page_wds], total, page, page_size)
        wd_ids_rev = list(range(wd_count, 0, -1))
        wds = await kv.batch_get([f"wd:{wid}" for wid in wd_ids_rev])
        wds = [w for w in wds if w]

    if status and status != "pending":
        wds = [w for w in wds if w.get("status") == status]

    # Get user info
    user_ids = list({w["user_id"] for w in wds})
    users = await kv.batch_get([f"user:{uid}" for uid in user_ids])
    user_map = {u["id"]: u for u in users if u}

    if keyword:
        kw = keyword.lower()
        wds = [w for w in wds if
            kw in user_map.get(w.get("user_id"), {}).get("nickname", "").lower() or
            kw in (w.get("alipay_account") or "").lower() or
            kw in (w.get("alipay_name") or "").lower()]

    total = len(wds)
    start = (page - 1) * page_size
    page_items = wds[start:start + page_size]

    return paginated_response([_build_wd_item(w, user_map) for w in page_items], total, page, page_size)


@router.post("/withdrawals/{wd_id}/complete")
async def complete_withdrawal(
    wd_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Mark a withdrawal as completed (admin has transferred funds). Deducts points."""
    wd = await kv.get(f"wd:{wd_id}")
    if not wd:
        raise AppException(ErrorCode.NOT_FOUND, "提现记录不存在", 404)
    if wd["status"] != "pending":
        raise AppException(ErrorCode.PERMISSION_DENIED, "该提现已处理")

    user = await kv.get(f"user:{wd['user_id']}")
    if not user:
        raise AppException(ErrorCode.NOT_FOUND, "用户不存在", 404)

    if user.get("points_balance", 0) < wd["amount"]:
        raise AppException(ErrorCode.PERMISSION_DENIED, f"用户积分不足（当前 {user.get('points_balance', 0)}，需要 {wd['amount']}），无法完成提现")

    now = datetime.now(timezone.utc).isoformat()

    # Deduct points and unlock
    user["points_balance"] = user["points_balance"] - wd["amount"]
    user["points_locked"] = max(0, user.get("points_locked", 0) - wd["amount"])
    await kv.put(f"user:{user['id']}", user)

    # Create points record
    actual_yuan = wd.get("actual_yuan", round(wd["amount"] / 10 * 0.96, 2))
    fee_yuan = wd.get("fee_yuan", round(wd["amount"] / 10 * 0.04, 2))
    record_id = await kv.next_id("pr")
    record = {
        "id": record_id,
        "user_id": user["id"],
        "type": "withdraw",
        "amount": -wd["amount"],
        "balance_after": user["points_balance"],
        "description": f"提现 {wd['amount']} 积分（手续费 ¥{fee_yuan}，实际到账 ¥{actual_yuan}）",
        "related_id": wd_id,
        "created_at": now,
    }
    await kv.put(f"pr:{record_id}", record)
    await kv.add_to_list(f"pr:by_user:{user['id']}", record_id)

    # Update withdrawal status
    wd["status"] = "completed"
    wd["completed_at"] = now
    wd["admin_id"] = admin["id"]
    await kv.put(f"wd:{wd_id}", wd)
    await kv.remove_from_list("wd:pending", wd_id)

    # Notify user
    msg_id = await kv.next_id("msg")
    await kv.put(f"msg:{msg_id}", {
        "id": msg_id,
        "user_id": user["id"],
        "type": "system",
        "title": "提现成功",
        "content": f"您申请提现的 {wd['amount']} 积分已转账至支付宝 {wd['alipay_account']}",
        "is_read": False,
        "created_at": now,
    })
    await kv.add_to_list(f"msg:by_user:{user['id']}", msg_id)
    await kv.add_to_list(f"msg:unread:{user['id']}", msg_id)

    return success_response()


@router.post("/withdrawals/{wd_id}/reject")
async def reject_withdrawal(
    wd_id: int,
    reason: str = Body("", embed=True),
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Reject a withdrawal request. Unlocks the locked points."""
    wd = await kv.get(f"wd:{wd_id}")
    if not wd:
        raise AppException(ErrorCode.NOT_FOUND, "提现记录不存在", 404)
    if wd["status"] != "pending":
        raise AppException(ErrorCode.PERMISSION_DENIED, "该提现已处理")

    now = datetime.now(timezone.utc).isoformat()
    wd["status"] = "rejected"
    wd["reject_reason"] = reason
    wd["completed_at"] = now
    await kv.put(f"wd:{wd_id}", wd)
    await kv.remove_from_list("wd:pending", wd_id)

    # Unlock points
    user = await kv.get(f"user:{wd['user_id']}")
    if user:
        user["points_locked"] = max(0, user.get("points_locked", 0) - wd["amount"])
        await kv.put(f"user:{user['id']}", user)

    # Notify user
    msg_id = await kv.next_id("msg")
    await kv.put(f"msg:{msg_id}", {
        "id": msg_id,
        "user_id": wd["user_id"],
        "type": "system",
        "title": "提现被拒绝",
        "content": reason or "您的提现申请未通过审核",
        "is_read": False,
        "created_at": now,
    })
    await kv.add_to_list(f"msg:by_user:{wd['user_id']}", msg_id)
    await kv.add_to_list(f"msg:unread:{wd['user_id']}", msg_id)

    return success_response()


# ========== Recharge Order Management ==========

@router.get("/recharges")
async def list_recharges(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """List all recharge orders for admin review."""
    order_count = int(await kv.get("recharge_order:_counter") or 0)

    def _build_order_item(o: dict, user_map: dict) -> dict:
        return {
            "id": o["id"],
            "order_no": o.get("order_no"),
            "user_id": o["user_id"],
            "user_name": user_map.get(o["user_id"], {}).get("nickname", ""),
            "amount_yuan": o.get("amount_yuan"),
            "points_amount": o.get("points_amount"),
            "payment_method": o.get("payment_method"),
            "status": o.get("status", "pending"),
            "created_at": o.get("created_at"),
            "paid_at": o.get("paid_at"),
        }

    if not keyword and not status:
        # 快速路径：直接在 ID 范围上分页（最新 = 最大 ID）
        total = order_count
        start = (page - 1) * page_size
        page_ids = list(range(order_count - start, max(0, order_count - start - page_size), -1))
        if not page_ids:
            return paginated_response([], total, page, page_size)
        orders_raw = await kv.batch_get([f"recharge_order:{oid}" for oid in page_ids])
        page_orders = [o for o in orders_raw if o]
        uid_set = list({o["user_id"] for o in page_orders})
        users_raw = await kv.batch_get([f"user:{uid}" for uid in uid_set])
        user_map = {u["id"]: u for u in users_raw if u}
        return paginated_response([_build_order_item(o, user_map) for o in page_orders], total, page, page_size)

    # 有过滤条件或关键词：全量加载后过滤
    order_ids_rev = list(range(order_count, 0, -1))
    orders = await kv.batch_get([f"recharge_order:{oid}" for oid in order_ids_rev])
    orders = [o for o in orders if o]

    if status:
        orders = [o for o in orders if o.get("status") == status]

    # Get user info
    user_ids = list({o["user_id"] for o in orders})
    users = await kv.batch_get([f"user:{uid}" for uid in user_ids])
    user_map = {u["id"]: u for u in users if u}

    if keyword:
        kw = keyword.lower()
        orders = [o for o in orders if
            kw in (o.get("order_no") or "").lower() or
            kw in user_map.get(o.get("user_id"), {}).get("nickname", "").lower()]

    total = len(orders)
    start = (page - 1) * page_size
    page_items = orders[start:start + page_size]
    return paginated_response([_build_order_item(o, user_map) for o in page_items], total, page, page_size)


@router.post("/recharges/{order_id}/confirm")
async def confirm_recharge(
    order_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Manually confirm a recharge order (admin force-complete)."""
    order = await kv.get(f"recharge_order:{order_id}")
    if not order:
        raise AppException(ErrorCode.NOT_FOUND, "充值订单不存在", 404)
    if order["status"] == "paid":
        raise AppException(ErrorCode.PERMISSION_DENIED, "该订单已完成")

    now = datetime.now(timezone.utc).isoformat()
    order["status"] = "paid"
    order["paid_at"] = now
    await kv.put(f"recharge_order:{order_id}", order)

    user = await kv.get(f"user:{order['user_id']}")
    if user:
        total_points = order["points_amount"]
        user["points_balance"] = user.get("points_balance", 0) + total_points
        await kv.put(f"user:{user['id']}", user)

        record_id = await kv.next_id("pr")
        record = {
            "id": record_id,
            "user_id": user["id"],
            "type": "recharge",
            "amount": total_points,
            "balance_after": user["points_balance"],
            "description": f"管理员确认充值 ¥{order['amount_yuan']}",
            "related_id": order_id,
            "created_at": now,
        }
        await kv.put(f"pr:{record_id}", record)
        await kv.add_to_list(f"pr:by_user:{user['id']}", record_id)

    return success_response()


@router.post("/recharges/{order_id}/cancel")
async def cancel_recharge(
    order_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Cancel a pending recharge order."""
    order = await kv.get(f"recharge_order:{order_id}")
    if not order:
        raise AppException(ErrorCode.NOT_FOUND, "充值订单不存在", 404)
    if order["status"] == "paid":
        raise AppException(ErrorCode.PERMISSION_DENIED, "已完成的订单不能作废")

    order["status"] = "cancelled"
    await kv.put(f"recharge_order:{order_id}", order)
    return success_response()


# ========== Site Settings ==========

# 敏感字段列表 — GET 时脱敏返回
_SENSITIVE_FIELDS = {
    "alipayPrivateKey", "alipayPublicKey",
    "wechatApiKey", "wechatApiV3Key",
    "qqAppKey",
    "wxLoginAppSecret",
    "wxMpAppSecret",
    "wxMiniAppSecret",
    "vtApiKey",
    "smtpPass",
    "s3SecretKey",
}

# 脱敏占位符
_MASK = "••••••••"


def _mask_settings(settings: dict) -> dict:
    """返回一份拷贝，敏感字段替换为脱敏占位符（保留是否已配置的信息）。"""
    out = dict(settings)
    for key in _SENSITIVE_FIELDS:
        val = out.get(key)
        if val:
            # 保留前后各 2 个字符，中间用掩码
            if len(val) > 6:
                out[key] = val[:2] + _MASK + val[-2:]
            else:
                out[key] = _MASK
    return out


# ========== Order Management ==========

@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    keyword: Optional[str] = None,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """List all purchase orders for admin view."""
    purchase_count = int(await kv.get("purchase:_counter") or 0)

    def _build_purchase_item(p: dict, user_map: dict, skill_map: dict) -> dict:
        skill = skill_map.get(p.get("skill_id"), {})
        return {
            "id": p.get("id"),
            "order_no": p.get("order_no", ""),
            "user_id": p.get("user_id"),
            "user_name": user_map.get(p.get("user_id"), {}).get("nickname", ""),
            "skill_id": p.get("skill_id"),
            "skill_title": skill.get("title", "已删除"),
            "price": p.get("price_paid") or p.get("price", 0),
            "payment_type": p.get("payment_type", "points"),
            "cash_paid_yuan": p.get("cash_paid_yuan"),
            "shipping_fee_yuan": p.get("shipping_fee_yuan", 0),
            "shipping_info": p.get("shipping_info"),
            "is_physical": bool(p.get("is_physical")) or skill.get("product_type") == "physical",
            "fulfillment_status": p.get("fulfillment_status"),
            "status": p.get("status", "completed"),
            "created_at": p.get("created_at", ""),
        }

    if not keyword:
        # 快速路径：直接在 ID 范围上分页（最新 = 最大 ID）
        total = purchase_count
        start = (page - 1) * page_size
        page_ids = list(range(purchase_count - start, max(0, purchase_count - start - page_size), -1))
        if not page_ids:
            return paginated_response([], total, page, page_size)
        purchases_raw = await kv.batch_get([f"purchase:{pid}" for pid in page_ids])
        page_purchases = [p for p in purchases_raw if p]
        uid_set = list({p["user_id"] for p in page_purchases})
        sid_set = list({p["skill_id"] for p in page_purchases})
        users_raw, skills_raw = await asyncio.gather(
            kv.batch_get([f"user:{uid}" for uid in uid_set]),
            kv.batch_get([f"skill:{sid}" for sid in sid_set]),
        )
        user_map = {u["id"]: u for u in users_raw if u}
        skill_map = {s["id"]: s for s in skills_raw if s}
        return paginated_response([_build_purchase_item(p, user_map, skill_map) for p in page_purchases], total, page, page_size)

    # 关键词搜索：全量加载
    purchase_ids = list(range(purchase_count, 0, -1))
    purchases_raw = await kv.batch_get([f"purchase:{pid}" for pid in purchase_ids])
    purchases = [p for p in purchases_raw if p]

    all_user_ids = list({p["user_id"] for p in purchases})
    all_skill_ids = list({p["skill_id"] for p in purchases})
    users, skills = await asyncio.gather(
        kv.batch_get([f"user:{uid}" for uid in all_user_ids]),
        kv.batch_get([f"skill:{sid}" for sid in all_skill_ids]),
    )
    user_map = {u["id"]: u for u in users if u}
    skill_map = {s["id"]: s for s in skills if s}

    kw = keyword.lower()
    purchases = [p for p in purchases if
        kw in (p.get("order_no") or "").lower() or
        kw in user_map.get(p.get("user_id"), {}).get("nickname", "").lower() or
        kw in skill_map.get(p.get("skill_id"), {}).get("title", "").lower()]

    total = len(purchases)
    start = (page - 1) * page_size
    page_items = purchases[start:start + page_size]
    return paginated_response([_build_purchase_item(p, user_map, skill_map) for p in page_items], total, page, page_size)


@router.get("/users/{user_id}/orders")
async def get_user_orders(
    user_id: int,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """Get a user's purchase orders and points records for admin view."""
    # Purchases + Points records（并行加载列表）
    purchase_ids, pr_ids = await asyncio.gather(
        kv.get_list(f"purchase:by_user:{user_id}"),
        kv.get_list(f"pr:by_user:{user_id}"),
    )
    purchases_raw, prs_raw = await asyncio.gather(
        kv.batch_get([f"purchase:{pid}" for pid in (purchase_ids or [])]),
        kv.batch_get([f"pr:{pid}" for pid in (pr_ids or [])]),
    )
    # Load skills for purchases in one batch
    valid_purchases = [p for p in purchases_raw if p]
    skill_ids_needed = list({p.get("skill_id") for p in valid_purchases if p.get("skill_id")})
    skills_raw = await kv.batch_get([f"skill:{sid}" for sid in skill_ids_needed]) if skill_ids_needed else []
    skill_map_u = {s["id"]: s for s in skills_raw if s}

    purchases = []
    for p in valid_purchases:
        skill = skill_map_u.get(p.get("skill_id"))
        purchases.append({
            "id": p.get("id"),
            "skill_id": p.get("skill_id"),
            "skill_title": skill.get("title", "未知") if skill else "已删除",
            "price": p.get("price_paid") or p.get("price", 0),
            "payment_type": p.get("payment_type", "points"),
            "cash_paid_yuan": p.get("cash_paid_yuan"),
            "shipping_fee_yuan": p.get("shipping_fee_yuan", 0),
            "shipping_info": p.get("shipping_info"),
            "is_physical": bool(p.get("is_physical")) or (skill and skill.get("product_type") == "physical"),
            "fulfillment_status": p.get("fulfillment_status"),
            "created_at": p.get("created_at", ""),
            "order_no": p.get("order_no", ""),
        })
    purchases.sort(key=_time_sort_key, reverse=True)

    # Points records
    points_records = []
    for r in prs_raw:
        if not r:
            continue
        points_records.append({
            "id": r.get("id"),
            "type": r.get("type", ""),
            "amount": r.get("amount", 0),
            "balance_after": r.get("balance_after", 0),
            "description": r.get("description", ""),
            "created_at": r.get("created_at", ""),
        })
    points_records.sort(key=_time_sort_key, reverse=True)

    # Sales (skills published by this user that have been purchased)
    user = await kv.get(f"user:{user_id}")
    sales = []
    if user:
        skill_ids = await kv.get_list(f"skill:by_user:{user_id}")
        for sid in (skill_ids or []):
            skill = await kv.get(f"skill:{sid}")
            if skill and skill.get("purchase_count", 0) > 0:
                sales.append({
                    "skill_id": sid,
                    "title": skill.get("title", ""),
                    "price": skill.get("price", 0),
                    "purchase_count": skill.get("purchase_count", 0),
                    "total_earned": skill.get("price", 0) * skill.get("purchase_count", 0),
                })

    return success_response({
        "purchases": purchases[:100],
        "points_records": points_records[:100],
        "sales": sales,
    })


@router.get("/settings")
async def get_settings(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    settings = await kv.get("site:settings") or {}
    return success_response(_mask_settings(settings))


@router.put("/settings")
async def save_settings(
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
    title: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    keywords: Optional[str] = Body(None),
    icp: Optional[str] = Body(None),
    police: Optional[str] = Body(None),
    about: Optional[str] = Body(None),
    feeRate: Optional[int] = Body(None),
    registerBonus: Optional[int] = Body(None),
    # Alipay config
    alipayEnabled: Optional[bool] = Body(None),
    alipayAppId: Optional[str] = Body(None),
    alipayPrivateKey: Optional[str] = Body(None),
    alipayPublicKey: Optional[str] = Body(None),
    alipaySandbox: Optional[bool] = Body(None),
    # WeChat Pay config
    wechatEnabled: Optional[bool] = Body(None),
    wechatAppId: Optional[str] = Body(None),
    wechatMchId: Optional[str] = Body(None),
    wechatApiKey: Optional[str] = Body(None),
    wechatApiV3Key: Optional[str] = Body(None),
    wechatSerialNo: Optional[str] = Body(None),
    # QQ OAuth config
    qqAppId: Optional[str] = Body(None),
    qqAppKey: Optional[str] = Body(None),
    qqRedirectUri: Optional[str] = Body(None),
    # WeChat OAuth login config
    wxLoginAppId: Optional[str] = Body(None),
    wxLoginAppSecret: Optional[str] = Body(None),
    wxLoginRedirectUri: Optional[str] = Body(None),
    # WeChat MP H5 OAuth config
    wxMpAppId: Optional[str] = Body(None),
    wxMpAppSecret: Optional[str] = Body(None),
    # WeChat Mini Program config
    wxMiniAppId: Optional[str] = Body(None),
    wxMiniAppSecret: Optional[str] = Body(None),
    # VirusTotal config
    vtApiKey: Optional[str] = Body(None),
    # Email notification config
    notifyEmail: Optional[str] = Body(None),
    smtpHost: Optional[str] = Body(None),
    smtpPort: Optional[int] = Body(None),
    smtpUser: Optional[str] = Body(None),
    smtpPass: Optional[str] = Body(None),
    smtpFrom: Optional[str] = Body(None),
    # S3 storage config
    s3Endpoint: Optional[str] = Body(None),
    s3Bucket: Optional[str] = Body(None),
    s3AccessKey: Optional[str] = Body(None),
    s3SecretKey: Optional[str] = Body(None),
    s3Region: Optional[str] = Body(None),
    s3PublicUrl: Optional[str] = Body(None),
    # Upload limits (in MB)
    maxImageSize: Optional[int] = Body(None),
    maxSkillPackageSize: Optional[int] = Body(None),
    # Feature toggles
    rechargeEnabled: Optional[bool] = Body(None),
    publishEnabled: Optional[bool] = Body(None),
    betaAnnouncement: Optional[bool] = Body(None),
    # Announcement content
    announcementTitle: Optional[str] = Body(None),
    announcementContent: Optional[str] = Body(None),
    # ===== 积分设置 =====
    rechargePackages: Optional[list] = Body(None),   # [{amountYuan, points}]
    minRechargeYuan: Optional[int] = Body(None),
    pointsPerYuan: Optional[int] = Body(None),
    # ===== 等级设置 =====
    levelsConfig: Optional[list] = Body(None),       # [{level, name, icon, minExp}]
    expPublish: Optional[int] = Body(None),
    expDownload: Optional[int] = Body(None),
    expFavorite: Optional[int] = Body(None),
    expRechargeYuan: Optional[int] = Body(None),
    # ===== 提现设置 =====
    withdrawFeeRate: Optional[float] = Body(None),   # 0.04 = 4%
    minWithdrawPoints: Optional[int] = Body(None),
):
    settings = await kv.get("site:settings") or {}
    for key, val in {
        "title": title, "description": description, "keywords": keywords,
        "icp": icp, "police": police, "about": about,
        "feeRate": feeRate, "registerBonus": registerBonus,
        "alipayEnabled": alipayEnabled,
        "alipayAppId": alipayAppId,
        "alipayPrivateKey": alipayPrivateKey,
        "alipayPublicKey": alipayPublicKey,
        "alipaySandbox": alipaySandbox,
        "wechatEnabled": wechatEnabled,
        "wechatAppId": wechatAppId,
        "wechatMchId": wechatMchId,
        "wechatApiKey": wechatApiKey,
        "wechatApiV3Key": wechatApiV3Key,
        "wechatSerialNo": wechatSerialNo,
        "qqAppId": qqAppId,
        "qqAppKey": qqAppKey,
        "qqRedirectUri": qqRedirectUri,
        "wxLoginAppId": wxLoginAppId,
        "wxLoginAppSecret": wxLoginAppSecret,
        "wxLoginRedirectUri": wxLoginRedirectUri,
        "wxMpAppId": wxMpAppId,
        "wxMpAppSecret": wxMpAppSecret,
        "wxMiniAppId": wxMiniAppId,
        "wxMiniAppSecret": wxMiniAppSecret,
        "vtApiKey": vtApiKey,
        "notifyEmail": notifyEmail,
        "smtpHost": smtpHost,
        "smtpPort": smtpPort,
        "smtpUser": smtpUser,
        "smtpPass": smtpPass,
        "smtpFrom": smtpFrom,
        "s3Endpoint": s3Endpoint,
        "s3Bucket": s3Bucket,
        "s3AccessKey": s3AccessKey,
        "s3SecretKey": s3SecretKey,
        "s3Region": s3Region,
        "s3PublicUrl": s3PublicUrl,
        "maxImageSize": maxImageSize,
        "maxSkillPackageSize": maxSkillPackageSize,
        "rechargeEnabled": rechargeEnabled,
        "publishEnabled": publishEnabled,
        "betaAnnouncement": betaAnnouncement,
        "announcementTitle": announcementTitle,
        "announcementContent": announcementContent,
        # 积分设置
        "rechargePackages": rechargePackages,
        "minRechargeYuan": minRechargeYuan,
        "pointsPerYuan": pointsPerYuan,
        # 等级设置
        "levelsConfig": levelsConfig,
        "expPublish": expPublish,
        "expDownload": expDownload,
        "expFavorite": expFavorite,
        "expRechargeYuan": expRechargeYuan,
        # 提现设置
        "withdrawFeeRate": withdrawFeeRate,
        "minWithdrawPoints": minWithdrawPoints,
    }.items():
        if val is not None:
            # 跳过未修改的敏感字段（前端回传的脱敏占位符）
            if key in _SENSITIVE_FIELDS and isinstance(val, str) and _MASK in val:
                continue
            settings[key] = val
    await kv.put("site:settings", settings)
    return success_response()


# ========== Backup & Restore ==========

# Key categorization rules (applied to sanitized keys like user_1, skill_by_status_approved)
# KV keys use ":" as separator which gets sanitized to "_" by the edge function.
# e.g. "user:1" → "user_1", "user:idx:username:foo" → "user_idx_username_foo"
_CATEGORY_RULES = [
    # Users: user_1, user_idx_*, user__counter
    ("users",        re.compile(r'^user_')),
    # Skills: skill_1, skill_by_*, skill__counter
    ("skills",       re.compile(r'^skill_')),
    # Skill images: si_1, si_by_skill_*
    ("skills",       re.compile(r'^si_')),
    # Skill versions: sv_1, sv_by_skill_*
    ("skills",       re.compile(r'^sv_')),
    # Categories: cat_1, cat_all
    ("categories",   re.compile(r'^cat_')),
    # Settings: site_settings
    ("settings",     re.compile(r'^site_')),
    # Orders / Recharge: recharge_order_*, order_*
    ("orders",       re.compile(r'^(order_|recharge_)')),
    # Messages: msg_1, msg_by_user_*, msg_unread_*, msg__counter
    ("messages",     re.compile(r'^msg_')),
    # Reviews: review_1, review_by_skill_*, review__counter
    ("reviews",      re.compile(r'^review_')),
    # Favorites: fav_1, fav_by_user_*, fav_idx_*
    ("favorites",    re.compile(r'^fav_')),
    # Tokens: token_1, token_idx_*, token_by_user_*, token__counter
    ("tokens",       re.compile(r'^token_')),
    # Purchases: purchase_1, purchase_by_user_*, purchase_idx_*, purchase__counter
    ("purchases",    re.compile(r'^purchase_')),
    # Points records: pr_1, pr_by_user_*
    ("points",       re.compile(r'^pr_')),
    # Withdrawals: wd_1, wd_by_user_*, wd_pending, wd__counter
    ("withdrawals",  re.compile(r'^wd_')),
    # Follows: follow_1, follow_idx_*, follow_by_*
    ("social",       re.compile(r'^follow_')),
    # Audits: audit_1, audit_by_skill_*
    ("audits",       re.compile(r'^audit_')),
]

def _categorize_key(key: str) -> str:
    # 将 key 中的 \":\" 替换为 \"_\"，统一格式以匹配 regex
    sanitized = key.replace(":", "_")
    for cat, pattern in _CATEGORY_RULES:
        if pattern.match(sanitized):
            return cat
    return "other"


class BackupRequest(BaseModel):
    categories: Optional[list] = None  # None = all


class RestoreRequest(BaseModel):
    data: dict  # { key: value, ... } — flat KV pairs for one or more categories

class ChunkRequest(BaseModel):
    keys: list  # list of KV keys to fetch


@router.post("/backup")
async def backup_keys(
    req: BackupRequest,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """第一步：返回所有 KV 键列表（按分类），不读取值。

    只做 1 次 batch_get（读 counter）+ 少量 get_list，秒级完成。
    前端拿到键列表后分批调用 /backup/chunk 获取值。
    """
    keys: list[str] = []

    # 读取所有 counter（1 次 batch_get）
    counter_entities = [
        "user", "review", "purchase", "msg", "audit", "fav",
        "pr", "wd", "token", "follow", "recharge_order", "si", "sv",
    ]
    counter_keys = [f"{e}:_counter" for e in counter_entities]
    counter_vals = await kv.batch_get(counter_keys, timeout=10)
    counters = {}
    for entity, ck, cv in zip(counter_entities, counter_keys, counter_vals):
        n = int(cv) if cv else 0
        counters[entity] = n
        if n > 0:
            keys.append(ck)
            for i in range(1, n + 1):
                keys.append(f"{entity}:{i}")

    user_count = counters["user"]

    # Skill status lists
    for status in ["approved", "pending", "rejected", "offline"]:
        list_key = f"skill:by_status:{status}"
        skill_ids = await kv.get_list(list_key)
        keys.append(list_key)
        for sid in skill_ids:
            keys.append(f"skill:{sid}")
            keys.append(f"si:by_skill:{sid}")
            keys.append(f"sv:by_skill:{sid}")
            keys.append(f"review:by_skill:{sid}")
            keys.append(f"audit:by_skill:{sid}")

    # Categories
    cat_ids = await kv.get_list("cat:all")
    keys.append("cat:all")
    for cid in cat_ids:
        keys.append(f"cat:{cid}")
        keys.append(f"skill:by_cat:{cid}")

    # User-associated list keys
    for uid in range(1, user_count + 1):
        for prefix in [
            "skill:by_user", "purchase:by_user", "fav:by_user",
            "msg:by_user", "msg:unread", "pr:by_user",
            "token:by_user", "follow:by_er", "follow:by_ing",
        ]:
            keys.append(f"{prefix}:{uid}")

    # Fixed keys
    keys.append("wd:pending")
    keys.append("site:settings")

    # 去重
    keys = list(dict.fromkeys(keys))

    print(f"[Backup] enumerated {len(keys)} keys")
    return success_response({"keys": keys, "total": len(keys)})


@router.post("/backup/chunk")
async def backup_chunk(
    req: ChunkRequest,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """第二步：根据前端给出的键列表分批获取值。每次最多 100 个键。"""
    batch_keys = req.keys[:100]  # 限制每批最多 100 个
    if not batch_keys:
        return success_response({"data": {}})

    data = {}
    try:
        values = await kv.batch_get(batch_keys, timeout=10)
        for k, v in zip(batch_keys, values):
            if v is not None:
                data[k] = v
    except Exception as e:
        print(f"[Backup/chunk] batch_get failed: {e}")
        raise AppException(ErrorCode.PARAMS_ERROR, f"批量读取失败: {e}")

    # 从已读取的值中发现索引键
    idx_keys = []
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        if key.startswith("user:") and not key.startswith("user:idx:") and not key.startswith("user:_"):
            for field, prefix in [
                ("username", "user:idx:username"), ("openid", "user:idx:openid"),
                ("unionid", "user:idx:unionid"), ("qq_openid", "user:idx:qq"),
                ("wx_openid", "user:idx:wx"), ("wx_mini_openid", "user:idx:wxmini"),
            ]:
                v = val.get(field)
                if v:
                    idx_keys.append(f"{prefix}:{v}")
        elif key.startswith("purchase:") and val.get("user_id") and val.get("skill_id"):
            idx_keys.append(f"purchase:idx:{val['user_id']}:{val['skill_id']}")
        elif key.startswith("fav:") and val.get("user_id") and val.get("skill_id"):
            idx_keys.append(f"fav:idx:{val['user_id']}:{val['skill_id']}")
        elif key.startswith("token:") and val.get("token_key"):
            idx_keys.append(f"token:idx:{val['token_key']}")
        elif key.startswith("follow:") and val.get("follower_id") and val.get("following_id"):
            idx_keys.append(f"follow:idx:{val['follower_id']}:{val['following_id']}")

    # 补充读取索引键
    new_idx = [k for k in idx_keys if k not in data]
    if new_idx:
        try:
            idx_vals = await kv.batch_get(new_idx, timeout=10)
            for k, v in zip(new_idx, idx_vals):
                if v is not None:
                    data[k] = v
        except Exception:
            pass  # 索引键读取失败不影响主数据

    return success_response({"data": data})


@router.post("/restore")
async def restore_all(
    req: RestoreRequest,
    admin: dict = Depends(get_current_admin),
    kv: KVStore = Depends(get_kv),
):
    """从 JSON 备份恢复 KV 数据。"""

    if not req.data:
        raise AppException(ErrorCode.PARAMS_ERROR, "备份数据为空")

    pairs = [{"key": k, "value": v} for k, v in req.data.items()]
    try:
        count = await kv.bulk_put(pairs)
    except Exception as e:
        print(f"[Restore] Failed to bulk put: {e}")
        raise AppException(ErrorCode.PARAMS_ERROR, f"恢复数据失败: {e}")

    return success_response({
        "restored_keys": count,
    })
