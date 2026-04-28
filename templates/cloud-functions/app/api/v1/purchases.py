import uuid
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import Response

from app.api.v1.deps import get_kv, get_current_user, get_s3
from app.core.exceptions import success_response, AppException, ErrorCode, paginated_response
from app.core.levels import EXP_PER_DOWNLOAD
from app.storage.kv import KVStore
from app.storage.s3 import S3Storage

router = APIRouter(prefix="/purchases", tags=["purchases"])


async def settle_cash_order(kv: KVStore, order_no: str, payment_method: str = ""):
    """Mark a cash product order as paid and create the matching purchase record."""
    order = await kv.get(f"order:cash:{order_no}")
    if not order:
        return None

    now = datetime.now(timezone.utc).isoformat()
    existing_purchase_id = await kv.get(f"purchase:idx:cash_order:{order_no}")
    if existing_purchase_id is not None:
        order["status"] = "paid"
        order["paid_at"] = order.get("paid_at") or now
        order["purchase_id"] = existing_purchase_id
        await kv.put(f"order:cash:{order_no}", order)
        return order

    try:
        claimed = await kv.claim_register(f"cash_order_callback:{order_no}")
    except Exception:
        claimed = True
    if not claimed:
        return order

    skill = await kv.get(f"skill:{order['skill_id']}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "商品不存在", 404)

    quantity = max(1, int(order.get("quantity") or 1))
    stock = skill.get("stock")
    if stock is not None:
        if int(stock) < quantity:
            raise AppException(ErrorCode.PARAMS_ERROR, "库存不足")
        skill["stock"] = max(0, int(stock) - quantity)

    purchase_id = await kv.next_id("purchase")
    is_physical = bool(order.get("is_physical")) or (skill.get("product_type") == "physical")
    fulfillment_status = "pending_shipment" if is_physical else "completed"
    purchase = {
        "id": purchase_id,
        "user_id": order["user_id"],
        "skill_id": order["skill_id"],
        "price_paid": 0,
        "cash_paid_yuan": float(order.get("total_yuan") or 0),
        "unit_price_yuan": float(order.get("unit_price_yuan") or 0),
        "shipping_fee_yuan": float(order.get("shipping_fee_yuan") or 0),
        "quantity": quantity,
        "payment_type": "cash",
        "payment_method": payment_method or order.get("payment_method"),
        "shipping_info": order.get("shipping_info"),
        "is_physical": is_physical,
        "fulfillment_status": fulfillment_status,
        "order_no": order_no,
        "status": "completed",
        "created_at": now,
        "paid_at": now,
    }
    await kv.put(f"purchase:{purchase_id}", purchase)
    await kv.put(f"purchase:idx:user_skill:{order['user_id']}:{order['skill_id']}", purchase_id)
    await kv.put(f"purchase:idx:cash_order:{order_no}", purchase_id)
    await kv.add_to_list(f"purchase:by_user:{order['user_id']}", purchase_id)

    skill["purchase_count"] = skill.get("purchase_count", 0) + quantity
    await kv.put(f"skill:{order['skill_id']}", skill)

    order["status"] = "paid"
    order["paid_at"] = now
    order["purchase_id"] = purchase_id
    order["fulfillment_status"] = fulfillment_status
    await kv.put(f"order:cash:{order_no}", order)

    if skill.get("user_id"):
        msg_id = await kv.next_id("msg")
        await kv.put(f"msg:{msg_id}", {
            "id": msg_id,
            "user_id": skill["user_id"],
            "type": "order",
            "title": f"商品 {skill.get('title', '')} 有新订单",
            "content": "实体商品订单请在后台订单管理中查看收货信息并安排发货" if is_physical else "现金商品订单已支付",
            "is_read": False,
            "related_type": "purchase",
            "related_id": purchase_id,
            "created_at": now,
        })
        await kv.add_to_list(f"msg:by_user:{skill['user_id']}", msg_id)
        await kv.add_to_list(f"msg:unread:{skill['user_id']}", msg_id)

    return order


@router.post("")
async def purchase_skill(
    skill_id: str = Body(..., embed=True),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    # Check skill
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
    if skill["status"] != "approved":
        raise AppException(ErrorCode.SKILL_REVIEWING, "技能暂不可用")
    if skill["user_id"] == user["id"]:
        raise AppException(ErrorCode.PARAMS_ERROR, "不能购买自己的技能")

    sale_mode = skill.get("sale_mode") or "points"
    if skill.get("product_type") == "physical":
        raise AppException(ErrorCode.PARAMS_ERROR, "实体商品请使用现金支付并填写收货地址")
    if sale_mode == "cash":
        raise AppException(ErrorCode.PARAMS_ERROR, "该商品仅支持现金支付")

    # Check already purchased
    existing = await kv.get(f"purchase:idx:user_skill:{user['id']}:{skill_id}")
    if existing is not None:
        raise AppException(ErrorCode.ALREADY_PURCHASED, "已购买过该技能")

    price = skill["price"]
    now = datetime.now(timezone.utc)

    if not skill.get("is_free") and price > 0:
        # 强一致读取买家最新余额，避免使用 token 中缓存的旧 user dict
        # 否则在并发场景下两笔扣费会基于同一余额写回，造成扣款不准 / 卖家少收
        fresh_buyer = await kv.get_fresh(f"user:{user['id']}") or user
        if fresh_buyer.get("points_balance", 0) < price:
            raise AppException(ErrorCode.POINTS_NOT_ENOUGH, "积分不足")

        # Deduct buyer points
        fresh_buyer["points_balance"] = fresh_buyer.get("points_balance", 0) - price
        await kv.put(f"user:{user['id']}", fresh_buyer)
        user = fresh_buyer  # 同步给后续 success_response 使用

        # Buyer points record
        buyer_record_id = await kv.next_id("pr")
        await kv.put(f"pr:{buyer_record_id}", {
            "id": buyer_record_id,
            "user_id": user["id"], "type": "purchase", "amount": -price,
            "balance_after": user["points_balance"],
            "description": f"购买技能: {skill['title']}",
            "related_id": skill_id,
            "created_at": now.isoformat(),
        })
        await kv.add_to_list(f"pr:by_user:{user['id']}", buyer_record_id)

        # Author earnings
        site_settings = await kv.get("site:settings") or {}
        fee_pct = site_settings.get("feeRate", 30)  # percent, e.g. 30
        fee_rate = fee_pct / 100.0
        author_earn = int(price * (1 - fee_rate))
        # 同样使用强一致读取卖家信息，避免并发下卖家积分被覆盖丢失
        author = await kv.get_fresh(f"user:{skill['user_id']}")
        if not author:
            # 卖家账号缺失：回滚买家扣费，避免出现"扣了钱但卖家没收到"的情况
            print(f"[Purchase] CRITICAL: author user not found, rolling back. skill_id={skill_id}, author_uid={skill['user_id']}")
            fresh_buyer["points_balance"] = fresh_buyer.get("points_balance", 0) + price
            await kv.put(f"user:{user['id']}", fresh_buyer)
            raise AppException(ErrorCode.SYSTEM_ERROR, "卖家账号异常，请稍后重试或联系客服", 500)

        author["points_balance"] = author.get("points_balance", 0) + author_earn
        author["total_earned"] = author.get("total_earned", 0) + author_earn
        await kv.put(f"user:{author['id']}", author)

        # Author points record
        author_record_id = await kv.next_id("pr")
        await kv.put(f"pr:{author_record_id}", {
            "id": author_record_id,
            "user_id": author["id"], "type": "earn", "amount": author_earn,
            "balance_after": author["points_balance"],
            "description": f"技能 {skill['title']} 被购买",
            "related_id": skill_id,
            "created_at": now.isoformat(),
        })
        await kv.add_to_list(f"pr:by_user:{author['id']}", author_record_id)

        # Notify author
        msg_id = await kv.next_id("msg")
        await kv.put(f"msg:{msg_id}", {
            "id": msg_id,
            "user_id": author["id"], "type": "earning",
            "title": f"技能 {skill['title']} 被购买",
            "content": f"用户购买了您的技能，您获得 {author_earn} 积分。",
            "is_read": False,
            "related_type": "skill", "related_id": skill_id,
            "created_at": now.isoformat(),
        })
        await kv.add_to_list(f"msg:by_user:{author['id']}", msg_id)
        await kv.add_to_list(f"msg:unread:{author['id']}", msg_id)

    # Create purchase
    order_no = f"P{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
    purchase_id = await kv.next_id("purchase")
    purchase = {
        "id": purchase_id,
        "user_id": user["id"],
        "skill_id": skill_id,
        "price_paid": price,
        "order_no": order_no,
        "status": "completed",
        "created_at": now.isoformat(),
    }
    await kv.put(f"purchase:{purchase_id}", purchase)
    await kv.put(f"purchase:idx:user_skill:{user['id']}:{skill_id}", purchase_id)
    await kv.add_to_list(f"purchase:by_user:{user['id']}", purchase_id)

    # Update skill purchase count
    skill["purchase_count"] = skill.get("purchase_count", 0) + 1
    await kv.put(f"skill:{skill_id}", skill)

    return success_response({
        "order_no": order_no,
        "price_paid": price,
        "points_balance": user["points_balance"],
    })


@router.get("")
async def list_purchases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    purchase_ids = await kv.get_list(f"purchase:by_user:{user['id']}")
    purchase_ids = list(reversed(purchase_ids))  # Newest first
    total = len(purchase_ids)

    start = (page - 1) * page_size
    page_ids = purchase_ids[start:start + page_size]
    purchases = await kv.batch_get([f"purchase:{pid}" for pid in page_ids])

    # Get associated skills
    skill_ids = [p["skill_id"] for p in purchases if p]
    skills = await kv.batch_get([f"skill:{sid}" for sid in skill_ids])
    skill_map = {s["id"]: s for s in skills if s}

    items = []
    for p in purchases:
        if not p:
            continue
        s = skill_map.get(p["skill_id"], {})
        items.append({
            "id": p["id"],
            "skill_id": p["skill_id"],
            "title": s.get("title", ""),
            "cover_image": s.get("cover_image"),
            "version": s.get("version", "1.0.0"),
            "price_paid": p["price_paid"],
            "payment_type": p.get("payment_type", "points"),
            "cash_paid_yuan": p.get("cash_paid_yuan"),
            "shipping_fee_yuan": p.get("shipping_fee_yuan", 0),
            "shipping_info": p.get("shipping_info"),
            "is_physical": bool(p.get("is_physical")) or s.get("product_type") == "physical",
            "product_type": s.get("product_type", "digital"),
            "fulfillment_status": p.get("fulfillment_status"),
            "category_name": s.get("category_name"),
            "order_no": p["order_no"],
            "tags": s.get("tags") or [],
            "purchase_time": p.get("created_at"),
        })

    return paginated_response(items, total, page, page_size)


@router.get("/{skill_id}/check")
async def check_purchase(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    purchase_id = await kv.get(f"purchase:idx:user_skill:{user['id']}:{skill_id}")
    if purchase_id is not None:
        purchase = await kv.get(f"purchase:{purchase_id}")
        return success_response({
            "purchased": True,
            "purchase_time": purchase.get("created_at") if purchase else None,
        })
    return success_response({"purchased": False, "purchase_time": None})


@router.get("/{skill_id}/download")
async def download_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
    s3: S3Storage = Depends(get_s3),
):
    # Check purchase or ownership
    purchase_id = await kv.get(f"purchase:idx:user_skill:{user['id']}:{skill_id}")
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
    if purchase_id is None and skill["user_id"] != user["id"] and not skill.get("is_free"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "请先购买该技能", 403)

    # Ensure S3 config is loaded from KV settings
    site_settings = await kv.get("site:settings") or {}
    s3.update_config(site_settings)

    # Generate download URL
    file_url = skill.get("file_url", "")
    if not file_url:
        raise AppException(ErrorCode.PARAMS_ERROR, "该技能没有可下载的文件", 404)

    try:
        if not file_url.startswith("/") and not file_url.startswith("http"):
            # It's an S3 key — use public accelerated URL directly
            public_url = s3.get_public_download_url(file_url)
            if public_url:
                download_url = public_url
            else:
                # Fallback to presigned URL
                download_url = s3.get_presigned_url(file_url)
        else:
            download_url = file_url
    except Exception as e:
        print(f"[Download] Failed to generate download URL, skill_id={skill_id}, key={file_url}, error={e}")
        raise AppException(
            ErrorCode.STORAGE_ERROR,
            f"下载链接生成失败：存储服务暂时不可用，请稍后重试。错误详情：{type(e).__name__}: {e}",
            500,
        )

    # Increment download count
    skill["download_count"] = skill.get("download_count", 0) + 1
    await kv.put(f"skill:{skill_id}", skill)
    # 更新作者统计缓存
    if skill.get("user_id"):
        from app.api.v1.users import update_user_stats
        await update_user_stats(kv, skill["user_id"], downloads_delta=1)

    # Award XP to skill author
    if skill.get("user_id"):
        settings = await kv.get("site:settings") or {}
        exp_dl = settings.get("expDownload", EXP_PER_DOWNLOAD)
        from app.api.v1.users import add_exp
        await add_exp(kv, skill["user_id"], exp_dl)

    return success_response({
        "download_url": download_url,
        "file_size": skill.get("file_size"),
        "filename": skill.get("original_filename") or "skill.zip",
    })


@router.get("/{skill_id}/download/file")
async def download_skill_file(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
    s3: S3Storage = Depends(get_s3),
):
    """Stream the skill file directly — for API/AI clients."""
    try:
        # Check purchase or ownership
        purchase_id = await kv.get(f"purchase:idx:user_skill:{user['id']}:{skill_id}")
        skill = await kv.get(f"skill:{skill_id}")
        if not skill:
            raise AppException(ErrorCode.SKILL_NOT_FOUND, "技能不存在", 404)
        if purchase_id is None and skill["user_id"] != user["id"] and not skill.get("is_free"):
            raise AppException(ErrorCode.PERMISSION_DENIED, "请先购买该技能", 403)

        file_url = skill.get("file_url", "")
        if not file_url:
            raise AppException(ErrorCode.PARAMS_ERROR, "该技能没有可下载的文件", 404)

        # Ensure S3 config is loaded from KV settings
        site_settings = await kv.get("site:settings") or {}
        s3.update_config(site_settings)

        # Try to fetch file bytes from storage
        key = file_url
        try:
            content = s3.get_file_bytes(key)
        except Exception as e:
            print(f"[Download] Failed to fetch file from S3, skill_id={skill_id}, key={key}, error={e}")
            raise AppException(
                ErrorCode.STORAGE_ERROR,
                f"文件下载失败：存储服务暂时不可用，请稍后重试。错误详情：{type(e).__name__}: {e}",
                500,
            )

        if content is None:
            print(f"[Download] File not found in S3, skill_id={skill_id}, key={key}")
            raise AppException(
                ErrorCode.STORAGE_ERROR,
                f"文件不存在或已被删除（存储路径：{key}），请联系技能作者或客服处理",
                404,
            )

        # Increment download count
        skill["download_count"] = skill.get("download_count", 0) + 1
        await kv.put(f"skill:{skill_id}", skill)

        # Award XP to skill author
        if skill.get("user_id"):
            settings = await kv.get("site:settings") or {}
            exp_dl = settings.get("expDownload", EXP_PER_DOWNLOAD)
            from app.api.v1.users import add_exp
            await add_exp(kv, skill["user_id"], exp_dl)

        # Build filename — prefer original upload filename, fallback to title
        original_fn = skill.get("original_filename")
        if original_fn:
            filename = original_fn
            raw_title = os.path.splitext(original_fn)[0]
            ext = os.path.splitext(original_fn)[1] or ".zip"
        else:
            raw_title = skill.get("title", "skill") or "skill"
            safe_title = "".join(c for c in raw_title if c.isascii() and (c.isalnum() or c in " _-")).strip()
            if not safe_title:
                safe_title = "skill"
            ext = os.path.splitext(file_url)[1] or ".zip"
            filename = f"{safe_title}{ext}"

        # For non-ASCII titles, add RFC 5987 filename* parameter
        from urllib.parse import quote
        encoded_title = quote(raw_title, safe='')
        filename_star = f"UTF-8''{encoded_title}{ext}"

        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"; filename*={filename_star}',
                "Content-Length": str(len(content)),
            },
        )

    except AppException:
        raise
    except Exception as e:
        print(f"[Download] Unexpected error in download_skill_file, skill_id={skill_id}, error={type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise AppException(
            ErrorCode.STORAGE_ERROR,
            f"下载失败：服务器内部错误。错误详情：{type(e).__name__}: {e}",
            500,
        )



# ─────────────────────────────────────────────────────────────────────────────
# Cash purchase flow (WeChat Pay / Alipay direct on the product detail page).
# Reuses the recharge gateway adapters from app/api/v1/points.py so we don't
# duplicate signing logic. The order is recorded under
#   `order:cash:<order_no>`
# and indexed by `order:cash:idx:user_skill:<uid>:<sid>` after callback.
# Physical goods carry shipping_fee_yuan + a free-form `shipping_info` dict
# captured at checkout time. Digital goods can also use this flow when the
# product was published with sale_mode=cash|both.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional as _Optional
from fastapi import Request as _Request


@router.post("/cash/order")
async def create_cash_order(
    request: _Request,
    skill_id: str = Body(..., embed=True),
    payment_method: str = Body("wechat", embed=True),
    sku: _Optional[str] = Body(None, embed=True),
    quantity: int = Body(1, embed=True),
    shipping_info: _Optional[dict] = Body(None, embed=True),
    client_type: str = Body("", embed=True),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Create a cash payment order for a product (digital or physical).

    Returns either `qr_url` (web NATIVE / Alipay redirect) or
    `jsapi_params` (mini-program WeChat JSAPI). The frontend polls
    `/purchases/cash/{order_no}/status` until the gateway callback updates
    the order to `paid`.
    """
    skill = await kv.get(f"skill:{skill_id}")
    if not skill:
        raise AppException(ErrorCode.SKILL_NOT_FOUND, "商品不存在", 404)
    if skill.get("status") != "approved":
        raise AppException(ErrorCode.SKILL_REVIEWING, "商品暂不可用")
    if skill.get("user_id") == user["id"]:
        raise AppException(ErrorCode.PARAMS_ERROR, "不能购买自己的商品")

    existing = await kv.get(f"purchase:idx:user_skill:{user['id']}:{skill_id}")
    if existing is not None:
        raise AppException(ErrorCode.ALREADY_PURCHASED, "已购买过该商品")

    sale_mode = (skill.get("sale_mode") or ("cash" if skill.get("cash_price_yuan") else "points"))
    if sale_mode not in ("cash", "both"):
        raise AppException(ErrorCode.PARAMS_ERROR, "该商品不支持现金支付")

    quantity = max(1, int(quantity or 1))
    unit_price = float(skill.get("cash_price_yuan") or 0)
    if unit_price <= 0:
        raise AppException(ErrorCode.PARAMS_ERROR, "商品未配置有效现金价格")

    is_physical = (skill.get("product_type") or "digital") == "physical"
    shipping_fee = float(skill.get("shipping_fee_yuan") or 0) if is_physical else 0
    if is_physical and not shipping_info:
        raise AppException(ErrorCode.PARAMS_ERROR, "请填写收货地址")

    # Decrement stock if managed
    stock = skill.get("stock")
    if stock is not None:
        if int(stock) < quantity:
            raise AppException(ErrorCode.PARAMS_ERROR, "库存不足")

    total_yuan = round(unit_price * quantity + shipping_fee, 2)

    site_settings = await kv.get("site:settings") or {}
    if payment_method == "alipay" and not site_settings.get("alipayEnabled"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "支付宝未启用，请联系管理员开启")
    if payment_method == "wechat" and not site_settings.get("wechatEnabled"):
        raise AppException(ErrorCode.PERMISSION_DENIED, "微信支付未启用，请联系管理员开启")

    # Reuse the gateway adapters we already ship for /points/recharge
    from app.api.v1.points import (
        _create_alipay_order, _create_wechat_order, _create_wechat_jsapi_order,
    )

    now = datetime.now(timezone.utc).isoformat()
    order_no = f"S{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"

    qr_url: _Optional[str] = None
    jsapi_params = None

    if payment_method == "alipay":
        qr_url = await _create_alipay_order(order_no, total_yuan, site_settings, request)
        if not qr_url:
            raise AppException(ErrorCode.RECHARGE_FAILED, "支付宝下单失败，请检查后台支付宝配置")
    elif payment_method == "wechat":
        origin = request.headers.get("x-internal-origin") or str(request.base_url).rstrip("/")
        if client_type == "miniprogram":
            jsapi_params = await _create_wechat_jsapi_order(order_no, total_yuan, site_settings, user, origin)
            if not jsapi_params:
                raise AppException(ErrorCode.RECHARGE_FAILED, "微信 JSAPI 下单失败")
        else:
            qr_url = await _create_wechat_order(order_no, total_yuan, site_settings, origin)
            if not qr_url:
                raise AppException(ErrorCode.RECHARGE_FAILED, "微信下单失败，请检查商户配置")
    else:
        raise AppException(ErrorCode.PARAMS_ERROR, "不支持的支付方式")

    order = {
        "order_no": order_no,
        "user_id": user["id"],
        "skill_id": skill_id,
        "title": skill.get("title"),
        "unit_price_yuan": unit_price,
        "quantity": quantity,
        "shipping_fee_yuan": shipping_fee,
        "total_yuan": total_yuan,
        "payment_method": payment_method,
        "sku": sku,
        "shipping_info": shipping_info or None,
        "is_physical": is_physical,
        "status": "pending",
        "created_at": now,
        "paid_at": None,
        "qr_url": qr_url,
    }
    await kv.put(f"order:cash:{order_no}", order)
    await kv.add_to_list(f"order:cash:by_user:{user['id']}", order_no)

    return success_response({
        "order_no": order_no,
        "payment_method": payment_method,
        "qr_url": qr_url,
        "jsapi_params": jsapi_params,
        "total_yuan": total_yuan,
        "is_physical": is_physical,
        "status": "pending",
    })


@router.get("/cash/{order_no}/status")
async def cash_order_status(
    order_no: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    order = await kv.get(f"order:cash:{order_no}")
    if not order or order.get("user_id") != user["id"]:
        raise AppException(ErrorCode.NOT_FOUND, "订单不存在", 404)
    return success_response({
        "order_no": order_no,
        "status": order.get("status", "pending"),
        "total_yuan": order.get("total_yuan"),
        "is_physical": order.get("is_physical"),
        "shipping_info": order.get("shipping_info"),
        "purchase_id": order.get("purchase_id"),
        "fulfillment_status": order.get("fulfillment_status"),
    })


@router.post("/cash/{order_no}/mark-paid")
async def cash_order_mark_paid(
    order_no: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    """Buyer-side optimistic confirmation: only flips status to `paid_unverified`
    so the frontend can leave the QR modal. The actual paid state still relies on
    the gateway callback (handled in app/api/v1/points.py:payment_callback) which
    additionally credits the seller and decrements stock.
    """
    order = await kv.get(f"order:cash:{order_no}")
    if not order or order.get("user_id") != user["id"]:
        raise AppException(ErrorCode.NOT_FOUND, "订单不存在", 404)
    if order.get("status") == "pending":
        order["status"] = "paid_unverified"
        await kv.put(f"order:cash:{order_no}", order)
    return success_response({"order_no": order_no, "status": order.get("status")})