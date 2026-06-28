"""
auto_content.py — Auto-Pilot Content Engine.

Schedules and runs:
  • Daily lesson generation (10am UTC) — generates 1 new lesson for the next-in-queue
    topic and either auto-publishes (if quality grade >= 7) or stashes as draft.
  • Monday full-path generation (10am UTC) — generates 1 complete learning path
    (3 modules × 3 lessons each).
  • Daily digest email (11am UTC) — summarizes what published yesterday.

Runtime model:
  - APScheduler in-process AsyncIOScheduler. Starts on FastAPI app startup.
  - All jobs are idempotent and safe to re-run manually.
  - Pause switch read from `system_settings.auto_content_paused`.

Quality gate:
  - After draft is produced, Claude 4.5 grades it on (accuracy, clarity, brand fit, depth)
    on 1-10. If any score < 7, drop to draft + flag for human review. Else auto-publish.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from emergentintegrations.llm.chat import LlmChat, UserMessage

import ai_studio
import curriculum_db as cdb
from ai_studio import _parse_json_block, _get_key, _slug  # type: ignore

log = logging.getLogger("auto_content")


# ─── Settings ──────────────────────────────────────────────────────────────
QUALITY_THRESHOLD = 7
SCHEDULE_TZ = "UTC"
DAILY_LESSON_HOUR = 10
MONDAY_PATH_HOUR = 10
DAILY_DIGEST_HOUR = 11

GRADER_SYSTEM = (
    "You are Ascendra's senior editor. Grade the following AI-generated lesson "
    "or path on 4 dimensions, 1-10 each. Output STRICT JSON only:\n"
    "{\n"
    '  "accuracy": <int 1-10, factual correctness on current AI tools/models>,\n'
    '  "clarity": <int 1-10, readability and structure>,\n'
    '  "brand_fit": <int 1-10, warm-expert tone, no corporate jargon, no fake stats>,\n'
    '  "depth": <int 1-10, substantive content vs filler>,\n'
    '  "notes": "<one short sentence on biggest weakness, max 140 chars>"\n'
    "}\n"
    "Be strict. A 7 means 'good enough to publish' — most drafts should land 5-7. "
    "Penalize: hallucinated stats, fake testimonials, generic advice, corporate jargon."
)


# ─── Topic queue ───────────────────────────────────────────────────────────
DEFAULT_QUEUE: list[dict] = [
    # 28 starter topics — one per day, ~4 weeks of daily content.
    {"topic": "Prompt engineering basics for non-engineers",                     "kind": "lesson", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Using GPT-5.2 for daily email triage and reply drafting",         "kind": "lesson", "level": "Beginner",     "model_hint": "GPT-5.2"},
    {"topic": "How to write prompts Gemini 3 actually understands",              "kind": "lesson", "level": "Beginner",     "model_hint": "Gemini 3"},
    {"topic": "Generating cover art that doesn't look 'AI' with Nano Banana",    "kind": "lesson", "level": "Beginner",     "model_hint": "Nano Banana"},
    {"topic": "Turning a screenplay outline into a Sora 2 storyboard",           "kind": "lesson", "level": "Intermediate", "model_hint": "Sora 2"},
    {"topic": "Cloning your own voice with ElevenLabs for content creation",    "kind": "lesson", "level": "Intermediate", "model_hint": "ElevenLabs"},
    {"topic": "AI-powered competitive research with Perplexity in 10 minutes",  "kind": "lesson", "level": "Beginner",     "model_hint": "Perplexity"},
    {"topic": "Designing storyboard frames with Midjourney for marketers",      "kind": "lesson", "level": "Intermediate", "model_hint": "Midjourney"},
    {"topic": "Building product explainer videos with Veo 3",                    "kind": "lesson", "level": "Intermediate", "model_hint": "Veo 3"},
    {"topic": "Transcribing podcasts and turning them into blog posts (Whisper + Claude)", "kind": "lesson", "level": "Beginner", "model_hint": "Whisper"},
    {"topic": "Using Cursor to ship features 10x faster as a solo founder",     "kind": "lesson", "level": "Intermediate", "model_hint": "Cursor"},
    {"topic": "Suno: writing ad jingles for your brand in under an hour",       "kind": "lesson", "level": "Beginner",     "model_hint": "Suno"},
    {"topic": "Prompt chaining patterns: when and why",                          "kind": "lesson", "level": "Intermediate", "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Building a custom GPT for customer support",                      "kind": "lesson", "level": "Intermediate", "model_hint": "GPT-5.2"},
    {"topic": "Long-form content generation: avoiding 'AI mush'",                "kind": "lesson", "level": "Intermediate", "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Multi-modal prompting: text + image + audio in one workflow",     "kind": "lesson", "level": "Advanced",     "model_hint": "Gemini 3"},
    {"topic": "AI-assisted UX research: synthesizing 30 user interviews",        "kind": "lesson", "level": "Intermediate", "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Cold email writing that doesn't sound like a robot",              "kind": "lesson", "level": "Beginner",     "model_hint": "GPT-5.2"},
    {"topic": "SEO content briefs with AI: from keyword to outline in 5 min",   "kind": "lesson", "level": "Intermediate", "model_hint": "Claude Sonnet 4.5"},
    {"topic": "AI for solo founders: the 5-hour workweek stack",                 "kind": "lesson", "level": "Beginner",     "model_hint": "GPT-5.2"},
    {"topic": "Edge AI: running models on your phone for offline use",           "kind": "lesson", "level": "Intermediate", "model_hint": "Nano Banana"},
    {"topic": "Negotiating with AI: practicing hard conversations safely",       "kind": "lesson", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Voice-first interfaces: when to use them vs avoid them",          "kind": "lesson", "level": "Intermediate", "model_hint": "ElevenLabs"},
    {"topic": "AI ethics for builders: bias, attribution, transparency",         "kind": "lesson", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5"},
    {"topic": "Storyboarding TikTok ads with Sora 2 + ElevenLabs",               "kind": "lesson", "level": "Intermediate", "model_hint": "Sora 2"},
    {"topic": "Personal AI dashboards: building your own assistant in a day",   "kind": "lesson", "level": "Advanced",     "model_hint": "GPT-5.2"},
    {"topic": "AI in spreadsheets: the patterns that actually save hours",       "kind": "lesson", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5"},
    {"topic": "What to do when the AI is confidently wrong",                     "kind": "lesson", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5"},
    # Monday "course" topics (full paths)
    {"topic": "Prompt Engineering Mastery: from novice to power user",           "kind": "path", "level": "Beginner",     "model_hint": "Claude Sonnet 4.5", "tier": "pathfinder"},
    {"topic": "AI Video Production for Marketers: Sora 2 + Veo 3 deep dive",     "kind": "path", "level": "Intermediate", "model_hint": "Sora 2",            "tier": "pathfinder"},
    {"topic": "AI Sales Engine: outbound, follow-up, and closing with GPT-5.2", "kind": "path", "level": "Intermediate", "model_hint": "GPT-5.2",          "tier": "sage"},
    {"topic": "Build Your Own AI Agent: orchestration patterns that ship",       "kind": "path", "level": "Advanced",     "model_hint": "Claude Sonnet 4.5", "tier": "sage"},
]


# ─── DB helpers ────────────────────────────────────────────────────────────
async def _settings_col(db):
    return db["system_settings"]


async def _queue_col(db):
    return db["content_queue"]


async def _runs_col(db):
    return db["auto_content_runs"]


async def get_settings(db) -> dict:
    col = await _settings_col(db)
    s = await col.find_one({"id": "auto_content"}, {"_id": 0})
    if not s:
        s = {
            "id": "auto_content",
            "paused": False,
            "auto_publish": True,
            "quality_threshold": QUALITY_THRESHOLD,
            "target_path_id": None,  # if set, daily lessons get added to this path
            "target_module_id": None,
            "updated_at": datetime.now(timezone.utc),
        }
        await col.insert_one(dict(s))
    return s


async def update_settings(db, patch: dict) -> dict:
    col = await _settings_col(db)
    patch["updated_at"] = datetime.now(timezone.utc)
    await col.update_one({"id": "auto_content"}, {"$set": patch}, upsert=True)
    return await get_settings(db)


async def seed_default_queue(db) -> int:
    col = await _queue_col(db)
    if await col.count_documents({}) > 0:
        return 0
    now = datetime.now(timezone.utc)
    docs = []
    for i, item in enumerate(DEFAULT_QUEUE):
        docs.append({
            "id": str(uuid.uuid4()),
            "topic": item["topic"],
            "kind": item.get("kind", "lesson"),
            "level": item.get("level", "Beginner"),
            "model_hint": item.get("model_hint"),
            "tier": item.get("tier"),
            "status": "pending",
            "priority": i,
            "created_at": now,
        })
    if docs:
        await col.insert_many(docs)
    return len(docs)


async def list_queue(db, *, status: Optional[str] = None, limit: int = 500) -> list:
    col = await _queue_col(db)
    q: dict = {}
    if status:
        q["status"] = status
    cur = col.find(q, {"_id": 0}).sort([("status", 1), ("priority", 1), ("created_at", 1)]).limit(limit)
    return await cur.to_list(limit)


async def next_queued(db, kind: str) -> Optional[dict]:
    col = await _queue_col(db)
    return await col.find_one(
        {"status": "pending", "kind": kind},
        {"_id": 0},
        sort=[("priority", 1), ("created_at", 1)],
    )


async def mark_queue_status(db, queue_id: str, status: str, **extra) -> None:
    col = await _queue_col(db)
    update = {"status": status, "updated_at": datetime.now(timezone.utc), **extra}
    await col.update_one({"id": queue_id}, {"$set": update})


async def add_queue_item(db, item: dict) -> dict:
    col = await _queue_col(db)
    doc = {
        "id": str(uuid.uuid4()),
        "topic": item["topic"],
        "kind": item.get("kind", "lesson"),
        "level": item.get("level", "Beginner"),
        "model_hint": item.get("model_hint"),
        "tier": item.get("tier"),
        "status": "pending",
        "priority": int(item.get("priority", 9999)),
        "created_at": datetime.now(timezone.utc),
    }
    await col.insert_one(dict(doc))
    return doc


async def remove_queue_item(db, queue_id: str) -> bool:
    col = await _queue_col(db)
    r = await col.delete_one({"id": queue_id})
    return r.deleted_count > 0


# ─── Run log ───────────────────────────────────────────────────────────────
async def log_run(db, *, kind: str, status: str, summary: dict) -> str:
    col = await _runs_col(db)
    run_id = str(uuid.uuid4())
    doc = {
        "id": run_id,
        "kind": kind,        # "daily_lesson" | "monday_path" | "manual"
        "status": status,    # "published" | "drafted" | "skipped" | "failed"
        "summary": summary,
        "created_at": datetime.now(timezone.utc),
    }
    await col.insert_one(doc)
    return run_id


async def list_runs(db, limit: int = 50) -> list:
    col = await _runs_col(db)
    cur = col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cur.to_list(limit)


# ─── Quality gate ──────────────────────────────────────────────────────────
async def grade_draft(text: str, kind: str = "lesson") -> dict:
    chat = LlmChat(
        api_key=_get_key(),
        session_id=f"grade-{uuid.uuid4().hex[:8]}",
        system_message=GRADER_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    user_msg = f"Type: {kind}\n\n{text[:6000]}"
    raw = await chat.send_message(UserMessage(text=user_msg))
    return _parse_json_block(raw)


def _is_passing(grades: dict, threshold: int = QUALITY_THRESHOLD) -> bool:
    return all(int(grades.get(k, 0)) >= threshold for k in ("accuracy", "clarity", "brand_fit", "depth"))


def _summarize_lesson_for_grading(draft: dict) -> str:
    bits = [f"Title: {draft.get('title')}"]
    for card in draft.get("cards", []):
        bits.append(f"--- {card.get('title','')}\n{card.get('body','')}")
    q = draft.get("quiz", {})
    if q.get("question"):
        bits.append(f"\nQUIZ: {q.get('question')}")
    return "\n\n".join(bits)


def _summarize_path_for_grading(path: dict, lessons_inline: list[dict] | None = None) -> str:
    bits = [f"Path: {path.get('title')}", f"Tagline: {path.get('tagline','')}"]
    for m in path.get("modules", []):
        bits.append(f"\nModule: {m.get('title')}")
        for l in m.get("lessons", []):
            bits.append(f"  - {l.get('title')}")
    if lessons_inline:
        for lsn in lessons_inline[:3]:
            bits.append(f"\nLesson Sample: {lsn.get('title')}")
            for card in lsn.get("cards", [])[:2]:
                bits.append(f"  · {card.get('title','')} — {card.get('body','')[:200]}")
    return "\n".join(bits)


# ─── Job implementations ───────────────────────────────────────────────────
async def _ensure_target_path(db) -> tuple[str, str]:
    """Find or create a target path/module where daily lessons get added."""
    s = await get_settings(db)
    if s.get("target_path_id") and s.get("target_module_id"):
        p = await cdb.get_path(db, s["target_path_id"])
        if p and any(m["id"] == s["target_module_id"] for m in p.get("modules", [])):
            return s["target_path_id"], s["target_module_id"]
    # Create the dump path
    outline = {
        "id": "daily-drops",
        "title": "Daily Drops",
        "tagline": "Fresh AI lessons, every weekday.",
        "tier": "free",
        "color": "#FFB000",
        "image": None,
        "source": "auto-pilot",
        "modules": [
            {"id": "drops-recent", "title": "Recent Drops", "lessons": []},
        ],
    }
    created = await cdb.create_path(db, outline)
    await update_settings(db, {"target_path_id": created["id"], "target_module_id": "drops-recent"})
    return created["id"], "drops-recent"


async def run_daily_lesson(db, *, source: str = "scheduler") -> dict:
    """Generate the next-in-queue lesson, grade it, publish or stash."""
    s = await get_settings(db)
    if s.get("paused"):
        rid = await log_run(db, kind="daily_lesson", status="skipped", summary={"reason": "paused"})
        return {"status": "skipped", "reason": "paused", "run_id": rid}
    item = await next_queued(db, kind="lesson")
    if not item:
        rid = await log_run(db, kind="daily_lesson", status="skipped", summary={"reason": "queue_empty"})
        return {"status": "skipped", "reason": "queue_empty", "run_id": rid}
    try:
        draft = await ai_studio.generate_lesson_draft(
            topic=item["topic"],
            level=item.get("level") or "Beginner",
        )
        text_for_grading = _summarize_lesson_for_grading(draft)
        grades = await grade_draft(text_for_grading, kind="lesson")
        passing = _is_passing(grades, s.get("quality_threshold", QUALITY_THRESHOLD))
        target_path_id, target_module_id = await _ensure_target_path(db)
        draft["source"] = "auto-pilot"
        published = None
        if passing and s.get("auto_publish", True):
            published = await cdb.add_lesson(db, target_path_id, target_module_id, draft)
            await mark_queue_status(db, item["id"], "published",
                                     lesson_id=(published.get("id") if published else None),
                                     path_id=target_path_id, grades=grades)
            status = "published"
            # Inline interactive-card generation: convert the brand new text-only
            # lesson into one with knowledge_check + fill_blank + playground cards.
            # Best-effort: if it fails, the hourly background sweep will pick it up.
            if published and published.get("id"):
                try:
                    await _interactivize_one(db, published["id"], path_id=target_path_id,
                                              module_id=target_module_id)
                except Exception as e:
                    log.warning(f"inline interactivize failed for {published['id']}: {e}")
        else:
            await mark_queue_status(db, item["id"], "needs_review", grades=grades, draft=draft)
            status = "drafted"
        rid = await log_run(db, kind="daily_lesson", status=status, summary={
            "topic": item["topic"], "lesson_id": (published or {}).get("id"),
            "path_id": target_path_id, "module_id": target_module_id,
            "grades": grades, "source": source,
        })
        return {"status": status, "topic": item["topic"], "grades": grades, "run_id": rid,
                "lesson_id": (published or {}).get("id")}
    except Exception as e:
        log.exception("daily lesson failed")
        await mark_queue_status(db, item["id"], "failed", error=str(e)[:200])
        rid = await log_run(db, kind="daily_lesson", status="failed", summary={"topic": item["topic"], "error": str(e)[:300]})
        return {"status": "failed", "error": str(e)[:200], "run_id": rid}


async def run_monday_path(db, *, source: str = "scheduler") -> dict:
    """Generate a full path. Idempotent — checks if already ran today."""
    s = await get_settings(db)
    if s.get("paused"):
        rid = await log_run(db, kind="monday_path", status="skipped", summary={"reason": "paused"})
        return {"status": "skipped", "reason": "paused", "run_id": rid}
    # Dedup: don't run twice in same UTC day
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    col = await _runs_col(db)
    if await col.count_documents({"kind": "monday_path", "status": {"$in": ["published", "drafted"]}, "created_at": {"$gte": today_start}}):
        rid = await log_run(db, kind="monday_path", status="skipped", summary={"reason": "already_ran_today"})
        return {"status": "skipped", "reason": "already_ran_today", "run_id": rid}
    item = await next_queued(db, kind="path")
    if not item:
        rid = await log_run(db, kind="monday_path", status="skipped", summary={"reason": "queue_empty"})
        return {"status": "skipped", "reason": "queue_empty", "run_id": rid}
    try:
        outline = await ai_studio.generate_path_outline(item["topic"], item.get("level") or "Beginner")
        outline["tier"] = item.get("tier") or "pathfinder"
        outline["source"] = "auto-pilot"
        # Generate cover
        try:
            outline["image"] = await ai_studio.generate_cover_image(outline["title"], outline.get("id"))
        except Exception as e:
            log.warning(f"cover gen failed: {e}")
        created = await cdb.create_path(db, outline)
        # Fill in first 3 lessons (cheap sampler so the grader has something to grade)
        sampled_lessons: list[dict] = []
        for m in created["modules"]:
            for lsn in m.get("lessons", []):
                try:
                    full = await ai_studio.generate_lesson_draft(
                        lsn["title"], item.get("level") or "Beginner",
                        path_context=f"{created['title']} — {created.get('tagline','')}",
                    )
                    full["id"] = lsn["id"]
                    full["title"] = lsn["title"]
                    full["source"] = "auto-pilot"
                    full["created_at"] = datetime.now(timezone.utc)
                    await cdb.update_lesson(db, created["id"], m["id"], lsn["id"], full)
                    sampled_lessons.append(full)
                except Exception as e:
                    log.warning(f"per-lesson gen failed for {lsn.get('id')}: {e}")
                if len(sampled_lessons) >= 3:
                    break
            if len(sampled_lessons) >= 3:
                break
        # Grade
        text_for_grading = _summarize_path_for_grading(created, sampled_lessons)
        grades = await grade_draft(text_for_grading, kind="path")
        passing = _is_passing(grades, s.get("quality_threshold", QUALITY_THRESHOLD))
        if passing and s.get("auto_publish", True):
            await mark_queue_status(db, item["id"], "published", path_id=created["id"], grades=grades)
            status = "published"
            # Inline interactive-card generation for all sampled lessons of the new path.
            # Hourly sweep will catch any others (later-generated lessons in the path).
            for sl in sampled_lessons:
                lid = sl.get("id")
                if not lid:
                    continue
                try:
                    await _interactivize_one(db, lid, path_id=created["id"])
                except Exception as e:
                    log.warning(f"inline interactivize (path lesson) failed for {lid}: {e}")
        else:
            await mark_queue_status(db, item["id"], "needs_review", path_id=created["id"], grades=grades)
            status = "drafted"
        rid = await log_run(db, kind="monday_path", status=status, summary={
            "topic": item["topic"], "path_id": created["id"], "grades": grades, "source": source,
        })
        return {"status": status, "topic": item["topic"], "path_id": created["id"], "grades": grades, "run_id": rid}
    except Exception as e:
        log.exception("monday path failed")
        await mark_queue_status(db, item["id"], "failed", error=str(e)[:200])
        rid = await log_run(db, kind="monday_path", status="failed", summary={"topic": item["topic"], "error": str(e)[:300]})
        return {"status": "failed", "error": str(e)[:200], "run_id": rid}


async def _interactivize_one(db, lesson_id: str, *, path_id: Optional[str] = None,
                              module_id: Optional[str] = None) -> bool:
    """Generate + apply interactive cards for a single lesson, in-place in the DB.
    Returns True on success. Best-effort — caller catches exceptions.
    """
    # Lazy-import to avoid circular imports & keep startup fast
    from interactive_generator import generate_and_apply
    # Locate the lesson document (with path/module context for the generator)
    q = {"modules.lessons.id": lesson_id}
    if path_id:
        q["id"] = path_id
    p = await db["curriculum_paths"].find_one(q, {"_id": 0})
    if not p:
        return False
    for m in p.get("modules", []):
        if module_id and m.get("id") != module_id:
            continue
        for lsn in m.get("lessons", []):
            if lsn.get("id") != lesson_id:
                continue
            if int(lsn.get("interactive_v") or 0) >= 1:
                return True   # already done
            enriched = {
                **lsn,
                "path_title": p.get("title", ""),
                "path_id": p.get("id", ""),
                "module_title": m.get("title", ""),
                "module_id": m.get("id", ""),
            }
            new_lsn = await generate_and_apply(enriched)
            if not new_lsn:
                return False
            # Strip injected context fields before writing back
            clean = {k: v for k, v in new_lsn.items()
                     if k not in ("path_title", "path_id", "module_title", "module_id")}
            await db["curriculum_paths"].update_one(
                {"id": p["id"], "modules.id": m["id"], "modules.lessons.id": lesson_id},
                {"$set": {"modules.$[mm].lessons.$[ll]": clean}},
                array_filters=[{"mm.id": m["id"]}, {"ll.id": lesson_id}],
            )
            return True
    return False


async def run_interactive_sweep(db) -> dict:
    """Sweep the curriculum for any lesson lacking interactive_v >= 1 and upgrade it.
    Safety-net for new lessons created via admin UI, AI Studio, or auto-pilot.
    Sequential (concurrency 1) to stay within LLM rate limits.
    """
    from interactive_generator import upgrade_all_lessons
    try:
        result = await upgrade_all_lessons(db, force=False, concurrency=1)
        log.info(f"interactive sweep: upgraded={len(result.get('upgraded', []))}, "
                 f"failed={len(result.get('failed', []))}, "
                 f"skipped={len(result.get('skipped', []))}")
        return result
    except Exception as e:
        log.exception(f"interactive sweep failed: {e}")
        return {"upgraded": [], "failed": [], "skipped": [], "total_attempted": 0, "error": str(e)[:200]}


async def send_daily_digest(db, *, admin_email: Optional[str] = None) -> dict:
    """Email a summary of what the auto-pilot did in the last 24h."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    col = await _runs_col(db)
    cur = col.find({"created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1)
    runs = await cur.to_list(100)
    if not runs:
        return {"ok": True, "skipped": True, "reason": "no_runs"}
    pub = [r for r in runs if r["status"] == "published"]
    drafted = [r for r in runs if r["status"] == "drafted"]
    failed = [r for r in runs if r["status"] == "failed"]
    # Resolve admin email
    if not admin_email:
        u = await db["users"].find_one({"is_admin": True}, {"_id": 0, "email": 1})
        admin_email = (u or {}).get("email")
    if not admin_email:
        return {"ok": False, "reason": "no_admin"}
    try:
        from email_service import send_digest
        return send_digest(to=admin_email, published=pub, drafted=drafted, failed=failed)
    except Exception as e:
        log.exception("digest send failed")
        return {"ok": False, "reason": "send_exception", "error": str(e)[:160]}


# ─── Scheduler bootstrap ───────────────────────────────────────────────────
_scheduler: Optional[AsyncIOScheduler] = None


def start_scheduler(db) -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    sched = AsyncIOScheduler(timezone=SCHEDULE_TZ)

    sched.add_job(
        run_daily_lesson, args=[db],
        trigger=CronTrigger(hour=DAILY_LESSON_HOUR, minute=0, timezone=SCHEDULE_TZ),
        id="daily_lesson", replace_existing=True,
    )
    sched.add_job(
        run_monday_path, args=[db],
        trigger=CronTrigger(day_of_week="mon", hour=MONDAY_PATH_HOUR, minute=0, timezone=SCHEDULE_TZ),
        id="monday_path", replace_existing=True,
    )
    sched.add_job(
        send_daily_digest, args=[db],
        trigger=CronTrigger(hour=DAILY_DIGEST_HOUR, minute=0, timezone=SCHEDULE_TZ),
        id="daily_digest", replace_existing=True,
    )
    # Hourly safety-net sweep: catch any lesson created via any path that
    # doesn't yet have interactive cards. Idempotent — skips already-upgraded.
    sched.add_job(
        run_interactive_sweep, args=[db],
        trigger=CronTrigger(minute=15, timezone=SCHEDULE_TZ),  # every hour at :15
        id="interactive_sweep", replace_existing=True,
    )

    sched.start()
    _scheduler = sched
    log.info(f"auto-content scheduler started (TZ={SCHEDULE_TZ}, daily_lesson=10:00, monday_path=Mon 10:00, digest=11:00)")
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("auto-content scheduler stopped")
    _scheduler = None


def next_run_times() -> dict:
    if not _scheduler:
        return {}
    out: dict = {}
    for job in _scheduler.get_jobs():
        nxt = getattr(job, "next_run_time", None)
        out[job.id] = nxt.isoformat() if nxt else None
    return out
