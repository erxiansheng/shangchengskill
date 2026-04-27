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
    # ===== 数码电器 (cat 1) =====
    {
        "title": "无线蓝牙耳机 Pro-演示商品",
        "subtitle": "主动降噪 · 30 小时续航",
        "description": "# 无线蓝牙耳机 Pro\n\n旗舰级降噪芯片，沉浸聆听每一个细节。\n\n- 主动降噪深度 -42 dB\n- IPX5 防水防汗\n- 双设备无缝切换",
        "price": 0, "cash_price_yuan": 399.0, "sale_mode": "cash",
        "stock": 200, "tags": ["数码", "耳机", "降噪"],
        "category_id": 1, "is_free": False, "cover_image": "",
    },
    {
        "title": "便携充电宝 20000mAh-演示商品",
        "subtitle": "三口快充 · 双向 PD 65W",
        "description": "# 大容量充电宝\n\n出差通勤一日无忧，PD/QC 全协议兼容。",
        "price": 1500, "cash_price_yuan": 169.0, "sale_mode": "both",
        "stock": 80, "tags": ["数码", "充电"],
        "category_id": 1, "is_free": False, "cover_image": "",
    },
    {
        "title": "机械键盘 87 键 RGB-演示商品",
        "subtitle": "热插拔轴体 · 全键无冲",
        "description": "# 机械键盘\n\n青轴 / 红轴可选，支持 5000 万次敲击寿命。",
        "price": 0, "cash_price_yuan": 299.0, "sale_mode": "cash",
        "stock": 60, "tags": ["数码", "键盘", "外设"],
        "category_id": 1, "is_free": False, "cover_image": "",
    },

    # ===== 服饰鞋包 (cat 2) =====
    {
        "title": "纯棉基础款 T 恤-演示商品",
        "subtitle": "260g 重磅纯棉 · 多色可选",
        "description": "# 基础款 T 恤\n\n精梳棉面料，舒适透气，百搭日常。",
        "price": 0, "cash_price_yuan": 79.0, "sale_mode": "cash",
        "stock": 500, "tags": ["服饰", "T恤", "百搭"],
        "category_id": 2, "is_free": False, "cover_image": "",
    },
    {
        "title": "复古帆布双肩包",
        "subtitle": "通勤旅行两相宜 · 15.6 寸笔记本仓",
        "description": "# 帆布双肩包\n\n大容量 + 多隔层，年轻潮人首选。",
        "price": 800, "cash_price_yuan": 89.0, "sale_mode": "both",
        "stock": 120, "tags": ["服饰", "包", "通勤"],
        "category_id": 2, "is_free": False, "cover_image": "",
    },

    # ===== 美妆个护 (cat 3) =====
    {
        "title": "氨基酸洁面慕斯 150ml-演示商品",
        "subtitle": "温和洁净 · 敏感肌可用",
        "description": "# 洁面慕斯\n\n弱酸性配方，告别紧绷干涩。",
        "price": 0, "cash_price_yuan": 49.0, "sale_mode": "cash",
        "stock": 300, "tags": ["美妆", "洁面"],
        "category_id": 3, "is_free": False, "cover_image": "",
    },

    # ===== 食品生鲜 (cat 4) =====
    {
        "title": "云南小粒咖啡豆 250g-演示商品",
        "subtitle": "中度烘焙 · 焦糖坚果香",
        "description": "# 精品咖啡豆\n\n手工分拣阿拉比卡豆，新鲜烘焙直发。",
        "price": 600, "cash_price_yuan": 58.0, "sale_mode": "both",
        "stock": 100, "tags": ["食品", "咖啡"],
        "category_id": 4, "is_free": False, "cover_image": "",
    },
    {
        "title": "新疆灰枣 500g-演示商品",
        "subtitle": "若羌大枣 · 自然甜润",
        "description": "# 新疆灰枣\n\n核小肉厚，泡水煮粥皆宜。",
        "price": 0, "cash_price_yuan": 39.9, "sale_mode": "cash",
        "stock": 200, "tags": ["食品", "干货"],
        "category_id": 4, "is_free": False, "cover_image": "",
    },

    # ===== 家居家装 (cat 5) =====
    {
        "title": "北欧风香薰蜡烛-演示商品",
        "subtitle": "天然大豆蜡 · 60 小时燃烧",
        "description": "# 香薰蜡烛\n\n薰衣草 / 雪松 / 玫瑰多香型可选。",
        "price": 0, "cash_price_yuan": 69.0, "sale_mode": "cash",
        "stock": 150, "tags": ["家居", "香薰"],
        "category_id": 5, "is_free": False, "cover_image": "",
    },
    {
        "title": "记忆棉慢回弹靠垫-演示商品",
        "subtitle": "护腰减压 · 久坐神器",
        "description": "# 记忆棉靠垫\n\n人体工学曲线设计，办公室必备。",
        "price": 1200, "cash_price_yuan": 0, "sale_mode": "points",
        "stock": 50, "tags": ["家居", "办公", "护腰"],
        "category_id": 5, "is_free": False, "cover_image": "",
    },

    # ===== 母婴玩具 (cat 6) =====
    {
        "title": "益智积木拼搭套装 200 件-演示商品",
        "subtitle": "ABS 安全材质 · 3 岁 +",
        "description": "# 积木套装\n\n激发儿童创造力，与孩子共度亲子时光。",
        "price": 0, "cash_price_yuan": 129.0, "sale_mode": "cash",
        "stock": 80, "tags": ["玩具", "亲子"],
        "category_id": 6, "is_free": False, "cover_image": "",
    },

    # ===== 运动户外 (cat 7) =====
    {
        "title": "瑜伽垫 6mm 加厚-演示商品",
        "subtitle": "TPE 环保 · 防滑减震",
        "description": "# 瑜伽垫\n\n附赠收纳带 + 教学视频。",
        "price": 0, "cash_price_yuan": 99.0, "sale_mode": "cash",
        "stock": 150, "tags": ["运动", "瑜伽"],
        "category_id": 7, "is_free": False, "cover_image": "",
    },
    {
        "title": "户外便携保温杯 500ml-演示商品",
        "subtitle": "316 不锈钢 · 12 小时保温",
        "description": "# 保温杯\n\n大口径易清洗，运动通勤都好用。",
        "price": 700, "cash_price_yuan": 79.0, "sale_mode": "both",
        "stock": 200, "tags": ["运动", "户外"],
        "category_id": 7, "is_free": False, "cover_image": "",
    },

    # ===== 图书音像 (cat 8) =====
    {
        "title": "《商城运营实战指南》电子书-演示商品",
        "subtitle": "PDF 立即下载 · 200 页干货",
        "description": "# 商城运营实战\n\n从 0 到 1 搭建你的电商业务。",
        "price": 0, "cash_price_yuan": 9.9, "sale_mode": "cash",
        "stock": None, "tags": ["图书", "电子书"],
        "category_id": 8, "is_free": False, "cover_image": "",
    },

    # ===== 虚拟商品 (cat 9) =====
    {
        "title": "VIP 会员月卡-演示商品",
        "subtitle": "解锁全站专属折扣 + 优先客服",
        "description": "# VIP 月卡\n\n享受会员价、生日礼包、积分加倍等多重权益。",
        "price": 0, "cash_price_yuan": 19.9, "sale_mode": "cash",
        "stock": None, "tags": ["虚拟", "会员"],
        "category_id": 9, "is_free": False, "cover_image": "",
    },

    # ===== 积分专区 (cat 10) =====
    {
        "title": "限量徽章（积分兑换）-演示商品",
        "subtitle": "用积分兑换专属社区徽章",
        "description": "# 限量徽章\n\n纯积分兑换示例，后台可删除。",
        "price": 100, "cash_price_yuan": 0, "sale_mode": "points",
        "stock": 50, "tags": ["积分", "周边"],
        "category_id": 10, "is_free": False, "cover_image": "",
    },
    {
        "title": "周边马克杯（积分 / 现金）-演示商品",
        "subtitle": "支持积分抵扣，也可全额现金购买",
        "description": "# 周边马克杯\n\n积分 + 现金双模式示例。",
        "price": 500, "cash_price_yuan": 49.9, "sale_mode": "both",
        "stock": 20, "tags": ["积分", "周边"],
        "category_id": 10, "is_free": False, "cover_image": "",
    },
    {
        "title": "5 元抵扣券（积分兑换）-演示商品",
        "subtitle": "下次购买现金商品时自动抵扣",
        "description": "# 抵扣券\n\n纯积分兑换的优惠券示例。",
        "price": 50, "cash_price_yuan": 0, "sale_mode": "points",
        "stock": 100, "tags": ["积分", "优惠券"],
        "category_id": 10, "is_free": False, "cover_image": "",
    },

    # ===== 限时特惠 / 体验 (cat 11) =====
    {
        "title": "免费体验装-演示商品",
        "subtitle": "0 元领取，体验完整下单流程",
        "description": "# 免费体验装\n\n用于测试下单与下载流程。",
        "price": 0, "cash_price_yuan": 0, "sale_mode": "points",
        "stock": None, "tags": ["免费", "体验"],
        "category_id": 11, "is_free": True, "cover_image": "",
    },
    {
        "title": "新人首单礼包-演示商品",
        "subtitle": "限时 1 元购，仅限新用户",
        "description": "# 新人礼包\n\n注册即享，限时秒杀首选。",
        "price": 0, "cash_price_yuan": 1.0, "sale_mode": "cash",
        "stock": 999, "tags": ["秒杀", "新人"],
        "category_id": 11, "is_free": False, "cover_image": "",
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
            "user_id": 0,
            "author_id": 0,  # legacy alias
            "author_name": "EdgeOne Mall Demo",
            "version": "1.0.0",
            "avg_rating": 0,
            "review_count": 0,
            "download_count": 0,
            "purchase_count": 0,
            "created_at": now,
            "published_at": now,
            "_demo": True,  # admin can bulk-delete by filter
        }
        await kv.put(f"skill:{pid}", record)
        listing_ids.append(pid)
        # Also index into the per-category and per-status lists that the
        # /api/v1/skills and /api/v1/categories/{id}/skills endpoints read.
        try:
            await kv.add_to_list("skill:by_status:approved", pid)
        except Exception:
            pass
        try:
            cat_id = p.get("category_id")
            if cat_id is not None:
                await kv.add_to_list(f"skill:by_cat:{cat_id}", pid)
        except Exception:
            pass

    # Legacy / homepage shard (kept for backward compatibility).
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
