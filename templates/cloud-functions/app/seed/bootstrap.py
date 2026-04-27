# Re-export to allow `from app.seed.bootstrap import ...`
from app.seed import seed_demo_products, seed_default_3d_model  # noqa: F401


# ---------------------------------------------------------------------------
# Self-contained one-shot seed routine. Used by /api/v1/system/bootstrap so
# that the public bootstrap endpoint does NOT need to import app.main (which
# could fail if the lazy middleware seed has not run yet, or trigger circular
# import edge cases).
# ---------------------------------------------------------------------------

async def run_full_seed(kv) -> dict:
    """Run all seed steps. Idempotent: each step checks-then-writes.
    Returns a small summary dict for the API response.
    """
    summary = {"categories": False, "settings": False, "admin": False, "demo": False}

    # ----- categories -----
    existing_cats = await kv.get_list("cat:all")
    if not existing_cats:
        categories = [
            {"id": 1,  "name": "数码电器", "icon": "📱", "sort_order": 1,  "parent_id": None},
            {"id": 2,  "name": "服饰鞋包", "icon": "👕", "sort_order": 2,  "parent_id": None},
            {"id": 3,  "name": "美妆个护", "icon": "💄", "sort_order": 3,  "parent_id": None},
            {"id": 4,  "name": "食品生鲜", "icon": "🍎", "sort_order": 4,  "parent_id": None},
            {"id": 5,  "name": "家居家装", "icon": "🛋️", "sort_order": 5,  "parent_id": None},
            {"id": 6,  "name": "母婴玩具", "icon": "🧸", "sort_order": 6,  "parent_id": None},
            {"id": 7,  "name": "运动户外", "icon": "⚽", "sort_order": 7,  "parent_id": None},
            {"id": 8,  "name": "图书音像", "icon": "📚", "sort_order": 8,  "parent_id": None},
            {"id": 9,  "name": "虚拟商品", "icon": "💎", "sort_order": 9,  "parent_id": None},
            {"id": 10, "name": "积分专区", "icon": "🎁", "sort_order": 10, "parent_id": None},
            {"id": 11, "name": "限时特惠", "icon": "⚡", "sort_order": 11, "parent_id": None},
        ]
        cat_ids = []
        for cat in categories:
            await kv.put(f"cat:{cat['id']}", cat)
            cat_ids.append(cat["id"])
        await kv.put("cat:all", cat_ids)
        await kv.put("cat:_counter", len(categories))
        summary["categories"] = True

    # ----- settings -----
    default_settings = {
        "loginMethods": {"email": True, "wechat": False, "qq": False, "github": False},
        "wxLoginAppId": "", "wxLoginAppSecret": "", "wxLoginRedirectUri": "",
        "wxMpAppId": "", "wxMpAppSecret": "",
        "storage_mode": "kv",
        "s3Endpoint": "", "s3Bucket": "", "s3AccessKey": "", "s3SecretKey": "",
        "s3Region": "us-east-1", "s3PublicUrl": "",
        "wechatPayMchId": "", "wechatPayApiKey": "",
        "alipayAppId": "", "alipayPrivateKey": "",
        "smtpHost": "", "smtpPort": 465, "smtpUser": "", "smtpPassword": "",
        "smtpFromAddress": "",
        "points_per_yuan": 10, "platform_fee_rate": 0.3,
    }
    existing_settings = await kv.get("site:settings") or {}
    changed = False
    for k, v in default_settings.items():
        if k not in existing_settings:
            existing_settings[k] = v
            changed = True
    if changed:
        await kv.put("site:settings", existing_settings)
        summary["settings"] = True

    # ----- admin user -----
    try:
        from app.api.v1.admin_auth import seed_default_admin
        await seed_default_admin(kv)
        summary["admin"] = True
    except Exception as e:
        print(f"[Seed] Admin seed error: {e}")

    # ----- demo products + 3D model -----
    if not await kv.get("seed:initialized"):
        try:
            await seed_demo_products(kv)
            await seed_default_3d_model(kv)
            import time as _t
            await kv.put("seed:initialized", int(_t.time()))
            summary["demo"] = True
        except Exception as e:
            print(f"[Seed] Demo seed error: {e}")

    return summary
