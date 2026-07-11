"""
content_scanner.py
──────────────────
Ascendra Content Health system.

Scans all lessons for signs of decay and auto-refreshes them in place:
  1. MODEL DRIFT — mentions of outdated AI model / product names.
  2. TIME-BASED STALENESS — lessons untouched for >= N days (default 120).
  3. DEAD LINKS — external URLs in lesson body that return 404 / connection error.

When auto-update is enabled, each flagged lesson is:
  a) Backed up to `content_history` (full snapshot + reason)
  b) Regenerated via `ai_studio.refresh_lesson()` (Claude 4.5)
  c) Persisted in place (same lesson id — user progress preserved)
  d) Logged to `content_audit` with before/after summary
  e) Available to revert from the /admin/content-health UI

Runs weekly via APScheduler; also exposed as a manual admin action.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

import ai_studio
from llm_retry import llm_call_with_retry, is_transient_llm_error

log = logging.getLogger("content_scanner")

# --- Config ------------------------------------------------------------
STALE_DAYS_DEFAULT = 120
DEAD_LINK_TIMEOUT_SEC = 6
DEAD_LINK_STATUS_CODES = {404, 410}  # Treat these as dead
# We treat 5xx as transient and don't flag them
URL_REGEX = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _extract_text_from_lesson(lesson: Dict[str, Any]) -> str:
    """Concatenate all text-fields of a lesson into a single blob."""
    parts = [lesson.get("title") or ""]
    for c in lesson.get("cards") or []:
        parts.append((c.get("title") or "") + " " + (c.get("body") or ""))
        # Also include quiz-adjacent card fields
        parts.append(c.get("question") or "")
        parts.append(c.get("prompt") or "")
        parts.append(c.get("instruction") or "")
        parts.append(c.get("explanation") or "")
        for opt in c.get("options") or []:
            parts.append(opt)
    q = lesson.get("quiz") or {}
    parts.append(q.get("question") or "")
    for opt in q.get("options") or []:
        parts.append(opt)
    parts.append(q.get("explanation") or "")
    return "\n".join([p for p in parts if p])


def _extract_urls(text: str) -> List[str]:
    seen = set()
    out = []
    for m in URL_REGEX.finditer(text):
        u = m.group(0).rstrip(".,);:!?")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def _check_link(client: httpx.AsyncClient, url: str) -> Tuple[str, Optional[int], Optional[str]]:
    """HEAD-then-GET fallback. Returns (url, status_code, error_str)."""
    try:
        # HEAD first (fast). Many sites 405 HEAD, so fall back to GET.
        try:
            r = await client.head(url, follow_redirects=True, timeout=DEAD_LINK_TIMEOUT_SEC)
            if r.status_code < 400 or r.status_code == 405:
                if r.status_code == 405:
                    r = await client.get(url, follow_redirects=True, timeout=DEAD_LINK_TIMEOUT_SEC)
            return (url, r.status_code, None)
        except httpx.RequestError:
            r = await client.get(url, follow_redirects=True, timeout=DEAD_LINK_TIMEOUT_SEC)
            return (url, r.status_code, None)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
        return (url, None, str(e)[:200])
    except Exception as e:
        return (url, None, str(e)[:200])


# --- Scanning ----------------------------------------------------------
async def scan_all_lessons(
    *,
    db,
    stale_days: int = STALE_DAYS_DEFAULT,
    check_dead_links: bool = True,
) -> Dict[str, Any]:
    """Walk every lesson and return the full findings report.

    Findings shape:
      {
        "scanned_at": iso,
        "stale_days": 120,
        "counts": {"outdated_model": N, "stale": N, "dead_links": N, "total": N},
        "findings": [
           {path_id, module_id, lesson_id, title,
            outdated_terms: [...], is_stale: bool, dead_links: [{url, status}, ...],
            last_updated: iso}
        ]
      }
    """
    stale_threshold = _now() - timedelta(days=stale_days)
    outdated_hits = 0
    stale_hits = 0
    dead_link_hits = 0
    findings: List[Dict[str, Any]] = []

    # Gather every lesson with its parent-path metadata
    all_lessons: List[Tuple[Dict, Dict, Dict]] = []
    async for p in db["curriculum_paths"].find({}):
        for m in p.get("modules", []):
            for lsn in m.get("lessons", []):
                all_lessons.append((p, m, lsn))

    # Prepare a shared http client for link checks
    async with httpx.AsyncClient(headers={"User-Agent": "AscendraContentScanner/1.0"}) as client:
        for p, m, lsn in all_lessons:
            text = _extract_text_from_lesson(lsn)
            outdated_terms = ai_studio.scan_outdated_terms(text)
            last_updated = lsn.get("updated_at") or lsn.get("created_at")
            if isinstance(last_updated, datetime):
                lu = last_updated if last_updated.tzinfo else last_updated.replace(tzinfo=timezone.utc)
            else:
                lu = None
            is_stale = lu is not None and lu < stale_threshold

            dead_links: List[Dict[str, Any]] = []
            if check_dead_links:
                urls = _extract_urls(text)
                # Cap per-lesson to avoid runaway scans
                for u in urls[:15]:
                    _, status, err = await _check_link(client, u)
                    if (status in DEAD_LINK_STATUS_CODES) or (err is not None and status is None):
                        dead_links.append({"url": u, "status": status, "error": err[:120] if err else None})

            if outdated_terms or is_stale or dead_links:
                findings.append({
                    "path_id": p.get("id"),
                    "path_title": p.get("title"),
                    "module_id": m.get("id"),
                    "module_title": m.get("title"),
                    "lesson_id": lsn.get("id"),
                    "lesson_title": lsn.get("title"),
                    "outdated_terms": outdated_terms,
                    "is_stale": is_stale,
                    "dead_links": dead_links,
                    "last_updated": lu.isoformat() if lu else None,
                })
                if outdated_terms: outdated_hits += 1
                if is_stale: stale_hits += 1
                if dead_links: dead_link_hits += 1

    return {
        "scanned_at": _now().isoformat(),
        "stale_days": stale_days,
        "counts": {
            "outdated_model": outdated_hits,
            "stale": stale_hits,
            "dead_links": dead_link_hits,
            "total": len(findings),
            "lessons_scanned": len(all_lessons),
        },
        "findings": findings,
    }


# --- Auto-update -------------------------------------------------------
async def auto_update_lesson(
    *,
    db,
    finding: Dict[str, Any],
    trigger: str = "auto",
) -> Dict[str, Any]:
    """Backup the current lesson, refresh it via Claude, and persist.

    Returns audit record. Raises on failure (does NOT persist a bad refresh).
    """
    path_id = finding["path_id"]
    module_id = finding["module_id"]
    lesson_id = finding["lesson_id"]

    # Find current lesson state
    path_doc = await db["curriculum_paths"].find_one({"id": path_id}, {"modules": 1})
    if not path_doc:
        raise LookupError(f"Path {path_id} not found")
    old_lesson: Optional[Dict[str, Any]] = None
    for m in path_doc.get("modules", []):
        if m.get("id") != module_id: continue
        for lsn in m.get("lessons", []):
            if lsn.get("id") == lesson_id:
                old_lesson = lsn
                break
        break
    if not old_lesson:
        raise LookupError(f"Lesson {lesson_id} not found in {path_id}/{module_id}")

    # 1. Backup — write full snapshot to content_history
    history_id = str(uuid.uuid4())
    await db["content_history"].insert_one({
        "id": history_id,
        "path_id": path_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "snapshot": old_lesson,
        "reason": {
            "outdated_terms": finding.get("outdated_terms", []),
            "is_stale": finding.get("is_stale", False),
            "dead_links": finding.get("dead_links", []),
        },
        "trigger": trigger,
        "created_at": _now(),
    })

    # 2. Refresh via ai_studio.refresh_lesson (Claude)
    try:
        async def _do_refresh():
            return await ai_studio.refresh_lesson(old_lesson)
        refreshed = await llm_call_with_retry(_do_refresh, max_retries=3, label="content-refresh")
    except Exception as e:
        log.warning(f"[content-scanner] refresh failed for {lesson_id}: {e}")
        # Log the failed attempt for the admin audit trail
        await db["content_audit"].insert_one({
            "id": str(uuid.uuid4()),
            "path_id": path_id,
            "module_id": module_id,
            "lesson_id": lesson_id,
            "lesson_title": old_lesson.get("title"),
            "history_id": history_id,
            "status": "failed",
            "error": str(e)[:400],
            "trigger": trigger,
            "reason": {
                "outdated_terms": finding.get("outdated_terms", []),
                "is_stale": finding.get("is_stale", False),
                "dead_links": finding.get("dead_links", []),
            },
            "created_at": _now(),
        })
        raise

    # 3. Persist refreshed lesson in place
    refreshed["id"] = lesson_id  # preserve id
    refreshed["updated_at"] = _now()
    # Preserve fields that shouldn't be blown away by regeneration
    for k in ("interactive_v", "tier"):
        if k in old_lesson and k not in refreshed:
            refreshed[k] = old_lesson[k]

    # Use array filters to update the exact lesson
    result = await db["curriculum_paths"].update_one(
        {"id": path_id},
        {"$set": {"modules.$[m].lessons.$[l]": refreshed}},
        array_filters=[{"m.id": module_id}, {"l.id": lesson_id}],
    )

    audit_id = str(uuid.uuid4())
    await db["content_audit"].insert_one({
        "id": audit_id,
        "path_id": path_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "lesson_title": refreshed.get("title", old_lesson.get("title")),
        "history_id": history_id,
        "status": "success" if result.modified_count > 0 else "no-op",
        "old_title": old_lesson.get("title"),
        "new_title": refreshed.get("title"),
        "old_card_count": len(old_lesson.get("cards", [])),
        "new_card_count": len(refreshed.get("cards", [])),
        "trigger": trigger,
        "reason": {
            "outdated_terms": finding.get("outdated_terms", []),
            "is_stale": finding.get("is_stale", False),
            "dead_links": finding.get("dead_links", []),
        },
        "created_at": _now(),
    })
    return {
        "audit_id": audit_id,
        "history_id": history_id,
        "lesson_id": lesson_id,
        "status": "success" if result.modified_count > 0 else "no-op",
    }


async def revert_lesson(*, db, history_id: str) -> Dict[str, Any]:
    """Restore a lesson from a content_history snapshot."""
    hist = await db["content_history"].find_one({"id": history_id})
    if not hist:
        raise LookupError(f"History {history_id} not found")
    snap = hist.get("snapshot")
    if not snap:
        raise LookupError("Snapshot missing")
    snap["id"] = hist["lesson_id"]
    snap["updated_at"] = _now()
    result = await db["curriculum_paths"].update_one(
        {"id": hist["path_id"]},
        {"$set": {"modules.$[m].lessons.$[l]": snap}},
        array_filters=[{"m.id": hist["module_id"]}, {"l.id": hist["lesson_id"]}],
    )
    audit_id = str(uuid.uuid4())
    await db["content_audit"].insert_one({
        "id": audit_id,
        "path_id": hist["path_id"],
        "module_id": hist["module_id"],
        "lesson_id": hist["lesson_id"],
        "lesson_title": snap.get("title"),
        "history_id": history_id,
        "status": "reverted",
        "trigger": "admin-revert",
        "created_at": _now(),
    })
    return {"audit_id": audit_id, "modified": result.modified_count}


# --- Scheduled run -----------------------------------------------------
_LAST_RUN: Dict[str, Any] = {
    "started_at": None,
    "finished_at": None,
    "scanned": 0,
    "updated": 0,
    "failed": 0,
    "in_progress": False,
}


async def scan_and_auto_update(
    *,
    db,
    stale_days: int = STALE_DAYS_DEFAULT,
    check_dead_links: bool = True,
    max_updates_per_run: int = 25,
    trigger: str = "scheduled",
) -> Dict[str, Any]:
    """Full scan + auto-update pipeline. Safe to call from scheduler or admin UI."""
    global _LAST_RUN
    if _LAST_RUN["in_progress"]:
        return {"already_running": True, **_LAST_RUN}
    _LAST_RUN = {"started_at": _now().isoformat(), "in_progress": True,
                 "scanned": 0, "updated": 0, "failed": 0, "finished_at": None,
                 "trigger": trigger}
    try:
        report = await scan_all_lessons(db=db, stale_days=stale_days, check_dead_links=check_dead_links)
        _LAST_RUN["scanned"] = report["counts"]["lessons_scanned"]
        _LAST_RUN["counts"] = report["counts"]
        updated = 0
        failed = 0
        # Only auto-update outdated_terms or stale; dead_links alone shouldn't
        # trigger a full lesson rewrite (Claude won't know which URL to swap).
        # We still surface them in the report for the admin to manually fix.
        candidates = [f for f in report["findings"] if f["outdated_terms"] or f["is_stale"]]
        for finding in candidates[:max_updates_per_run]:
            try:
                await auto_update_lesson(db=db, finding=finding, trigger=trigger)
                updated += 1
            except Exception as e:
                failed += 1
                log.warning(f"[content-scanner] auto-update failed for {finding.get('lesson_id')}: {e}")
        _LAST_RUN["updated"] = updated
        _LAST_RUN["failed"] = failed
        _LAST_RUN["dead_links_only"] = len([f for f in report["findings"] if f["dead_links"] and not f["outdated_terms"] and not f["is_stale"]])
        return {
            **_LAST_RUN,
            "report": report,
        }
    finally:
        _LAST_RUN["in_progress"] = False
        _LAST_RUN["finished_at"] = _now().isoformat()


def get_last_run_status() -> Dict[str, Any]:
    return dict(_LAST_RUN)


# --- APScheduler registration -----------------------------------------
def register_scheduler(sched, db) -> None:
    """Register the weekly auto-scan job. Runs every Sunday at 03:00 UTC."""
    async def _wrapped():
        try:
            log.info("[content-scanner] weekly auto-scan starting")
            r = await scan_and_auto_update(db=db, trigger="scheduled-weekly")
            log.info(f"[content-scanner] weekly auto-scan done: {r.get('counts', {})} updated={r.get('updated')} failed={r.get('failed')}")
        except Exception as e:
            log.exception(f"[content-scanner] weekly auto-scan crashed: {e}")

    try:
        sched.add_job(
            _wrapped,
            "cron",
            day_of_week="sun",
            hour=3,
            minute=0,
            id="content_scanner_weekly",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        log.info("[content-scanner] weekly auto-scan registered (Sun 03:00 UTC)")
    except Exception as e:
        log.exception(f"[content-scanner] scheduler registration failed: {e}")
