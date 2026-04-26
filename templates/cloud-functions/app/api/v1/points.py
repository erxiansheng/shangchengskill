import uuid
import json
import hashlib
import hmac
import urllib.request
import urllib.error
import urllib.parse
import base64
import time
from datetime import datetime, timezone
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, Query, Request, Body

from app.api.v1.deps import get_kv, get_current_user
from app.core.exceptions import success_response, paginated_response, AppException, ErrorCode
from app.schemas.points import RechargeRequest
from app.storage.kv import KVStore

router = APIRouter(prefix="/points", tags=["points"])

_DEFAULT_PACKAGES = [
    {"amount_yuan": 6, "points": 60},
    {"amount_yuan": 30, "points": 300},
    {"amount_yuan": 98, "points": 980},
    {"amount_yuan": 198, "points": 1980},
]

_DEFAULT_MIN_RECHARGE_YUAN = 1
_DEFAULT_POINTS_PER_YUAN = 10


@router.get("/config")
async def get_points_config(
    kv: KVStore = Depends(get_kv),
):
    """Public endpoint: returns feature flags, levels, recharge & withdraw config."""
    from app.core.levels import LEVELS, WITHDRAW_FEE_RATE, MIN_WITHDRAW_POINTS, EXP_PUBLISH_SKILL, EXP_PER_DOWNLOAD, EXP_PER_FAVORITE, EXP_PER_RECHARGE_YUAN
    settings = await kv.get("site:settings") or {}
    return success_response({
        "rechargeEnabled": bool(settings.get("rechargeEnabled", True)),
        "publishEnabled": bool(settings.get("publishEnabled", True)),
        "levels": settings.get("levelsConfig") or LEVELS,
        "expPublish": settings.get("expPublish", EXP_PUBLISH_SKILL),
        "expDownload": settings.get("expDownload", EXP_PER_DOWNLOAD),
        "expFavorite": settings.get("expFavorite", EXP_PER_FAVORITE),
        "expRechargeYuan": settings.get("expRechargeYuan", EXP_PER_RECHARGE_YUAN),
        "withdrawFeeRate": settings.get("withdrawFeeRate", WITHDRAW_FEE_RATE),
        "minWithdrawPoints": settings.get("minWithdrawPoints", MIN_WITHDRAW_POINTS),
        "minRechargeYuan": settings.get("minRechargeYuan", _DEFAULT_MIN_RECHARGE_YUAN),
        "pointsPerYuan": settings.get("pointsPerYuan", _DEFAULT_POINTS_PER_YUAN),
    })


@router.get("/balance")
async def get_balance(
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    # Calculate total spent from points records
    record_ids = await kv.get_list(f"pr:by_user:{user['id']}")
    records = await kv.batch_get([f"pr:{rid}" for rid in record_ids])
    total_spent = sum(abs(r["amount"]) for r in records if r and r["amount"] < 0)

    return success_response({
        "balance": user["points_balance"],
        "points_locked": user.get("points_locked", 0),
        "total_earned": user.get("total_earned", 0),
        "total_spent": total_spent,
    })


@router.get("/records")
async def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    type: str = Query("all"),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    record_ids = await kv.get_list(f"pr:by_user:{user['id']}")
    record_ids = list(reversed(record_ids))  # Newest first
    records = await kv.batch_get([f"pr:{rid}" for rid in record_ids])
    records = [r for r in records if r]

    if type and type != "all":
        records = [r for r in records if r.get("type") == type]

    total = len(records)
    start = (page - 1) * page_size
    page_items = records[start:start + page_size]

    items = [{
        "id": r["id"], "type": r["type"], "amount": r["amount"],
        "balance_after": r["balance_after"],
        "description": r.get("description"),
        "created_at": r.get("created_at"),
    } for r in page_items]

    return paginated_response(items, total, page, page_size)


@router.get("/packages")
async def get_packages(
    kv: KVStore = Depends(get_kv),
):
    settings = await kv.get("site:settings") or {}
    packages = settings.get("rechargePackages") or _DEFAULT_PACKAGES
    return success_response({"packages": packages})


@router.post("/recharge")
async def create_recharge(
    request: Request,
    data: RechargeRequest,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Create a recharge order. Returns a QR code URL for payment.
    Requires payment to be configured in admin settings."""
    site_cfg = await kv.get("site:settings") or {}
    min_recharge = site_cfg.get("minRechargeYuan", _DEFAULT_MIN_RECHARGE_YUAN)
    points_per_yuan = site_cfg.get("pointsPerYuan", _DEFAULT_POINTS_PER_YUAN)
    packages = site_cfg.get("rechargePackages") or _DEFAULT_PACKAGES

    if data.amount_yuan < min_recharge:
        raise AppException(ErrorCode.PARAMS_ERROR, f"最低充值金额为 {min_recharge} 元")

    # Find matching package or calculate by rate
    pkg = None
    for p in packages:
        if abs(p["amount_yuan"] - data.amount_yuan) < 0.01:
            pkg = p
            break
    if not pkg:
        pkg = {"amount_yuan": data.amount_yuan, "points": int(data.amount_yuan * points_per_yuan)}

    total_points = pkg["points"]
    now = datetime.now(timezone.utc)
    order_no = f"R{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"

    # Create recharge order
    order_id = await kv.next_id("recharge_order")
    order = {
        "id": order_id,
        "user_id": user["id"],
        "order_no": order_no,
        "amount_yuan": data.amount_yuan,
        "points_amount": total_points,
        "payment_method": data.payment_method,
        "status": "pending",
        "created_at": now.isoformat(),
        "paid_at": None,
    }

    # Check if real payment is configured
    site_settings = await kv.get("site:settings") or {}
    qr_url = None

    if data.payment_method == "alipay":
        if not site_settings.get("alipayEnabled"):
            raise AppException(ErrorCode.PERMISSION_DENIED, "支付宝支付未启用，请联系管理员在后台开启")
        pay_url = await _create_alipay_order(order_no, data.amount_yuan, site_settings, request)
        if not pay_url:
            raise AppException(ErrorCode.RECHARGE_FAILED, "支付宝下单失败，请检查后台支付宝配置是否正确")
        qr_url = pay_url  # pay_url is a redirect URL for page.pay
    elif data.payment_method == "wechat":
        if not site_settings.get("wechatEnabled"):
            raise AppException(ErrorCode.PERMISSION_DENIED, "微信支付未启用，请联系管理员在后台开启")
        origin = request.headers.get("x-internal-origin") or str(request.base_url).rstrip("/")

        # Mini-program uses JSAPI, web uses NATIVE (QR code)
        if data.client_type == "miniprogram":
            jsapi_params = await _create_wechat_jsapi_order(order_no, data.amount_yuan, site_settings, user, origin)
            if not jsapi_params:
                raise AppException(ErrorCode.RECHARGE_FAILED, "微信JSAPI下单失败，请检查小程序AppID和微信支付配置")

            order["qr_url"] = ""  # JSAPI has no QR url
            await kv.put(f"recharge_order:{order_id}", order)
            await kv.put(f"recharge_order:idx:order_no:{order_no}", order_id)

            return success_response({
                "order_no": order_no,
                "order_id": order_id,
                "payment_method": "wechat",
                "pay_type": "jsapi",
                "jsapi_params": jsapi_params,
                "amount_yuan": data.amount_yuan,
                "points_amount": total_points,
                "status": "pending",
            })
        else:
            qr_url = await _create_wechat_order(order_no, data.amount_yuan, site_settings, origin)
            if not qr_url:
                raise AppException(ErrorCode.RECHARGE_FAILED, "微信下单失败，请检查后台微信支付配置是否正确")
    else:
        raise AppException(ErrorCode.PARAMS_ERROR, "不支持的支付方式")

    # Real payment flow: save pending order, return QR url
    order["qr_url"] = qr_url
    await kv.put(f"recharge_order:{order_id}", order)
    await kv.put(f"recharge_order:idx:order_no:{order_no}", order_id)

    return success_response({
        "order_no": order_no,
        "order_id": order_id,
        "qr_url": qr_url,
        "payment_method": data.payment_method,
        "amount_yuan": data.amount_yuan,
        "points_amount": total_points,
        "status": "pending",
    })


@router.get("/recharge/{order_no}/status")
async def check_recharge_status(
    order_no: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Poll the payment status of a recharge order."""
    order_id = await kv.get(f"recharge_order:idx:order_no:{order_no}")
    if order_id is None:
        raise AppException(ErrorCode.NOT_FOUND, "订单不存在", 404)

    order = await kv.get(f"recharge_order:{order_id}")
    if not order or order["user_id"] != user["id"]:
        raise AppException(ErrorCode.NOT_FOUND, "订单不存在", 404)

    return success_response({
        "order_no": order_no,
        "status": order.get("status", "pending"),
        "points_amount": order.get("points_amount", 0),
    })


@router.post("/recharge/callback/{method}")
async def payment_callback(
    method: str,
    request: Request,
    kv: KVStore = Depends(get_kv),
):
    """Handle payment callbacks from Alipay or WeChat Pay."""
    site_settings = await kv.get("site:settings") or {}

    order_no = None
    verified = False

    if method == "alipay":
        # Alipay callback: form-encoded body
        body = await request.body()
        params = dict(urllib.parse.parse_qsl(body.decode("utf-8")))
        order_no = params.get("out_trade_no")
        trade_status = params.get("trade_status")
        if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            return {"status": "ignored"}
        # Verify signature
        alipay_public_key = site_settings.get("alipayPublicKey", "")
        if alipay_public_key:
            verified = _verify_alipay_sign(params, alipay_public_key)
        else:
            verified = True  # No key configured, accept

    elif method == "wechat":
        # WeChat callback: XML body
        body = await request.body()
        print(f"[WeChatPay Callback] Received body length={len(body)}")
        xml = _parse_wechat_xml(body.decode("utf-8"))
        order_no = xml.get("out_trade_no")
        result_code = xml.get("result_code")
        print(f"[WeChatPay Callback] order_no={order_no}, result_code={result_code}")
        if result_code != "SUCCESS":
            print(f"[WeChatPay Callback] result_code not SUCCESS, xml={xml}")
            return _wechat_xml_response("FAIL", "result_code not SUCCESS")
        api_key = site_settings.get("wechatApiKey", "")
        if api_key:
            verified = _verify_wechat_sign(xml, api_key)
            if not verified:
                print(f"[WeChatPay Callback] Signature verification FAILED for order_no={order_no}")
        else:
            verified = True
            print(f"[WeChatPay Callback] No API key configured, skipping signature verification")

    if not order_no or not verified:
        if method == "wechat":
            print(f"[Payment Callback] REJECTED: order_no={order_no}, verified={verified}")
            return _wechat_xml_response("FAIL", "验签失败")
        return {"status": "error", "message": "验签失败"}

    # Process the payment
    order_id = await kv.get(f"recharge_order:idx:order_no:{order_no}")
    if order_id is None:
        print(f"[Payment Callback] Order not found in KV: order_no={order_no}")
        if method == "wechat":
            return _wechat_xml_response("SUCCESS", "OK")
        return {"status": "ok"}

    order = await kv.get(f"recharge_order:{order_id}")
    if not order or order["status"] == "paid":
        print(f"[Payment Callback] Order already paid or missing: order_id={order_id}")
        if method == "wechat":
            return _wechat_xml_response("SUCCESS", "OK")
        return {"status": "ok"}

    # 幂等性检查（持久化）：若该订单已生成过积分流水，则说明已经到账，直接返回成功。
    # 防止支付平台多次回调（如微信/支付宝重试）导致重复加积分。
    existing_pr_id = await kv.get(f"pr:idx:recharge_order:{order_id}")
    if existing_pr_id is not None:
        print(f"[Payment Callback] DUPLICATE callback ignored: order_id={order_id}, existing_pr_id={existing_pr_id}")
        # 顺手补齐订单状态，避免 status 没被前一次 callback 写成功
        if order.get("status") != "paid":
            order["status"] = "paid"
            order["paid_at"] = order.get("paid_at") or datetime.now(timezone.utc).isoformat()
            await kv.put(f"recharge_order:{order_id}", order)
        if method == "wechat":
            return _wechat_xml_response("SUCCESS", "OK")
        return {"status": "ok"}

    # 边缘内存短锁：在并发回调到达时尽量阻止两边同时通过持久化检查
    try:
        claimed = await kv.claim_register(f"recharge_callback:{order_id}")
    except Exception:
        claimed = True  # 保底放行
    if not claimed:
        print(f"[Payment Callback] Concurrent callback locked, skip: order_id={order_id}")
        if method == "wechat":
            return _wechat_xml_response("SUCCESS", "OK")
        return {"status": "ok"}

    # Mark as paid and credit points
    now = datetime.now(timezone.utc).isoformat()
    order["status"] = "paid"
    order["paid_at"] = now
    await kv.put(f"recharge_order:{order_id}", order)
    print(f"[Payment Callback] Order marked as paid: order_no={order_no}, order_id={order_id}")

    user = await kv.get(f"user:{order['user_id']}")
    if user:
        total_points = order["points_amount"]
        user["points_balance"] = user.get("points_balance", 0) + total_points
        # Award XP for recharge
        from app.core.levels import EXP_PER_RECHARGE_YUAN
        exp_recharge = site_settings.get("expRechargeYuan", EXP_PER_RECHARGE_YUAN)
        user["exp"] = user.get("exp", 0) + int(order["amount_yuan"] * exp_recharge)
        await kv.put(f"user:{user['id']}", user)

        record_id = await kv.next_id("pr")
        record = {
            "id": record_id,
            "user_id": user["id"],
            "type": "recharge",
            "amount": total_points,
            "balance_after": user["points_balance"],
            "description": f"充值 ¥{order['amount_yuan']}",
            "related_id": order_id,
            "created_at": now,
        }
        await kv.put(f"pr:{record_id}", record)
        await kv.add_to_list(f"pr:by_user:{user['id']}", record_id)
        # 写入持久化幂等索引（必须在加积分之后，确保不会出现"标记已到账但积分没加"的状态）
        await kv.put(f"pr:idx:recharge_order:{order_id}", record_id)

        # 发送充值到账通知邮件
        from app.api.v1.admin import send_notify_email
        await send_notify_email(kv,
            f"💰 用户充值到账 ¥{order['amount_yuan']}",
            f"用户: {user.get('nickname', '')} (ID: {user['id']})\n充值金额: ¥{order['amount_yuan']}\n积分: +{total_points}\n支付方式: {method}\n时间: {now}")

    if method == "wechat":
        return _wechat_xml_response("SUCCESS", "OK")
    return {"status": "ok"}


# ========== Withdrawal ==========

from app.core.levels import WITHDRAW_FEE_RATE, MIN_WITHDRAW_POINTS, calc_withdraw_yuan


@router.get("/withdraw/calc")
async def calc_withdraw(
    amount: int = Query(..., ge=100),
    kv: KVStore = Depends(get_kv),
):
    """Calculate withdrawal: fee, actual yuan received."""
    settings = await kv.get("site:settings") or {}
    fee_rate = settings.get("withdrawFeeRate", WITHDRAW_FEE_RATE)
    gross_yuan = amount / 10
    fee_yuan = round(gross_yuan * fee_rate, 2)
    actual_yuan = round(gross_yuan - fee_yuan, 2)
    return success_response({
        "points": amount,
        "gross_yuan": gross_yuan,
        "fee_rate": fee_rate,
        "fee_yuan": fee_yuan,
        "actual_yuan": actual_yuan,
    })


@router.post("/withdraw")
async def request_withdrawal(
    amount: int = Body(..., ge=100),
    alipay_account: str = Body(..., min_length=1),
    alipay_name: str = Body(..., min_length=1),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Submit a withdrawal request. Points are locked immediately."""
    settings = await kv.get("site:settings") or {}
    fee_rate = settings.get("withdrawFeeRate", WITHDRAW_FEE_RATE)
    min_wd = settings.get("minWithdrawPoints", MIN_WITHDRAW_POINTS)
    if amount < min_wd:
        raise AppException(ErrorCode.PARAMS_ERROR, f"最低提现积分为 {min_wd}")

    available = user.get("points_balance", 0) - user.get("points_locked", 0)
    if available < amount:
        raise AppException(ErrorCode.PERMISSION_DENIED, "可用积分余额不足（已扣除锁定中的积分）")

    # Check for existing pending withdrawal
    wd_ids = await kv.get_list(f"wd:by_user:{user['id']}")
    if wd_ids:
        wds = await kv.batch_get([f"wd:{wid}" for wid in wd_ids])
        for wd in wds:
            if wd and wd.get("status") == "pending":
                raise AppException(ErrorCode.PERMISSION_DENIED, "您有提现申请正在处理中，请等待处理完成")

    # Calculate fee
    gross_yuan = amount / 10
    fee_yuan = round(gross_yuan * fee_rate, 2)
    actual_yuan = round(gross_yuan - fee_yuan, 2)

    now = datetime.now(timezone.utc).isoformat()
    wd_id = await kv.next_id("wd")
    withdrawal = {
        "id": wd_id,
        "user_id": user["id"],
        "amount": amount,
        "fee_yuan": fee_yuan,
        "actual_yuan": actual_yuan,
        "alipay_account": alipay_account,
        "alipay_name": alipay_name,
        "status": "pending",
        "created_at": now,
    }
    await kv.put(f"wd:{wd_id}", withdrawal)
    await kv.add_to_list(f"wd:by_user:{user['id']}", wd_id)
    await kv.add_to_list("wd:pending", wd_id)

    # Lock points
    user["points_locked"] = user.get("points_locked", 0) + amount
    await kv.put(f"user:{user['id']}", user)

    # 发送提现申请通知邮件
    from app.api.v1.admin import send_notify_email
    await send_notify_email(kv,
        f"📤 新提现申请 - {amount} 积分",
        f"用户: {user.get('nickname', '')} (ID: {user['id']})\n提现积分: {amount}\n手续费: ¥{fee_yuan}\n实际到账: ¥{actual_yuan}\n支付宝账号: {alipay_account}\n真实姓名: {alipay_name}\n时间: {now}\n\n请登录管理后台处理。")

    return success_response({"id": wd_id, "status": "pending", "fee_yuan": fee_yuan, "actual_yuan": actual_yuan})


@router.get("/withdrawals")
async def my_withdrawals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Get user's withdrawal history."""
    wd_ids = await kv.get_list(f"wd:by_user:{user['id']}")
    wd_ids = list(reversed(wd_ids))
    wds = await kv.batch_get([f"wd:{wid}" for wid in wd_ids])
    wds = [w for w in wds if w]

    total = len(wds)
    start = (page - 1) * page_size
    page_items = wds[start:start + page_size]

    items = [{
        "id": w["id"],
        "amount": w["amount"],
        "fee_yuan": w.get("fee_yuan"),
        "actual_yuan": w.get("actual_yuan"),
        "alipay_account": w["alipay_account"],
        "alipay_name": w["alipay_name"],
        "status": w["status"],
        "reject_reason": w.get("reject_reason"),
        "created_at": w.get("created_at"),
        "completed_at": w.get("completed_at"),
    } for w in page_items]

    return paginated_response(items, total, page, page_size)


# ========== Payment Helpers ==========

async def _create_alipay_order(order_no: str, amount: float, settings: dict, request: Request = None) -> str | None:
    """Create an Alipay page pay order (电脑网站支付). Returns a payment redirect URL or None."""
    app_id = settings.get("alipayAppId", "")
    private_key = settings.get("alipayPrivateKey", "")
    sandbox = settings.get("alipaySandbox", False)

    if not app_id or not private_key:
        return None

    gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do" if sandbox else "https://openapi.alipay.com/gateway.do"

    # Determine return_url (sync redirect after payment) and notify_url (async callback)
    origin = ""
    if request:
        from app.api.v1.auth import _resolve_origin
        origin = _resolve_origin(request)

    # 支付宝要求回调域名与配置一致，强制使用 www 前缀
    if origin and "://YOUR_DOMAIN_HERE" in origin:
        origin = origin.replace("://YOUR_DOMAIN_HERE", "://YOUR_DOMAIN_HERE")

    biz_content = json.dumps({
        "out_trade_no": order_no,
        "total_amount": f"{amount:.2f}",
        "subject": f"EdgeOneMall 积分充值 ¥{amount}",
        "product_code": "FAST_INSTANT_TRADE_PAY",
    }, ensure_ascii=False)

    params = {
        "app_id": app_id,
        "method": "alipay.trade.page.pay",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": biz_content,
    }

    if origin:
        params["return_url"] = f"{origin}/points?pay_result=success"
        params["notify_url"] = f"{origin}/api/v1/points/recharge/callback/alipay"

    try:
        sign = _rsa2_sign(params, private_key)
        params["sign"] = sign

        # For page.pay, we construct the full redirect URL (browser opens it)
        pay_url = f"{gateway}?{urllib.parse.urlencode(params)}"
        return pay_url
    except Exception as e:
        print(f"[Alipay] Failed to create page pay URL: {e}")
        return None


async def _create_wechat_order(order_no: str, amount: float, settings: dict, origin: str = "") -> str | None:
    """Create a WeChat Pay native (QR code) order. Returns QR code URL or None."""
    app_id = settings.get("wechatAppId", "")
    mch_id = settings.get("wechatMchId", "")
    api_key = settings.get("wechatApiKey", "")

    if not app_id or not mch_id or not api_key:
        return None

    nonce = uuid.uuid4().hex[:32]
    total_fee = int(amount * 100)  # Convert to cents

    notify_url = f"{origin}/api/v1/points/recharge/callback/wechat" if origin else "https://YOUR_DOMAIN_HERE/api/v1/points/recharge/callback/wechat"

    params = {
        "appid": app_id,
        "mch_id": mch_id,
        "nonce_str": nonce,
        "body": f"SkillHub积分充值",
        "out_trade_no": order_no,
        "total_fee": str(total_fee),
        "spbill_create_ip": "127.0.0.1",
        "notify_url": notify_url,
        "trade_type": "NATIVE",
    }

    # Sign
    sign = _wechat_sign(params, api_key)
    params["sign"] = sign

    # Build XML
    xml_parts = ["<xml>"]
    for k, v in params.items():
        xml_parts.append(f"<{k}>{v}</{k}>")
    xml_parts.append("</xml>")
    xml_body = "".join(xml_parts).encode("utf-8")

    try:
        req = urllib.request.Request(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            data=xml_body,
            headers={"Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result_xml = resp.read().decode("utf-8")

        parsed = _parse_wechat_xml(result_xml)
        if parsed.get("return_code") == "SUCCESS" and parsed.get("result_code") == "SUCCESS":
            return parsed.get("code_url")
        else:
            print(f"[WeChatPay] Error: {parsed}")
            return None
    except Exception as e:
        print(f"[WeChatPay] Failed to create order: {e}")
        return None


async def _create_wechat_jsapi_order(order_no: str, amount: float, settings: dict, user: dict, origin: str = "") -> dict | None:
    """Create a WeChat Pay JSAPI order for mini-program. Returns payment params for wx.requestPayment."""
    mini_app_id = settings.get("wxMiniAppId", "")
    mch_id = settings.get("wechatMchId", "")
    api_key = settings.get("wechatApiKey", "")

    if not mini_app_id or not mch_id or not api_key:
        print("[WeChatPay JSAPI] Missing wxMiniAppId, wechatMchId or wechatApiKey")
        return None

    openid = user.get("wx_mini_openid", "")
    if not openid:
        print(f"[WeChatPay JSAPI] User {user.get('id')} has no wx_mini_openid")
        return None

    nonce = uuid.uuid4().hex[:32]
    total_fee = int(amount * 100)

    notify_url = f"{origin}/api/v1/points/recharge/callback/wechat" if origin else "https://YOUR_DOMAIN_HERE/api/v1/points/recharge/callback/wechat"

    params = {
        "appid": mini_app_id,
        "mch_id": mch_id,
        "nonce_str": nonce,
        "body": "SkillHub积分充值",
        "out_trade_no": order_no,
        "total_fee": str(total_fee),
        "spbill_create_ip": "127.0.0.1",
        "notify_url": notify_url,
        "trade_type": "JSAPI",
        "openid": openid,
    }

    sign = _wechat_sign(params, api_key)
    params["sign"] = sign

    xml_parts = ["<xml>"]
    for k, v in params.items():
        xml_parts.append(f"<{k}>{v}</{k}>")
    xml_parts.append("</xml>")
    xml_body = "".join(xml_parts).encode("utf-8")

    try:
        req = urllib.request.Request(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            data=xml_body,
            headers={"Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result_xml = resp.read().decode("utf-8")

        parsed = _parse_wechat_xml(result_xml)
        if parsed.get("return_code") == "SUCCESS" and parsed.get("result_code") == "SUCCESS":
            prepay_id = parsed.get("prepay_id")
            if not prepay_id:
                print("[WeChatPay JSAPI] No prepay_id in response")
                return None

            # Build params for wx.requestPayment
            timestamp = str(int(time.time()))
            nonce_str = uuid.uuid4().hex[:32]
            package = f"prepay_id={prepay_id}"

            pay_sign_params = {
                "appId": mini_app_id,
                "timeStamp": timestamp,
                "nonceStr": nonce_str,
                "package": package,
                "signType": "MD5",
            }
            pay_sign = _wechat_sign(pay_sign_params, api_key)

            return {
                "timeStamp": timestamp,
                "nonceStr": nonce_str,
                "package": package,
                "signType": "MD5",
                "paySign": pay_sign,
            }
        else:
            print(f"[WeChatPay JSAPI] Error: {parsed}")
            return None
    except Exception as e:
        print(f"[WeChatPay JSAPI] Failed to create order: {e}")
        return None


def _rsa2_sign(params: dict, private_key_str: str) -> str:
    """Sign params with RSA2 (SHA256withRSA) for Alipay."""
    try:
        from Crypto.Signature import pkcs1_15
        from Crypto.PublicKey import RSA
        from Crypto.Hash import SHA256
    except ImportError:
        try:
            from Cryptodome.Signature import pkcs1_15
            from Cryptodome.PublicKey import RSA
            from Cryptodome.Hash import SHA256
        except ImportError:
            print("[Alipay] pycryptodome not installed, signing unavailable")
            return ""

    # Sort and concatenate params
    sorted_keys = sorted(params.keys())
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys if params[k])

    # Normalize private key PEM
    key_str = private_key_str.strip()
    if "BEGIN" not in key_str:
        key_str = f"-----BEGIN RSA PRIVATE KEY-----\n{key_str}\n-----END RSA PRIVATE KEY-----"

    key = RSA.import_key(key_str)
    h = SHA256.new(sign_str.encode("utf-8"))
    signature = pkcs1_15.new(key).sign(h)
    return base64.b64encode(signature).decode("utf-8")


def _verify_alipay_sign(params: dict, public_key_str: str) -> bool:
    """Verify Alipay callback signature."""
    try:
        from Crypto.Signature import pkcs1_15
        from Crypto.PublicKey import RSA
        from Crypto.Hash import SHA256

        sign = params.pop("sign", "")
        params.pop("sign_type", None)

        sorted_keys = sorted(params.keys())
        sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys if params[k])

        key_str = public_key_str.strip()
        if "BEGIN" not in key_str:
            key_str = f"-----BEGIN PUBLIC KEY-----\n{key_str}\n-----END PUBLIC KEY-----"

        key = RSA.import_key(key_str)
        h = SHA256.new(sign_str.encode("utf-8"))
        pkcs1_15.new(key).verify(h, base64.b64decode(sign))
        return True
    except Exception as e:
        print(f"[Alipay] Signature verify failed: {e}")
        return False


def _wechat_sign(params: dict, api_key: str) -> str:
    """Generate WeChat Pay MD5 signature."""
    sorted_keys = sorted(params.keys())
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys if params[k] is not None and params[k] != "")
    sign_str += f"&key={api_key}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


def _verify_wechat_sign(params: dict, api_key: str) -> bool:
    """Verify WeChat Pay callback signature."""
    sign = params.pop("sign", "")
    expected = _wechat_sign(params, api_key)
    return hmac.compare_digest(sign, expected)


def _parse_wechat_xml(xml_str: str) -> dict:
    """Parse WeChat Pay XML response to dict."""
    result = {}
    try:
        root = ElementTree.fromstring(xml_str)
        for child in root:
            result[child.tag] = (child.text or "").strip()
    except Exception:
        pass
    return result


def _wechat_xml_response(return_code: str, return_msg: str) -> str:
    """Build WeChat Pay XML callback response."""
    from fastapi.responses import Response
    xml = f"<xml><return_code><![CDATA[{return_code}]]></return_code><return_msg><![CDATA[{return_msg}]]></return_msg></xml>"
    return Response(content=xml, media_type="application/xml")
