from fastapi import APIRouter, Depends

from app.core.exceptions import success_response
from app.storage.kv import KVStore
from app.api.v1.deps import get_kv

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(kv: KVStore = Depends(get_kv)):
    ids = await kv.get_list("cat:all")
    if not ids:
        return success_response({"categories": []})

    categories = await kv.batch_get([f"cat:{cid}" for cid in ids])
    cats = [c for c in categories if c]

    # Build tree (parent/children)
    cat_map = {c["id"]: {**c, "children": []} for c in cats}
    roots = []
    for c in sorted(cats, key=lambda x: x.get("sort_order", 0)):
        node = cat_map[c["id"]]
        parent_id = c.get("parent_id")
        if parent_id and parent_id in cat_map:
            cat_map[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return success_response({"categories": roots})
