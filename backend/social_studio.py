"""
social_studio.py — Free social content generator.

Given a lesson or path, generate:
  • Twitter/X: 5-tweet thread (text)
  • Instagram: 5-slide carousel (PIL-generated images with text overlay, no AI image cost)
  • TikTok: 30-sec silent MP4 slideshow (ffmpeg-stitched PIL slides) — optional

Output saved to MongoDB `social_posts` collection. Admin can preview/copy/edit in
/admin/social. Posting to platforms is NOT implemented (requires user-supplied API
tokens from Twitter, Meta, TikTok dev apps). The infrastructure is here to wire it
up when those tokens arrive.
"""
from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile
import textwrap
import uuid
from datetime import datetime, timezone
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_studio import _get_key, _parse_json_block

log = logging.getLogger("social_studio")

# Brand
BRAND_GOLD = "#FFB000"
BRAND_DARK = "#0A0413"
BRAND_PURPLE = "#7C3AED"
TEXT_COLOR = "#FFFFFF"
SUBTEXT_COLOR = "#C8C5E6"

# Try common system font locations for arm64 Debian
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


# ─── LLM content generators ────────────────────────────────────────────────
TWEET_SYSTEM = (
    "You are Ascendra's social media voice — warm, expert, energetic. "
    "Given a lesson, generate a 5-tweet thread that teaches the core insight. "
    "OUTPUT VALID JSON ONLY:\n"
    "{\n"
    '  "tweets": ["Tweet 1 hook (≤ 280 chars)", "Tweet 2", "Tweet 3", "Tweet 4", "Tweet 5 CTA (link to Ascendra)"],\n'
    '  "hashtags": ["#AI", "#Learning", "#Ascendra", ...]\n'
    "}\n"
    "Rules:\n"
    "- Tweet 1 must hook hard. Question, contrarian take, or specific number.\n"
    "- Tweets 2-4: one concrete idea each. NO 'as an AI' filler.\n"
    "- Tweet 5: soft CTA mentioning Ascendra Academy.\n"
    "- Plain prose. No emojis except maybe one per tweet.\n"
    "- NEVER invent statistics or 'X% of people' claims.\n"
)

CAROUSEL_SYSTEM = (
    "You are Ascendra's social designer. Given a lesson, generate a 5-slide Instagram/LinkedIn carousel. "
    "OUTPUT VALID JSON ONLY:\n"
    "{\n"
    '  "slides": [\n'
    '    {"heading": "Hook (≤ 6 words)", "body": "Subtext (≤ 100 chars)"},\n'
    '    {"heading": "Point 1", "body": "..."},\n'
    '    {"heading": "Point 2", "body": "..."},\n'
    '    {"heading": "Point 3", "body": "..."},\n'
    '    {"heading": "Try it", "body": "CTA to Ascendra"}\n'
    "  ],\n"
    '  "caption": "Instagram caption with line breaks. 80-180 words."\n'
    "}\n"
    "Rules:\n"
    "- Slide 1 must hook. Question, bold claim, or specific number.\n"
    "- Slides 2-4: each makes ONE clear point. Heading is the point. Body explains briefly.\n"
    "- Slide 5: warm CTA mentioning Ascendra Academy.\n"
    "- NEVER invent statistics.\n"
)


async def generate_tweet_thread(lesson_summary: str) -> dict:
    return await _llm_json(
        TWEET_SYSTEM, lesson_summary[:4000],
        session_prefix="tweets",
        retry_hint="Use straight single quotes, never curly quotes. Escape any double quotes inside strings with backslash.",
    )


async def generate_carousel(lesson_summary: str) -> dict:
    return await _llm_json(
        CAROUSEL_SYSTEM, lesson_summary[:4000],
        session_prefix="carousel",
        retry_hint="Use straight single quotes, never curly quotes. Escape any double quotes inside strings with backslash.",
    )


async def _llm_json(system: str, user: str, *, session_prefix: str = "social",
                     retry_hint: str = "", model: str = "claude-sonnet-4-5-20250929") -> dict:
    """LLM call with one retry on JSON parse failure."""
    import json as _json

    def _try_parse(raw: str) -> dict:
        return _parse_json_block(raw)

    for attempt in range(2):
        chat = LlmChat(
            api_key=_get_key(),
            session_id=f"{session_prefix}-{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("anthropic", model)
        prompt = user if attempt == 0 else (
            user + f"\n\nIMPORTANT: Your previous response had invalid JSON. {retry_hint} Return ONLY the JSON object."
        )
        raw = await chat.send_message(UserMessage(text=prompt))
        try:
            return _try_parse(raw)
        except (ValueError, _json.JSONDecodeError) as e:
            if attempt == 0:
                log.warning(f"{session_prefix} JSON parse failed (will retry): {e}")
                continue
            # Final fallback: try to extract using more lenient parsing
            try:
                # Strip control chars + try once more
                cleaned = "".join(c for c in raw if ord(c) >= 32 or c in "\n\r\t")
                return _parse_json_block(cleaned)
            except Exception:
                log.error(f"{session_prefix} JSON parse failed after retry: {raw[:300]}")
                raise


# ─── Image / video rendering ───────────────────────────────────────────────
def render_carousel_slide(heading: str, body: str, slide_num: int = 1, total: int = 5,
                           size: tuple[int, int] = (1080, 1080)) -> bytes:
    """Generate a 1080x1080 Instagram-friendly slide. Returns PNG bytes."""
    w, h = size
    img = Image.new("RGB", size, BRAND_DARK)
    draw = ImageDraw.Draw(img)

    # Diagonal gradient overlay
    for i in range(h):
        ratio = i / h
        r = int(10 + (124 - 10) * ratio * 0.25)
        g = int(4 + (58 - 4) * ratio * 0.25)
        b = int(19 + (237 - 19) * ratio * 0.25)
        draw.line([(0, i), (w, i)], fill=(r, g, b))

    # ASCENDRA branding top-left
    f_brand = _font(28)
    draw.text((60, 60), "ASCENDRA", font=f_brand, fill=BRAND_GOLD)
    draw.rectangle([60, 105, 110, 109], fill=BRAND_GOLD)

    # Slide counter top-right
    f_count = _font(22)
    counter = f"{slide_num} / {total}"
    bbox = draw.textbbox((0, 0), counter, font=f_count)
    cw = bbox[2] - bbox[0]
    draw.text((w - 60 - cw, 60), counter, font=f_count, fill=SUBTEXT_COLOR)

    # Heading
    f_head = _font(80)
    wrapped_head = textwrap.fill(heading, width=18)
    bbox = draw.multiline_textbbox((0, 0), wrapped_head, font=f_head, spacing=14)
    hh = bbox[3] - bbox[1]
    draw.multiline_text((60, h * 0.32 - hh / 2), wrapped_head, font=f_head, fill=TEXT_COLOR, spacing=14)

    # Body
    if body:
        f_body = _font(40)
        wrapped_body = textwrap.fill(body, width=32)
        draw.multiline_text((60, int(h * 0.62)), wrapped_body, font=f_body, fill=SUBTEXT_COLOR, spacing=12)

    # Bottom URL
    f_url = _font(24)
    draw.text((60, h - 80), "ascendraacademy.com", font=f_url, fill=BRAND_GOLD)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_slideshow_mp4(slides_png_bytes: list[bytes], seconds_per_slide: float = 3.5) -> Optional[bytes]:
    """Stitch PNG slides into a silent MP4 via ffmpeg. Returns bytes or None."""
    if not slides_png_bytes:
        return None
    try:
        with tempfile.TemporaryDirectory() as td:
            for i, b in enumerate(slides_png_bytes):
                with open(os.path.join(td, f"slide_{i:03d}.png"), "wb") as f:
                    f.write(b)
            out_path = os.path.join(td, "out.mp4")
            # 1080x1080 @ 30fps, ~seconds_per_slide per slide
            framerate = 1.0 / seconds_per_slide
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", f"{framerate}", "-i", os.path.join(td, "slide_%03d.png"),
                "-vf", "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-r", "30",
                out_path,
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=60)
            if r.returncode != 0:
                log.error(f"ffmpeg failed: {r.stderr.decode()[:500]}")
                return None
            with open(out_path, "rb") as f:
                return f.read()
    except Exception as e:
        log.exception(f"slideshow render failed: {e}")
        return None


# ─── DB layer ──────────────────────────────────────────────────────────────
async def _col(db):
    return db["social_posts"]


async def list_posts(db, *, limit: int = 100, status: Optional[str] = None) -> list:
    col = await _col(db)
    q = {} if not status else {"status": status}
    cur = col.find(q, {"_id": 0, "slide_png_bytes": 0, "mp4_bytes": 0}).sort("created_at", -1).limit(min(limit, 500))
    return await cur.to_list(min(limit, 500))


async def get_post(db, post_id: str) -> Optional[dict]:
    col = await _col(db)
    return await col.find_one({"id": post_id}, {"_id": 0})


async def get_slide_bytes(db, post_id: str, slide_idx: int) -> Optional[bytes]:
    col = await _col(db)
    doc = await col.find_one({"id": post_id}, {"_id": 0, "slide_png_bytes": 1})
    if not doc:
        return None
    slides = doc.get("slide_png_bytes") or []
    return slides[slide_idx] if 0 <= slide_idx < len(slides) else None


async def get_mp4_bytes(db, post_id: str) -> Optional[bytes]:
    col = await _col(db)
    doc = await col.find_one({"id": post_id}, {"_id": 0, "mp4_bytes": 1})
    return (doc or {}).get("mp4_bytes")


def _summarize_lesson_for_social(lesson: dict, path_title: Optional[str] = None) -> str:
    bits = [f"Lesson: {lesson.get('title','')}"]
    if path_title:
        bits.append(f"From path: {path_title}")
    for card in lesson.get("cards", []) or []:
        bits.append(f"- {card.get('title','')}: {card.get('body','')[:400]}")
    q = lesson.get("quiz") or {}
    if q.get("question"):
        bits.append(f"Key takeaway: {q['question']}")
    return "\n".join(bits)


async def generate_post_for_lesson(db, lesson: dict, *, path_title: Optional[str] = None,
                                     path_id: Optional[str] = None, lesson_id: Optional[str] = None,
                                     include_video: bool = True) -> dict:
    summary = _summarize_lesson_for_social(lesson, path_title)
    thread = await generate_tweet_thread(summary)
    carousel = await generate_carousel(summary)
    # Render carousel slides
    slides_bytes: list[bytes] = []
    for i, slide in enumerate(carousel.get("slides", [])):
        png = render_carousel_slide(
            heading=slide.get("heading", ""),
            body=slide.get("body", ""),
            slide_num=i + 1, total=len(carousel.get("slides", [])),
        )
        slides_bytes.append(png)
    mp4_bytes = render_slideshow_mp4(slides_bytes) if include_video and slides_bytes else None

    now = datetime.now(timezone.utc)
    post_id = str(uuid.uuid4())
    doc = {
        "id": post_id,
        "lesson_title": lesson.get("title"),
        "path_title": path_title,
        "path_id": path_id,
        "lesson_id": lesson_id,
        "tweets": thread.get("tweets", []),
        "hashtags": thread.get("hashtags", []),
        "slides": carousel.get("slides", []),
        "caption": carousel.get("caption", ""),
        "slide_count": len(slides_bytes),
        "slide_png_bytes": slides_bytes,
        "mp4_bytes": mp4_bytes,
        "has_video": bool(mp4_bytes),
        "status": "ready",  # ready | posted | archived
        "platforms": {"twitter": "draft", "instagram": "draft", "tiktok": "draft"},
        "created_at": now,
        "updated_at": now,
    }
    col = await _col(db)
    await col.insert_one(dict(doc))
    # Return slim doc (no binary)
    return {k: v for k, v in doc.items() if k not in ("slide_png_bytes", "mp4_bytes")}


async def delete_post(db, post_id: str) -> bool:
    col = await _col(db)
    r = await col.delete_one({"id": post_id})
    return r.deleted_count > 0
