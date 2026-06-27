"""
interactive_generator.py
─────────────────────────
Uses Claude Sonnet 4.5 (via Emergent LLM key) to convert a text-only lesson
into an interactive lesson by inserting 3 new card types:
  - knowledge_check  (multiple choice, mid-lesson)
  - fill_blank       (text input)
  - playground       (hands-on AI prompt practice)

It is idempotent at the lesson level: callers should check
`lesson.get("interactive_v", 0) >= 1` before invoking.
"""
from __future__ import annotations
import json
import logging
import os
import re
import asyncio
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

log = logging.getLogger("interactive_generator")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"

SYS_PROMPT = """You are an expert AI curriculum designer for Ascendra Academy.
You convert text-only micro-lessons into engaging, interactive learning by inserting
exactly 3 new card types at the right beats in the lesson:

1. KNOWLEDGE_CHECK — A mid-lesson multiple-choice question that tests the most
   important concept from the cards seen so far. 4 options, exactly one correct.
   Explanation should teach, not just confirm.

2. FILL_BLANK — A sentence with a single ___ blank, placed after the user has
   read enough context to answer it. The answer must be 1-4 words. Include 2-4
   acceptable aliases (different casing, plural form, common synonyms).

3. PLAYGROUND — A hands-on "try a prompt" exercise at the END of the lesson.
   It connects the lesson concept to action. Provide a seed_prompt the user
   can run as-is OR modify. Optional system instruction to steer the AI tutor.

Your response MUST be a JSON object with this exact shape:

{
  "knowledge_check": {
    "title": "Quick check",
    "question": "Which of these is the most important reason ...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer_index": 2,
    "explanation": "Short, helpful explanation of why C is correct."
  },
  "fill_blank": {
    "title": "Fill in the blank",
    "prompt": "The architecture that made modern LLMs possible is the ___.",
    "answer": "Transformer",
    "aliases": ["transformers", "transformer architecture", "the transformer"],
    "explanation": "Brief teaching note."
  },
  "playground": {
    "title": "Try a prompt",
    "instruction": "Now you try. Ask an AI to ... and see how it responds.",
    "seed_prompt": "Write a clear, specific prompt that ..."
  },
  "knowledge_check_after_card": 1,
  "fill_blank_after_card": 3
}

Rules:
- `knowledge_check_after_card` and `fill_blank_after_card` are zero-based indices
  into the ORIGINAL text cards array. They mean "insert this card AFTER the text
  card at that index". Always place knowledge_check earlier than fill_blank.
- For a 2-card lesson: knowledge_check_after_card=0, fill_blank_after_card=1
- For a 3-card lesson: knowledge_check_after_card=1, fill_blank_after_card=2
- For a 4+-card lesson: knowledge_check around 1/3 in, fill_blank around 2/3 in.
- The playground is ALWAYS appended after the last text card. No position field needed.
- Output ONLY the JSON. No markdown fences, no commentary.
"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from a model response, tolerating markdown fences."""
    if not text:
        return None
    t = text.strip()
    # Strip ``` fences if present
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    # Try direct parse first
    try:
        return json.loads(t)
    except Exception:
        pass
    # Fallback: find the first {...} balanced block
    start = t.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(t)):
        c = t[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except Exception:
                    return None
    return None


def _safe_int(v, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _is_valid_payload(p: Dict[str, Any]) -> bool:
    try:
        kc = p["knowledge_check"]
        fb = p["fill_blank"]
        pg = p["playground"]
        assert isinstance(kc["question"], str) and len(kc["question"]) > 5
        assert isinstance(kc["options"], list) and len(kc["options"]) == 4
        assert all(isinstance(o, str) and len(o) > 0 for o in kc["options"])
        assert isinstance(kc["answer_index"], int) and 0 <= kc["answer_index"] < 4
        assert isinstance(fb["prompt"], str) and "___" in fb["prompt"]
        assert isinstance(fb["answer"], str) and len(fb["answer"]) > 0
        assert isinstance(pg["instruction"], str) and len(pg["instruction"]) > 5
        return True
    except Exception:
        return False


async def generate_interactive_payload(lesson: Dict[str, Any], max_retries: int = 4) -> Optional[Dict[str, Any]]:
    """Calls Claude to generate the interactive payload for a lesson.
    Retries on rate-limit / transient errors with exponential backoff.
    Returns None only after retries are exhausted.
    """
    if not EMERGENT_LLM_KEY:
        log.warning("EMERGENT_LLM_KEY not set — cannot generate interactive cards")
        return None

    # Build context summary for Claude
    text_cards = [c for c in (lesson.get("cards") or []) if (c.get("kind") or "text") == "text"]
    if not text_cards:
        return None

    summary_lines = [
        f"LESSON TITLE: {lesson.get('title','(untitled)')}",
        f"PATH: {lesson.get('path_title','')} / MODULE: {lesson.get('module_title','')}",
        "",
        f"TEXT CARDS ({len(text_cards)} total):",
    ]
    for i, c in enumerate(text_cards):
        summary_lines.append(f"  [{i}] {c.get('title','')}: {c.get('body','')}")
    if lesson.get("quiz"):
        q = lesson["quiz"]
        summary_lines.append("")
        summary_lines.append("FINAL QUIZ (for reference, do NOT duplicate this question in knowledge_check):")
        summary_lines.append(f"  Q: {q.get('question','')}")
        summary_lines.append(f"  A: {q.get('options', [''])[_safe_int(q.get('answer_index', 0), 0)]}")

    user_msg = "\n".join(summary_lines) + (
        "\n\nGenerate the interactive payload now. JSON only."
    )

    backoff_seconds = [2, 5, 10, 20]  # exponential-ish, total ~37s worst-case
    last_err = None
    for attempt in range(max_retries):
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"interactive-gen-{lesson.get('id','?')}-{attempt}",
                system_message=SYS_PROMPT,
            ).with_model(MODEL_PROVIDER, MODEL_NAME)
            reply = await chat.send_message(UserMessage(text=user_msg))
            payload = _extract_json(reply)
            if payload and _is_valid_payload(payload):
                return payload
            last_err = f"invalid payload: {str(reply)[:200]}"
            # Bad output is not retried (it's not transient)
            log.warning(f"Invalid payload for lesson {lesson.get('id')} on attempt {attempt+1}: {last_err}")
            return None
        except Exception as e:
            msg = str(e)
            last_err = msg
            transient = (
                "429" in msg or "rate" in msg.lower() or "concurren" in msg.lower()
                or "timeout" in msg.lower() or "503" in msg or "502" in msg
                or "overloaded" in msg.lower()
            )
            if not transient or attempt == max_retries - 1:
                log.warning(f"LLM call failed (final) for lesson {lesson.get('id')}: {msg[:240]}")
                return None
            wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
            log.info(f"LLM transient error for lesson {lesson.get('id')} attempt {attempt+1}/{max_retries}, retrying in {wait}s")
            await asyncio.sleep(wait)
    log.warning(f"LLM gave up after {max_retries} retries for lesson {lesson.get('id')}: {last_err}")
    return None


def apply_interactive_payload(lesson: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a generated payload to a lesson, inserting the new cards at the
    right positions. Returns a new (mutated) lesson dict. Does NOT touch the
    lesson if it already has interactive cards (idempotency safety net)."""
    existing_kinds = {c.get("kind") for c in lesson.get("cards", [])}
    if {"knowledge_check", "fill_blank", "playground"} & existing_kinds:
        # Already has interactive cards — don't double-insert.
        lesson["interactive_v"] = 1
        return lesson

    text_cards: List[Dict[str, Any]] = list(lesson.get("cards") or [])
    n = len(text_cards)
    if n < 1:
        lesson["interactive_v"] = 1
        return lesson

    kc_after = max(0, min(n - 1, _safe_int(payload.get("knowledge_check_after_card"), max(0, n // 2 - 1))))
    fb_after = max(kc_after + 1, min(n - 1, _safe_int(payload.get("fill_blank_after_card"), n - 1)))

    kc = payload["knowledge_check"]
    fb = payload["fill_blank"]
    pg = payload["playground"]

    new_cards: List[Dict[str, Any]] = []
    for i, tc in enumerate(text_cards):
        new_cards.append(tc)
        if i == kc_after:
            new_cards.append({
                "kind": "knowledge_check",
                "title": kc.get("title", "Quick check"),
                "question": kc["question"],
                "options": kc["options"],
                "answer_index": int(kc["answer_index"]),
                "explanation": kc.get("explanation", ""),
            })
        if i == fb_after and fb_after != kc_after:
            new_cards.append({
                "kind": "fill_blank",
                "title": fb.get("title", "Fill in the blank"),
                "prompt": fb["prompt"],
                "answer": fb["answer"],
                "aliases": fb.get("aliases", []),
                "explanation": fb.get("explanation", ""),
            })

    # Always append playground at end
    new_cards.append({
        "kind": "playground",
        "title": pg.get("title", "Try a prompt"),
        "instruction": pg["instruction"],
        "seed_prompt": pg.get("seed_prompt", ""),
        "system": pg.get("system", ""),
    })

    lesson["cards"] = new_cards
    lesson["interactive_v"] = 1
    return lesson


async def generate_and_apply(lesson: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot helper: generate + apply. Returns the upgraded lesson, or None on failure."""
    payload = await generate_interactive_payload(lesson)
    if not payload:
        return None
    return apply_interactive_payload(lesson, payload)


async def upgrade_all_lessons(db, *, force: bool = False, concurrency: int = 1,
                              on_progress=None) -> Dict[str, Any]:
    """Find all lessons in DB without `interactive_v >= 1` and upgrade them.
    Marks each lesson `interactive_v: 1` once done. Resilient: a single failure
    is skipped (not rolled back). Concurrency-limited to avoid LLM rate caps.

    Returns: {upgraded: [lesson_ids], failed: [lesson_ids], skipped: [lesson_ids]}
    """
    paths = await db["curriculum_paths"].find({}, {"_id": 0}).to_list(1000)
    to_process: List[Dict[str, Any]] = []
    skipped_ids: List[str] = []
    for p in paths:
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                already = (not force) and int(lsn.get("interactive_v") or 0) >= 1
                has_inter = any((c.get("kind") in ("knowledge_check", "fill_blank", "playground"))
                                for c in lsn.get("cards", []))
                if already or (has_inter and not force):
                    skipped_ids.append(lsn.get("id"))
                    continue
                to_process.append({
                    "lesson": {
                        **lsn,
                        "path_title": p.get("title", ""),
                        "path_id": p.get("id", ""),
                        "module_title": m.get("title", ""),
                        "module_id": m.get("id", ""),
                    },
                    "path_id": p.get("id"),
                    "module_id": m.get("id"),
                    "lesson_id": lsn.get("id"),
                })

    sem = asyncio.Semaphore(concurrency)
    upgraded: List[str] = []
    failed: List[str] = []

    async def _worker(item):
        async with sem:
            lid = item["lesson_id"]
            try:
                upgraded_lesson = await generate_and_apply(item["lesson"])
                if not upgraded_lesson:
                    failed.append(lid)
                    return
                # Strip the temporary path/module title fields we injected
                clean = {k: v for k, v in upgraded_lesson.items()
                         if k not in ("path_title", "path_id", "module_title", "module_id")}
                # Write back into the DB document's nested array
                await db["curriculum_paths"].update_one(
                    {"id": item["path_id"], "modules.id": item["module_id"],
                     "modules.lessons.id": lid},
                    {"$set": {"modules.$[m].lessons.$[l]": clean}},
                    array_filters=[{"m.id": item["module_id"]}, {"l.id": lid}],
                )
                upgraded.append(lid)
                if on_progress:
                    try:
                        on_progress(lid, len(upgraded), len(to_process))
                    except Exception:
                        pass
            except Exception as e:
                log.exception(f"upgrade failed for lesson {lid}: {e}")
                failed.append(lid)

    await asyncio.gather(*[_worker(it) for it in to_process])

    return {"upgraded": upgraded, "failed": failed, "skipped": skipped_ids,
            "total_attempted": len(to_process)}
