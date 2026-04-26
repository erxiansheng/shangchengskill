from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_kv, get_current_user
from app.core.exceptions import success_response, paginated_response
from app.storage.kv import KVStore

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
async def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    type: str = Query("all"),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    all_ids = await kv.get_list(f"msg:by_user:{user['id']}")
    # Reverse for newest first
    all_ids = list(reversed(all_ids))

    # Fetch all messages to filter by type
    if type and type != "all":
        messages = await kv.batch_get([f"msg:{mid}" for mid in all_ids])
        filtered = [(mid, m) for mid, m in zip(all_ids, messages) if m and m.get("type") == type]
        all_ids = [mid for mid, _ in filtered]
        total = len(all_ids)
    else:
        total = len(all_ids)

    # Paginate
    start = (page - 1) * page_size
    page_ids = all_ids[start:start + page_size]

    if type and type != "all":
        # Already fetched above, just slice
        items_data = [m for mid, m in filtered[start:start + page_size]]
    else:
        items_data = await kv.batch_get([f"msg:{mid}" for mid in page_ids])

    items = []
    for m in items_data:
        if m:
            items.append({
                "id": m["id"], "type": m["type"], "title": m["title"],
                "content": m["content"], "is_read": m.get("is_read", False),
                "related_type": m.get("related_type"),
                "related_id": m.get("related_id"),
                "created_at": m.get("created_at"),
            })

    return paginated_response(items, total, page, page_size)


@router.put("/{message_id}/read")
async def mark_read(
    message_id: int,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    msg = await kv.get(f"msg:{message_id}")
    if msg and msg.get("user_id") == user["id"]:
        msg["is_read"] = True
        await kv.put(f"msg:{message_id}", msg)
        await kv.remove_from_list(f"msg:unread:{user['id']}", message_id)
    return success_response()


@router.put("/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    unread_ids = await kv.get_list(f"msg:unread:{user['id']}")
    if unread_ids:
        messages = await kv.batch_get([f"msg:{mid}" for mid in unread_ids])
        for mid, m in zip(unread_ids, messages):
            if m:
                m["is_read"] = True
                await kv.put(f"msg:{mid}", m)
        await kv.put(f"msg:unread:{user['id']}", [])
    return success_response()


@router.get("/unread-count")
async def unread_count(
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    unread_ids = await kv.get_list(f"msg:unread:{user['id']}")
    return success_response({"count": len(unread_ids)})
