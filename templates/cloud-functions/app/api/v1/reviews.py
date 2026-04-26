import base64
import hashlib
import hmac
import math
import random
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.deps import get_kv, get_current_user
from app.core.config import settings
from app.core.exceptions import success_response, AppException, ErrorCode, paginated_response
from app.core.levels import get_level_info
from app.schemas.review import ReviewCreate
from app.storage.kv import KVStore

router = APIRouter(prefix="", tags=["reviews"])

REVIEW_RATE_LIMIT_SECONDS = 180  # 3 minutes
REVIEW_MAX_LENGTH = 300

# ── 敏感词列表（广告/色情等） ─────────────────
_BANNED_WORDS = [
    # 色情
    "约炮", "一夜情", "裸聊", "色情", "成人视频", "成人网站", "av女优", "性服务",
    "嫖娼", "卖淫", "援交", "包夜", "按摩服务", "上门服务",
    # 赌博
    "赌博", "博彩", "网赌", "赌场", "百家乐", "老虎机", "六合彩", "时时彩",
    "北京赛车", "幸运飞艇",
    # 诈骗/违法
    "代开发票", "办证", "枪支", "毒品", "冰毒", "大麻", "迷药",
    # 广告/引流
    "加微信", "加QQ", "扫码领取", "免费领", "日赚", "月入过万","微信",
    "兼职赚钱", "躺赚", "刷单", "薅羊毛",
    "代理加盟", "财务自由",
    # 政治敏感
    "翻墙", "VPN推荐",
]


def _contains_banned_content(text: str) -> bool:
    """检查文本是否包含违禁内容"""
    lower = text.lower()
    for word in _BANNED_WORDS:
        if word.lower() in lower:
            return True
    return False


# ── 验证码工具 ──────────────────────────
_CAPTCHA_SECRET = settings.SECRET_KEY[:16]
_CAPTCHA_EXPIRE = 300  # 5 minutes


def _generate_captcha() -> dict:
    """生成算术验证码，返回 {image_base64, token}"""
    ops = [
        lambda: (random.randint(1, 50), random.randint(1, 50), "+"),
        lambda: (random.randint(10, 99), random.randint(1, 30), "-"),
        lambda: (random.randint(2, 12), random.randint(2, 9), "×"),
    ]
    a, b, op = random.choice(ops)()
    if op == "+":
        answer = a + b
    elif op == "-":
        answer = a - b
    else:
        answer = a * b

    question = f"{a} {op} {b} = ?"

    # 生成带干扰的 SVG 图片
    svg = _render_captcha_svg(question)
    image_b64 = base64.b64encode(svg.encode()).decode()

    ts = int(time.time())
    payload = f"{answer}:{ts}"
    sig = hmac.new(_CAPTCHA_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    token = f"{ts}:{sig}"

    return {"image": f"data:image/svg+xml;base64,{image_b64}", "token": token}


def _render_captcha_svg(text: str) -> str:
    """渲染带干扰线和噪点的 SVG 验证码图片"""
    w, h = 180, 50
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">']

    # 随机背景色（浅色）
    bg_r, bg_g, bg_b = random.randint(230, 255), random.randint(230, 255), random.randint(230, 255)
    parts.append(f'<rect width="{w}" height="{h}" fill="rgb({bg_r},{bg_g},{bg_b})"/>')

    # 干扰线（4-6 条弧线）
    for _ in range(random.randint(4, 6)):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        cx, cy = random.randint(0, w), random.randint(0, h)
        r, g, b = random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)
        sw = round(random.uniform(0.8, 2.0), 1)
        parts.append(f'<path d="M{x1},{y1} Q{cx},{cy} {x2},{y2}" '
                     f'fill="none" stroke="rgb({r},{g},{b})" stroke-width="{sw}"/>')

    # 噪点（20-30 个小圆）
    for _ in range(random.randint(20, 30)):
        cx, cy = random.randint(0, w), random.randint(0, h)
        r, g, b = random.randint(120, 220), random.randint(120, 220), random.randint(120, 220)
        radius = round(random.uniform(0.5, 1.5), 1)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="rgb({r},{g},{b})"/>')

    # 逐字符渲染（带随机旋转、偏移、大小、颜色）
    chars = list(text)
    x_cursor = 10
    for ch in chars:
        font_size = random.randint(20, 28)
        rot = random.randint(-15, 15)
        dy = random.randint(-4, 4)
        r, g, b = random.randint(20, 100), random.randint(20, 100), random.randint(20, 100)
        y_pos = h // 2 + 6 + dy
        parts.append(
            f'<text x="{x_cursor}" y="{y_pos}" font-size="{font_size}" '
            f'font-family="Arial,sans-serif" font-weight="bold" '
            f'fill="rgb({r},{g},{b})" '
            f'transform="rotate({rot},{x_cursor},{y_pos})">{ch}</text>'
        )
        x_cursor += random.randint(14, 22) if ch != ' ' else 8

    parts.append('</svg>')
    return ''.join(parts)


def _verify_captcha(token: str, user_answer: int) -> bool:
    """验证用户的验证码答案"""
    try:
        parts = token.split(":")
        if len(parts) != 2:
            return False
        ts, sig = int(parts[0]), parts[1]
        if int(time.time()) - ts > _CAPTCHA_EXPIRE:
            return False
        payload = f"{user_answer}:{ts}"
        expected = hmac.new(_CAPTCHA_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        return hmac.compare_digest(sig, expected)
    except (ValueError, TypeError):
        return False


@router.get("/captcha")
async def get_captcha():
    """获取评论验证码（返回 SVG 图片 base64）"""
    cap = _generate_captcha()
    return success_response({
        "image": cap["image"],
        "token": cap["token"],
    })


@router.get("/skills/{skill_id}/reviews")
async def get_reviews(
    skill_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort: str = Query("newest"),
    kv: KVStore = Depends(get_kv),
):
    review_ids = await kv.get_list(f"review:by_skill:{skill_id}")
    reviews = await kv.batch_get([f"review:{rid}" for rid in review_ids])
    visible = [r for r in reviews if r and r.get("status") == "visible"]

    # Sort
    visible.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    total = len(visible)

    # Paginate
    start = (page - 1) * page_size
    page_items = visible[start:start + page_size]

    # Get user info
    user_ids = list({r["user_id"] for r in page_items})
    users = await kv.batch_get([f"user:{uid}" for uid in user_ids])
    user_map = {u["id"]: u for u in users if u}

    # Configurable levels
    site_settings = await kv.get("site:settings") or {}
    cfg_levels = site_settings.get("levelsConfig") or None

    items = []
    for r in page_items:
        u = user_map.get(r["user_id"], {})
        items.append({
            "id": r["id"], "rating": r["rating"], "content": r.get("content"),
            "user_id": r["user_id"],
            "user_nickname": u.get("nickname"), "user_avatar": u.get("avatar_url"),
            "user_role": u.get("role", "user"),
            "user_level_info": get_level_info(u.get("exp", 0), levels=cfg_levels),
            "created_at": r.get("created_at"),
        })

    return paginated_response(items, total, page, page_size)


@router.post("/skills/{skill_id}/reviews")
async def create_review(
    skill_id: str,
    data: ReviewCreate,
    request: Request,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    # 验证码校验
    if not _verify_captcha(data.captcha_token, data.captcha_answer):
        raise AppException(ErrorCode.PARAMS_ERROR, "验证码错误或已过期，请重新获取")

    # 内容长度校验
    content = (data.content or "").strip()
    if len(content) > REVIEW_MAX_LENGTH:
        raise AppException(ErrorCode.PARAMS_ERROR, f"评价内容不能超过 {REVIEW_MAX_LENGTH} 字")

    # 内容风控
    if content and _contains_banned_content(content):
        raise AppException(ErrorCode.PARAMS_ERROR, "评价内容包含违规信息，请整改后重新发布")

    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)

    # IP-based rate limiting: 1 review per 3 minutes per IP
    client_ip = request.headers.get("X-Real-IP") or (request.client.host if request.client else "unknown")
    if client_ip and client_ip != "unknown":
        rate_key = f"rate:review_ip:{client_ip}"
        last_review_ts = await kv.get(rate_key)
        now_ts = datetime.now(timezone.utc).timestamp()
        if last_review_ts and (now_ts - float(last_review_ts)) < REVIEW_RATE_LIMIT_SECONDS:
            remaining = int(REVIEW_RATE_LIMIT_SECONDS - (now_ts - float(last_review_ts)))
            raise AppException(ErrorCode.PARAMS_ERROR, f"评论过于频繁，请 {remaining} 秒后再试", 429)
        await kv.put(rate_key, now_ts)

    review_id = await kv.next_id("review")
    now = datetime.now(timezone.utc).isoformat()
    review = {
        "id": review_id,
        "user_id": user["id"],
        "skill_id": skill_id,
        "rating": max(1, min(5, data.rating)),
        "content": content,
        "status": "visible",
        "created_at": now,
    }
    await kv.put(f"review:{review_id}", review)
    await kv.add_to_list(f"review:by_skill:{skill_id}", review_id)

    # Recalculate average rating
    all_review_ids = await kv.get_list(f"review:by_skill:{skill_id}")
    all_reviews = await kv.batch_get([f"review:{rid}" for rid in all_review_ids])
    visible_ratings = [r["rating"] for r in all_reviews if r and r.get("status") == "visible"]
    if visible_ratings:
        skill["avg_rating"] = round(sum(visible_ratings) / len(visible_ratings), 1)
    skill["review_count"] = len(visible_ratings)
    await kv.put(f"skill:{skill_id}", skill)

    return success_response({"id": review_id})


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    review = await kv.get(f"review:{review_id}")
    if not review:
        raise AppException(ErrorCode.PARAMS_ERROR, "评价不存在", 404)
    if review["user_id"] != user["id"] and user.get("role") != "admin":
        raise AppException(ErrorCode.PERMISSION_DENIED, "无权限操作", 403)

    review["status"] = "hidden"
    await kv.put(f"review:{review_id}", review)
    return success_response()


@router.post("/reviews/{review_id}/report")
async def report_review(
    review_id: int,
    reason: str = "",
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    review = await kv.get(f"review:{review_id}")
    if not review:
        raise AppException(ErrorCode.PARAMS_ERROR, "评价不存在", 404)
    review["status"] = "reported"
    await kv.put(f"review:{review_id}", review)
    return success_response()
