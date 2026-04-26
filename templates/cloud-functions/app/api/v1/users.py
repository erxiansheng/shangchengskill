import asyncio
from datetime import datetime, timezone
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Depends, Query
import re

from pydantic import BaseModel

from app.api.v1.deps import get_kv, get_current_user
from app.core.exceptions import success_response, AppException, ErrorCode, paginated_response
from app.core.levels import get_level_info, LEVELS
from app.schemas.user import UserUpdate
from app.storage.kv import KVStore

router = APIRouter(prefix="/users", tags=["users"])


async def add_exp(kv: KVStore, user_id: int, amount: int):
    """给用户增加经验值"""
    user = await kv.get(f"user:{user_id}")
    if user:
        user["exp"] = user.get("exp", 0) + amount
        await kv.put(f"user:{user_id}", user)


async def update_user_stats(kv: KVStore, user_id: int, skill_delta: int = 0, downloads_delta: int = 0) -> None:
    """增量更新用户统计缓存（skill_count, total_downloads）。
    若 user:stats:{user_id} 尚未初始化，则先从技能列表全量重建（一次性开销），
    之后再应用增量，确保新用户发布技能后数据立刻准确。
    """
    stats = await kv.get(f"user:stats:{user_id}")
    if stats is None:
        # 首次：扫描全量技能列表建立基准，避免后续一直显示 0
        skill_ids = await kv.get_list(f"skill:by_user:{user_id}")
        skill_count = 0
        total_downloads = 0
        if skill_ids:
            BATCH = 200
            for i in range(0, len(skill_ids), BATCH):
                items = await kv.batch_get([f"skill:{sid}" for sid in skill_ids[i:i + BATCH]])
                for s in items:
                    if s and s.get("status") == "approved":
                        skill_count += 1
                        total_downloads += s.get("download_count", 0)
        stats = {"skill_count": skill_count, "total_downloads": total_downloads}
    await kv.put(f"user:stats:{user_id}", {
        "skill_count": max(0, stats.get("skill_count", 0) + skill_delta),
        "total_downloads": max(0, stats.get("total_downloads", 0) + downloads_delta),
    })


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    safe = {k: v for k, v in user.items() if k not in ("password_hash", "_token_scopes")}
    safe["level_info"] = get_level_info(user.get("exp", 0))
    return success_response(safe)


@router.put("/me")
async def update_me(
    data: UserUpdate,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    if data.nickname is not None:
        user["nickname"] = data.nickname
    if data.bio is not None:
        user["bio"] = data.bio
    if data.avatar_url is not None:
        user["avatar_url"] = data.avatar_url
    user["updated_at"] = datetime.now(timezone.utc).isoformat()

    await kv.put(f"user:{user['id']}", user)
    safe = {k: v for k, v in user.items() if k not in ("password_hash", "_token_scopes")}
    return success_response(safe)


# ─── 邮箱绑定 ───

class SendEmailCodeRequest(BaseModel):
    email: str

class BindEmailRequest(BaseModel):
    email: str
    code: str


@router.post("/me/email/send-code")
async def send_email_code(
    data: SendEmailCodeRequest,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """发送邮箱验证码（使用管理员 SMTP 配置发送）"""
    # 简单邮箱格式校验
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', data.email):
        raise AppException(ErrorCode.PARAMS_ERROR, "邮箱格式不正确")
    # 检查邮箱是否已被其他用户绑定
    existing_uid = await kv.get(f"user:idx:email:{data.email}")
    if existing_uid is not None and existing_uid != user["id"]:
        raise AppException(ErrorCode.PARAMS_ERROR, "该邮箱已被其他账号绑定")

    # 频率限制：60 秒内只能发一次
    rate_key = f"email_code_rate:{user['id']}"
    last_sent = await kv.get(rate_key)
    if last_sent:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_sent)).total_seconds()
        if elapsed < 60:
            raise AppException(ErrorCode.PARAMS_ERROR, f"请{int(60 - elapsed)}秒后再试")

    # 生成6位验证码
    code = f"{random.randint(100000, 999999)}"

    # 读取管理员 SMTP 配置
    settings = await kv.get("site:settings") or {}
    smtp_host = settings.get("smtpHost", "")
    smtp_port = int(settings.get("smtpPort", 465))
    smtp_user = settings.get("smtpUser", "")
    smtp_pass = settings.get("smtpPass", "")
    smtp_from = settings.get("smtpFrom", "") or smtp_user

    if not all([smtp_host, smtp_user, smtp_pass]):
        raise AppException(ErrorCode.PERMISSION_DENIED, "邮件服务未配置，请联系管理员")

    # 构造 HTML 邮件
    site_title = settings.get("title", "EdgeOneMall")
    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 0">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">
  <tr><td style="background:linear-gradient(135deg,#1ee07f,#00c853);padding:32px 40px;text-align:center">
    <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700">{site_title}</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px">邮箱绑定验证</p>
  </td></tr>
  <tr><td style="padding:36px 40px">
    <p style="margin:0 0 20px;color:#333;font-size:15px;line-height:1.6">您好，您正在将邮箱绑定到 <strong>{site_title}</strong> 账号。请使用以下验证码完成验证：</p>
    <div style="text-align:center;margin:28px 0">
      <div style="display:inline-block;background:#f0faf5;border:2px dashed #1ee07f;border-radius:12px;padding:16px 48px">
        <span style="font-size:36px;font-weight:800;letter-spacing:8px;color:#1a1a2e;font-family:monospace">{code}</span>
      </div>
    </div>
    <p style="margin:20px 0 0;color:#666;font-size:13px;line-height:1.6">⏱ 验证码有效期 <strong>10 分钟</strong>，请勿泄露给他人。</p>
    <p style="margin:8px 0 0;color:#999;font-size:12px">如非本人操作，请忽略此邮件。</p>
  </td></tr>
  <tr><td style="background:#fafafa;padding:20px 40px;text-align:center;border-top:1px solid #eee">
    <p style="margin:0;color:#aaa;font-size:12px">&copy; {site_title} · AI 技能交易市场</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【{site_title}】邮箱绑定验证码: {code}"
    msg["From"] = smtp_from
    msg["To"] = data.email
    # Plain text fallback
    plain = f"您好，您正在绑定邮箱到 {site_title} 账号。\n\n验证码：{code}\n\n验证码有效期 10 分钟，请勿泄露给他人。"
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # 发送邮件
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [data.email], msg.as_string())
        server.quit()
    except Exception as e:
        raise AppException(ErrorCode.SYSTEM_ERROR, f"邮件发送失败: {str(e)}")

    # 存储验证码（10分钟有效）
    code_key = f"email_code:{user['id']}"
    await kv.put(code_key, {"code": code, "email": data.email, "created_at": datetime.now(timezone.utc).isoformat()})
    await kv.put(rate_key, datetime.now(timezone.utc).isoformat())

    return success_response({"sent": True})


@router.post("/me/email/bind")
async def bind_email(
    data: BindEmailRequest,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """验证验证码并绑定邮箱"""
    code_key = f"email_code:{user['id']}"
    try:
        stored = await kv.get(code_key)
    except Exception:
        raise AppException(ErrorCode.SYSTEM_ERROR, "读取验证码失败，请重试")

    if not stored or not isinstance(stored, dict):
        raise AppException(ErrorCode.PARAMS_ERROR, "请先获取验证码")

    # 检查过期（10分钟）
    try:
        created = datetime.fromisoformat(stored["created_at"])
    except (KeyError, ValueError):
        await kv.delete(code_key)
        raise AppException(ErrorCode.PARAMS_ERROR, "验证码数据异常，请重新获取")

    if (datetime.now(timezone.utc) - created).total_seconds() > 600:
        await kv.delete(code_key)
        raise AppException(ErrorCode.PARAMS_ERROR, "验证码已过期，请重新获取")

    if stored.get("code") != data.code or stored.get("email") != data.email:
        raise AppException(ErrorCode.PARAMS_ERROR, "验证码错误")

    # 再次检查邮箱冲突
    existing_uid = await kv.get(f"user:idx:email:{data.email}")
    if existing_uid is not None and str(existing_uid) != str(user["id"]):
        raise AppException(ErrorCode.PARAMS_ERROR, "该邮箱已被其他账号绑定")

    # 删除旧邮箱索引
    old_email = user.get("email")
    if old_email:
        try:
            await kv.delete(f"user:idx:email:{old_email}")
        except Exception:
            pass  # non-critical

    # 绑定新邮箱
    user["email"] = data.email
    user["updated_at"] = datetime.now(timezone.utc).isoformat()
    await kv.put(f"user:{user['id']}", user)
    await kv.put(f"user:idx:email:{data.email}", user["id"])

    # 清理验证码
    try:
        await kv.delete(code_key)
    except Exception:
        pass

    return success_response({"email": data.email})


@router.get("/{user_id}/profile")
async def get_user_profile(user_id: int, kv: KVStore = Depends(get_kv)):
    user = await kv.get(f"user:{user_id}")
    if not user:
        raise AppException(ErrorCode.USER_NOT_FOUND, "用户不存在", 404)

    # 并发获取预计算统计缓存和关注者列表，避免全量扫描技能
    stats, follower_ids = await asyncio.gather(
        kv.get(f"user:stats:{user_id}"),
        kv.get_list(f"follow:by_ing:{user_id}"),
    )
    follower_count = len(follower_ids) if follower_ids else 0
    # stats 由 /admin/users/rebuild-stats 初始化，之后由各接口增量维护
    # 但老用户 / 从未触发过统计更新的用户 stats 可能为 None：此时按需懒加载初始化，
    # 否则前端会一直显示 0，且后续即便发生下载/发布，由于 update_user_stats 内部
    # 会先 rebuild 一次再加 delta，结果通常正确，但首次访问公开主页之前一直是 0。
    if stats is None:
        await update_user_stats(kv, user_id, 0, 0)
        stats = await kv.get(f"user:stats:{user_id}")
    skill_count = stats.get("skill_count", 0) if stats else 0
    total_downloads = stats.get("total_downloads", 0) if stats else 0

    # 只取最近 20 条技能用于展示，避免对大用户全量 batch_get
    skill_ids = await kv.get_list(f"skill:by_user:{user_id}")
    recent_ids = list(reversed(skill_ids))[:20] if skill_ids else []
    recent_skills = await kv.batch_get([f"skill:{sid}" for sid in recent_ids]) if recent_ids else []
    profile_skills = [
        {
            "id": s["id"],
            "title": s["title"],
            "price": s["price"],
            "is_free": s.get("is_free", False),
            "avg_rating": s.get("avg_rating", 0),
            "download_count": s.get("download_count", 0),
        }
        for s in recent_skills if s and s.get("status") == "approved"
    ]

    return success_response({
        "id": user["id"],
        "nickname": user["nickname"],
        "avatar_url": user.get("avatar_url"),
        "bio": user.get("bio"),
        "level": user.get("level", 1),
        "level_info": get_level_info(user.get("exp", 0)),
        "role": user.get("role", "user"),
        "created_at": user.get("created_at"),
        "skill_count": skill_count,
        "total_downloads": total_downloads,
        "follower_count": follower_count,
        "skills": profile_skills,
    })


@router.get("/{user_id}/follow/check")
async def check_follow(
    user_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Check if current user follows the target user."""
    existing = await kv.get(f"follow:idx:pair:{user['id']}:{user_id}")
    return success_response({"followed": existing is not None})


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    if user_id == user["id"]:
        raise AppException(ErrorCode.PARAMS_ERROR, "不能关注自己")

    existing = await kv.get(f"follow:idx:pair:{user['id']}:{user_id}")
    if existing is not None:
        raise AppException(ErrorCode.PARAMS_ERROR, "已经关注过了")

    follow_id = await kv.next_id("follow")
    now = datetime.now(timezone.utc).isoformat()
    follow = {
        "id": follow_id,
        "follower_id": user["id"],
        "following_id": user_id,
        "created_at": now,
    }
    await kv.put(f"follow:{follow_id}", follow)
    await kv.put(f"follow:idx:pair:{user['id']}:{user_id}", follow_id)
    await kv.add_to_list(f"follow:by_er:{user['id']}", follow_id)
    await kv.add_to_list(f"follow:by_ing:{user_id}", follow_id)
    return success_response({"followed": True})


@router.delete("/{user_id}/follow")
async def unfollow_user(
    user_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    follow_id = await kv.get(f"follow:idx:pair:{user['id']}:{user_id}")
    if follow_id is not None:
        await kv.delete(f"follow:{follow_id}")
        await kv.delete(f"follow:idx:pair:{user['id']}:{user_id}")
        await kv.remove_from_list(f"follow:by_er:{user['id']}", follow_id)
        await kv.remove_from_list(f"follow:by_ing:{user_id}", follow_id)
    return success_response({"followed": False})


@router.get("/me/following")
async def get_following(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    follow_ids = await kv.get_list(f"follow:by_er:{user['id']}")
    total = len(follow_ids)

    start = (page - 1) * page_size
    page_ids = follow_ids[start:start + page_size]
    follows = await kv.batch_get([f"follow:{fid}" for fid in page_ids])

    # Get user info for each following
    target_ids = [f["following_id"] for f in follows if f]
    users = await kv.batch_get([f"user:{uid}" for uid in target_ids])

    items = []
    for u in users:
        if u:
            items.append({"id": u["id"], "nickname": u["nickname"], "avatar_url": u.get("avatar_url")})

    return paginated_response(items, total, page, page_size)


@router.get("/me/followers")
async def get_followers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    follow_ids = await kv.get_list(f"follow:by_ing:{user['id']}")
    total = len(follow_ids)

    start = (page - 1) * page_size
    page_ids = follow_ids[start:start + page_size]
    follows = await kv.batch_get([f"follow:{fid}" for fid in page_ids])

    # Get user info for each follower
    follower_ids = [f["follower_id"] for f in follows if f]
    users = await kv.batch_get([f"user:{uid}" for uid in follower_ids])

    items = []
    for u in users:
        if u:
            items.append({"id": u["id"], "nickname": u["nickname"], "avatar_url": u.get("avatar_url")})

    return paginated_response(items, total, page, page_size)
