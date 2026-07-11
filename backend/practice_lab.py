"""
practice_lab.py
────────────────
Powers Ascendra's "Try It Live" practice system.

Users complete short applied-practice tasks (write a prompt, design a schema,
transform a paragraph, etc). Claude 4.5 evaluates each attempt against a
task-specific rubric and returns:
    - score (0-100)
    - strengths (encouraging opening)
    - improvements (honest critique)
    - next_step (single actionable follow-up)
    - ai_response (when the attempt is a prompt, show what the AI would actually output)
    - master_example (a strong reference answer for comparison)

When a user's score >= MASTERY_THRESHOLD, the attempt is stamped as "mastered"
and auto-saved to their portfolio (private by default).

Tone (per product decision 1c): BALANCED — celebrate wins first, then critique
honestly, then leave the learner with ONE clear next step.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from llm_retry import llm_call_with_retry, friendly_llm_error

log = logging.getLogger("practice_lab")

# --- Config ------------------------------------------------------------
# Read env at call-time (not import-time) so we don't cache an empty value
# if practice_lab is imported before load_dotenv() runs in server.py.
def _get_llm_key() -> str:
    return os.environ.get("EMERGENT_LLM_KEY", "")

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"

MASTERY_THRESHOLD = 80  # score required to save to portfolio
MIN_SCORE_TO_RETRY_HINT = 60  # below this, show a stronger hint
MAX_ATTEMPT_CHARS = 4000  # hard cap on user submission size

# --- Grading prompt ----------------------------------------------------
GRADING_SYS_PROMPT = """You are Ascendra Academy's practice coach — an expert AI educator
who evaluates learner attempts on applied practice tasks. Your grading tone
is BALANCED: you always open with a genuine, specific strength ("what's
working"), then deliver honest, actionable critique, and close with a SINGLE
concrete next step. Never sycophantic, never harsh. You care about the
learner's growth.

You will be given:
  1. TASK — the practice challenge the learner was asked to attempt
  2. RUBRIC — 3-5 criteria on which to grade the attempt (each 0-100)
  3. ATTEMPT — the learner's submission (usually a prompt, sometimes a short essay)
  4. TASK_TYPE — one of: "prompt" (attempt is a prompt to be run through AI),
                          "artifact" (attempt is an artifact to be judged directly)

Your response MUST be a JSON object with this exact shape:

{
  "score": 87,
  "rubric_scores": [
    {"criterion": "Clarity of intent", "score": 90, "note": "Very specific ask"},
    {"criterion": "Role definition", "score": 85, "note": "Coach role is clear"},
    {"criterion": "Constraint setting", "score": 82, "note": "Length limit set; missing tone constraint"}
  ],
  "strengths": [
    "You clearly defined the audience (beginners) which is exactly the right instinct.",
    "The success criteria were specific and measurable — great prompting habit."
  ],
  "improvements": [
    "Add a tone constraint (e.g., 'supportive, never intimidating') to prevent generic replies.",
    "Consider forbidding medical claims explicitly since fitness advice can drift into that."
  ],
  "next_step": "Try adding: 'Never give medical advice — always recommend seeing a doctor for pain.'",
  "master_example": "You are an encouraging beginner-fitness coach... [3-6 sentence reference answer]",
  "mastered": true
}

Rules:
- `score` is a WEIGHTED integer 0-100. Use the rubric scores + your judgment.
- If the attempt is completely off-task, empty, or nonsense, score 0-15 and
  the "improvements" should focus on re-reading the task.
- `strengths` MUST include 1-3 items; NEVER return an empty strengths array
  (find something — even effort — to acknowledge; but if the attempt is truly
  empty/nonsense, use a single item like "You're here trying — that's the start.")
- `improvements` MUST include 1-3 items. Be honest but never harsh.
- `next_step` is ONE sentence: a specific, actionable change the learner
  should make on their next attempt. This is the highest-leverage item.
- `master_example` is a 3-6 sentence reference answer showing what a strong
  attempt looks like. Focus on demonstrating the concept, not showing off.
- `mastered` is true if score >= 80. Otherwise false.
- Output ONLY the JSON. No markdown fences, no commentary.
"""


def _hash_attempt(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _strip_json(text: str) -> str:
    """Strip markdown fences from an LLM response to isolate the JSON."""
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` or ``` ... ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def _grade_via_claude(
    *,
    task_title: str,
    task_instruction: str,
    rubric: List[Dict[str, Any]],
    attempt: str,
    task_type: str = "prompt",
) -> Dict[str, Any]:
    """Call Claude with the grading prompt and return parsed JSON."""
    key = _get_llm_key()
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY is not configured")

    session_id = f"grade-{uuid.uuid4().hex[:12]}"
    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=GRADING_SYS_PROMPT,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)

    user_content = (
        f"TASK_TITLE: {task_title}\n\n"
        f"TASK_INSTRUCTION:\n{task_instruction}\n\n"
        f"TASK_TYPE: {task_type}\n\n"
        f"RUBRIC (grade on each 0-100):\n"
        + "\n".join([f"  - {c.get('criterion','?')}: {c.get('description','')}" for c in rubric])
        + f"\n\nATTEMPT:\n{attempt}\n\n"
        "Return the JSON only."
    )

    async def call():
        return await chat.send_message(UserMessage(text=user_content))

    raw = await llm_call_with_retry(call, max_retries=4, label="practice-grade")
    raw = _strip_json(str(raw))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"[practice-grade] JSON parse failed: {e}. Raw: {raw[:400]}")
        # Salvage: extract score if possible
        raise ValueError("The AI returned an unexpected format. Please try again.")
    # Sanitize
    score = int(data.get("score", 0))
    score = max(0, min(100, score))
    strengths = data.get("strengths") or []
    improvements = data.get("improvements") or []
    if not isinstance(strengths, list): strengths = [str(strengths)]
    if not isinstance(improvements, list): improvements = [str(improvements)]
    return {
        "score": score,
        "rubric_scores": data.get("rubric_scores") or [],
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "next_step": str(data.get("next_step") or "").strip()[:400],
        "master_example": str(data.get("master_example") or "").strip()[:1200],
        "mastered": score >= MASTERY_THRESHOLD,
    }


async def _run_user_prompt_through_ai(prompt: str) -> str:
    """When TASK_TYPE == 'prompt', ALSO run the user's prompt through the AI
    so they can see what output their prompt would produce. Best learning
    experience — feedback + real result side by side.
    """
    key = _get_llm_key()
    if not key or not prompt.strip():
        return ""
    session_id = f"prompt-run-{uuid.uuid4().hex[:12]}"
    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message="You are a helpful assistant. Respond directly to the user's prompt as-if you were the AI they were prompting. Keep responses to 6-10 sentences maximum.",
    ).with_model(MODEL_PROVIDER, MODEL_NAME)

    async def call():
        return await chat.send_message(UserMessage(text=prompt[:MAX_ATTEMPT_CHARS]))

    try:
        result = await llm_call_with_retry(call, max_retries=3, label="prompt-run")
        return str(result).strip()
    except Exception as e:
        log.warning(f"[prompt-run] failed: {e}")
        return ""  # Non-fatal: grading still works without this


# --- Public API --------------------------------------------------------
async def grade_attempt(
    *,
    db,
    user: Dict[str, Any],
    challenge: Dict[str, Any],
    attempt_text: str,
) -> Dict[str, Any]:
    """Grade a single user attempt on a practice challenge.

    Persists the attempt to `practice_attempts` collection. If mastered,
    marks it as `in_portfolio: True` (private by default).

    Args:
        db: motor AsyncIOMotorDatabase
        user: current user dict (must have `id` and `email`)
        challenge: challenge dict (see practice_challenges schema)
        attempt_text: raw user submission
    Returns:
        {
            attempt_id, score, strengths[], improvements[], next_step,
            master_example, mastered, ai_response (optional),
            mastered_first_time (bool)
        }
    """
    attempt_text = (attempt_text or "").strip()
    if not attempt_text:
        raise ValueError("Attempt cannot be empty.")
    if len(attempt_text) > MAX_ATTEMPT_CHARS:
        raise ValueError(f"Attempt too long (max {MAX_ATTEMPT_CHARS} characters).")

    task_type = challenge.get("task_type", "prompt")

    # Run the two AI calls (grade + optional prompt-execution) in parallel-ish.
    # We do them sequentially here to be gentle on rate limits.
    grading = await _grade_via_claude(
        task_title=challenge.get("title", ""),
        task_instruction=challenge.get("instruction", ""),
        rubric=challenge.get("rubric") or [],
        attempt=attempt_text,
        task_type=task_type,
    )

    ai_response = ""
    if task_type == "prompt":
        try:
            ai_response = await _run_user_prompt_through_ai(attempt_text)
        except Exception:
            ai_response = ""

    now = _now()
    attempt_id = str(uuid.uuid4())
    mastered = grading["mastered"]

    # Check if user has already mastered this challenge (for "first time" flag)
    prior_mastery = await db.practice_attempts.find_one({
        "user_id": user["id"],
        "challenge_id": challenge["id"],
        "mastered": True,
    })
    mastered_first_time = mastered and prior_mastery is None

    doc = {
        "id": attempt_id,
        "user_id": user["id"],
        "user_email": user.get("email"),
        "challenge_id": challenge["id"],
        "challenge_title": challenge.get("title"),
        "lesson_id": challenge.get("lesson_id"),
        "path_id": challenge.get("path_id"),
        "attempt_text": attempt_text,
        "attempt_hash": _hash_attempt(attempt_text),
        "score": grading["score"],
        "rubric_scores": grading["rubric_scores"],
        "strengths": grading["strengths"],
        "improvements": grading["improvements"],
        "next_step": grading["next_step"],
        "master_example": grading["master_example"],
        "ai_response": ai_response,
        "mastered": mastered,
        # Portfolio state: attempts that hit mastery are saved automatically.
        # Users can toggle individual items public per product decision 2a.
        "in_portfolio": mastered,
        "is_public": False,  # Private by default
        "created_at": now,
    }
    await db.practice_attempts.insert_one(doc)

    # If mastered, also mark the "best" attempt for this (user, challenge)
    # so the portfolio can pick the single best submission if the user
    # retries after mastering.
    if mastered:
        await db.practice_attempts.update_many(
            {
                "user_id": user["id"],
                "challenge_id": challenge["id"],
                "id": {"$ne": attempt_id},
            },
            {"$set": {"in_portfolio": False}},
        )

    return {
        "attempt_id": attempt_id,
        "score": grading["score"],
        "rubric_scores": grading["rubric_scores"],
        "strengths": grading["strengths"],
        "improvements": grading["improvements"],
        "next_step": grading["next_step"],
        "master_example": grading["master_example"],
        "ai_response": ai_response,
        "mastered": mastered,
        "mastered_first_time": mastered_first_time,
        "in_portfolio": mastered,
        "is_public": False,
    }


async def get_user_portfolio(
    *,
    db,
    user_id: str,
    only_public: bool = False,
) -> List[Dict[str, Any]]:
    """Return the user's portfolio items (mastered attempts).

    If only_public=True, filter to items the user has toggled public.
    """
    query: Dict[str, Any] = {
        "user_id": user_id,
        "in_portfolio": True,
        "mastered": True,
    }
    if only_public:
        query["is_public"] = True

    cursor = db.practice_attempts.find(query).sort("created_at", -1).limit(200)
    items = []
    async for doc in cursor:
        items.append(_public_attempt_view(doc))
    return items


async def toggle_portfolio_item_public(
    *,
    db,
    user_id: str,
    attempt_id: str,
) -> Dict[str, Any]:
    """Toggle the is_public flag on a portfolio item. Returns new state."""
    doc = await db.practice_attempts.find_one({"id": attempt_id, "user_id": user_id})
    if not doc:
        raise LookupError("Portfolio item not found.")
    if not doc.get("in_portfolio"):
        raise ValueError("This attempt isn't in your portfolio yet — you need to master it first.")
    new_state = not bool(doc.get("is_public", False))
    await db.practice_attempts.update_one(
        {"id": attempt_id, "user_id": user_id},
        {"$set": {"is_public": new_state, "updated_at": _now()}},
    )
    return {"attempt_id": attempt_id, "is_public": new_state}


async def get_user_attempts_for_challenge(
    *,
    db,
    user_id: str,
    challenge_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Recent attempts by a user on a specific challenge (for the retry UI)."""
    cursor = db.practice_attempts.find({
        "user_id": user_id,
        "challenge_id": challenge_id,
    }).sort("created_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        items.append(_public_attempt_view(doc))
    return items


def _public_attempt_view(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a MongoDB doc into a JSON-safe response shape."""
    return {
        "attempt_id": doc.get("id"),
        "challenge_id": doc.get("challenge_id"),
        "challenge_title": doc.get("challenge_title"),
        "lesson_id": doc.get("lesson_id"),
        "path_id": doc.get("path_id"),
        "attempt_text": doc.get("attempt_text"),
        "score": doc.get("score"),
        "rubric_scores": doc.get("rubric_scores"),
        "strengths": doc.get("strengths"),
        "improvements": doc.get("improvements"),
        "next_step": doc.get("next_step"),
        "master_example": doc.get("master_example"),
        "ai_response": doc.get("ai_response"),
        "mastered": bool(doc.get("mastered")),
        "in_portfolio": bool(doc.get("in_portfolio")),
        "is_public": bool(doc.get("is_public")),
        "created_at": (doc.get("created_at") or _now()).isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
    }


# --- Challenge lookup / creation helpers -------------------------------
async def get_challenge(db, challenge_id: str) -> Optional[Dict[str, Any]]:
    doc = await db.practice_challenges.find_one({"id": challenge_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


async def list_challenges_for_lesson(db, lesson_id: str) -> List[Dict[str, Any]]:
    cursor = db.practice_challenges.find({"lesson_id": lesson_id}).sort("order", 1)
    items = []
    async for doc in cursor:
        doc.pop("_id", None)
        items.append(doc)
    return items


async def upsert_challenge(db, challenge: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a challenge by id."""
    now = _now()
    challenge_id = challenge.get("id") or str(uuid.uuid4())
    challenge["id"] = challenge_id
    challenge.setdefault("created_at", now)
    challenge["updated_at"] = now
    await db.practice_challenges.update_one(
        {"id": challenge_id},
        {"$set": challenge},
        upsert=True,
    )
    return challenge


# --- Auto-generation (admin tool) --------------------------------------
CHALLENGE_GEN_SYS_PROMPT = """You are Ascendra Academy's practice-challenge designer.
Given the content of a lesson, design ONE hands-on "Try It Live" practice
challenge that lets the learner APPLY the lesson's core concept.

Return a JSON object with this exact shape:

{
  "title": "Design an encouraging fitness coach",
  "instruction": "Write a system prompt that turns an AI into a supportive fitness coach for beginners. It should define the role, set the tone, and establish what the coach WILL and WON'T do.",
  "task_type": "prompt",
  "success_criteria": [
    "Defines the role clearly (fitness coach, beginners)",
    "Sets an encouraging, non-intimidating tone",
    "Establishes 1-2 constraints (e.g., no medical advice)"
  ],
  "rubric": [
    {"criterion": "Role clarity", "description": "Does the prompt clearly say what the AI is and who it serves?"},
    {"criterion": "Tone", "description": "Is the tone explicit and appropriate for beginners?"},
    {"criterion": "Constraints", "description": "Are safe-scope constraints included (e.g., no medical claims)?"}
  ],
  "seed_prompt": "You are ..."
}

Rules:
- `task_type` should be "prompt" for prompt-writing tasks (most common)
  or "artifact" for tasks like writing an outline, summary, or short answer.
- The rubric MUST have 3-5 criteria, each with a short description.
- `seed_prompt` (optional) is a light starting stub the learner can build on;
  it should NOT be a complete answer — just enough to lower the blank-page barrier.
- Output ONLY the JSON. No markdown fences, no commentary.
"""


async def auto_generate_challenge_for_lesson(
    *,
    db,
    lesson: Dict[str, Any],
) -> Dict[str, Any]:
    """Use Claude to design a practice challenge for an existing lesson."""
    key = _get_llm_key()
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    # Summarize lesson cards into a compact context string
    cards = lesson.get("cards") or []
    context_parts = []
    for i, c in enumerate(cards[:8]):
        kind = c.get("kind", "text")
        if kind == "text":
            context_parts.append(f"[Card {i} · text] {c.get('title','')}: {c.get('body','')[:400]}")
        elif kind == "knowledge_check":
            context_parts.append(f"[Card {i} · quiz] Q: {c.get('question','')[:200]}")
        elif kind == "playground":
            context_parts.append(f"[Card {i} · playground] {c.get('instruction','')[:200]}")
        elif kind == "fill_blank":
            context_parts.append(f"[Card {i} · fill_blank] {c.get('prompt','')[:200]}")

    session_id = f"gen-challenge-{uuid.uuid4().hex[:12]}"
    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=CHALLENGE_GEN_SYS_PROMPT,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)

    user_content = (
        f"LESSON TITLE: {lesson.get('title','')}\n\n"
        f"LESSON CARDS:\n" + "\n\n".join(context_parts) + "\n\n"
        "Design one practice challenge. Output JSON only."
    )

    async def call():
        return await chat.send_message(UserMessage(text=user_content))

    raw = await llm_call_with_retry(call, max_retries=4, label="challenge-gen")
    raw = _strip_json(str(raw))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("The AI returned an unexpected format when generating the challenge. Try again.")

    challenge = {
        "title": str(data.get("title", "Practice Challenge"))[:200],
        "instruction": str(data.get("instruction", ""))[:2000],
        "task_type": str(data.get("task_type", "prompt")),
        "success_criteria": data.get("success_criteria") or [],
        "rubric": data.get("rubric") or [],
        "seed_prompt": str(data.get("seed_prompt", ""))[:800],
        "lesson_id": lesson.get("id"),
        "path_id": lesson.get("path_id"),
        "order": 0,
    }
    return await upsert_challenge(db, challenge)
