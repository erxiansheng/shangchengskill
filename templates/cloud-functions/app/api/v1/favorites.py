from fastapi import APIRouter, Depends, Query, Body
from datetime import datetime, timezone

from app.api.v1.deps import get_kv, get_current_user
from app.core.exceptions import success_response, paginated_response
from app.core.levels import EXP_PER_FAVORITE
from app.storage.kv import KVStore

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("")
async def add_favorite(
    skill_id: str = Body(..., embed=True),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    # Check already favorited
    existing = await kv.get(f"fav:idx:user_skill:{user['id']}:{skill_id}")
    if existing is not None:
        return success_response({"favorited": True})

    fav_id = await kv.next_id("fav")
    now = datetime.now(timezone.utc).isoformat()
    fav = {
        "id": fav_id,
        "user_id": user["id"],
        "skill_id": skill_id,
        "created_at": now,
    }
    await kv.put(f"fav:{fav_id}", fav)
    await kv.put(f"fav:idx:user_skill:{user['id']}:{skill_id}", fav_id)
    await kv.add_to_list(f"fav:by_user:{user['id']}", fav_id)
    # 二次校验：并发收藏时 add_to_list 可能因 read-modify-write 竞争丢失条目，
    # 这里再读一次并补写一次，最大程度保证 fav_id 出现在列表中
    try:
        current = await kv.get_list(f"fav:by_user:{user['id']}")
        if not any(str(x) == str(fav_id) for x in (current or [])):
            await kv.add_to_list(f"fav:by_user:{user['id']}", fav_id)
    except Exception as e:
        print(f"[Favorites] verify add_to_list failed: {e}")

    # Increment favorite_count on the skill
    skill_data = await kv.get(f"skill:{skill_id}")
    if skill_data:
        skill_data["favorite_count"] = skill_data.get("favorite_count", 0) + 1
        await kv.put(f"skill:{skill_id}", skill_data)

    # Award XP to skill author
    skill = await kv.get(f"skill:{skill_id}")
    if skill and skill.get("user_id") and skill["user_id"] != user["id"]:
        settings = await kv.get("site:settings") or {}
        exp_fav = settings.get("expFavorite", EXP_PER_FAVORITE)
        from app.api.v1.users import add_exp
        await add_exp(kv, skill["user_id"], exp_fav)

    return success_response({"favorited": True})


@router.delete("/{skill_id}")
async def remove_favorite(
    skill_id: str,
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    fav_id = await kv.get(f"fav:idx:user_skill:{user['id']}:{skill_id}")
    if fav_id is not None:
        await kv.delete(f"fav:{fav_id}")
        await kv.delete(f"fav:idx:user_skill:{user['id']}:{skill_id}")
        await kv.remove_from_list(f"fav:by_user:{user['id']}", fav_id)

        # Decrement favorite_count on the skill
        skill_data = await kv.get(f"skill:{skill_id}")
        if skill_data:
            skill_data["favorite_count"] = max(0, skill_data.get("favorite_count", 0) - 1)
            await kv.put(f"skill:{skill_id}", skill_data)
    return success_response({"favorited": False})


@router.get("")
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    kv: KVStore = Depends(get_kv),
):
    fav_ids = await kv.get_list(f"fav:by_user:{user['id']}")

    # 自愈：若聚合列表为空，则尝试从 idx 反查重建
    # 历史上 add_to_list 在并发收藏时可能丢失条目，导致计数恒为 0
    if not fav_ids:
        try:
            idx_keys = await kv.list_keys(prefix=f"fav:idx:user_skill:{user['id']}:")
            if idx_keys:
                recovered = await kv.batch_get(idx_keys)
                fav_ids = [v for v in recovered if v is not None]
                if fav_ids:
                    # 去重并写回聚合列表
                    seen = set()
                    deduped = []
                    for fid in fav_ids:
                        key = str(fid)
                        if key not in seen:
                            seen.add(key)
                            deduped.append(fid)
                    fav_ids = deduped
                    await kv.put(f"fav:by_user:{user['id']}", fav_ids)
                    print(f"[Favorites] Rebuilt fav:by_user:{user['id']} from {len(idx_keys)} idx keys -> {len(fav_ids)} favs")
        except Exception as e:
            print(f"[Favorites] self-heal failed for user {user['id']}: {e}")

    fav_ids = list(reversed(fav_ids))  # Newest first
    total = len(fav_ids)

    start = (page - 1) * page_size
    page_ids = fav_ids[start:start + page_size]
    favs = await kv.batch_get([f"fav:{fid}" for fid in page_ids])

    # Get associated skills
    skill_ids = [f["skill_id"] for f in favs if f]
    skills = await kv.batch_get([f"skill:{sid}" for sid in skill_ids])
    skill_map = {s["id"]: s for s in skills if s}

    items = []
    for f in favs:
        if not f:
            continue
        s = skill_map.get(f["skill_id"])
        if s:
            items.append({
                "skill_id": s["id"], "title": s["title"], "price": s["price"],
                "cover_image": s.get("cover_image"), "avg_rating": s.get("avg_rating", 0),
                "tags": s.get("tags") or [],
                "favorited_at": f.get("created_at"),
            })

    return paginated_response(items, total, page, page_size)
