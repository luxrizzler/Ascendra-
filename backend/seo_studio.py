"""
seo_studio.py — Programmatic SEO content generator + DB layer.

Generates AI-written landing pages for:
  • Model hubs           → /learn/{model_slug}
  • Use-case sub-pages   → /learn/{model_slug}/{use_case_slug}

Each page is stored as a single MongoDB document in collection `seo_pages`.
Pages render via the React frontend after being fetched from
GET /api/seo/page/{...} (public, no auth — these pages are for crawlers).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

# Reuse helpers from ai_studio for consistency
from ai_studio import _slug, _parse_json_block, _get_key  # type: ignore

# ─── Prompts ───────────────────────────────────────────────────────────────
HUB_SYSTEM = (
    "You are Ascendra's senior SEO content writer. You write AI model landing pages "
    "that rank in Google AND convert visitors into Ascendra Academy signups.\n\n"
    "OUTPUT VALID JSON ONLY (no prose, no markdown fences). Shape:\n"
    "{\n"
    '  "title": "Page <H1> (under 70 chars)",\n'
    '  "subtitle": "One-line value prop under H1",\n'
    '  "meta_title": "SEO title tag — keyword-leading, under 60 chars",\n'
    '  "meta_description": "Compelling meta description, 140-160 chars, includes a CTA",\n'
    '  "hero_eyebrow": "Short kicker e.g. \\"AI MODEL GUIDE\\"",\n'
    '  "intro_md": "First paragraph (60-100 words). Plain prose — no markdown.",\n'
    '  "tldr": ["3-5 short bullet points summarizing the model"],\n'
    '  "what_it_is": "Section: what the model is, 80-140 words",\n'
    '  "what_its_good_at": ["List 4-6 strengths, 6-10 words each"],\n'
    '  "what_it_struggles_with": ["List 3-4 honest weaknesses"],\n'
    '  "best_for_personas": ["List 4-5 personas (one-liners) who get the most value"],\n'
    '  "comparison": "1 paragraph comparing it to 1-2 rivals (80-120 words)",\n'
    '  "use_cases": ["List 6-8 concrete use cases, 4-8 words each"],\n'
    '  "getting_started": "1 paragraph of practical first-step advice (80-120 words)",\n'
    '  "faqs": [{"q": "Question (under 80 chars)", "a": "Answer 40-90 words"}],\n'
    '  "cta_headline": "Conversion-focused subhead under 70 chars",\n'
    '  "cta_body": "1-2 sentences pushing toward Ascendra signup"\n'
    "}\n\n"
    "Rules:\n"
    "- Tone: warm, expert, energetic. Like a great teacher who gets excited about ideas.\n"
    "- Mention Ascendra Academy at least twice across the body (not spammy).\n"
    "- Avoid corporate jargon (\"leverage\", \"empower\", \"synergize\").\n"
    "- 5-7 FAQs. Cover pricing context, getting started, comparisons, common pitfalls.\n"
    "- Reference only real 2026 model names; do not invent product names.\n"
    "- Use plain prose. No markdown formatting inside text fields.\n"
    "- CRITICAL: do NOT invent specific statistics, user counts, revenue numbers, "
    "or social proof (e.g. 'Join 12,000+ founders'). Only mention numbers you would "
    "find documented in the model's public release. When in doubt, omit the number.\n"
)

USECASE_SYSTEM = (
    "You are Ascendra's senior SEO content writer. You write 'how to use {model} for "
    "{use_case}' landing pages that rank in Google AND drive signups.\n\n"
    "OUTPUT VALID JSON ONLY. Shape:\n"
    "{\n"
    '  "title": "<Model> for <Use Case>: A Practical Guide",\n'
    '  "subtitle": "One-line promise: what the reader will be able to do",\n'
    '  "meta_title": "SEO title tag, under 60 chars",\n'
    '  "meta_description": "140-160 chars, ends with a CTA",\n'
    '  "hero_eyebrow": "Short kicker e.g. \\"USE-CASE PLAYBOOK\\"",\n'
    '  "intro_md": "Opening paragraph (60-100 words) explaining who this is for",\n'
    '  "why_this_model": "80-120 words on why this model is a good fit for this use case",\n'
    '  "step_by_step": [\n'
    '    {"title": "Step title (4-8 words)", "body": "What to do, 40-80 words"}\n'
    "  ],\n"
    '  "prompts": ["List 4-6 example prompts (specific, realistic, copy-pastable)"],\n'
    '  "common_mistakes": ["List 4-5 mistakes beginners make"],\n'
    '  "pro_tips": ["List 4-5 high-leverage tips"],\n'
    '  "tools_to_combine": ["List 3-4 other AI tools that pair well, with 1 line each"],\n'
    '  "faqs": [{"q": "Question", "a": "Answer 40-90 words"}],\n'
    '  "cta_headline": "Conversion subhead under 70 chars",\n'
    '  "cta_body": "1-2 sentences pushing toward Ascendra signup"\n'
    "}\n\n"
    "Rules:\n"
    "- 5-7 step_by_step items in a clear progression.\n"
    "- 5-7 FAQs covering pricing, ethics, common issues, alternatives.\n"
    "- Mention Ascendra Academy at least twice naturally.\n"
    "- Reference real 2026 models; don't invent product names.\n"
    "- Plain prose only inside text fields.\n"
    "- CRITICAL: do NOT invent specific statistics, user counts, revenue numbers, "
    "or social proof (e.g. 'Join 12,000+ founders'). Only mention numbers you would "
    "find documented in the model's public release. When in doubt, omit the number.\n"
)


async def _chat_complete(system: str, user_msg: str, model: str = "claude-sonnet-4-5-20250929") -> str:
    chat = LlmChat(
        api_key=_get_key(),
        session_id=f"seo-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", model)
    return await chat.send_message(UserMessage(text=user_msg))


# ─── Public generators ─────────────────────────────────────────────────────
async def generate_hub_page(model_name: str, model_slug: Optional[str] = None) -> dict:
    user_msg = (
        f"Model: {model_name}\n"
        f"Write the model hub page for /learn/{model_slug or _slug(model_name)}\n"
        "Output JSON only."
    )
    raw = await _chat_complete(HUB_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    # Normalize
    data["model_name"] = model_name
    data["model_slug"] = model_slug or _slug(model_name)
    data["use_case_slug"] = None
    data["kind"] = "hub"
    return data


async def generate_usecase_page(model_name: str, use_case: str,
                                  model_slug: Optional[str] = None,
                                  use_case_slug: Optional[str] = None) -> dict:
    user_msg = (
        f"Model: {model_name}\n"
        f"Use Case: {use_case}\n"
        f"Write the use-case landing page for "
        f"/learn/{model_slug or _slug(model_name)}/{use_case_slug or _slug(use_case)}\n"
        "Output JSON only."
    )
    raw = await _chat_complete(USECASE_SYSTEM, user_msg)
    data = _parse_json_block(raw)
    data["model_name"] = model_name
    data["model_slug"] = model_slug or _slug(model_name)
    data["use_case_name"] = use_case
    data["use_case_slug"] = use_case_slug or _slug(use_case)
    data["kind"] = "use_case"
    return data


# ─── DB helpers ────────────────────────────────────────────────────────────
def _doc_id(model_slug: str, use_case_slug: Optional[str]) -> str:
    if use_case_slug:
        return f"{model_slug}/{use_case_slug}"
    return model_slug


async def upsert_page(db, page: dict, *, status: str = "draft", published: bool = False) -> dict:
    col = db["seo_pages"]
    page_id = _doc_id(page["model_slug"], page.get("use_case_slug"))
    now = datetime.now(timezone.utc)
    existing = await col.find_one({"id": page_id}, {"_id": 0})
    doc = {
        **page,
        "id": page_id,
        "status": "published" if published else status,
        "updated_at": now,
    }
    if existing:
        # Preserve original created_at and published_at when re-saving
        doc["created_at"] = existing.get("created_at", now)
        doc["published_at"] = existing.get("published_at") or (now if published else None)
        await col.update_one({"id": page_id}, {"$set": doc})
    else:
        doc["created_at"] = now
        doc["published_at"] = now if published else None
        await col.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def get_page(db, model_slug: str, use_case_slug: Optional[str] = None) -> Optional[dict]:
    col = db["seo_pages"]
    doc = await col.find_one({"id": _doc_id(model_slug, use_case_slug)}, {"_id": 0})
    return doc


async def list_pages(db, *, status: Optional[str] = None, limit: int = 500) -> list:
    col = db["seo_pages"]
    q: dict = {}
    if status:
        q["status"] = status
    cur = col.find(q, {"_id": 0}).sort("updated_at", -1).limit(limit)
    return await cur.to_list(limit)


async def delete_page(db, model_slug: str, use_case_slug: Optional[str] = None) -> bool:
    col = db["seo_pages"]
    r = await col.delete_one({"id": _doc_id(model_slug, use_case_slug)})
    return r.deleted_count > 0


async def set_status(db, model_slug: str, use_case_slug: Optional[str], status: str) -> Optional[dict]:
    col = db["seo_pages"]
    page_id = _doc_id(model_slug, use_case_slug)
    update: dict = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if status == "published":
        update["published_at"] = datetime.now(timezone.utc)
    await col.update_one({"id": page_id}, {"$set": update})
    return await col.find_one({"id": page_id}, {"_id": 0})


# ─── Sitemap generation ────────────────────────────────────────────────────
def render_sitemap_xml(public_base: str, pages: list, extra_paths: list[str] | None = None) -> str:
    """Render sitemap.xml from published SEO pages + extra known public paths."""
    public_base = public_base.rstrip("/")
    rows: list[str] = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for p in extra_paths or []:
        rows.append(
            f"  <url>\n"
            f"    <loc>{public_base}{p}</loc>\n"
            f"    <lastmod>{now_iso}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )
    for pg in pages:
        if pg.get("status") != "published":
            continue
        loc = f"{public_base}/learn/{pg['model_slug']}"
        if pg.get("use_case_slug"):
            loc += f"/{pg['use_case_slug']}"
        last = pg.get("updated_at") or pg.get("published_at") or pg.get("created_at")
        try:
            last_iso = last.strftime("%Y-%m-%d") if last else now_iso
        except Exception:
            last_iso = now_iso
        rows.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{last_iso}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.7</priority>\n"
            f"  </url>"
        )
    body = "\n".join(rows)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def render_robots_txt(public_base: str) -> str:
    public_base = public_base.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        f"\nSitemap: {public_base}/api/seo/sitemap.xml\n"
    )
