"""
Ascendra AI Studio.
Uses the Emergent Universal LLM Key (Claude Sonnet 4.5 for text, gpt-image-1 for images).

Generates engaging, teacher-quality lessons, paths, and cover artwork.
"""
from __future__ import annotations
import os
import re
import uuid
import json
import base64
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
def _get_key() -> str:
    """Read the key live so .env loaded later still works."""
    return os.environ.get("EMERGENT_LLM_KEY", "") or EMERGENT_LLM_KEY
PUBLIC_WEB_URL = (os.environ.get("PUBLIC_WEB_URL") or "").rstrip("/")
STATIC_DIR = Path(__file__).parent / "static"
COVERS_DIR = STATIC_DIR / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("ascendra.studio")

# ─── System prompts ────────────────────────────────────────────────────────
LESSON_SYSTEM = (
    "You are Ascendra, the AI learning architect for the Ascendra Academy platform. "
    "You write lessons the way the world's best teachers do — clear, encouraging, "
    "vivid, packed with concrete examples, and just a little daring. You teach humans "
    "how to use AI in 2026 (current models: GPT-5.2, Claude Sonnet 4.5, Gemini 3 "
    "Pro/Flash, Nano Banana, Sora 2, ElevenLabs, Perplexity, Cursor, Suno). "
    "\n\nWhen asked to write a lesson, OUTPUT VALID JSON ONLY (no prose before or after). "
    "The JSON must follow this exact shape:\n"
    "{\n"
    '  "title": "Concise 4-7 word lesson title",\n'
    '  "duration_min": 5,\n'
    '  "xp": 50,\n'
    '  "cards": [\n'
    '    {"title": "Hook-style card title", "body": "2-3 sentence card body. Use a vivid analogy. End with a question or punchy insight. Use *asterisks* for emphasis when useful."}\n'
    "  ],\n"
    '  "quiz": {\n'
    '    "question": "A single, sharp check-for-understanding question",\n'
    '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
    '    "answer_index": 0,\n'
    '    "explanation": "1-2 sentences explaining why that\'s right and gently why the others are not."\n'
    "  }\n"
    "}\n\n"
    "Rules:\n"
    "- Exactly 4 cards. Each card.body must be 50–120 words. No bullet lists in card.body — flowing prose only.\n"
    "- Card 1 sets the hook (\"why this matters\"). Card 2 explains the core concept. "
    "Card 3 gives a real example. Card 4 is \"what this means for you\" — applied takeaway.\n"
    "- Quiz must have exactly 4 options. Make distractors plausible (not obviously wrong).\n"
    "- Tone: warm, energetic, encouraging — like a great teacher who believes in the learner.\n"
    "- Reference real 2026 models when relevant; do not invent product names.\n"
    "- duration_min between 4 and 10. xp between 40 and 80.\n"
)


PATH_SYSTEM = (
    "You are Ascendra, the curriculum designer. When given a path concept, output a JSON "
    "outline for a complete learning path (NOT the lesson bodies — just titles and structure). "
    "OUTPUT VALID JSON ONLY (no prose).\n\n"
    "Shape:\n"
    "{\n"
    '  "title": "Path title (4-6 words)",\n'
    '  "subtitle": "Beginner -> Intermediate" or similar progression,\n'
    '  "tagline": "One punchy sentence selling the path",\n'
    '  "level": "Beginner" | "Intermediate" | "Advanced",\n'
    '  "duration": "~3 hours" or similar,\n'
    '  "color": "#FFB000",  // hex; pick something on-brand from the celestial palette\n'
    '  "modules": [\n'
    '    {"title": "Module title", "lessons": [{"title": "Lesson 1 title"}, {"title": "Lesson 2 title"}]}\n'
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- 3–5 modules. Each module has 2–4 lesson titles (titles ONLY at this stage).\n"
    "- Lesson titles should read like a coherent learning arc, not a list.\n"
    "- color must be a real hex from this palette: #FFB000 #FF6B35 #BFB4FF #7C3AED #E8C572 #34D399 #FB7185 #38BDF8.\n"
    "- Be specific to the topic — no generic filler.\n"
)


REFRESH_SYSTEM = (
    "You are Ascendra, the curriculum maintainer. You receive a lesson JSON written in a "
    "previous year and your job is to refresh it for 2026. Update any mentions of outdated "
    "AI models to current ones (GPT-4 -> GPT-5.2, Claude 3 -> Claude Sonnet 4.5, "
    "GPT-3.5 -> GPT-5.2 mini, Bard -> Gemini 3, DALL-E -> Nano Banana for new image work, "
    "DALL-E 3 -> Nano Banana, Stable Diffusion 1.5 -> Flux). Modernize examples while "
    "keeping the lesson's pedagogical intent intact. Keep card structure (4 cards), quiz, "
    "and titles unchanged unless they reference an outdated model. OUTPUT VALID JSON ONLY "
    "matching the same shape as the input lesson."
)


OUTDATED_TERMS = [
    # OpenAI — pre-GPT-5.2 era
    "GPT-4o", "GPT-4 Turbo", "GPT-4", "GPT-3.5", "GPT-3", "GPT-2",
    "DALL-E 3", "DALL-E 2", "DALL-E", "Codex", "ChatGPT Plus",
    # Anthropic — pre-Claude 4.5 era
    "Claude 3.5 Sonnet", "Claude 3.5 Haiku",
    "Claude 3 Opus", "Claude 3 Sonnet", "Claude 3 Haiku",
    "Claude 3.7 Sonnet", "Claude 2.1", "Claude 2", "Claude Instant",
    # Google — pre-Gemini 3 era
    "Gemini 2.0 Flash", "Gemini 2.0 Pro", "Gemini 2.5 Pro",
    "Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini 1.5",
    "Gemini 1.0", "Gemini Pro", "Bard", "PaLM 2", "PaLM",
    # Video / Image gen — pre-Sora 2 / Nano Banana era
    "Sora 1", "Runway Gen-2", "Runway Gen-3", "Pika 1.0",
    "Stable Diffusion 1", "Stable Diffusion 2", "Stable Diffusion 3",
    "SDXL 1.0", "Midjourney v5", "Midjourney v6",
    # Meta / open-source — older versions
    "Llama 2", "Llama 3", "Llama 3.1",
    # Voice / audio — older
    "ElevenLabs v1", "ElevenLabs Multilingual v1",
    # Coding / dev tools — older
    "Copilot X", "Cody 1",
]


# ─── Helpers ────────────────────────────────────────────────────────────────
def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s[:48] or f"id-{uuid.uuid4().hex[:8]}"


def _parse_json_block(raw: str) -> dict:
    """Tolerant JSON extraction from an LLM response."""
    raw = raw.strip()
    # strip ```json fences
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    # find the first { ... } block
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in response")
    return json.loads(raw[start : end + 1])


async def _chat_complete(system: str, user_msg: str, model: str = "claude-sonnet-4-5-20250929") -> str:
    from llm_retry import llm_call_with_retry

    async def _do_call() -> str:
        chat = LlmChat(
            api_key=_get_key(),
            session_id=f"studio-{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("anthropic", model)
        return await chat.send_message(UserMessage(text=user_msg))

    return await llm_call_with_retry(_do_call, max_retries=4, label="ai_studio._chat_complete")


# ─── Public Studio API ──────────────────────────────────────────────────────
async def generate_lesson_draft(topic: str, level: str = "Beginner", path_context: Optional[str] = None) -> dict:
    """Generate a lesson draft (cards + quiz). Returns a dict ready to insert."""
    user_msg = (
        f"Topic: {topic}\n"
        f"Difficulty level: {level}\n"
        + (f"Path context: {path_context}\n" if path_context else "")
        + "\nWrite the lesson as a teacher would — engaging, concrete, encouraging. "
        "Use real 2026 model names where relevant. Output the JSON only."
    )
    raw = await _chat_complete(LESSON_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    # Normalize
    data["id"] = _slug(data.get("title", topic)) + "-" + uuid.uuid4().hex[:4]
    data["duration_min"] = int(data.get("duration_min", 5))
    data["xp"] = int(data.get("xp", 50))
    # Validate quiz shape
    q = data.get("quiz") or {}
    q.setdefault("question", "")
    q.setdefault("options", [])
    q.setdefault("answer_index", 0)
    q.setdefault("explanation", "")
    data["quiz"] = q
    # Validate cards shape
    cards = data.get("cards") or []
    norm_cards = []
    for c in cards:
        norm_cards.append({"title": c.get("title", ""), "body": c.get("body", "")})
    data["cards"] = norm_cards
    return data


async def generate_path_outline(concept: str, level: str = "Beginner") -> dict:
    user_msg = (
        f"Path concept: {concept}\n"
        f"Difficulty level: {level}\n\n"
        "Design a coherent, exciting learning path. Output JSON only."
    )
    raw = await _chat_complete(PATH_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    data["id"] = _slug(data.get("title", concept))
    data.setdefault("color", "#FFB000")
    data.setdefault("level", level)
    data.setdefault("duration", "~2 hours")
    # Add lesson IDs (placeholder — fully populated when lessons are generated)
    modules_out = []
    for m in data.get("modules", []):
        mid = _slug(m["title"])
        lessons = [{"id": _slug(l["title"]) + "-" + uuid.uuid4().hex[:4], "title": l["title"]} for l in m.get("lessons", [])]
        modules_out.append({"id": mid, "title": m["title"], "lessons": lessons})
    data["modules"] = modules_out
    return data


async def refresh_lesson(lesson: dict) -> dict:
    """Modernize a lesson for 2026."""
    user_msg = (
        "Here is a lesson written in a prior year. Refresh it for 2026 (update model "
        "mentions, modernize examples). Output the refreshed lesson JSON only.\n\n"
        f"INPUT LESSON:\n{json.dumps({k: v for k, v in lesson.items() if k in ('title','cards','quiz')}, indent=2)}"
    )
    raw = await _chat_complete(REFRESH_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    refreshed = dict(lesson)
    for k in ("title", "cards", "quiz"):
        if k in data:
            refreshed[k] = data[k]
    return refreshed


def scan_outdated_terms(text: str) -> list:
    found = []
    if not text:
        return found
    upper = text
    for term in OUTDATED_TERMS:
        # Whole-word-ish match, case-insensitive
        pat = re.compile(re.escape(term), re.IGNORECASE)
        if pat.search(upper):
            found.append(term)
    return list(set(found))


# ─── Image Generation (Cover Art) ───────────────────────────────────────────
async def generate_cover_image(prompt: str, path_id: Optional[str] = None) -> str:
    """Generate a cover image via gpt-image-1, save to disk, return public URL."""
    if not _get_key():
        raise RuntimeError("EMERGENT_LLM_KEY missing")
    styled_prompt = (
        f"Editorial, cinematic cover artwork for an AI learning module titled '{prompt}'. "
        "Dark cosmic background with violet and amber gold accents, golden hour lighting, "
        "subtle ascendant motion, ethereal yet hopeful, no text, no watermarks. "
        "Style: modern editorial poster, painterly digital art, square 1:1."
    )
    gen = OpenAIImageGeneration(api_key=_get_key())
    try:
        images = await gen.generate_images(prompt=styled_prompt, model="gpt-image-1", number_of_images=1, quality="low")
    except Exception as e:
        log.exception("Image generation failed")
        raise RuntimeError(f"Image generation failed: {str(e)[:160]}")
    if not images:
        raise RuntimeError("No image returned")

    raw = images[0]
    # Some libs return bytes, some return base64 string. Normalize.
    if isinstance(raw, str):
        try:
            raw = base64.b64decode(raw)
        except Exception:
            raise RuntimeError("Unrecognized image payload")
    elif isinstance(raw, dict):
        # In case of {"b64_json": ...}
        if raw.get("b64_json"):
            raw = base64.b64decode(raw["b64_json"])
        elif raw.get("url"):
            return raw["url"]
        else:
            raise RuntimeError("Unrecognized image payload")

    # Save to /app/backend/static/covers/<id>.png
    name = (path_id or _slug(prompt) or "cover") + "-" + uuid.uuid4().hex[:6] + ".png"
    fpath = COVERS_DIR / name
    fpath.write_bytes(raw)
    public_url = (PUBLIC_WEB_URL or "") + f"/api/static/covers/{name}"
    return public_url
