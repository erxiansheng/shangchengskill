# Architecture

```
┌────────────┐   HTTPS    ┌──────────────────┐  fetch    ┌────────────────────┐
│  Browser   │ ─────────▶ │  Edge Function   │ ────────▶ │ Cloud Function     │
│ (Vue 3 SPA)│            │ api/[[default]].js│           │ (FastAPI / Python) │
└────────────┘            │  - JWT 校验       │           │  fn/[[default]].py │
       │                  │  - Cache 头注入   │           │  app/api/v1/*.py   │
       │                  │  - KV 透传        │           └─────────┬──────────┘
       │                  └────────┬──────────┘                     │
       │                           │ HTTP (KV REST)                 │ HTTP (KV REST)
       │                           ▼                                ▼
       │                    ┌────────────────────────────────────────────┐
       │                    │           EdgeOne Pages KV                 │
       │                    │  user:{id}, skill:{id}, order:{id},        │
       │                    │  asset:{id}:meta + asset:{id}:chunk:{n},   │
       │                    │  models3d:item:{id}, site:settings, …      │
       │                    └────────────────────────────────────────────┘
       │
       │   /assets/{id}  (binary stream from chunked KV)
       └────────────────────────────────────────────────────────────────▶
```

## Layer responsibilities

- **Vue SPA**: pure presentational + routing. All API calls go through
  `src/api/request.js` which prefixes `/api/v1` and attaches the
  storefront token.
- **Vue admin module**: built into the storefront SPA at `/admin`, reusing
  the normal storefront token and guarded by `id=1` / `role=admin` checks.
- **Edge Function**: thin proxy. Validates JWT (rejects expired tokens at
  the edge to save Cloud Function invocations), injects KV namespace via
  `MY_KV` binding, forwards everything else to the Cloud Function.
- **Cloud Function (FastAPI)**: business logic, schema validation, password
  hashing, JWT issuance. Talks to KV through HTTP (no in-process binding —
  Python runtime cannot bind `MY_KV`), with the Edge Function acting as
  trusted proxy gated by `INTERNAL_KEY` header.
- **KV**: single source of truth. No relational DB.

## Why two functions?

EdgeOne Pages Cloud Functions (Python, FastAPI-class workloads) cannot
directly bind KV — only Edge Functions (V8 JS) get the `MY_KV` global.
The Edge Function therefore:

1. authenticates the request (cheap),
2. forwards `/api/v1/*` to the Python Cloud Function URL with a signed
   `INTERNAL_KEY` header so the Python side trusts it,
3. exposes a small KV REST passthrough (`/__kv/*`) so the Python side can
   `GET/PUT` keys without holding cloud credentials.

## Data flow example: image upload (storage_mode = kv)

1. Browser `POST /api/v1/upload/image` (multipart, JWT in header).
2. Edge Function checks JWT, forwards to Cloud Function.
3. `upload.py` reads `site:settings.storage_mode` → `"kv"` → calls
   `chunked_kv.put_asset(kv, content, content_type)`.
4. `put_asset` slices content into 512 KB chunks, base64-encodes each,
   writes `asset:{id}:chunk:{n}` and `asset:{id}:meta`.
5. Returns `{ id, url: "/api/v1/assets/<id>", size, sha256 }`.
6. Future `GET /api/v1/assets/<id>` walks chunks back via async generator
   into a `StreamingResponse`.
