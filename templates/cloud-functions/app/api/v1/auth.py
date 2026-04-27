import asyncio
from datetime import datetime, timezone
import hashlib
import urllib.parse
import httpx

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.api.v1.deps import get_kv
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import AppException, ErrorCode, success_response
from app.schemas.user import UserRegister, UserLogin, RefreshTokenRequest
from app.storage.kv import KVStore

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserRegister, kv: KVStore = Depends(get_kv)):
    # Check unique username
    existing = await kv.get(f"user:idx:username:{data.username}")
    if existing is not None:
        raise AppException(ErrorCode.PHONE_REGISTERED, "用户名已被占用")

    # Check unique email / phone
    if data.email:
        if await kv.get(f"user:idx:email:{data.email}") is not None:
            raise AppException(ErrorCode.PHONE_REGISTERED, "邮箱已被注册")
    if data.phone:
        if await kv.get(f"user:idx:phone:{data.phone}") is not None:
            raise AppException(ErrorCode.PHONE_REGISTERED, "手机号已被注册")

    user_id = await kv.next_id("user")
    now = datetime.now(timezone.utc).isoformat()

    settings = await kv.get("site:settings") or {}
    register_bonus = settings.get("registerBonus", 100)

    # First-registered-user-auto-admin: if no admin exists yet (or only the
    # bootstrap "admin" placeholder seeded by `seed_default_admin` is the sole
    # entry and never logged in), promote this brand-new user to admin so the
    # site owner can log in to /admin with their normal account.
    password_hash = hash_password(data.password)
    admin_list = await kv.get_list("admin:list") or []
    is_first_real_user = (user_id == 1) or (len(admin_list) == 0)
    role = "admin" if is_first_real_user else "user"

    user = {
        "id": user_id,
        "username": data.username,
        "nickname": data.nickname,
        "password_hash": password_hash,
        "phone": data.phone,
        "email": data.email,
        "avatar_url": None,
        "bio": None,
        "level": 1,
        "points_balance": register_bonus,
        "total_earned": 0,
        "role": role,
        "status": "active",
        "wx_openid": None,
        "created_at": now,
        "updated_at": now,
    }

    await kv.put(f"user:{user_id}", user)
    await kv.put(f"user:idx:username:{data.username}", user_id)
    if data.email:
        await kv.put(f"user:idx:email:{data.email}", user_id)
    if data.phone:
        await kv.put(f"user:idx:phone:{data.phone}", user_id)

    if is_first_real_user:
        admin_username = data.username.lower()
        admin_rec = {
            "username": admin_username,
            "password_hash": password_hash,
            "created_at": now,
            "must_change_password": False,
            "disabled": False,
            "linked_user_id": user_id,
        }
        await kv.put(f"admin:user:{admin_username}", admin_rec)
        if admin_username not in admin_list:
            await kv.add_to_list("admin:list", admin_username)

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 7200,
        "user": {
            "id": user_id,
            "nickname": data.nickname,
            "avatar_url": None,
            "points_balance": register_bonus,
            "role": role,
        },
        "is_admin": is_first_real_user,
    })


@router.post("/login")
async def login(data: UserLogin, kv: KVStore = Depends(get_kv)):
    user_id = await kv.get(f"user:idx:username:{data.username}")
    if user_id is None:
        raise AppException(ErrorCode.USER_NOT_FOUND, "账号不存在")

    user = await kv.get(f"user:{user_id}")
    if not user:
        raise AppException(ErrorCode.USER_NOT_FOUND, "账号不存在")
    if not verify_password(data.password, user["password_hash"]):
        raise AppException(ErrorCode.PASSWORD_ERROR, "密码错误")
    if user.get("status") == "banned" or user.get("is_banned"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)

    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])

    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 7200,
        "user": {
            "id": user["id"],
            "nickname": user["nickname"],
            "avatar_url": user.get("avatar_url"),
            "points_balance": user["points_balance"],
            "role": user.get("role", "user"),
        },
    })


@router.post("/refresh")
async def refresh_token(data: RefreshTokenRequest, kv: KVStore = Depends(get_kv)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AppException(ErrorCode.NOT_AUTHENTICATED, "刷新令牌无效", 401)

    user_id = int(payload["sub"])
    user = await kv.get(f"user:{user_id}")
    if not user:
        raise AppException(ErrorCode.USER_NOT_FOUND, "用户不存在")
    if user.get("status") == "banned" or user.get("is_banned"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)

    new_access = create_access_token(user["id"])
    new_refresh = create_refresh_token(user["id"])
    return success_response({
        "access_token": new_access,
        "refresh_token": new_refresh,
        "expires_in": 7200,
    })


@router.post("/sms-code")
async def send_sms_code(phone: str = "", scene: str = "register"):
    """Mock SMS code sending."""
    return success_response({"message": "验证码已发送（开发模式: 123456）"})


# ─── QQ OAuth 登录 ───

QQ_AUTH_URL = "https://graph.qq.com/oauth2.0/authorize"
QQ_TOKEN_URL = "https://graph.qq.com/oauth2.0/token"
QQ_OPENID_URL = "https://graph.qq.com/oauth2.0/me"
QQ_USERINFO_URL = "https://graph.qq.com/user/get_user_info"


async def _get_qq_config(kv: KVStore):
    settings = await kv.get("site:settings") or {}
    app_id = settings.get("qqAppId", "")
    app_key = settings.get("qqAppKey", "")
    if not app_id or not app_key:
        return None
    return {"app_id": app_id, "app_key": app_key, "redirect_uri": settings.get("qqRedirectUri", "")}


@router.get("/qq/login")
async def qq_login_redirect(request: Request, kv: KVStore = Depends(get_kv)):
    """Redirect user to QQ authorization page."""
    cfg = await _get_qq_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "QQ 登录未配置，请联系管理员")

    redirect_uri = cfg["redirect_uri"]
    if not redirect_uri:
        origin = _resolve_origin(request)
        if origin:
            redirect_uri = f"{origin}/api/v1/auth/qq/callback"

    if not redirect_uri:
        raise AppException(ErrorCode.PERMISSION_DENIED, "无法确定QQ回调地址，请在管理后台配置回调地址")

    params = {
        "response_type": "code",
        "client_id": cfg["app_id"],
        "redirect_uri": redirect_uri,
        "state": "EdgeOneMall_qq",
        "scope": "get_user_info",
    }
    url = f"{QQ_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/qq/callback")
async def qq_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
    kv: KVStore = Depends(get_kv),
):
    """Handle QQ OAuth callback: exchange code → get openid → get user info → login/register."""
    cfg = await _get_qq_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "QQ 登录未配置")

    redirect_uri = cfg["redirect_uri"]
    if not redirect_uri:
        origin = _resolve_origin(request)
        if origin:
            redirect_uri = f"{origin}/api/v1/auth/qq/callback"

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Exchange code for access token
        token_resp = await client.get(QQ_TOKEN_URL, params={
            "grant_type": "authorization_code",
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_key"],
            "code": code,
            "redirect_uri": redirect_uri,
            "fmt": "json",
        })
        token_data = token_resp.json()
        qq_access_token = token_data.get("access_token")
        if not qq_access_token:
            raise AppException(ErrorCode.PERMISSION_DENIED, f"QQ 授权失败: {token_data.get('error_description', '未知错误')}")

        # 2. Get openid
        openid_resp = await client.get(QQ_OPENID_URL, params={
            "access_token": qq_access_token,
            "fmt": "json",
        })
        openid_data = openid_resp.json()
        qq_openid = openid_data.get("openid")
        if not qq_openid:
            raise AppException(ErrorCode.PERMISSION_DENIED, "获取 QQ openid 失败")

        # 3. Get user info
        userinfo_resp = await client.get(QQ_USERINFO_URL, params={
            "access_token": qq_access_token,
            "oauth_consumer_key": cfg["app_id"],
            "openid": qq_openid,
        })
        qq_user = userinfo_resp.json()

    # 4. Check if user already linked via qq_openid
    existing_uid = await kv.get(f"user:idx:qq_openid:{qq_openid}")
    if existing_uid:
        user = await kv.get(f"user:{existing_uid}")
        if user:
            if user.get("status") == "banned" or user.get("is_banned"):
                raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            # Redirect to frontend with tokens
            return _oauth_redirect(access_token, refresh_token, user, request)

    # 5. Auto-register new user — with dedup lock
    lock_ok = await kv.claim_register(f"qq:{qq_openid}")
    if not lock_ok:
        await asyncio.sleep(1)
        dup_uid = await kv.get_fresh(f"user:idx:qq_openid:{qq_openid}")
        if dup_uid:
            user = await kv.get(f"user:{dup_uid}")
            if user:
                access_token = create_access_token(user["id"])
                refresh_token = create_refresh_token(user["id"])
                return _oauth_redirect(access_token, refresh_token, user, request)

    nickname = qq_user.get("nickname", f"QQ用户{qq_openid[:6]}")
    avatar_url = qq_user.get("figureurl_qq_2") or qq_user.get("figureurl_qq_1") or None
    user_id = await kv.next_id("user")

    # Race check after next_id
    race_uid = await kv.get_fresh(f"user:idx:qq_openid:{qq_openid}")
    if race_uid:
        user = await kv.get(f"user:{race_uid}")
        if user:
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            return _oauth_redirect(access_token, refresh_token, user, request)

    now = datetime.now(timezone.utc).isoformat()

    # 生成简洁的 qq_xxxxxx 格式用户名
    _qq_hash = hashlib.md5(qq_openid.encode()).hexdigest()[:6]
    username = f"qq_{_qq_hash}"
    # Ensure unique username
    if await kv.get(f"user:idx:username:{username}"):
        username = f"qq_{_qq_hash}_{user_id}"

    settings = await kv.get("site:settings") or {}
    register_bonus = settings.get("registerBonus", 100)

    user = {
        "id": user_id,
        "username": username,
        "nickname": nickname,
        "password_hash": "",
        "phone": None,
        "email": None,
        "avatar_url": avatar_url,
        "bio": None,
        "level": 1,
        "points_balance": register_bonus,
        "total_earned": 0,
        "role": "user",
        "status": "active",
        "wx_openid": None,
        "qq_openid": qq_openid,
        "created_at": now,
        "updated_at": now,
    }

    await kv.put(f"user:{user_id}", user)
    await kv.put(f"user:idx:username:{username}", user_id)
    await kv.put(f"user:idx:qq_openid:{qq_openid}", user_id)

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return _oauth_redirect(access_token, refresh_token, user, request)


def _oauth_redirect(access_token: str, refresh_token: str, user: dict, request=None):
    """Redirect back to frontend with tokens in URL fragment (hash)."""
    params = urllib.parse.urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "nickname": user.get("nickname", ""),
        "user_id": user.get("id", ""),
        "role": user.get("role", "user"),
    })
    # Use absolute URL to avoid issues in WeChat browser
    origin = ""
    if request:
        origin = _resolve_origin(request)
    redirect_path = f"{origin}/login/oauth-callback#{params}"
    return RedirectResponse(url=redirect_path, status_code=302)


# ─── 微信 OAuth 扫码登录 ───

WX_AUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
WX_H5_AUTH_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
WX_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WX_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


async def _get_wx_config(kv: KVStore):
    settings = await kv.get("site:settings") or {}
    app_id = settings.get("wxLoginAppId", "")
    app_secret = settings.get("wxLoginAppSecret", "")
    if not app_id or not app_secret:
        return None
    return {"app_id": app_id, "app_secret": app_secret, "redirect_uri": settings.get("wxLoginRedirectUri", "")}


async def _get_wx_mp_config(kv: KVStore):
    """获取微信公众号配置（用于 H5 网页授权）"""
    settings = await kv.get("site:settings") or {}
    app_id = settings.get("wxMpAppId", "")
    app_secret = settings.get("wxMpAppSecret", "")
    if not app_id or not app_secret:
        return None
    return {"app_id": app_id, "app_secret": app_secret}


def _resolve_origin(request) -> str:
    """从请求头中获取站点 origin（优先使用 Edge Function 传递的 X-Internal-Origin）。"""
    origin = request.headers.get("x-internal-origin", "")
    if not origin:
        host = request.headers.get("host", "")
        scheme = request.headers.get("x-forwarded-proto", "https")
        if host:
            origin = f"{scheme}://{host}"
    return origin.rstrip("/")


@router.get("/wechat/login")
async def wechat_login_redirect(request: Request, kv: KVStore = Depends(get_kv), debug: str = Query("")):
    """Redirect user to WeChat QR scan authorization page."""
    cfg = await _get_wx_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信登录未配置，请联系管理员")

    # 优先使用管理后台配置的回调地址，否则自动根据请求来源生成
    redirect_uri = cfg["redirect_uri"]
    if not redirect_uri:
        origin = _resolve_origin(request)
        if origin:
            redirect_uri = f"{origin}/api/v1/auth/wechat/callback"

    if not redirect_uri:
        raise AppException(ErrorCode.PERMISSION_DENIED, "无法确定微信回调地址，请在管理后台配置回调地址")

    params = {
        "appid": cfg["app_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": "EdgeOneMall_wx",
    }

    # debug 模式：返回即将跳转的完整 URL 和参数，便于排查
    if debug == "1":
        full_url = f"{WX_AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"
        return success_response({
            "redirect_url": full_url,
            "params": params,
            "origin_detected": _resolve_origin(request),
            "hint": "请确认: 1) AppID 是微信开放平台(open.weixin.qq.com)网站应用的AppID 2) 授权回调域已设为对应域名(不含协议和路径)"
        })

    url = f"{WX_AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"
    return RedirectResponse(url=url, status_code=302)


@router.get("/wechat/callback")
async def wechat_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
    kv: KVStore = Depends(get_kv),
):
    """Handle WeChat OAuth callback."""
    cfg = await _get_wx_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信登录未配置")

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Exchange code for access token + openid
        token_resp = await client.get(WX_TOKEN_URL, params={
            "appid": cfg["app_id"],
            "secret": cfg["app_secret"],
            "code": code,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        wx_access_token = token_data.get("access_token")
        wx_openid = token_data.get("openid")
        if not wx_access_token or not wx_openid:
            raise AppException(ErrorCode.PERMISSION_DENIED, f"微信授权失败: {token_data.get('errmsg', '未知错误')}")

        # 2. Get user info
        userinfo_resp = await client.get(WX_USERINFO_URL, params={
            "access_token": wx_access_token,
            "openid": wx_openid,
            "lang": "zh_CN",
        })
        wx_user = userinfo_resp.json()

    # 3. Check if user already linked — prefer unionid for cross-platform matching
    wx_unionid = token_data.get("unionid") or wx_user.get("unionid") or ""
    existing_uid = None
    if wx_unionid:
        existing_uid = await kv.get(f"user:idx:wx_unionid:{wx_unionid}")
    if existing_uid is None:
        existing_uid = await kv.get(f"user:idx:wx_openid:{wx_openid}")
    if existing_uid:
        user = await kv.get(f"user:{existing_uid}")
        if user:
            if user.get("status") == "banned" or user.get("is_banned"):
                raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)
            # Backfill unionid index if missing
            if wx_unionid and not user.get("wx_unionid"):
                user["wx_unionid"] = wx_unionid
                await kv.put(f"user:{user['id']}", user)
                await kv.put(f"user:idx:wx_unionid:{wx_unionid}", user["id"])
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            return _oauth_redirect(access_token, refresh_token, user, request)

    # 4. Auto-register — with dedup lock
    lock_ok = await kv.claim_register(f"wx:{wx_unionid or wx_openid}")
    if not lock_ok:
        await asyncio.sleep(1)
        dup_uid = await kv.get_fresh(f"user:idx:wx_openid:{wx_openid}")
        if not dup_uid and wx_unionid:
            dup_uid = await kv.get_fresh(f"user:idx:wx_unionid:{wx_unionid}")
        if dup_uid:
            user = await kv.get(f"user:{dup_uid}")
            if user:
                access_token = create_access_token(user["id"])
                refresh_token = create_refresh_token(user["id"])
                return _oauth_redirect(access_token, refresh_token, user, request)

    nickname = wx_user.get("nickname", f"微信用户{wx_openid[:6]}")
    avatar_url = wx_user.get("headimgurl") or None
    user_id = await kv.next_id("user")

    # Race check after next_id
    race_uid = await kv.get_fresh(f"user:idx:wx_openid:{wx_openid}")
    if not race_uid and wx_unionid:
        race_uid = await kv.get_fresh(f"user:idx:wx_unionid:{wx_unionid}")
    if race_uid:
        user = await kv.get(f"user:{race_uid}")
        if user:
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            return _oauth_redirect(access_token, refresh_token, user, request)

    now = datetime.now(timezone.utc).isoformat()

    # 生成简洁的 wx_xxxxxx 格式用户名
    _wx_hash = hashlib.md5(wx_openid.encode()).hexdigest()[:6]
    username = f"wx_{_wx_hash}"
    if await kv.get(f"user:idx:username:{username}"):
        username = f"wx_{_wx_hash}_{user_id}"

    settings = await kv.get("site:settings") or {}
    register_bonus = settings.get("registerBonus", 100)

    user = {
        "id": user_id,
        "username": username,
        "nickname": nickname,
        "password_hash": "",
        "phone": None,
        "email": None,
        "avatar_url": avatar_url,
        "bio": None,
        "level": 1,
        "points_balance": register_bonus,
        "total_earned": 0,
        "role": "user",
        "status": "active",
        "wx_openid": wx_openid,
        "wx_unionid": wx_unionid,
        "qq_openid": None,
        "created_at": now,
        "updated_at": now,
    }

    await kv.put(f"user:{user_id}", user)
    await kv.put(f"user:idx:username:{username}", user_id)
    await kv.put(f"user:idx:wx_openid:{wx_openid}", user_id)
    if wx_unionid:
        await kv.put(f"user:idx:wx_unionid:{wx_unionid}", user_id)

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return _oauth_redirect(access_token, refresh_token, user, request)


# ─── 微信 H5 网页授权（公众号）───

@router.get("/wechat/h5-login")
async def wechat_h5_login(request: Request, kv: KVStore = Depends(get_kv), debug: str = Query("")):
    """Redirect user to WeChat H5 OAuth authorize page (requires 公众号 AppID)."""
    cfg = await _get_wx_mp_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信公众号 H5 登录未配置，请在管理后台填写公众号 AppID/AppSecret")

    origin = _resolve_origin(request)
    # 微信公众号后台配置的授权域名需要和 redirect_uri 一致，强制 www
    if origin and "://YOUR_DOMAIN_HERE" in origin:
        origin = origin.replace("://YOUR_DOMAIN_HERE", "://YOUR_DOMAIN_HERE")
    redirect_uri = f"{origin}/api/v1/auth/wechat/h5-callback" if origin else ""
    if not redirect_uri:
        raise AppException(ErrorCode.PERMISSION_DENIED, "无法确定微信 H5 回调地址")

    params = {
        "appid": cfg["app_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": "EdgeOneMall_wx_h5",
    }

    if debug == "1":
        full_url = f"{WX_H5_AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"
        return success_response({
            "redirect_url": full_url,
            "params": params,
            "origin_detected": origin,
            "hint": "H5 网页授权需要: 1) 已认证的微信服务号 AppID 2) 在公众号后台设置网页授权域名",
        })

    url = f"{WX_H5_AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"
    return RedirectResponse(url=url, status_code=302)


@router.get("/wechat/h5-callback")
async def wechat_h5_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
    kv: KVStore = Depends(get_kv),
):
    """Handle WeChat H5 OAuth callback (公众号网页授权)."""
    cfg = await _get_wx_mp_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信公众号 H5 登录未配置")

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Exchange code for access token + openid
        token_resp = await client.get(WX_TOKEN_URL, params={
            "appid": cfg["app_id"],
            "secret": cfg["app_secret"],
            "code": code,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        wx_access_token = token_data.get("access_token")
        wx_openid = token_data.get("openid")
        if not wx_access_token or not wx_openid:
            raise AppException(ErrorCode.PERMISSION_DENIED, f"微信 H5 授权失败: {token_data.get('errmsg', '未知错误')}")

        # 2. Get user info
        userinfo_resp = await client.get(WX_USERINFO_URL, params={
            "access_token": wx_access_token,
            "openid": wx_openid,
            "lang": "zh_CN",
        })
        wx_user = userinfo_resp.json()

    # 3. Check if user already linked — prefer unionid for cross-platform matching
    wx_unionid = token_data.get("unionid") or wx_user.get("unionid") or ""
    existing_uid = None
    if wx_unionid:
        existing_uid = await kv.get(f"user:idx:wx_unionid:{wx_unionid}")
    if existing_uid is None:
        existing_uid = await kv.get(f"user:idx:wx_openid:{wx_openid}")
    if existing_uid:
        user = await kv.get(f"user:{existing_uid}")
        if user:
            if user.get("status") == "banned" or user.get("is_banned"):
                raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)
            if wx_unionid and not user.get("wx_unionid"):
                user["wx_unionid"] = wx_unionid
                await kv.put(f"user:{user['id']}", user)
                await kv.put(f"user:idx:wx_unionid:{wx_unionid}", user["id"])
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            return _oauth_redirect(access_token, refresh_token, user, request)

    # 4. Auto-register — with dedup lock (H5)
    lock_ok = await kv.claim_register(f"wx_h5:{wx_unionid or wx_openid}")
    if not lock_ok:
        await asyncio.sleep(1)
        dup_uid = await kv.get_fresh(f"user:idx:wx_openid:{wx_openid}")
        if not dup_uid and wx_unionid:
            dup_uid = await kv.get_fresh(f"user:idx:wx_unionid:{wx_unionid}")
        if dup_uid:
            user = await kv.get(f"user:{dup_uid}")
            if user:
                access_token = create_access_token(user["id"])
                refresh_token = create_refresh_token(user["id"])
                return _oauth_redirect(access_token, refresh_token, user, request)

    nickname = wx_user.get("nickname", f"微信用户{wx_openid[:6]}")
    avatar_url = wx_user.get("headimgurl") or None
    user_id = await kv.next_id("user")

    # Race check after next_id
    race_uid = await kv.get_fresh(f"user:idx:wx_openid:{wx_openid}")
    if not race_uid and wx_unionid:
        race_uid = await kv.get_fresh(f"user:idx:wx_unionid:{wx_unionid}")
    if race_uid:
        user = await kv.get(f"user:{race_uid}")
        if user:
            access_token = create_access_token(user["id"])
            refresh_token = create_refresh_token(user["id"])
            return _oauth_redirect(access_token, refresh_token, user, request)

    now = datetime.now(timezone.utc).isoformat()

    _wx_hash = hashlib.md5(wx_openid.encode()).hexdigest()[:6]
    username = f"wx_{_wx_hash}"
    if await kv.get(f"user:idx:username:{username}"):
        username = f"wx_{_wx_hash}_{user_id}"

    settings = await kv.get("site:settings") or {}
    register_bonus = settings.get("registerBonus", 100)

    user = {
        "id": user_id,
        "username": username,
        "nickname": nickname,
        "password_hash": "",
        "phone": None,
        "email": None,
        "avatar_url": avatar_url,
        "bio": None,
        "level": 1,
        "points_balance": register_bonus,
        "total_earned": 0,
        "role": "user",
        "status": "active",
        "wx_openid": wx_openid,
        "wx_unionid": wx_unionid,
        "qq_openid": None,
        "created_at": now,
        "updated_at": now,
    }

    await kv.put(f"user:{user_id}", user)
    await kv.put(f"user:idx:username:{username}", user_id)
    await kv.put(f"user:idx:wx_openid:{wx_openid}", user_id)
    if wx_unionid:
        await kv.put(f"user:idx:wx_unionid:{wx_unionid}", user_id)

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return _oauth_redirect(access_token, refresh_token, user, request)


# ─── 微信小程序登录 ───

WX_MINI_JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


async def _get_wx_mini_config(kv: KVStore):
    """获取微信小程序配置"""
    settings = await kv.get("site:settings") or {}
    app_id = settings.get("wxMiniAppId", "")
    app_secret = settings.get("wxMiniAppSecret", "")
    if not app_id or not app_secret:
        return None
    return {"app_id": app_id, "app_secret": app_secret}


@router.post("/wechat/miniprogram")
async def wechat_miniprogram_login(
    request: Request,
    kv: KVStore = Depends(get_kv),
):
    """Handle WeChat mini program login via wx.login() code."""
    body = await request.json()
    code = body.get("code", "")
    if not code:
        raise AppException(ErrorCode.PARAMS_ERROR, "缺少 code 参数")

    cfg = await _get_wx_mini_config(kv)
    if not cfg:
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信小程序登录未配置，请在管理后台填写小程序 AppID/AppSecret")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WX_MINI_JSCODE2SESSION_URL, params={
            "appid": cfg["app_id"],
            "secret": cfg["app_secret"],
            "js_code": code,
            "grant_type": "authorization_code",
        })
        data = resp.json()

    openid = data.get("openid")
    if not openid:
        raise AppException(ErrorCode.PERMISSION_DENIED, f"小程序登录失败: {data.get('errmsg', '未知错误')}")

    # Use unionid for cross-platform matching (same user across mini program, web, H5)
    # NOTE: unionid is only returned if the mini program is bound to the WeChat Open Platform
    unionid = data.get("unionid") or ""
    if not unionid:
        print(f"[WX Mini] WARNING: unionid is empty for openid={openid[:8]}... — "
              "please bind the mini program to the WeChat Open Platform for cross-platform account sync")

    existing_uid = None
    if unionid:
        existing_uid = await kv.get(f"user:idx:wx_unionid:{unionid}")
    if existing_uid is None:
        # Check mini program openid index
        existing_uid = await kv.get(f"user:idx:wx_mini_openid:{openid}")
    if existing_uid is None:
        existing_uid = await kv.get(f"user:idx:wx_openid:{openid}")
    if existing_uid:
        user = await kv.get(f"user:{existing_uid}")
        if user:
            if user.get("status") == "banned" or user.get("is_banned"):
                raise AppException(ErrorCode.PERMISSION_DENIED, "账号已被封禁", 403)
            # Backfill unionid/openid indexes if missing
            if unionid and not user.get("wx_unionid"):
                user["wx_unionid"] = unionid
                await kv.put(f"user:{user['id']}", user)
                await kv.put(f"user:idx:wx_unionid:{unionid}", user["id"])
            if not user.get("wx_mini_openid"):
                user["wx_mini_openid"] = openid
                await kv.put(f"user:{user['id']}", user)
                await kv.put(f"user:idx:wx_mini_openid:{openid}", user["id"])
            access_token = create_access_token(user["id"])
            return success_response({
                "access_token": access_token,
                "user": {
                    "id": user["id"],
                    "nickname": user.get("nickname", ""),
                    "avatar": user.get("avatar_url", ""),
                    "role": user.get("role", "user"),
                },
            })

    # Auto-register — with dedup lock (miniprogram)
    lock_ok = await kv.claim_register(f"wx_mini:{unionid or openid}")
    if not lock_ok:
        await asyncio.sleep(1)
        dup_uid = await kv.get_fresh(f"user:idx:wx_mini_openid:{openid}")
        if not dup_uid and unionid:
            dup_uid = await kv.get_fresh(f"user:idx:wx_unionid:{unionid}")
        if dup_uid:
            user = await kv.get(f"user:{dup_uid}")
            if user:
                access_token = create_access_token(user["id"])
                return success_response({
                    "access_token": access_token,
                    "user": {
                        "id": user["id"],
                        "nickname": user.get("nickname", ""),
                        "avatar": user.get("avatar_url", ""),
                        "role": user.get("role", "user"),
                    },
                })

    user_id = await kv.next_id("user")

    # Race check after next_id
    race_uid = await kv.get_fresh(f"user:idx:wx_mini_openid:{openid}")
    if not race_uid and unionid:
        race_uid = await kv.get_fresh(f"user:idx:wx_unionid:{unionid}")
    if race_uid:
        user = await kv.get(f"user:{race_uid}")
        if user:
            access_token = create_access_token(user["id"])
            return success_response({
                "access_token": access_token,
                "user": {
                    "id": user["id"],
                    "nickname": user.get("nickname", ""),
                    "avatar": user.get("avatar_url", ""),
                    "role": user.get("role", "user"),
                },
            })

    now = datetime.now(timezone.utc).isoformat()
    _wx_hash = hashlib.md5(openid.encode()).hexdigest()[:6]
    username = f"wx_{_wx_hash}"
    if await kv.get(f"user:idx:username:{username}"):
        username = f"wx_{_wx_hash}_{user_id}"

    settings = await kv.get("site:settings") or {}
    register_bonus = settings.get("registerBonus", 100)

    user = {
        "id": user_id,
        "username": username,
        "nickname": f"微信用户{_wx_hash}",
        "password_hash": "",
        "phone": None,
        "email": None,
        "avatar_url": None,
        "bio": None,
        "level": 1,
        "points_balance": register_bonus,
        "total_earned": 0,
        "role": "user",
        "status": "active",
        "wx_openid": openid,
        "wx_mini_openid": openid,
        "wx_unionid": unionid,
        "qq_openid": None,
        "created_at": now,
        "updated_at": now,
    }

    await kv.put(f"user:{user_id}", user)
    await kv.put(f"user:idx:username:{username}", user_id)
    await kv.put(f"user:idx:wx_mini_openid:{openid}", user_id)
    await kv.put(f"user:idx:wx_openid:{openid}", user_id)
    if unionid:
        await kv.put(f"user:idx:wx_unionid:{unionid}", user_id)

    access_token = create_access_token(user_id)
    return success_response({
        "access_token": access_token,
        "user": {
            "id": user_id,
            "nickname": user["nickname"],
            "avatar": "",
            "role": "user",
        },
    })