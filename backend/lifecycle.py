"""
lifecycle.py — Lead capture + Welcome drip + Lifecycle email automation.

Triggers (all run daily via APScheduler at 09:00 UTC):
  • Welcome drip: Day 2, Day 5, Day 10, Day 14 after lead capture or signup
  • Trial ending: 1 day before $2.99 trial converts to full price
  • Winback: 7 days after subscription cancellation
  • Streak saver: 14 days since last_active_at
  • Annual upsell: monthly subscriber after 90 days of consecutive billing

All sends are idempotent — each user/lead doc tracks last_*_sent timestamps so the
same email is never sent twice for the same trigger period.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from apscheduler.triggers.cron import CronTrigger

import email_service as _email

log = logging.getLogger("lifecycle")

# ─── Config ────────────────────────────────────────────────────────────────
PUBLIC_BASE = (os.environ.get("PUBLIC_WEB_URL") or "https://repo-to-site-2.preview.emergentagent.com").rstrip("/")
TIERS = {
    "ascender":    {"monthly": 9.99,  "annual": 99.0},
    "pathfinder":  {"monthly": 19.99, "annual": 199.0},
    "sage":        {"monthly": 29.99, "annual": 299.0},
}
DRIP_DAYS = {2: "welcome_d2", 5: "welcome_d5", 10: "welcome_d10", 14: "welcome_d14"}


# ─── Leads collection ──────────────────────────────────────────────────────
async def _leads_col(db):
    return db["leads"]


async def _users_col(db):
    return db["users"]


async def capture_lead(db, email: str, name: Optional[str] = None, source: Optional[str] = None) -> dict:
    """Idempotent: upsert lead by email."""
    email = email.strip().lower()
    col = await _leads_col(db)
    now = datetime.now(timezone.utc)
    existing = await col.find_one({"email": email}, {"_id": 0})
    if existing:
        if name and not existing.get("name"):
            await col.update_one({"email": email}, {"$set": {"name": name, "updated_at": now}})
        return existing
    doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "source": source or "landing",
        "created_at": now,
        "updated_at": now,
        "signed_up_user_id": None,
        "drip_sent": {},  # day -> timestamp
        "lead_magnet_sent_at": None,
    }
    await col.insert_one(dict(doc))
    return doc


async def send_lead_magnet_email(db, email: str, name: Optional[str] = None) -> dict:
    """Send the Day 0 lead magnet immediately + record."""
    col = await _leads_col(db)
    lead = await col.find_one({"email": email}, {"_id": 0})
    if not lead:
        return {"ok": False, "reason": "lead_not_found"}
    if lead.get("lead_magnet_sent_at"):
        return {"ok": True, "skipped": True, "reason": "already_sent"}
    r = _email.send_lead_magnet(
        to=email, name=name or lead.get("name"),
        roadmap_url=f"{PUBLIC_BASE}/resources/ai-roadmap",
        signup_url=f"{PUBLIC_BASE}/signup?email={email}",
    )
    if r.get("ok"):
        await col.update_one({"email": email}, {"$set": {"lead_magnet_sent_at": datetime.now(timezone.utc)}})
    return r


# ─── Welcome drip scan ─────────────────────────────────────────────────────
async def scan_welcome_drip(db) -> dict:
    """Daily scan: send Day 2/5/10/14 emails to leads + signed-up users."""
    now = datetime.now(timezone.utc)
    sent = {"d2": 0, "d5": 0, "d10": 0, "d14": 0}
    skipped = 0
    failed = 0

    # Combine leads + users (signed-up users with created_at within last 30d)
    leads = await (await _leads_col(db)).find({}, {"_id": 0}).to_list(5000)
    users = await (await _users_col(db)).find(
        {"created_at": {"$gte": now - timedelta(days=30)}}, {"_id": 0}
    ).to_list(5000)

    pricing_url = f"{PUBLIC_BASE}/pricing"
    dashboard_url = f"{PUBLIC_BASE}/dashboard"
    lesson_url = f"{PUBLIC_BASE}/paths"

    async def _process(record, source: str, anchor_field: str):
        nonlocal skipped, failed
        anchor = record.get(anchor_field) or record.get("created_at")
        if not anchor:
            return
        # MongoDB may strip tzinfo when reading datetimes back; coerce to UTC.
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=timezone.utc)
        age = now - anchor
        drip_sent = record.get("drip_sent") or {}
        for day, key in DRIP_DAYS.items():
            window_low = timedelta(days=day - 0.5)
            window_high = timedelta(days=day + 0.5)
            if not (window_low <= age <= window_high):
                continue
            if drip_sent.get(str(day)):
                continue
            try:
                fn = getattr(_email, f"send_{key}")
                args = {"to": record["email"], "name": record.get("name")}
                if key == "welcome_d2":
                    args["lesson_url"] = lesson_url
                elif key == "welcome_d5":
                    args["pricing_url"] = pricing_url
                elif key == "welcome_d10":
                    args["dashboard_url"] = dashboard_url
                elif key == "welcome_d14":
                    args["pricing_url"] = pricing_url
                r = fn(**args)
                if r.get("ok"):
                    col = await _leads_col(db) if source == "lead" else await _users_col(db)
                    await col.update_one(
                        {"email": record["email"]},
                        {"$set": {f"drip_sent.{day}": now}},
                    )
                    sent[f"d{day}"] += 1
                else:
                    failed += 1
            except Exception as e:
                log.exception(f"drip send failed for {record['email']} day={day}: {e}")
                failed += 1

    for lead in leads:
        await _process(lead, "lead", "lead_magnet_sent_at")
    for user in users:
        # Skip users who already have a lead with drips (avoid duplicate)
        existing_lead = await (await _leads_col(db)).find_one({"email": user.get("email")}, {"_id": 0})
        if existing_lead and existing_lead.get("drip_sent"):
            continue
        await _process(user, "user", "created_at")

    return {"sent": sent, "skipped": skipped, "failed": failed, "scanned_leads": len(leads), "scanned_users": len(users)}


# ─── Lifecycle scans ───────────────────────────────────────────────────────
def _aware(dt):
    """Coerce a possibly-naive datetime (e.g. from MongoDB) to UTC-aware."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def scan_trial_ending(db) -> dict:
    """Find users whose trial ends in ~1 day. Idempotent per period_end."""
    now = datetime.now(timezone.utc)
    window_low = now + timedelta(hours=18)
    window_high = now + timedelta(hours=30)
    users = await (await _users_col(db)).find({
        "subscription_status": {"$in": ["trialing", "active"]},
        "tier_expires_at": {"$gte": window_low, "$lte": window_high},
    }, {"_id": 0}).to_list(2000)
    sent, skipped = 0, 0
    for u in users:
        if not u.get("email"):
            continue
        last = _aware(u.get("last_trial_ending_sent_for"))
        ends = _aware(u.get("tier_expires_at"))
        if last and ends and abs((last - ends).total_seconds()) < 86400:
            skipped += 1
            continue
        tier = u.get("tier") or "ascender"
        interval = u.get("subscription_interval") or "monthly"
        amount = TIERS.get(tier, {}).get(interval, 9.99)
        try:
            r = _email.send_trial_ending(
                to=u["email"], name=u.get("name"),
                tier=tier,
                charge_date_str=ends.strftime("%B %-d, %Y") if ends else "tomorrow",
                amount_usd=float(amount),
                portal_url=f"{PUBLIC_BASE}/profile",
            )
            if r.get("ok"):
                await (await _users_col(db)).update_one(
                    {"id": u["id"]},
                    {"$set": {"last_trial_ending_sent_for": ends, "last_trial_ending_sent_at": now}},
                )
                sent += 1
        except Exception as e:
            log.exception(f"trial_ending failed for {u.get('email')}: {e}")
    return {"sent": sent, "skipped": skipped, "scanned": len(users)}


async def scan_winback(db) -> dict:
    """Send winback to users whose subscription canceled ~7 days ago."""
    now = datetime.now(timezone.utc)
    low = now - timedelta(days=7, hours=12)
    high = now - timedelta(days=6, hours=12)
    users = await (await _users_col(db)).find({
        "subscription_status": "canceled",
        "subscription_canceled_at": {"$gte": low, "$lte": high},
    }, {"_id": 0}).to_list(2000)
    sent = 0
    for u in users:
        if u.get("last_winback_sent_at"):
            continue
        try:
            r = _email.send_winback(
                to=u["email"], name=u.get("name"),
                tier=u.get("last_tier") or u.get("tier") or "ascender",
                signup_url=f"{PUBLIC_BASE}/pricing",
            )
            if r.get("ok"):
                await (await _users_col(db)).update_one(
                    {"id": u["id"]},
                    {"$set": {"last_winback_sent_at": now}},
                )
                sent += 1
        except Exception as e:
            log.exception(f"winback failed for {u.get('email')}: {e}")
    return {"sent": sent, "scanned": len(users)}


async def scan_streak_saver(db) -> dict:
    """Send streak-saver to users with no activity in ~14 days."""
    now = datetime.now(timezone.utc)
    low = now - timedelta(days=15)
    high = now - timedelta(days=13)
    users = await (await _users_col(db)).find({
        "last_active_at": {"$gte": low, "$lte": high},
    }, {"_id": 0}).to_list(2000)
    sent = 0
    for u in users:
        if not u.get("email"):
            continue
        last = _aware(u.get("last_streak_saver_sent_at"))
        if last and (now - last).days < 30:
            continue
        try:
            last_active = _aware(u.get("last_active_at"))
            days_away = (now - last_active).days if last_active else 14
            r = _email.send_streak_saver(
                to=u["email"], name=u.get("name"),
                days_away=days_away,
                dashboard_url=f"{PUBLIC_BASE}/dashboard",
            )
            if r.get("ok"):
                await (await _users_col(db)).update_one(
                    {"id": u["id"]},
                    {"$set": {"last_streak_saver_sent_at": now}},
                )
                sent += 1
        except Exception as e:
            log.exception(f"streak_saver failed for {u.get('email')}: {e}")
    return {"sent": sent, "scanned": len(users)}


async def scan_annual_upsell(db) -> dict:
    """Send annual upsell to monthly subscribers at 90 days."""
    now = datetime.now(timezone.utc)
    low = now - timedelta(days=92)
    high = now - timedelta(days=88)
    users = await (await _users_col(db)).find({
        "subscription_status": "active",
        "subscription_interval": "monthly",
        "tier": {"$in": ["pathfinder", "sage"]},
        "subscription_started_at": {"$gte": low, "$lte": high},
    }, {"_id": 0}).to_list(2000)
    sent = 0
    for u in users:
        if not u.get("email"):
            continue
        if u.get("last_annual_upsell_sent_at"):
            continue
        tier = u.get("tier")
        monthly = TIERS.get(tier, {}).get("monthly", 19.99)
        annual = TIERS.get(tier, {}).get("annual", 199.0)
        savings = (monthly * 12) - annual
        try:
            r = _email.send_annual_upsell(
                to=u["email"], name=u.get("name"),
                tier=tier, monthly_price=monthly, annual_price=annual, savings_usd=savings,
                pricing_url=f"{PUBLIC_BASE}/pricing",
            )
            if r.get("ok"):
                await (await _users_col(db)).update_one(
                    {"id": u["id"]},
                    {"$set": {"last_annual_upsell_sent_at": now}},
                )
                sent += 1
        except Exception as e:
            log.exception(f"annual_upsell failed for {u.get('email')}: {e}")
    return {"sent": sent, "scanned": len(users)}


async def run_all_lifecycle(db) -> dict:
    """Master daily scan: runs all lifecycle email triggers."""
    return {
        "drip":         await scan_welcome_drip(db),
        "trial_ending": await scan_trial_ending(db),
        "winback":      await scan_winback(db),
        "streak_saver": await scan_streak_saver(db),
        "annual_upsell": await scan_annual_upsell(db),
        "run_at": datetime.now(timezone.utc).isoformat(),
    }


def register_jobs(scheduler, db) -> None:
    """Register the daily lifecycle scan on an existing AsyncIOScheduler."""
    import asyncio as _asyncio
    scheduler.add_job(
        lambda: _asyncio.create_task(run_all_lifecycle(db)),
        CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="lifecycle_daily_scan", replace_existing=True,
    )
    log.info("lifecycle scheduler registered (daily 09:00 UTC)")
