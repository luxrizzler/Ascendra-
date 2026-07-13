"""
revenue.py — Phase 1 of the Revenue Control Center.

Provides:
  • Contacts + Organizations (skeleton models, no lifecycle logic yet)
  • Internal Event engine (idempotent, correlation-tracked)
  • Approval queue (validated state machine)
  • Audit log (append-only, filter + export)
  • Integration status registry (env-var-driven, no live calls)
  • Approved monthly operating budget (Decimal, versioned history)
  • Master safety gate: AUTOMATION_LIVE_ACTIONS_ENABLED

All routes are protected admin routes mounted under /api/admin/revenue/*.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Master safety gate ────────────────────────────────────────────────────
def live_actions_enabled() -> bool:
    return os.environ.get("AUTOMATION_LIVE_ACTIONS_ENABLED", "false").strip().lower() == "true"


# ─── Pydantic models (Phase 1 scope) ───────────────────────────────────────
Lifecycle = Literal[
    "new_lead", "engaged_lead", "assessment_completed", "qualified_lead",
    "offer_recommended", "offer_sent", "checkout_started", "customer",
    "active_subscriber", "organization_customer", "inactive_customer",
    "cancelled_customer", "reactivated_customer",
]

ApprovalStatus = Literal["pending", "approved", "rejected", "expired", "cancelled", "completed"]
_APPROVAL_VALID_TRANSITIONS = {
    "pending": {"approved", "rejected", "expired", "cancelled"},
    "approved": {"completed", "cancelled"},
    "rejected": set(),
    "expired": set(),
    "cancelled": set(),
    "completed": set(),
}


class ContactIn(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    organization_size: Optional[str] = None
    employee_count: Optional[int] = None
    stated_needs: Optional[str] = None
    lead_source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    referred_by_name: Optional[str] = None
    referred_by_email: Optional[str] = None
    source_url: Optional[str] = None
    source_notes: Optional[str] = None
    consent_marketing: bool = False
    simulated: bool = False


class EventIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    source: str = "manual"
    payload: dict = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    contact_id: Optional[str] = None
    organization_id: Optional[str] = None
    simulated: bool = False


class ApprovalIn(BaseModel):
    request_type: str
    requested_action: str
    reason: str
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    financial_amount_usd: Optional[float] = None
    related_contact_id: Optional[str] = None
    related_organization_id: Optional[str] = None
    supporting_records: dict = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    simulated: bool = False


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected", "cancelled", "completed"]
    notes: Optional[str] = None


class BudgetIn(BaseModel):
    monthly_budget_usd: str  # Decimal-safe: string in, converted server-side
    effective_date: datetime
    notes: Optional[str] = None

    @field_validator("monthly_budget_usd")
    @classmethod
    def _decimal_ok(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except Exception:
            raise ValueError("monthly_budget_usd must be a decimal string like '12345.67'")
        if d < 0:
            raise ValueError("monthly_budget_usd cannot be negative")
        return str(d)


# ─── Router ────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/admin/revenue", tags=["revenue"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_email(e: str) -> str:
    return e.strip().lower()


async def _audit(db, *, actor: str, action: str, target_type: str, target_id: str,
                   reason: str = "", correlation_id: Optional[str] = None,
                   simulated: bool = True, result: str = "ok",
                   approval_required: bool = False, approval_status: Optional[str] = None,
                   error: Optional[str] = None, extra: Optional[dict] = None) -> str:
    """Append an audit entry. Immutable by convention (no update/delete endpoints)."""
    doc = {
        "id": str(uuid.uuid4()),
        "actor": actor,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "result": result,
        "error": error,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "approval_required": approval_required,
        "approval_status": approval_status,
        "simulated": simulated,
        "live_actions_enabled_at_time": live_actions_enabled(),
        "created_at": _now(),
        "extra": extra or {},
    }
    await db["audit_log"].insert_one(doc)
    return doc["id"]


async def ensure_indexes(db) -> None:
    """Idempotent index creation. Call from server startup."""
    await db["contacts"].create_index("email_normalized", unique=True)
    await db["contacts"].create_index("lifecycle_stage")
    await db["contacts"].create_index("created_at")
    await db["organizations"].create_index("name_normalized", unique=True)
    await db["internal_events"].create_index("id", unique=True)
    await db["internal_events"].create_index("idempotency_key", unique=True, sparse=True)
    await db["internal_events"].create_index("event_type")
    await db["internal_events"].create_index("correlation_id")
    await db["internal_events"].create_index("created_at")
    await db["approval_queue"].create_index("id", unique=True)
    await db["approval_queue"].create_index("status")
    await db["approval_queue"].create_index("created_at")
    await db["audit_log"].create_index("created_at")
    await db["audit_log"].create_index("actor")
    await db["audit_log"].create_index("action")
    await db["audit_log"].create_index("correlation_id")
    await db["integration_status"].create_index("provider", unique=True)
    await db["operating_budget_history"].create_index("effective_date")
    await db["operating_budget_history"].create_index("created_at")


# ─── System state ──────────────────────────────────────────────────────────
@router.get("/system/state")
async def system_state(request_state=Depends(lambda: None)):
    return {
        "live_actions_enabled": live_actions_enabled(),
        "phase": "phase_1",
        "safety_gate_env": "AUTOMATION_LIVE_ACTIONS_ENABLED",
        "note": "While live_actions_enabled=false, all integrations remain simulated or routed to approval queue.",
        "server_time_utc": _now().isoformat(),
    }


# ─── Contacts ──────────────────────────────────────────────────────────────
def register_routes(db, require_admin):
    """Attach db- and auth-bound routes. Called from server.py after db is ready."""

    @router.post("/contacts")
    async def create_contact(body: ContactIn, admin=Depends(require_admin)):
        email_norm = _norm_email(body.email)
        existing = await db["contacts"].find_one({"email_normalized": email_norm}, {"_id": 0})
        if existing:
            return {"contact": existing, "duplicate": True}
        doc = {
            "id": str(uuid.uuid4()),
            "email": body.email,
            "email_normalized": email_norm,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "phone": body.phone,
            "company_name": body.company_name,
            "business_type": body.business_type,
            "organization_size": body.organization_size,
            "employee_count": body.employee_count,
            "stated_needs": body.stated_needs,
            "readiness_score": None,
            "lead_score": None,
            "lifecycle_stage": "new_lead",
            "recommended_offer_id": None,
            "qualification_reason": None,
            "next_action": None,
            "last_contact_at": None,
            "consent_marketing": body.consent_marketing,
            "customer_status": "prospect",
            "subscription_status": None,
            "attribution": {
                "lead_source": body.lead_source,
                "utm_source": body.utm_source, "utm_medium": body.utm_medium,
                "utm_campaign": body.utm_campaign, "utm_content": body.utm_content,
                "utm_term": body.utm_term,
                "referred_by_name": body.referred_by_name,
                "referred_by_email": body.referred_by_email,
                "source_url": body.source_url, "source_notes": body.source_notes,
                "first_touch_source": body.utm_source or body.lead_source,
                "last_touch_source": body.utm_source or body.lead_source,
            },
            "simulated": body.simulated,
            "created_at": _now(), "updated_at": _now(),
        }
        await db["contacts"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="contact.created",
                       target_type="contact", target_id=doc["id"],
                       reason="manual create", simulated=body.simulated)
        return {"contact": {**doc, "_id": None}, "duplicate": False}

    @router.get("/contacts")
    async def list_contacts(lifecycle: Optional[str] = None, limit: int = Query(50, le=200),
                              admin=Depends(require_admin)):
        q = {}
        if lifecycle:
            q["lifecycle_stage"] = lifecycle
        rows = await db["contacts"].find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"contacts": rows, "count": len(rows)}

    # ─── Internal events ──────────────────────────────────────────────────
    @router.post("/events")
    async def create_event(body: EventIn, admin=Depends(require_admin)):
        # Idempotency: if idempotency_key supplied and already seen, return existing.
        if body.idempotency_key:
            existing = await db["internal_events"].find_one(
                {"idempotency_key": body.idempotency_key}, {"_id": 0})
            if existing:
                return {"event": existing, "duplicate": True}
        doc = {
            "id": str(uuid.uuid4()),
            "event_type": body.event_type,
            "source": body.source,
            "payload": body.payload,
            "contact_id": body.contact_id,
            "organization_id": body.organization_id,
            "idempotency_key": body.idempotency_key,
            "correlation_id": body.correlation_id or str(uuid.uuid4()),
            "processing_status": "pending",
            "retry_count": 0, "error": None,
            "simulated": body.simulated or not live_actions_enabled(),
            "created_at": _now(), "processed_at": None,
        }
        try:
            await db["internal_events"].insert_one(doc)
        except Exception as e:
            # Unique index on idempotency_key raced — return existing
            if body.idempotency_key:
                existing = await db["internal_events"].find_one(
                    {"idempotency_key": body.idempotency_key}, {"_id": 0})
                if existing:
                    return {"event": existing, "duplicate": True}
            raise HTTPException(500, f"event insert failed: {str(e)[:120]}")
        await _audit(db, actor=admin["email"], action="event.created",
                       target_type="internal_event", target_id=doc["id"],
                       correlation_id=doc["correlation_id"], simulated=doc["simulated"])
        return {"event": {**doc, "_id": None}, "duplicate": False}

    @router.get("/events")
    async def list_events(event_type: Optional[str] = None, limit: int = Query(50, le=200),
                            admin=Depends(require_admin)):
        q = {}
        if event_type:
            q["event_type"] = event_type
        rows = await db["internal_events"].find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"events": rows, "count": len(rows)}

    # ─── Approval queue ───────────────────────────────────────────────────
    @router.post("/approvals")
    async def create_approval(body: ApprovalIn, admin=Depends(require_admin)):
        doc = {
            "id": str(uuid.uuid4()),
            "request_type": body.request_type,
            "requested_action": body.requested_action,
            "reason": body.reason,
            "risk_level": body.risk_level,
            "financial_amount_usd": body.financial_amount_usd,
            "related_contact_id": body.related_contact_id,
            "related_organization_id": body.related_organization_id,
            "supporting_records": body.supporting_records,
            "correlation_id": body.correlation_id or str(uuid.uuid4()),
            "status": "pending",
            "decided_by": None, "decided_at": None, "notes": None,
            "expires_at": body.expires_at,
            "simulated": body.simulated or not live_actions_enabled(),
            "created_at": _now(),
        }
        await db["approval_queue"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="approval.requested",
                       target_type="approval", target_id=doc["id"],
                       correlation_id=doc["correlation_id"],
                       approval_required=True, approval_status="pending",
                       simulated=doc["simulated"])
        return {"approval": {**doc, "_id": None}}

    @router.post("/approvals/{approval_id}/decision")
    async def decide_approval(approval_id: str, decision: ApprovalDecision,
                                 admin=Depends(require_admin)):
        item = await db["approval_queue"].find_one({"id": approval_id}, {"_id": 0})
        if not item:
            raise HTTPException(404, "Approval not found")
        current = item["status"]
        target = decision.decision
        if target not in _APPROVAL_VALID_TRANSITIONS.get(current, set()):
            raise HTTPException(400, f"Illegal transition: {current} → {target}")
        updates = {
            "status": target,
            "decided_by": admin["email"],
            "decided_at": _now(),
            "notes": decision.notes,
        }
        await db["approval_queue"].update_one({"id": approval_id}, {"$set": updates})
        await _audit(db, actor=admin["email"], action=f"approval.{target}",
                       target_type="approval", target_id=approval_id,
                       correlation_id=item.get("correlation_id"),
                       approval_required=True, approval_status=target,
                       reason=decision.notes or "", simulated=item.get("simulated", True))
        return {"approval": {**item, **updates}}

    @router.get("/approvals")
    async def list_approvals(status: Optional[str] = None, limit: int = Query(100, le=500),
                                admin=Depends(require_admin)):
        q = {}
        if status:
            q["status"] = status
        rows = await db["approval_queue"].find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"approvals": rows, "count": len(rows)}

    # ─── Audit log ────────────────────────────────────────────────────────
    @router.get("/audit")
    async def list_audit(actor: Optional[str] = None, action: Optional[str] = None,
                            simulated: Optional[bool] = None,
                            limit: int = Query(100, le=500),
                            admin=Depends(require_admin)):
        q: dict = {}
        if actor: q["actor"] = actor
        if action: q["action"] = action
        if simulated is not None: q["simulated"] = simulated
        rows = await db["audit_log"].find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"entries": rows, "count": len(rows)}

    @router.get("/audit/export")
    async def export_audit(limit: int = Query(1000, le=5000), admin=Depends(require_admin)):
        rows = await db["audit_log"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        await _audit(db, actor=admin["email"], action="audit.exported",
                       target_type="audit_log", target_id="bulk",
                       reason=f"exported {len(rows)} rows", simulated=True)
        return {"entries": rows, "count": len(rows), "exported_at": _now().isoformat()}

    # ─── Integration status ───────────────────────────────────────────────
    _KNOWN_INTEGRATIONS = ["stripe", "resend", "buffer", "gmail", "gcal"]

    @router.get("/integrations")
    async def integration_status(admin=Depends(require_admin)):
        """Report which integrations have credentials present. No live calls made."""
        rows = []
        env_checks = {
            "stripe": ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"],
            "resend": ["RESEND_API_KEY"],
            "buffer": ["BUFFER_ACCESS_TOKEN"],
            "gmail": ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET"],
            "gcal": ["GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET"],
        }
        live = live_actions_enabled()
        for provider in _KNOWN_INTEGRATIONS:
            needed = env_checks.get(provider, [])
            present = all(os.environ.get(k, "").strip() for k in needed)
            stored = await db["integration_status"].find_one({"provider": provider}, {"_id": 0}) or {}
            rows.append({
                "provider": provider,
                "configured": present,
                "enabled": present,
                "environment": "sandbox" if not live else "live",
                "live_actions_permitted": present and live,
                "env_keys_expected": needed,
                "last_successful_connection": stored.get("last_successful_connection"),
                "last_failed_connection": stored.get("last_failed_connection"),
                "error_message": stored.get("error_message"),
                "state": "live" if (present and live) else ("simulated" if present else "unavailable"),
            })
        return {"integrations": rows, "live_actions_enabled": live}

    # ─── Operating budget (Phase-1 placeholder + versioned history) ───────
    @router.get("/budget")
    async def get_budget(admin=Depends(require_admin)):
        current = await db["operating_budget_history"].find_one(
            {}, {"_id": 0}, sort=[("effective_date", -1)])
        history = await db["operating_budget_history"].find({}, {"_id": 0}) \
            .sort("effective_date", -1).limit(50).to_list(50)
        return {
            "current": current,
            "history": history,
            "note": "Approved monthly operating budget. Phase 3 will use this + actual expenses (when 3+ months of history exist) for reserve target calculation.",
        }

    @router.post("/budget")
    async def set_budget(body: BudgetIn, admin=Depends(require_admin)):
        doc = {
            "id": str(uuid.uuid4()),
            "monthly_budget_usd": body.monthly_budget_usd,  # Decimal-safe string
            "effective_date": body.effective_date,
            "notes": body.notes,
            "updated_by": admin["email"],
            "created_at": _now(),
        }
        await db["operating_budget_history"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="budget.updated",
                       target_type="operating_budget", target_id=doc["id"],
                       reason=body.notes or "budget set",
                       extra={"monthly_budget_usd": body.monthly_budget_usd},
                       simulated=True)
        return {"budget": {**doc, "_id": None}}

    # ─── Dashboard summary (Phase 1 lightweight) ──────────────────────────
    @router.get("/summary")
    async def summary(admin=Depends(require_admin)):
        counts = {
            "contacts": await db["contacts"].count_documents({}),
            "contacts_simulated": await db["contacts"].count_documents({"simulated": True}),
            "events": await db["internal_events"].count_documents({}),
            "events_pending": await db["internal_events"].count_documents({"processing_status": "pending"}),
            "approvals_pending": await db["approval_queue"].count_documents({"status": "pending"}),
            "approvals_approved": await db["approval_queue"].count_documents({"status": "approved"}),
            "audit_entries": await db["audit_log"].count_documents({}),
        }
        return {
            "counts": counts,
            "live_actions_enabled": live_actions_enabled(),
            "phase": "phase_1",
            "data_status": "no live revenue data yet — Phase 3 wires financial ledger",
        }

    return router
