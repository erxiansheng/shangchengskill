from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from app.core.exceptions import AppException, ErrorCode
from app.storage.kv import KVStore

TITLE_INDEXED_STATUSES = {"pending", "approved"}
_APPROVED_AGGREGATE_SHARD_COUNT = 10
_APPROVED_AGGREGATE_SHARD_PREFIX = "skill_listdata_s"
_APPROVED_AGGREGATE_LEGACY_KEY = "skill_approved_listdata"
_TITLE_INDEX_STORAGE_RE = re.compile(r"^skill_title_(approved|pending)_[0-9a-f]{64}$")


def normalize_skill_title(title: str) -> str:
    return (title or "").strip().lower()


def _title_index_key(status: str, title: str) -> str:
    normalized_title = normalize_skill_title(title)
    title_hash = hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()
    return f"skill:title:{status}:{title_hash}"


def _extract_skill_id(raw_value: Any) -> Optional[str]:
    if isinstance(raw_value, dict):
        skill_id = raw_value.get("skill_id") or raw_value.get("id")
        return str(skill_id) if skill_id not in (None, "") else None
    if raw_value in (None, ""):
        return None
    return str(raw_value)


def _same_skill(left: Optional[str | int], right: Optional[str | int]) -> bool:
    if left is None or right is None:
        return False
    return str(left) == str(right)


def _find_duplicate_in_skill_rows(
    skill_rows: list[Any],
    normalized_title: str,
    exclude_skill_id: Optional[str | int] = None,
) -> Optional[str]:
    for skill in skill_rows:
        if not isinstance(skill, dict):
            continue
        skill_id = skill.get("id")
        if skill_id in (None, "") or _same_skill(skill_id, exclude_skill_id):
            continue
        if normalize_skill_title(skill.get("title", "")) == normalized_title:
            return str(skill_id)
    return None


async def set_skill_title_index(kv: KVStore, status: Optional[str], title: str, skill_id: str) -> None:
    if status not in TITLE_INDEXED_STATUSES:
        return
    normalized_title = normalize_skill_title(title)
    if not normalized_title:
        return
    await kv.put(_title_index_key(status, normalized_title), {
        "skill_id": str(skill_id),
        "title": normalized_title,
    })


async def remove_skill_title_index(
    kv: KVStore,
    status: Optional[str],
    title: str,
    skill_id: Optional[str | int] = None,
) -> None:
    if status not in TITLE_INDEXED_STATUSES:
        return
    normalized_title = normalize_skill_title(title)
    if not normalized_title:
        return
    index_key = _title_index_key(status, normalized_title)
    existing = await kv.get(index_key)
    existing_skill_id = _extract_skill_id(existing)
    if skill_id is not None and existing_skill_id and not _same_skill(skill_id, existing_skill_id):
        return
    await kv.delete(index_key)


async def sync_skill_title_index(
    kv: KVStore,
    skill: dict,
    previous_status: Optional[str] = None,
    previous_title: Optional[str] = None,
) -> None:
    current_status = skill.get("status")
    current_title = skill.get("title") or ""
    current_normalized = normalize_skill_title(current_title)
    previous_normalized = normalize_skill_title(previous_title or "")

    if previous_status in TITLE_INDEXED_STATUSES and previous_normalized:
        should_remove_old = (
            previous_status != current_status
            or previous_normalized != current_normalized
            or current_status not in TITLE_INDEXED_STATUSES
        )
        if should_remove_old:
            await remove_skill_title_index(kv, previous_status, previous_normalized, skill.get("id"))

    if current_status in TITLE_INDEXED_STATUSES and current_normalized:
        should_add_current = (
            previous_status not in TITLE_INDEXED_STATUSES
            or previous_status != current_status
            or previous_normalized != current_normalized
        )
        if should_add_current:
            await set_skill_title_index(kv, current_status, current_normalized, str(skill.get("id")))


async def _find_duplicate_in_approved_aggregate(
    kv: KVStore,
    normalized_title: str,
    exclude_skill_id: Optional[str | int] = None,
) -> tuple[Optional[str], bool]:
    shard_keys = [
        f"{_APPROVED_AGGREGATE_SHARD_PREFIX}{index}"
        for index in range(_APPROVED_AGGREGATE_SHARD_COUNT)
    ]
    shard_values = await kv.batch_get(shard_keys, timeout=30)

    aggregate_skills: list[Any] = []
    for shard in shard_values:
        if isinstance(shard, list):
            aggregate_skills.extend(item for item in shard if isinstance(item, dict))

    if not aggregate_skills:
        legacy_payload = await kv.get(_APPROVED_AGGREGATE_LEGACY_KEY)
        if isinstance(legacy_payload, dict):
            aggregate_skills = [
                item for item in (legacy_payload.get("skills") or [])
                if isinstance(item, dict)
            ]

    duplicate_skill_id = _find_duplicate_in_skill_rows(
        aggregate_skills,
        normalized_title,
        exclude_skill_id,
    )
    return duplicate_skill_id, bool(aggregate_skills)


async def _find_duplicate_in_status_list(
    kv: KVStore,
    status: str,
    normalized_title: str,
    exclude_skill_id: Optional[str | int] = None,
    timeout: int = 30,
) -> Optional[str]:
    skill_ids = await kv.get_list(f"skill:by_status:{status}")
    if not skill_ids:
        return None
    skills = await kv.batch_get([f"skill:{skill_id}" for skill_id in skill_ids], timeout=timeout)
    return _find_duplicate_in_skill_rows(skills, normalized_title, exclude_skill_id)


async def find_duplicate_skill_id_by_title(
    kv: KVStore,
    title: str,
    exclude_skill_id: Optional[str | int] = None,
) -> Optional[str]:
    normalized_title = normalize_skill_title(title)
    if not normalized_title:
        return None

    exclude_skill_id_str = str(exclude_skill_id) if exclude_skill_id is not None else None

    for status in TITLE_INDEXED_STATUSES:
        indexed_skill_id = _extract_skill_id(await kv.get(_title_index_key(status, normalized_title)))
        if indexed_skill_id and indexed_skill_id != exclude_skill_id_str:
            return indexed_skill_id

    duplicate_skill_id, aggregate_loaded = await _find_duplicate_in_approved_aggregate(
        kv,
        normalized_title,
        exclude_skill_id_str,
    )
    if duplicate_skill_id:
        return duplicate_skill_id

    pending_duplicate_id = await _find_duplicate_in_status_list(
        kv,
        "pending",
        normalized_title,
        exclude_skill_id_str,
        timeout=30,
    )
    if pending_duplicate_id:
        return pending_duplicate_id

    if not aggregate_loaded:
        return await _find_duplicate_in_status_list(
            kv,
            "approved",
            normalized_title,
            exclude_skill_id_str,
            timeout=60,
        )

    return None


async def assert_skill_title_unique(
    kv: KVStore,
    title: str,
    exclude_skill_id: Optional[str | int] = None,
) -> None:
    duplicate_skill_id = await find_duplicate_skill_id_by_title(kv, title, exclude_skill_id)
    if duplicate_skill_id:
        raise AppException(
            ErrorCode.SKILL_TITLE_DUPLICATE,
            f"技能名称“{title}”已存在，请使用其他名称",
        )


async def rebuild_skill_title_indexes(kv: KVStore) -> dict[str, Any]:
    existing_keys = await kv.list_keys(prefix="skill:title:", timeout=30)
    existing_index_keys = [key for key in existing_keys if _TITLE_INDEX_STORAGE_RE.match(key)]

    for key in existing_index_keys:
        await kv.delete(key)

    pairs: list[dict[str, Any]] = []
    conflicts: dict[tuple[str, str], dict[str, Any]] = {}
    indexed_statuses = {status: 0 for status in sorted(TITLE_INDEXED_STATUSES)}
    scanned_statuses = {status: 0 for status in sorted(TITLE_INDEXED_STATUSES)}
    skipped_empty_title = 0
    skipped_invalid_skills = 0

    for status in sorted(TITLE_INDEXED_STATUSES):
        skill_ids = await kv.get_list(f"skill:by_status:{status}")
        scanned_statuses[status] = len(skill_ids)
        if not skill_ids:
            continue

        skills = await kv.batch_get([f"skill:{skill_id}" for skill_id in skill_ids], timeout=60)
        seen_titles: dict[str, str] = {}

        for skill in skills:
            if not isinstance(skill, dict):
                skipped_invalid_skills += 1
                continue
            skill_id = skill.get("id")
            if skill_id in (None, "") or skill.get("status") != status:
                skipped_invalid_skills += 1
                continue

            normalized_title = normalize_skill_title(skill.get("title", ""))
            if not normalized_title:
                skipped_empty_title += 1
                continue

            skill_id_str = str(skill_id)
            previous_skill_id = seen_titles.get(normalized_title)
            if previous_skill_id and previous_skill_id != skill_id_str:
                conflict_key = (status, normalized_title)
                conflict = conflicts.get(conflict_key)
                if not conflict:
                    conflict = {
                        "status": status,
                        "title": skill.get("title") or normalized_title,
                        "skill_ids": [previous_skill_id],
                    }
                    conflicts[conflict_key] = conflict
                if skill_id_str not in conflict["skill_ids"]:
                    conflict["skill_ids"].append(skill_id_str)
                continue

            seen_titles[normalized_title] = skill_id_str
            pairs.append({
                "key": _title_index_key(status, normalized_title),
                "value": {
                    "skill_id": skill_id_str,
                    "title": normalized_title,
                },
            })
            indexed_statuses[status] += 1

    if pairs:
        await kv.bulk_put(pairs)

    conflict_list = sorted(
        conflicts.values(),
        key=lambda item: (item["status"], item["title"]),
    )

    return {
        "deleted_index_keys": len(existing_index_keys),
        "rebuilt_indexes": len(pairs),
        "scanned_statuses": scanned_statuses,
        "indexed_statuses": indexed_statuses,
        "skipped_empty_title": skipped_empty_title,
        "skipped_invalid_skills": skipped_invalid_skills,
        "conflict_count": len(conflict_list),
        "conflicts": conflict_list[:20],
    }