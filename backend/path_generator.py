"""
path_generator.py — User-Generated Learning Paths.

Given a user's free-text goal, builds a multi-level path with 3 modules
(Beginner / Intermediate / Advanced) and 5-7 lessons each (~15-21 total).

Two-stage flow:
  1. STAGE 1 — outline (fast, 1 Claude call):
       Path title + tagline + cover color + 3 modules × 5-7 lesson titles.
       This is what the user sees immediately after clicking "Generate".
  2. STAGE 2 — fill content (background, slower, N Claude calls):
       Generate full lesson body + interactive cards for each lesson
       in a controlled-concurrency loop. Front-end can poll for completion.
       Failures are tolerated — the existing `interactive_sweep` cron will
       pick up any lessons that still have empty `cards`.

Design choices:
- Submission is paid-only (enforced in the route, not here).
- The path is created with `visibility="pending_review"` and
  `admin_review_status="pending"` so admin can approve/reject.
- The creator can immediately start taking it (tier_gate uses `created_by`).
- Lessons can be taken in any order — there's no required sequence on the path.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
import json
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_studio import _get_key, _parse_json_block, _slug, generate_lesson_draft

log = logging.getLogger("ascendra.path_generator")


USER_PATH_SYSTEM = (
    "You are Ascendra, the AI learning architect. The user has described a goal "
    "they want to achieve with AI. You will design a complete, multi-level "
    "learning path that takes them from total novice to confident practitioner.\n\n"
    "OUTPUT VALID JSON ONLY (no prose). Shape:\n"
    "{\n"
    '  "title": "Concise, exciting path title (5-9 words)",\n'
    '  "tagline": "1-line value proposition (max 100 chars)",\n'
    '  "color": "#FFB000 | #FF6B35 | #BFB4FF | #7C3AED | #E8C572 | #34D399 | #FB7185 | #38BDF8",\n'
    '  "duration": "~6 hours" (estimate based on lesson count),\n'
    '  "modules": [\n'
    '    {\n'
    '      "title": "Foundations — Beginner",\n'
    '      "level": "Beginner",\n'
    '      "lessons": [\n'
    '        {"title": "Concise 4-7 word lesson title", "duration_min": 5},\n'
    '        ... (5-7 beginner lessons)\n'
    '      ]\n'
    '    },\n'
    '    {\n'
    '      "title": "Building — Intermediate",\n'
    '      "level": "Intermediate",\n'
    '      "lessons": [ 5-7 intermediate lessons ]\n'
    '    },\n'
    '    {\n'
    '      "title": "Shipping — Advanced",\n'
    '      "level": "Advanced",\n'
    '      "lessons": [ 5-7 advanced lessons ]\n'
    '    }\n'
    '  ]\n'
    "}\n\n"
    "RULES:\n"
    "- EXACTLY 3 modules in this order: Beginner, Intermediate, Advanced.\n"
    "- 5-7 lessons per module (15-21 total). Bias toward 6.\n"
    "- Lesson titles are short, vivid, action-oriented. NO generic filler like "
    '"Introduction to X" or "Conclusion".\n'
    "- Lessons within a module should read as a coherent arc.\n"
    "- Advanced lessons must feel like shipping real work, not theory.\n"
    "- Reference current models when relevant: GPT-5.2, Claude Sonnet 4.5, "
    "Gemini 3, Nano Banana, Sora 2, ElevenLabs, Perplexity, Cursor.\n"
    "- Pick `color` based on the topic mood (cool topics → cool colors, "
    "creative topics → warm).\n"
)


async def _chat_complete(system: str, user_msg: str,
                          model: str = "claude-sonnet-4-5-20250929") -> str:
    chat = LlmChat(
        api_key=_get_key(),
        session_id=f"userpath-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", model)
    return await chat.send_message(UserMessage(text=user_msg))


async def generate_user_path_outline(goal: str) -> dict:
    """STAGE 1: outline only. Fast (~5-10s, 1 Claude call)."""
    user_msg = (
        f"User's goal:\n{goal.strip()[:1500]}\n\n"
        "Design a 3-level learning path (Beginner, Intermediate, Advanced) "
        "with 5-7 lessons per module. Output JSON only."
    )
    raw = await _chat_complete(USER_PATH_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    # Sanitize and ID-ify
    data["id"] = _slug(data.get("title", "user-path")) + "-" + uuid.uuid4().hex[:6]
    data.setdefault("color", "#BFB4FF")
    data.setdefault("duration", "~6 hours")
    data["level"] = "Mixed"   # path spans 3 levels
    modules_out = []
    for m in data.get("modules", []):
        mid = _slug(m.get("title", "module")) + "-" + uuid.uuid4().hex[:4]
        lvl = m.get("level") or _infer_level(m.get("title", ""))
        lessons = []
        for lsn_in in m.get("lessons", []) or []:
            lessons.append({
                "id": _slug(lsn_in.get("title", "lesson")) + "-" + uuid.uuid4().hex[:4],
                "title": lsn_in.get("title", "Untitled lesson")[:120],
                "duration_min": int(lsn_in.get("duration_min", 5) or 5),
                "xp": 50,
                "cards": [],  # filled in stage 2
                "interactive_v": 0,
            })
        modules_out.append({
            "id": mid,
            "title": m.get("title", "Module"),
            "level": lvl,
            "lessons": lessons,
        })
    data["modules"] = modules_out
    return data


def _infer_level(title: str) -> str:
    t = (title or "").lower()
    if "advanced" in t or "shipping" in t or "expert" in t:
        return "Advanced"
    if "intermediate" in t or "building" in t:
        return "Intermediate"
    return "Beginner"


async def fill_path_lessons(db, path_id: str, *,
                              concurrency: int = 2,
                              path_title: Optional[str] = None,
                              path_tagline: Optional[str] = None) -> dict:
    """STAGE 2: fill each lesson's content via Claude.

    Sequential-ish (small concurrency) to stay within rate limits.
    Returns counts of filled vs failed.
    """
    p = await db["curriculum_paths"].find_one({"id": path_id}, {"_id": 0})
    if not p:
        return {"ok": False, "filled": 0, "failed": 0, "skipped": 0,
                "reason": "path_not_found"}
    path_title = path_title or p.get("title", "")
    path_tagline = path_tagline or p.get("tagline", "")
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    filled, failed, skipped = 0, 0, 0

    async def _fill_one(module_id: str, lesson_id: str, lesson_title: str,
                          lesson_level: str):
        nonlocal filled, failed
        async with sem:
            try:
                full = await generate_lesson_draft(
                    lesson_title, lesson_level,
                    path_context=f"{path_title} — {path_tagline}",
                )
                full["id"] = lesson_id
                full["title"] = lesson_title
                full["source"] = "user-generated"
                full["interactive_v"] = 0  # interactive_sweep will upgrade later
                await db["curriculum_paths"].update_one(
                    {"id": path_id, "modules.id": module_id,
                     "modules.lessons.id": lesson_id},
                    {"$set": {"modules.$[mm].lessons.$[ll]": full}},
                    array_filters=[{"mm.id": module_id}, {"ll.id": lesson_id}],
                )
                filled += 1
            except Exception as e:
                log.warning(f"fill_path_lessons: {lesson_id} failed: {e}")
                failed += 1

    tasks = []
    for m in p.get("modules", []):
        level = m.get("level", "Beginner")
        for lsn in m.get("lessons", []):
            if lsn.get("cards"):
                skipped += 1
                continue
            tasks.append(_fill_one(m["id"], lsn["id"], lsn["title"], level))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    log.info(f"fill_path_lessons {path_id}: filled={filled} failed={failed} skipped={skipped}")
    return {"ok": True, "filled": filled, "failed": failed, "skipped": skipped,
            "total": len(tasks) + skipped}
