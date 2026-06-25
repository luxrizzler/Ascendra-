"""
Curriculum DB layer.
- On first boot (collection empty), seeds from curriculum.py PATHS.
- All reads/writes flow through MongoDB.
- Preserves the same shape used by server.py (path/module/lesson dicts).
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

# Import the static seed
from curriculum import PATHS as SEED_PATHS, AI_MODELS  # noqa: F401  (AI_MODELS re-exported)


PATHS_COLL = "curriculum_paths"


def _norm_path(p: dict) -> dict:
    """Strip Mongo _id and ensure required fields are present."""
    p = {k: v for k, v in p.items() if k != "_id"}
    p.setdefault("tier", "free")
    p.setdefault("modules", [])
    return p


async def ensure_seeded(db: AsyncIOMotorDatabase) -> None:
    coll = db[PATHS_COLL]
    count = await coll.count_documents({})
    if count == 0:
        # Seed from the static file
        docs = []
        for idx, p in enumerate(SEED_PATHS):
            d = dict(p)
            d["order"] = idx
            d["created_at"] = datetime.now(timezone.utc)
            d["updated_at"] = datetime.now(timezone.utc)
            d["source"] = "seed"
            docs.append(d)
        if docs:
            await coll.insert_many(docs)
    # Indexes
    await coll.create_index("id", unique=True)
    await coll.create_index("order")


# ─── Reads ──────────────────────────────────────────────────────────────────
async def list_paths(db) -> List[dict]:
    cur = db[PATHS_COLL].find({}, {"_id": 0}).sort("order", 1)
    return [_norm_path(p) for p in await cur.to_list(500)]


async def get_path(db, path_id: str) -> Optional[dict]:
    p = await db[PATHS_COLL].find_one({"id": path_id}, {"_id": 0})
    return _norm_path(p) if p else None


async def get_lesson(db, lesson_id: str) -> Optional[dict]:
    """Find a lesson + its path/module context. Mirrors the file-based helper."""
    paths = await list_paths(db)
    for p in paths:
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                if lsn["id"] == lesson_id:
                    return {
                        **lsn,
                        "path_id": p["id"],
                        "path_title": p["title"],
                        "path_color": p["color"],
                        "path_tier": p.get("tier", "free"),
                        "module_id": m["id"],
                        "module_title": m["title"],
                    }
    return None


def path_summary(p: dict) -> dict:
    total_lessons = sum(len(m.get("lessons", [])) for m in p.get("modules", []))
    total_xp = sum(lsn.get("xp", 0) for m in p.get("modules", []) for lsn in m.get("lessons", []))
    return {
        "id": p["id"],
        "title": p["title"],
        "subtitle": p.get("subtitle", ""),
        "tagline": p.get("tagline", ""),
        "color": p.get("color", "#FFB000"),
        "level": p.get("level", "Beginner"),
        "duration": p.get("duration", ""),
        "image": p.get("image", ""),
        "tier": p.get("tier", "free"),
        "total_lessons": total_lessons,
        "total_xp": total_xp,
    }


def can_access(user_tier: str, path_tier: str) -> bool:
    rank = {"free": 0, "ascender": 1, "pathfinder": 2, "sage": 3}
    return rank.get(user_tier, 0) >= rank.get(path_tier, 0)


# ─── Writes ─────────────────────────────────────────────────────────────────
async def create_path(db, payload: dict) -> dict:
    pid = payload.get("id") or _slug(payload["title"])
    # ensure unique
    existing = await db[PATHS_COLL].find_one({"id": pid})
    if existing:
        pid = f"{pid}-{uuid.uuid4().hex[:4]}"
    last = await db[PATHS_COLL].find_one({}, sort=[("order", -1)])
    order = (last["order"] + 1) if last else 0
    doc = {
        "id": pid,
        "title": payload["title"],
        "subtitle": payload.get("subtitle", ""),
        "tagline": payload.get("tagline", ""),
        "color": payload.get("color", "#FFB000"),
        "level": payload.get("level", "Beginner"),
        "duration": payload.get("duration", "~2 hours"),
        "image": payload.get("image", "https://images.pexels.com/photos/12623752/pexels-photo-12623752.jpeg"),
        "tier": payload.get("tier", "free"),
        "modules": payload.get("modules", []),
        "order": order,
        "source": payload.get("source", "manual"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db[PATHS_COLL].insert_one(dict(doc))
    return _norm_path(doc)


async def update_path(db, path_id: str, patch: dict) -> Optional[dict]:
    allowed = {"title", "subtitle", "tagline", "color", "level", "duration", "image", "tier", "modules", "order"}
    update = {k: v for k, v in patch.items() if k in allowed}
    if not update:
        return await get_path(db, path_id)
    update["updated_at"] = datetime.now(timezone.utc)
    res = await db[PATHS_COLL].update_one({"id": path_id}, {"$set": update})
    if res.matched_count == 0:
        return None
    return await get_path(db, path_id)


async def delete_path(db, path_id: str) -> bool:
    res = await db[PATHS_COLL].delete_one({"id": path_id})
    return res.deleted_count > 0


async def add_module(db, path_id: str, module: dict) -> Optional[dict]:
    mid = module.get("id") or _slug(module["title"])
    p = await get_path(db, path_id)
    if not p:
        return None
    used = {m["id"] for m in p["modules"]}
    if mid in used:
        mid = f"{mid}-{uuid.uuid4().hex[:4]}"
    new_module = {"id": mid, "title": module["title"], "lessons": module.get("lessons", [])}
    p["modules"].append(new_module)
    await update_path(db, path_id, {"modules": p["modules"]})
    return new_module


async def update_module(db, path_id: str, module_id: str, patch: dict) -> Optional[dict]:
    p = await get_path(db, path_id)
    if not p:
        return None
    for i, m in enumerate(p["modules"]):
        if m["id"] == module_id:
            if "title" in patch:
                m["title"] = patch["title"]
            if "lessons" in patch:
                m["lessons"] = patch["lessons"]
            p["modules"][i] = m
            await update_path(db, path_id, {"modules": p["modules"]})
            return m
    return None


async def delete_module(db, path_id: str, module_id: str) -> bool:
    p = await get_path(db, path_id)
    if not p:
        return False
    new_modules = [m for m in p["modules"] if m["id"] != module_id]
    if len(new_modules) == len(p["modules"]):
        return False
    await update_path(db, path_id, {"modules": new_modules})
    return True


async def add_lesson(db, path_id: str, module_id: str, lesson: dict) -> Optional[dict]:
    p = await get_path(db, path_id)
    if not p:
        return None
    used = {lsn["id"] for m in p["modules"] for lsn in m.get("lessons", [])}
    lid = lesson.get("id") or _slug(lesson["title"])
    if lid in used:
        lid = f"{lid}-{uuid.uuid4().hex[:4]}"
    new_lesson = {
        "id": lid,
        "title": lesson["title"],
        "duration_min": int(lesson.get("duration_min", 5)),
        "xp": int(lesson.get("xp", 50)),
        "cards": lesson.get("cards", []),
        "quiz": lesson.get("quiz") or {"question": "", "options": [], "answer_index": 0, "explanation": ""},
        "source": lesson.get("source", "manual"),
        "created_at": datetime.now(timezone.utc),
    }
    for i, m in enumerate(p["modules"]):
        if m["id"] == module_id:
            m.setdefault("lessons", []).append(new_lesson)
            p["modules"][i] = m
            await update_path(db, path_id, {"modules": p["modules"]})
            return new_lesson
    return None


async def update_lesson(db, path_id: str, module_id: str, lesson_id: str, patch: dict) -> Optional[dict]:
    p = await get_path(db, path_id)
    if not p:
        return None
    for i, m in enumerate(p["modules"]):
        if m["id"] != module_id:
            continue
        for j, lsn in enumerate(m.get("lessons", [])):
            if lsn["id"] != lesson_id:
                continue
            for k in ("title", "duration_min", "xp", "cards", "quiz", "source", "created_at"):
                if k in patch:
                    lsn[k] = patch[k]
            m["lessons"][j] = lsn
            p["modules"][i] = m
            await update_path(db, path_id, {"modules": p["modules"]})
            return lsn
    return None


async def delete_lesson(db, path_id: str, module_id: str, lesson_id: str) -> bool:
    p = await get_path(db, path_id)
    if not p:
        return False
    changed = False
    for i, m in enumerate(p["modules"]):
        if m["id"] != module_id:
            continue
        before = len(m.get("lessons", []))
        m["lessons"] = [l for l in m.get("lessons", []) if l["id"] != lesson_id]
        if len(m["lessons"]) < before:
            p["modules"][i] = m
            changed = True
    if changed:
        await update_path(db, path_id, {"modules": p["modules"]})
    return changed


def _slug(text: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s[:48] or f"id-{uuid.uuid4().hex[:8]}"
