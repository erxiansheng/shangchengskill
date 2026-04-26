"""
System / one-shot bootstrap endpoint.

Why this exists
---------------
The Python Cloud Function on EdgeOne Pages cannot access the KV namespace
directly — only Edge Functions have the `MY_KV` binding. Cloud Function
writes to KV by HTTP-callbacking the Edge Function's `/api/_internal/kv`
proxy. The proxy URL is taken from the `X-Internal-Origin` header that
the Edge Function injects on every forwarded request.

This means seed_data() is intrinsically lazy: it only runs after the
first real request flows through the Edge Function. After a CLI deploy,
nobody hits the site → seed never runs → KV stays empty.

This endpoint provides a no-auth, idempotent way for the deployer to
trigger the seed exactly once after a fresh deploy:

    GET /api/v1/system/bootstrap

Behavior:
- First call: runs seed_data(), writes a `system:bootstrap_done` flag,
  returns {"bootstrapped": true, "first": true}.
- Subsequent calls: returns 200 with {"bootstrapped": true, "first": false}
  WITHOUT re-running seed (which is itself idempotent anyway).

Security:
- Public on purpose — this endpoint MUST be reachable before any user
  exists. It writes only the same defaults that the lazy middleware
  would write on the first request anyway, so the attack surface is
  zero (an attacker hitting it after deploy just races the deployer
  to a no-op).
- After the flag is set, calls do nothing observable beyond returning
  the flag — they cannot inject data.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.exceptions import success_response
from app.storage.kv import KVStore
from app.api.v1.deps import get_kv

router = APIRouter(prefix="/system", tags=["system"])

_BOOTSTRAP_FLAG_KEY = "system:bootstrap_done"


def _safe_json(payload, status: int = 200):
    """Best-effort JSON response that never raises during serialization."""
    try:
        return JSONResponse(status_code=status, content=payload)
    except Exception:
        return JSONResponse(status_code=status, content={"code": 9999, "message": "serialization failed"})


@router.get("/bootstrap")
async def bootstrap(kv: KVStore = Depends(get_kv)):
    """One-shot KV seed trigger. No auth — see module docstring.
    Wraps everything in try/except so EdgeOne never sees an unhandled
    exception (which would surface as 544 Error return from script).
    """
    # Step 1: probe KV
    try:
        existing = await kv.get(_BOOTSTRAP_FLAG_KEY)
    except Exception as e:
        return _safe_json({
            "code": 0,
            "message": "KV proxy unreachable. 请确认 EdgeOne 控制台已绑定名为 MY_KV 的命名空间，且 INTERNAL_KEY 在 _secrets.py 与 [[default]].js 中一致。",
            "data": {"bootstrapped": False, "stage": "kv_probe", "error": str(e)},
        })

    if existing:
        return _safe_json({
            "code": 0,
            "message": "已完成初始化，无需重复触发",
            "data": {"bootstrapped": True, "first": False},
        })

    # Step 2: run seed
    try:
        from app.seed.bootstrap import run_full_seed
        summary = await run_full_seed(kv)
    except Exception as e:
        import traceback
        return _safe_json({
            "code": 0,
            "message": "种子注入失败",
            "data": {
                "bootstrapped": False,
                "stage": "seed",
                "error": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[:2000],  # cap to avoid huge response
            },
        })

    # Step 3: write the flag
    try:
        import time as _t
        await kv.put(_BOOTSTRAP_FLAG_KEY, {"at": int(_t.time()), "summary": summary})
    except Exception:
        pass  # not fatal

    return _safe_json({
        "code": 0,
        "message": "种子注入完成",
        "data": {"bootstrapped": True, "first": True, "summary": summary},
    })
