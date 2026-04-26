"""First-run seeding helpers.

Called from main.py the first time the Cloud Function boots after deploy
(detected by the absence of `seed:initialized` in KV). Creates a small
catalog of demo products spanning all three sale modes (points / cash /
both) and **uploads the bundled `logo_opt.glb` mascot into chunked KV**
so the homepage 3D Logo works out of the box without any post-deploy
scripts. Operators can delete or replace anything from /admin afterwards.

Demo products are intentionally minimal — they exist so the freshly
generated mall doesn't show an empty homepage during the first preview.
The default 3D mascot is shipped as `app/seed/assets/logo_opt.glb`
(≈ 600 KB), split into 512 KB chunks at runtime by `chunked_kv.put_asset`.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.storage.kv import KVStore
from app.storage import chunked_kv


DEMO_PRODUCTS = [
    {
        "title": "示例商品 · 限量徽章（积分售卖）",
        "subtitle": "用积分兑换专属社区徽章",
        "description": "# 限量徽章\n\n这是一个 **纯积分** 售卖的示例商品。后台可以删除。",
        "price": 100,
        "cash_price_yuan": 0,
        "sale_mode": "points",
        "stock": 50,
        "tags": ["示例", "积分"],
        "is_free": False,
        "cover_image": "",
    },
    {
        "title": "示例商品 · 入门指南电子书（现金售卖）",
        "subtitle": "PDF 立即下载",
        "description": "# 入门指南\n\n这是一个 **纯现金** 售卖的示例商品。",
        "price": 0,
        "cash_price_yuan": 9.9,
        "sale_mode": "cash",
        "stock": None,
        "tags": ["示例", "电子书"],
        "is_free": False,
        "cover_image": "",
    },
    {
        "title": "示例商品 · 周边马克杯（积分 / 现金 二选一）",
        "subtitle": "支持积分抵扣，也可全额现金购买",
        "description": "# 周边马克杯\n\n这是 **积分+现金** 双模式示例。",
        "price": 500,
        "cash_price_yuan": 49.9,
        "sale_mode": "both",
        "stock": 20,
        "tags": ["示例", "周边"],
        "is_free": False,
        "cover_image": "",
    },
    {
        "title": "免费体验装",
        "subtitle": "0 元即可领取，体验完整下单流程",
        "description": "# 免费体验装\n\n用于测试下单与下载流程。",
        "price": 0,
        "cash_price_yuan": 0,
        "sale_mode": "points",
        "stock": None,
        "tags": ["示例", "免费"],
        "is_free": True,
        "cover_image": "",
    },
    {
        "title": "限量优惠券（5 元抵扣）",
        "subtitle": "下次购买现金商品时自动抵扣",
        "description": "# 抵扣券示例\n\n积分兑换抵扣券的示例。",
        "price": 50,
        "cash_price_yuan": 0,
        "sale_mode": "points",
        "stock": 100,
        "tags": ["示例", "优惠券"],
        "is_free": False,
        "cover_image": "",
    },
]


async def seed_demo_products(kv: KVStore) -> None:
    """Insert demo products into KV with status=approved so they show on the homepage."""
    now = int(time.time())
    listing_ids: list[str] = []
    for idx, p in enumerate(DEMO_PRODUCTS, start=1):
        pid = f"demo{idx}"
        record = {
            "id": pid,
            **p,
            "status": "approved",
            "author_id": 0,
            "author_name": "EdgeOne Mall Demo",
            "created_at": now,
            "published_at": now,
            "_demo": True,  # admin can bulk-delete by filter
        }
        await kv.put(f"skill:{pid}", record)
        listing_ids.append(pid)

    # Also push into the approved listings shard the homepage reads
    await kv.put("skill_approved_listdata", listing_ids)


async def seed_default_3d_model(kv: KVStore) -> None:
    """Push the bundled `logo_opt.glb` mascot into chunked KV and register
    it as the default enabled 3D model so `/api/v1/models3d/active` returns
    a real asset on first boot.

    Idempotent: re-running after the model exists is a no-op.
    """
    existing = await kv.get_list("models3d:list") or []
    if existing:
        return

    glb_path = Path(__file__).resolve().parent / "assets" / "logo_opt.glb"
    if not glb_path.exists():
        print(
            f"[Seed] Default 3D mascot asset not found at {glb_path}; "
            "skipping. Upload one from /admin/models3d."
        )
        return

    try:
        content = glb_path.read_bytes()
        print(
            f"[Seed] Uploading default 3D mascot ({len(content)} bytes) "
            "into chunked KV…"
        )
        asset = await chunked_kv.put_asset(kv, content, "model/gltf-binary")

        import secrets
        mid = secrets.token_urlsafe(8)
        rec = {
            "id": mid,
            "name": "Default Mascot",
            "asset_id": asset["id"],
            "size": len(content),
            "enabled": True,
            "order": 0,
            "params": {
                "scale": 1.0,
                "speed_x": 0.5, "speed_y": 0.3, "speed_z": 0.4,
                "bounds_x": 2.0, "bounds_y": 1.5, "bounds_z": 1.5,
            },
            "created_at": int(time.time()),
        }
        await kv.put(f"models3d:item:{mid}", rec)
        await kv.add_to_list("models3d:list", mid)
        print(f"[Seed] Default 3D mascot registered as {mid}.")
    except Exception as exc:
        # Never block first-boot for a 3D model failure — fallback CSS logo
        # in Logo3D.vue keeps the homepage usable.
        print(
            f"[Seed] Failed to seed default 3D mascot: {exc}. "
            "Logo3D will fall back to the CSS-only animation. Upload a "
            ".glb from /admin/models3d to retry."
        )
