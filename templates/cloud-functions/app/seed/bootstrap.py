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
            {"id": 1, "name": "AI 智能",   "icon": "🤖", "sort_order": 1, "parent_id": None},
            {"id": 2, "name": "开发工具",  "icon": "🛠️", "sort_order": 2, "parent_id": None},
            {"id": 3, "name": "效率提升",  "icon": "⚡", "sort_order": 3, "parent_id": None},
            {"id": 4, "name": "数据分析",  "icon": "📊", "sort_order": 4, "parent_id": None},
            {"id": 5, "name": "内容创作",  "icon": "🎨", "sort_order": 5, "parent_id": None},
            {"id": 6, "name": "安全合规",  "icon": "🔒", "sort_order": 6, "parent_id": None},
            {"id": 7, "name": "通讯协作",  "icon": "💬", "sort_order": 7, "parent_id": None},
        ]
        cat_ids = []
        for cat in categories:
            await kv.put(f"cat:{cat['id']}", cat)
            cat_ids.append(cat["id"])
        await kv.put("cat:all", cat_ids)
        await kv.put("cat:_counter", 7)
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
