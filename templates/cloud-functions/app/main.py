import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler, generic_exception_handler
from app.api.v1.deps import init_storage, get_kv

# Import routers
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.skills import router as skills_router
from app.api.v1.purchases import router as purchases_router
from app.api.v1.points import router as points_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.messages import router as messages_router
from app.api.v1.upload import router as upload_router
from app.api.v1.categories import router as categories_router
from app.api.v1.admin import router as admin_router
from app.api.v1.tokens import router as tokens_router
# edgeone-mall additions
from app.api.v1.assets import router as assets_router
from app.api.v1.admin_auth import router as admin_auth_router, seed_default_admin
from app.api.v1.system import router as system_router
from app.api.v1.models3d import (
    admin_router as models3d_admin_router,
    public_router as models3d_public_router,
)


_seed_done = False


async def seed_data():
    """Seed default categories and initial site settings into KV.
    Called lazily on first request (when KV proxy origin is available).

    NOTE: ``_seed_done`` is flipped only AFTER the seeding finishes successfully.
    The previous "set True at the top" pattern caused a transient KV failure
    on the very first request (e.g. proxy 502 while the deploy is still warming
    up) to permanently disable seeding for the lifetime of that worker, leaving
    the KV namespace empty until the next cold start. With the flag flipped at
    the end, callers will retry on subsequent requests until the seed actually
    lands.
    """
    global _seed_done
    if _seed_done:
        return

    kv = get_kv()

    # Check if already seeded
    existing_cats = await kv.get_list("cat:all")
    if not existing_cats:
        print("[Seed] Seeding default data to KV...")

        # Seed categories
        categories = [
            {"id": 1, "name": "AI 智能", "icon": "🤖", "sort_order": 1, "parent_id": None},
            {"id": 2, "name": "开发工具", "icon": "🛠️", "sort_order": 2, "parent_id": None},
            {"id": 3, "name": "效率提升", "icon": "⚡", "sort_order": 3, "parent_id": None},
            {"id": 4, "name": "数据分析", "icon": "📊", "sort_order": 4, "parent_id": None},
            {"id": 5, "name": "内容创作", "icon": "🎨", "sort_order": 5, "parent_id": None},
            {"id": 6, "name": "安全合规", "icon": "🔒", "sort_order": 6, "parent_id": None},
            {"id": 7, "name": "通讯协作", "icon": "💬", "sort_order": 7, "parent_id": None},
        ]
        cat_ids = []
        for cat in categories:
            await kv.put(f"cat:{cat['id']}", cat)
            cat_ids.append(cat["id"])
        await kv.put("cat:all", cat_ids)
        await kv.put("cat:_counter", 7)
    else:
        print("[Seed] Data already exists, skipping.")

    # Merge default settings — add missing keys without overwriting existing values.
    # NOTE: Storage / payment / login credentials are intentionally BLANK in
    # this template. Configure them via the /admin Settings panel after deploy.
    default_settings = {
        # ----- login providers -----
        "loginMethods": {"email": True, "wechat": False, "qq": False, "github": False},
        "wxLoginAppId": "",
        "wxLoginAppSecret": "",
        "wxLoginRedirectUri": "",
        "wxMpAppId": "",
        "wxMpAppSecret": "",
        # ----- storage -----
        "storage_mode": "kv",  # 'kv' (chunked KV, default) or 's3'
        "s3Endpoint": "",
        "s3Bucket": "",
        "s3AccessKey": "",
        "s3SecretKey": "",
        "s3Region": "us-east-1",
        "s3PublicUrl": "",
        # ----- payment (placeholder, configure in admin) -----
        "wechatPayMchId": "",
        "wechatPayApiKey": "",
        "alipayAppId": "",
        "alipayPrivateKey": "",
        # ----- email (SMTP placeholder) -----
        "smtpHost": "",
        "smtpPort": 465,
        "smtpUser": "",
        "smtpPassword": "",
        "smtpFromAddress": "",
        # ----- platform economics -----
        "points_per_yuan": 10,
        "platform_fee_rate": 0.3,
    }
    existing_settings = await kv.get("site:settings") or {}
    updated = False
    for key, val in default_settings.items():
        if key not in existing_settings:
            existing_settings[key] = val
            updated = True
    if updated:
        await kv.put("site:settings", existing_settings)
        print("[Seed] Settings updated with defaults.")

    # Seed bootstrap admin (account+password) if none exists
    try:
        await seed_default_admin(kv)
    except Exception as e:
        print(f"[Seed] Admin seed error: {e}")

    # Seed example products + 3D model on first run
    if not await kv.get("seed:initialized"):
        try:
            from app.seed import seed_demo_products, seed_default_3d_model
            await seed_demo_products(kv)
            await seed_default_3d_model(kv)
            await kv.put("seed:initialized", int(__import__("time").time()))
            print("[Seed] Demo products + default 3D model seeded.")
        except Exception as e:
            print(f"[Seed] Demo seed error: {e}")

    _seed_done = True
    print("[Seed] Done.")


class KVOriginMiddleware(BaseHTTPMiddleware):
    """Extract X-Internal-Origin from Edge Function and configure KVStore.
    Also triggers lazy seed on first request.
    """

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("x-internal-origin")
        if origin:
            kv = get_kv()
            if not kv.ready:
                kv.set_origin(origin)
            # Seed on first request
            try:
                await seed_data()
            except Exception as e:
                print(f"[Seed] Error during seeding: {e}")
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise storage singletons (KV origin set later by middleware)
    init_storage()
    yield
    kv = get_kv()
    await kv.close()


def configure_app(application: FastAPI, api_prefix: str = None):
    """Configure the FastAPI app with middleware, exception handlers, and routers."""
    prefix = api_prefix or settings.API_V1_PREFIX

    # KV origin middleware (must be added before CORS)
    application.add_middleware(KVOriginMiddleware)

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler
    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Mount local uploads for dev fallback
    uploads_dir = "./uploads"
    if os.path.exists(uploads_dir):
        application.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # Include all v1 routers
    application.include_router(auth_router, prefix=prefix)
    application.include_router(users_router, prefix=prefix)
    application.include_router(skills_router, prefix=prefix)
    application.include_router(purchases_router, prefix=prefix)
    application.include_router(points_router, prefix=prefix)
    application.include_router(reviews_router, prefix=prefix)
    application.include_router(favorites_router, prefix=prefix)
    application.include_router(messages_router, prefix=prefix)
    application.include_router(upload_router, prefix=prefix)
    application.include_router(categories_router, prefix=prefix)
    application.include_router(admin_router, prefix=prefix)
    application.include_router(tokens_router, prefix=prefix)
    # edgeone-mall additions
    application.include_router(assets_router, prefix=prefix)
    application.include_router(admin_auth_router, prefix=prefix)
    application.include_router(system_router, prefix=prefix)
    application.include_router(models3d_admin_router, prefix=prefix)
    application.include_router(models3d_public_router, prefix=prefix)

    @application.get("/")
    @application.get("/")
    async def root():
        return {"message": "EdgeOne Mall API is running", "version": settings.VERSION}


# NOTE: We deliberately do NOT define a module-level `app = FastAPI(...)` here.
# EdgeOne's Python runtime auto-registers every .py file under cloud-functions/
# that exposes a top-level ASGI app as a separate function entrypoint. Having
# `app = FastAPI(...)` at module scope would cause `app/main.py` to be exposed
# at the route `/app/main`, doubling cold-start cost and creating duplicate
# KV singletons. The single legitimate entrypoint is `fn/[[default]].py`,
# which imports `configure_app` and `lifespan` from this module.
