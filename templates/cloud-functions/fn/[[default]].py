"""
EdgeOne Pages Python Runtime - FastAPI ASGI Entry Point (Cloud Function)

Handles write operations and authenticated requests forwarded from the
Edge Function router (api/[[default]].js).

Route: /fn/* -> EdgeOne strips /fn prefix -> FastAPI receives /v1/...

KV Storage: The Edge Function passes X-Internal-Origin header on each
forwarded request. The KVOriginMiddleware in main.py reads this header
and configures the KVStore to proxy KV operations back through the
Edge Function's /_internal/kv endpoint.
"""

import sys
import os

# cloud-functions root is one level up from fn/
_cf_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _cf_root not in sys.path:
    sys.path.insert(0, _cf_root)

from fastapi import FastAPI
from app.main import configure_app, lifespan
from app.api.v1.deps import init_storage

# Eagerly initialise storage singletons at module level.
# EdgeOne Pages Python runtime may not send ASGI lifespan events,
# so we cannot rely solely on the lifespan context manager.
init_storage()

# ---- EdgeOne Pages ASGI entry flag ----
app = FastAPI(
    title="EdgeOneMall API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure with /v1 prefix (EdgeOne strips the /fn file route prefix)
configure_app(app, api_prefix="/v1")
