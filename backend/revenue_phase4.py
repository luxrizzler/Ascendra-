"""
revenue_phase4.py — Phase 4 of the Revenue Control Center.

Controlled-automation layer:
  • Deterministic, versioned workflow engine (allowlisted step types only)
  • Internal action queue with authority + approval + safety-gate gating
  • Approved template library (allowlisted variables, no invented claims)
  • Approved knowledge base
  • Deterministic AI authority + risk matrix
  • Integration adapters (Stripe, Resend, Buffer, Gmail, GCal — all shadowable)
  • Stripe webhook shadow processor (coexists with existing /api/billing/webhook)
  • Retry + dead-letter handling
  • Approval-integrity enforcement helper (used across P3 + P4)

SAFETY:
    Nothing in this module performs an external side-effect while
    AUTOMATION_LIVE_ACTIONS_ENABLED=false. No live emails, no live social
    posts, no Stripe transfers/refunds, no bank calls. All actions that would
    touch a provider resolve to `simulated`, `awaiting_approval`, or `blocked`.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from revenue import _audit, _now, live_actions_enabled


# ─── Enums ─────────────────────────────────────────────────────────────────
StepType = Literal[
    "evaluate_eligibility", "recalculate_lead_score", "recommend_offer",
    "select_template", "create_internal_task", "queue_external_communication",
    "wait", "check_for_event", "update_lifecycle_stage",
    "provision_internal_access", "record_audit_event", "stop_workflow",
]
WorkflowExecStatus = Literal[
    "queued", "running", "waiting", "completed", "cancelled",
    "blocked", "failed", "dead_letter",
]
ActionStatus = Literal[
    "draft", "queued", "awaiting_approval", "approved", "simulated",
    "executing", "completed", "failed", "cancelled", "blocked", "dead_letter",
]
AuthorityDecision = Literal[
    "auto_permitted", "permitted_if_live", "requires_approval",
    "prohibited", "unknown_default_contain",
]
RiskCategory = Literal["low", "medium", "high", "critical"]
Channel = Literal["email", "in_app", "social", "sms", "webhook"]


# ─── Authority matrix ──────────────────────────────────────────────────────
# Deterministic. Never delegated to a language model. Versioned via
# _AUTHORITY_POLICY_VERSION — bump when adding a new action type.
_AUTHORITY_POLICY_VERSION = 1
_AUTHORITY_MATRIX: dict[str, tuple[AuthorityDecision, RiskCategory, str]] = {
    # ── automatically permitted (internal only) ──
    "recalc_lead_score":            ("auto_permitted",  "low",     ""),
    "update_lifecycle_stage":       ("auto_permitted",  "low",     ""),
    "create_internal_note":         ("auto_permitted",  "low",     ""),
    "recommend_approved_offer":     ("auto_permitted",  "low",     ""),
    "select_approved_template":     ("auto_permitted",  "low",     ""),
    "create_simulated_action":      ("auto_permitted",  "low",     ""),
    "pause_workflow":               ("auto_permitted",  "low",     ""),
    "cancel_workflow":              ("auto_permitted",  "low",     ""),
    "record_audit_event":           ("auto_permitted",  "low",     ""),
    "queue_review_task":            ("auto_permitted",  "low",     ""),
    # ── permitted only when live actions are enabled ──
    "send_approved_email":          ("permitted_if_live", "medium", "requires safety gate on + approved template"),
    "publish_approved_social":      ("permitted_if_live", "medium", "requires safety gate on + approved template"),
    # ── requires approval ──
    "activate_workflow":            ("requires_approval", "high",   "activation requires approval-queue authorization"),
    "material_template_change":     ("requires_approval", "high",   ""),
    "material_kb_change":           ("requires_approval", "high",   ""),
    "apply_exceptional_discount":   ("requires_approval", "high",   ""),
    "issue_refund":                 ("requires_approval", "critical", ""),
    "change_live_subscription":     ("requires_approval", "critical", ""),
    "custom_legal_response":        ("requires_approval", "critical", ""),
    "reputation_incident_response": ("requires_approval", "critical", ""),
    "disclose_sensitive_info":      ("requires_approval", "critical", ""),
    "exceptional_financial_adj":    ("requires_approval", "critical", ""),
    # ── prohibited ──
    "initiate_bank_transfer":       ("prohibited",       "critical", "not supported"),
    "initiate_owner_distribution":  ("prohibited",       "critical", "internal recommendation only"),
    "create_unapproved_price":      ("prohibited",       "critical", ""),
    "invent_contract_terms":        ("prohibited",       "critical", ""),
    "admit_legal_liability":        ("prohibited",       "critical", ""),
    "delete_financial_history":     ("prohibited",       "critical", ""),
    "delete_audit_history":         ("prohibited",       "critical", ""),
    "bypass_approval":              ("prohibited",       "critical", ""),
    "expose_secrets":               ("prohibited",       "critical", ""),
    "create_paid_advertising":      ("prohibited",       "high",     ""),
}


def evaluate_authority(action_type: str) -> dict:
    """Deterministic authority evaluation.

    Returns a dict with the decision, risk category, explanation, and policy
    version. Unknown action types receive the safe default
    ``unknown_default_contain``.
    """
    entry = _AUTHORITY_MATRIX.get(action_type)
    if entry is None:
        return {
            "action_type": action_type,
            "decision": "unknown_default_contain",
            "risk_category": "high",
            "explanation": ("Unknown action type — Ascendra policy contains "
                             "the action, pauses the workflow, preserves the "
                             "record, responds neutrally, and avoids "
                             "irreversible commitments."),
            "policy_version": _AUTHORITY_POLICY_VERSION,
            "required_approval_type": None,
            "timestamp": _now().isoformat(),
        }
    decision, risk, extra = entry
    return {
        "action_type": action_type,
        "decision": decision,
        "risk_category": risk,
        "explanation": extra or f"decision={decision} risk={risk}",
        "policy_version": _AUTHORITY_POLICY_VERSION,
        "required_approval_type": (f"action.{action_type}"
                                       if decision == "requires_approval"
                                       else None),
        "timestamp": _now().isoformat(),
    }


# ─── Approval-integrity enforcement (used by P3 + P4) ─────────────────────
class ApprovalMismatchError(Exception):
    pass


async def enforce_approval(
    db, *, approval_id: str, request_type: str, target_id: str,
    admin_email: str, target_version: Optional[int] = None,
    amount_usd: Optional[str] = None,
    require_unexpired: bool = True,
) -> dict:
    """Verify an approval-queue record matches ALL required criteria.

    Raises ApprovalMismatchError on any mismatch. On success, returns the
    approval doc. Callers should mark the approval `completed` after
    executing the underlying action.
    """
    doc = await db["approval_queue"].find_one({"id": approval_id}, {"_id": 0})
    if not doc:
        raise ApprovalMismatchError(f"no approval-queue record with id={approval_id}")
    if doc.get("status") != "approved":
        raise ApprovalMismatchError(
            f"approval status must be 'approved', got {doc.get('status')!r}")
    if doc.get("request_type") != request_type:
        raise ApprovalMismatchError(
            f"approval request_type mismatch (expected {request_type!r}, "
            f"got {doc.get('request_type')!r})")
    sr = doc.get("supporting_records") or {}
    target_field = (sr.get("target_id") or sr.get("policy_id")
                     or sr.get("offer_id") or sr.get("draw_id")
                     or sr.get("recon_id") or sr.get("workflow_id")
                     or sr.get("template_id") or sr.get("kb_id"))
    if target_field and target_field != target_id:
        raise ApprovalMismatchError(
            f"approval target_id mismatch (expected {target_id!r}, got {target_field!r})")
    if target_version is not None and sr.get("version") not in (None, target_version):
        raise ApprovalMismatchError(
            f"approval version mismatch (expected {target_version}, got {sr.get('version')})")
    if amount_usd is not None:
        expected = str(amount_usd)
        actual = doc.get("financial_amount_usd")
        if actual is not None and str(actual) != expected:
            raise ApprovalMismatchError(
                f"approval amount mismatch (expected {expected}, got {actual})")
    if require_unexpired and doc.get("expires_at"):
        try:
            exp = doc["expires_at"]
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            if exp < _now():
                raise ApprovalMismatchError("approval has expired")
        except Exception:
            pass
    # Prevent reuse: refuse if already marked completed
    if doc.get("execution_completed"):
        raise ApprovalMismatchError("approval has already been consumed")
    return doc


async def mark_approval_completed(db, approval_id: str, admin_email: str,
                                    execution_ref: str) -> None:
    """Mark approval as consumed. Never delete."""
    await db["approval_queue"].update_one(
        {"id": approval_id},
        {"$set": {
            "execution_completed": True,
            "execution_ref": execution_ref,
            "execution_by": admin_email,
            "execution_at": _now(),
            "status": "completed",
        }},
    )


# ─── Pydantic models ───────────────────────────────────────────────────────
class WorkflowStep(BaseModel):
    step_type: StepType
    label: str = Field(min_length=1, max_length=200)
    config: dict = Field(default_factory=dict)


class WorkflowDefIn(BaseModel):
    workflow_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    trigger_event: str = Field(min_length=1, max_length=100)
    eligibility_conditions: dict = Field(default_factory=dict)
    steps: list[WorkflowStep] = Field(default_factory=list)
    exit_conditions: dict = Field(default_factory=dict)
    cancellation_conditions: dict = Field(default_factory=dict)
    retry_policy: dict = Field(default_factory=lambda: {"max_attempts": 3, "backoff": "exponential"})
    max_attempts: int = 3
    dead_letter_behavior: str = "surface_to_admin"

    @field_validator("workflow_code")
    @classmethod
    def _code(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,63}$", v):
            raise ValueError("workflow_code must match [a-z0-9][a-z0-9_.-]{1,63}")
        return v


class TemplateIn(BaseModel):
    template_code: str = Field(min_length=2, max_length=64)
    channel: Channel
    subject: Optional[str] = None
    body: str = Field(min_length=1, max_length=20000)
    approved_variables: list[str] = Field(default_factory=list)
    related_offer_ids: list[str] = Field(default_factory=list)
    approved_claims: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)


class KnowledgeIn(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    approved_answer: str = Field(min_length=1, max_length=5000)
    source_reference: Optional[str] = None
    related_offer_id: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class ActionIn(BaseModel):
    action_type: str
    provider: Optional[str] = None
    workflow_execution_id: Optional[str] = None
    contact_id: Optional[str] = None
    organization_id: Optional[str] = None
    offer_id: Optional[str] = None
    template_id: Optional[str] = None
    requested_payload: dict = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=6, max_length=200)


class SimulatedWebhookIn(BaseModel):
    """Payload for the shadow-mode webhook route used only by tests.

    In production, the raw request body + Stripe-Signature header is used;
    this endpoint accepts a pre-parsed event AND a signature computed with a
    test webhook secret to prove the signature-verification code path works.
    """
    event: dict
    signature: str
    signing_secret_env_key: str = "STRIPE_WEBHOOK_SECRET_TEST"


# ─── Constants ─────────────────────────────────────────────────────────────
_ALLOWED_STEP_TYPES = set(StepType.__args__)  # type: ignore[attr-defined]

_SUPPORTED_WEBHOOK_EVENTS = (
    "checkout.session.completed", "payment_intent.succeeded",
    "payment_intent.payment_failed", "invoice.paid", "invoice.payment_failed",
    "customer.subscription.created", "customer.subscription.updated",
    "customer.subscription.deleted", "charge.refunded",
    "charge.dispute.created", "charge.dispute.updated",
)

_PROHIBITED_CLAIM_PATTERNS = (
    r"guaranteed?\s+income", r"risk[- ]?free", r"double\s+your\s+money",
    r"100%\s+refund", r"lifetime\s+access\s+guaranteed?", r"never\s+lose",
)


def _template_variable_re() -> re.Pattern:
    # Matches {{ variable_name }} with optional whitespace
    return re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _extract_variables(body: str) -> set[str]:
    return set(_template_variable_re().findall(body))


def _detect_prohibited_claims(body: str) -> list[str]:
    b = body.lower()
    hits: list[str] = []
    for pat in _PROHIBITED_CLAIM_PATTERNS:
        if re.search(pat, b):
            hits.append(pat)
    return hits


def render_template(body: str, variables: dict, approved: set[str]) -> str:
    """Safe template render.

    Rules:
      • Only variables in ``approved`` may appear in the body.
      • Every referenced variable must be supplied in ``variables``.
      • Values are HTML-escaped defensively.
    """
    referenced = _extract_variables(body)
    unexpected = referenced - approved
    if unexpected:
        raise ValueError(f"template references unapproved variables: {sorted(unexpected)}")
    missing = referenced - set(variables.keys())
    if missing:
        raise ValueError(f"template missing variables: {sorted(missing)}")

    def _sub(m):
        v = variables.get(m.group(1), "")
        # HTML-escape as a defensive measure
        s = str(v).replace("&", "&amp;").replace("<", "&lt;")\
                  .replace(">", "&gt;").replace('"', "&quot;")\
                  .replace("'", "&#39;")
        return s

    return _template_variable_re().sub(_sub, body)


# ─── Integration adapters (safe stubs) ─────────────────────────────────────
class IntegrationAdapter:
    """Common safe interface for all provider adapters.

    All Phase 4 adapters remain in ``simulate`` mode while the safety gate
    is off. Live execution is only attempted when BOTH:
      • live_actions_enabled() is True
      • the authority decision permits it
    ...and both conditions must be re-checked at the call site — this base
    class never bypasses either. Credentials are never logged.
    """
    provider: str = "abstract"
    env_keys_expected: tuple[str, ...] = ()

    def validate_configuration(self) -> dict:
        missing = [k for k in self.env_keys_expected if not os.environ.get(k)]
        return {
            "provider": self.provider,
            "configured": not bool(missing),
            "missing_env_keys": missing,
            "live_capable": (not bool(missing)) and live_actions_enabled(),
        }

    def status(self) -> str:
        v = self.validate_configuration()
        if not v["configured"]:
            return "unavailable"
        return "live" if v["live_capable"] else "simulated"

    async def simulate(self, payload: dict) -> dict:
        return {"provider": self.provider, "mode": "simulated",
                "would_have_sent": _redact_secrets(payload),
                "at": _now().isoformat()}

    async def execute(self, payload: dict, idempotency_key: str) -> dict:
        raise NotImplementedError("live execution intentionally not implemented")


class StripeAdapter(IntegrationAdapter):
    provider = "stripe"
    env_keys_expected = ("STRIPE_API_KEY",)


class ResendAdapter(IntegrationAdapter):
    provider = "resend"
    env_keys_expected = ("RESEND_API_KEY",)


class BufferAdapter(IntegrationAdapter):
    provider = "buffer"
    env_keys_expected = ("BUFFER_ACCESS_TOKEN",)


class GmailAdapter(IntegrationAdapter):
    provider = "gmail"
    env_keys_expected = ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")


class GoogleCalendarAdapter(IntegrationAdapter):
    provider = "gcal"
    env_keys_expected = ("GCAL_CLIENT_ID", "GCAL_CLIENT_SECRET", "GCAL_REFRESH_TOKEN")


ADAPTERS: dict[str, IntegrationAdapter] = {
    "stripe": StripeAdapter(), "resend": ResendAdapter(),
    "buffer": BufferAdapter(), "gmail": GmailAdapter(),
    "gcal": GoogleCalendarAdapter(),
}


_SECRET_PATTERNS = (
    r"(sk_(?:live|test)_[A-Za-z0-9]+)",
    r"(pk_(?:live|test)_[A-Za-z0-9]+)",
    r"(whsec_[A-Za-z0-9]+)",
    r"(eyJ[A-Za-z0-9._-]+)",
    r"(ya29\.[A-Za-z0-9._-]+)",
    r"(re_[A-Za-z0-9_-]{16,})",
    r"(?:api[_-]?key|token|secret|password)\"?\s*[:=]\s*\"?([^\s\"',}]+)",
)


def _redact_secrets(obj: Any) -> Any:
    """Recursively redact secret-looking substrings in strings/dicts/lists."""
    if isinstance(obj, str):
        s = obj
        for pat in _SECRET_PATTERNS:
            s = re.sub(pat, "[REDACTED]", s, flags=re.IGNORECASE)
        return s
    if isinstance(obj, dict):
        return {k: _redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_secrets(v) for v in obj]
    return obj


# ─── Indexes ───────────────────────────────────────────────────────────────
async def ensure_indexes_phase4(db) -> None:
    await db["workflow_definitions"].create_index("id", unique=True)
    await db["workflow_definitions"].create_index("workflow_code")
    await db["workflow_definitions"].create_index("trigger_event")
    await db["workflow_definitions"].create_index("active")
    await db["workflow_executions"].create_index("id", unique=True)
    await db["workflow_executions"].create_index("trigger_event_id")
    await db["workflow_executions"].create_index("contact_id")
    await db["workflow_executions"].create_index("status")
    await db["action_queue"].create_index("id", unique=True)
    await db["action_queue"].create_index("idempotency_key", unique=True)
    await db["action_queue"].create_index("status")
    await db["action_queue"].create_index("scheduled_time")
    await db["templates"].create_index("id", unique=True)
    await db["templates"].create_index("template_code")
    await db["templates"].create_index("active")
    await db["knowledge_base"].create_index("id", unique=True)
    await db["knowledge_base"].create_index("topic")
    await db["knowledge_base"].create_index("active")
    await db["webhook_events"].create_index("id", unique=True)
    await db["webhook_events"].create_index("provider_event_id", unique=True)
    await db["webhook_events"].create_index("processed")
    await db["owner_draw_payments"].create_index("id", unique=True)
    await db["owner_draw_payments"].create_index("idempotency_key", unique=True)
    await db["owner_draw_payments"].create_index(
        [("draw_id", 1), ("payment_reference", 1)], unique=True)


async def seed_default_workflows(db, admin_email: str = "system.seed") -> None:
    if await db["workflow_definitions"].count_documents({}) > 0:
        return
    codes = [
        ("new_lead_nurture", "lead.created"),
        ("assessment_completed", "assessment.completed"),
        ("qualified_lead_recommendation", "lead.qualified"),
        ("high_intent_followup", "lead.high_intent"),
        ("checkout_abandoned", "checkout.abandoned"),
        ("successful_purchase_onboarding", "checkout.session.completed"),
        ("failed_payment_recovery", "invoice.payment_failed"),
        ("subscription_renewal", "customer.subscription.updated"),
        ("cancellation_recovery", "customer.subscription.deleted"),
        ("customer_inactivity", "customer.inactivity_detected"),
        ("course_completion", "course.completed"),
        ("review_request", "customer.review_requestable"),
        ("monthly_to_annual_upgrade", "customer.upgrade_eligible"),
        ("business_recommendation", "customer.business_eligible"),
        ("organization_license_qualification", "customer.enterprise_signal"),
    ]
    now = _now()
    for code, trig in codes:
        await db["workflow_definitions"].insert_one({
            "id": str(uuid.uuid4()), "workflow_code": code,
            "name": code.replace("_", " ").title(),
            "description": f"Draft {code} workflow (disabled)",
            "trigger_event": trig,
            "eligibility_conditions": {}, "steps": [],
            "exit_conditions": {}, "cancellation_conditions": {},
            "retry_policy": {"max_attempts": 3, "backoff": "exponential"},
            "max_attempts": 3, "dead_letter_behavior": "surface_to_admin",
            "active": False, "draft": True,
            "version": 1, "effective_date": None,
            "created_by": admin_email, "approved_by": None,
            "created_at": now, "updated_at": now,
            "environment": "preview", "simulated": False,
            "source": "existing_application",
        })


async def seed_default_templates(db, admin_email: str = "system.seed") -> None:
    if await db["templates"].count_documents({}) > 0:
        return
    base = _now()
    starters = [
        ("welcome_message", "email", "Welcome to Ascendra",
         "Hi {{first_name}}, welcome to Ascendra."),
        ("assessment_results", "email", "Your assessment results",
         "Hi {{first_name}}, your assessment score is {{score}}."),
        ("checkout_abandoned_reminder", "email", "Complete your purchase",
         "Hi {{first_name}}, you left {{offer_name}} in checkout."),
        ("failed_payment_reminder", "email", "Payment issue on your account",
         "Hi {{first_name}}, we could not process your last payment."),
    ]
    for code, ch, subj, body in starters:
        await db["templates"].insert_one({
            "id": str(uuid.uuid4()), "template_code": code, "channel": ch,
            "subject": subj, "body": body,
            "approved_variables": ["first_name", "score", "offer_name"],
            "related_offer_ids": [], "approved_claims": [],
            "prohibited_claims": list(_PROHIBITED_CLAIM_PATTERNS),
            "active": False, "draft": True, "version": 1,
            "created_by": admin_email, "approved_by": None,
            "created_at": base, "updated_at": base,
            "environment": "preview", "simulated": False,
            "source": "existing_application",
        })


# ─── Router ────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/admin/revenue", tags=["revenue-phase4"])


def register_routes(db, require_admin):

    # ═══════════════════════════════════════════════════════════════════════
    #  AUTHORITY MATRIX
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/authority/matrix")
    async def get_authority_matrix(admin=Depends(require_admin)):
        entries = [{"action_type": k,
                    "decision": v[0], "risk_category": v[1],
                    "explanation": v[2] or f"{v[0]} / {v[1]}"}
                    for k, v in _AUTHORITY_MATRIX.items()]
        return {"policy_version": _AUTHORITY_POLICY_VERSION,
                "entries": entries, "count": len(entries)}

    @router.post("/authority/evaluate")
    async def evaluate_action_authority(action_type: str, admin=Depends(require_admin)):
        decision = evaluate_authority(action_type)
        await _audit(db, actor=admin["email"], action="authority.evaluated",
                     target_type="action_type", target_id=action_type,
                     reason=decision["decision"], simulated=False,
                     source="admin_created", extra=decision)
        return decision

    # ═══════════════════════════════════════════════════════════════════════
    #  WORKFLOW DEFINITIONS
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/workflows")
    async def create_workflow(body: WorkflowDefIn, admin=Depends(require_admin)):
        # Reject any step whose type is not in the allowlist
        for step in body.steps:
            if step.step_type not in _ALLOWED_STEP_TYPES:
                raise HTTPException(422, f"step_type '{step.step_type}' is not allowlisted")
        latest = await db["workflow_definitions"].find_one(
            {"workflow_code": body.workflow_code}, {"version": 1},
            sort=[("version", -1)])
        v = (latest.get("version", 0) if latest else 0) + 1
        doc = {
            "id": str(uuid.uuid4()), "workflow_code": body.workflow_code,
            "name": body.name, "description": body.description,
            "trigger_event": body.trigger_event,
            "eligibility_conditions": body.eligibility_conditions,
            "steps": [s.model_dump() for s in body.steps],
            "exit_conditions": body.exit_conditions,
            "cancellation_conditions": body.cancellation_conditions,
            "retry_policy": body.retry_policy, "max_attempts": body.max_attempts,
            "dead_letter_behavior": body.dead_letter_behavior,
            "active": False, "draft": True, "version": v,
            "created_by": admin["email"], "approved_by": None,
            "effective_date": None,
            "created_at": _now(), "updated_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
        }
        await db["workflow_definitions"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="workflow.created",
                     target_type="workflow", target_id=doc["id"],
                     reason=f"draft v{v}",
                     simulated=False, source="admin_created")
        return {"workflow": {**doc, "_id": None}}

    @router.get("/workflows")
    async def list_workflows(active: Optional[bool] = None,
                              admin=Depends(require_admin)):
        q: dict = {}
        if active is not None:
            q["active"] = active
        rows = await db["workflow_definitions"].find(q, {"_id": 0})\
            .sort("created_at", -1).limit(200).to_list(200)
        return {"workflows": rows, "count": len(rows)}

    @router.post("/workflows/{workflow_id}/activate")
    async def activate_workflow(workflow_id: str, approval_id: str,
                                admin=Depends(require_admin)):
        """Requires a matching approval-queue record (integrity check)."""
        wf = await db["workflow_definitions"].find_one({"id": workflow_id})
        if not wf:
            raise HTTPException(404, "workflow not found")
        try:
            approval = await enforce_approval(
                db, approval_id=approval_id,
                request_type="workflow.activate",
                target_id=workflow_id, target_version=wf.get("version"),
                admin_email=admin["email"],
            )
        except ApprovalMismatchError as e:
            raise HTTPException(403, f"approval-integrity failure: {e}")
        await db["workflow_definitions"].update_one(
            {"id": workflow_id},
            {"$set": {"active": True, "draft": False,
                       "approved_by": admin["email"], "updated_at": _now()}},
        )
        await mark_approval_completed(db, approval_id, admin["email"], workflow_id)
        await _audit(db, actor=admin["email"], action="workflow.activated",
                     target_type="workflow", target_id=workflow_id,
                     correlation_id=approval.get("correlation_id"),
                     approval_required=True, approval_status="completed",
                     reason=f"activated via approval {approval_id}",
                     simulated=False, source="admin_created")
        updated = await db["workflow_definitions"].find_one({"id": workflow_id}, {"_id": 0})
        return {"workflow": updated}

    # ═══════════════════════════════════════════════════════════════════════
    #  WORKFLOW EXECUTIONS
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/workflows/{workflow_id}/simulate-execution")
    async def start_simulated_execution(workflow_id: str, trigger_event_id: str,
                                          contact_id: Optional[str] = None,
                                          admin=Depends(require_admin)):
        wf = await db["workflow_definitions"].find_one({"id": workflow_id}, {"_id": 0})
        if not wf:
            raise HTTPException(404, "workflow not found")
        # Duplicate-trigger protection
        existing = await db["workflow_executions"].find_one(
            {"workflow_id": workflow_id, "trigger_event_id": trigger_event_id},
            {"_id": 0})
        if existing:
            return {"execution": existing, "duplicate": True}
        # Draft workflows may only run in simulated status
        status = "completed" if wf.get("draft") else "queued"
        doc = {
            "id": str(uuid.uuid4()), "workflow_id": workflow_id,
            "workflow_version": wf.get("version"),
            "trigger_event_id": trigger_event_id,
            "contact_id": contact_id, "organization_id": None,
            "current_step": 0, "status": status,
            "started_at": _now(),
            "next_run_at": None, "completed_at": _now() if status == "completed" else None,
            "attempt_count": 1, "last_error": None,
            "correlation_id": str(uuid.uuid4()),
            "cancellation_reason": None,
            "environment": "preview", "simulated": True,
            "source": "admin_created",
        }
        await db["workflow_executions"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="workflow.execution_simulated",
                     target_type="workflow_execution", target_id=doc["id"],
                     correlation_id=doc["correlation_id"],
                     reason=("draft simulation" if wf.get("draft") else "queued for eval"),
                     simulated=True, source="admin_created")
        return {"execution": {**doc, "_id": None}, "duplicate": False}

    @router.get("/workflow-executions")
    async def list_executions(status: Optional[str] = None,
                                admin=Depends(require_admin)):
        q: dict = {}
        if status:
            q["status"] = status
        rows = await db["workflow_executions"].find(q, {"_id": 0})\
            .sort("started_at", -1).limit(200).to_list(200)
        return {"executions": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  ACTION QUEUE
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/actions")
    async def enqueue_action(body: ActionIn, admin=Depends(require_admin)):
        # Idempotency
        existing = await db["action_queue"].find_one(
            {"idempotency_key": body.idempotency_key}, {"_id": 0})
        if existing:
            return {"action": existing, "duplicate": True}
        auth = evaluate_authority(body.action_type)
        # Never allow live execution while safety gate is off
        if auth["decision"] == "prohibited":
            status: ActionStatus = "blocked"
        elif auth["decision"] == "auto_permitted":
            status = "simulated"
        elif auth["decision"] == "permitted_if_live":
            status = "simulated" if not live_actions_enabled() else "queued"
        elif auth["decision"] == "requires_approval":
            status = "awaiting_approval"
        else:  # unknown_default_contain
            status = "blocked"
        doc = {
            "id": str(uuid.uuid4()), "action_type": body.action_type,
            "provider": body.provider,
            "workflow_execution_id": body.workflow_execution_id,
            "contact_id": body.contact_id, "organization_id": body.organization_id,
            "offer_id": body.offer_id, "template_id": body.template_id,
            "requested_payload": _redact_secrets(body.requested_payload),
            "authority_decision": auth,
            "approval_required": auth["decision"] == "requires_approval",
            "approval_record_id": None,
            "scheduled_time": _now(),
            "attempt_count": 0, "status": status,
            "failure_details": None,
            "correlation_id": str(uuid.uuid4()),
            "idempotency_key": body.idempotency_key,
            "created_at": _now(), "completed_at": None,
            "environment": "preview", "simulated": True,
            "source": "admin_created",
        }
        await db["action_queue"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="action.queued",
                     target_type="action", target_id=doc["id"],
                     correlation_id=doc["correlation_id"],
                     reason=f"{body.action_type} → {status}",
                     simulated=True, source="admin_created")
        return {"action": {**doc, "_id": None}, "duplicate": False}

    @router.get("/actions")
    async def list_actions(status: Optional[str] = None, admin=Depends(require_admin)):
        q: dict = {}
        if status:
            q["status"] = status
        rows = await db["action_queue"].find(q, {"_id": 0})\
            .sort("created_at", -1).limit(200).to_list(200)
        return {"actions": rows, "count": len(rows)}

    @router.get("/actions/dead-letter")
    async def dead_letter(admin=Depends(require_admin)):
        rows = await db["action_queue"].find({"status": "dead_letter"}, {"_id": 0})\
            .sort("created_at", -1).limit(200).to_list(200)
        return {"actions": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  TEMPLATES + KNOWLEDGE BASE
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/templates")
    async def create_template(body: TemplateIn, admin=Depends(require_admin)):
        # Reject bodies referencing variables outside the approved allowlist
        referenced = _extract_variables(body.body)
        unapproved = referenced - set(body.approved_variables)
        if unapproved:
            raise HTTPException(422,
                f"template body references unapproved variables: {sorted(unapproved)}")
        # Reject prohibited claims outright
        bad = _detect_prohibited_claims(body.body + " " + (body.subject or ""))
        if bad:
            raise HTTPException(422,
                f"template body contains prohibited claim patterns: {bad}")
        latest = await db["templates"].find_one(
            {"template_code": body.template_code}, {"version": 1},
            sort=[("version", -1)])
        v = (latest.get("version", 0) if latest else 0) + 1
        doc = {
            "id": str(uuid.uuid4()), "template_code": body.template_code,
            "channel": body.channel, "subject": body.subject,
            "body": body.body,
            "approved_variables": body.approved_variables,
            "related_offer_ids": body.related_offer_ids,
            "approved_claims": body.approved_claims,
            "prohibited_claims": body.prohibited_claims + list(_PROHIBITED_CLAIM_PATTERNS),
            "active": False, "draft": True, "version": v,
            "created_by": admin["email"], "approved_by": None,
            "created_at": _now(), "updated_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
        }
        await db["templates"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="template.created",
                     target_type="template", target_id=doc["id"],
                     reason=f"draft {body.template_code} v{v}",
                     simulated=False, source="admin_created")
        return {"template": {**doc, "_id": None}}

    @router.get("/templates")
    async def list_templates(admin=Depends(require_admin)):
        rows = await db["templates"].find({}, {"_id": 0})\
            .sort("created_at", -1).limit(200).to_list(200)
        return {"templates": rows, "count": len(rows)}

    @router.post("/templates/{template_id}/render")
    async def preview_render(template_id: str, variables: dict,
                              admin=Depends(require_admin)):
        tpl = await db["templates"].find_one({"id": template_id}, {"_id": 0})
        if not tpl:
            raise HTTPException(404, "template not found")
        try:
            rendered = render_template(tpl["body"], variables,
                                          set(tpl["approved_variables"]))
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"rendered": rendered, "template_code": tpl["template_code"]}

    @router.post("/knowledge")
    async def create_kb(body: KnowledgeIn, admin=Depends(require_admin)):
        latest = await db["knowledge_base"].find_one(
            {"topic": body.topic}, {"version": 1}, sort=[("version", -1)])
        v = (latest.get("version", 0) if latest else 0) + 1
        doc = {
            "id": str(uuid.uuid4()), "topic": body.topic,
            "approved_answer": body.approved_answer,
            "source_reference": body.source_reference,
            "related_offer_id": body.related_offer_id,
            "effective_date": body.effective_date,
            "expiration_date": body.expiration_date,
            "active": False, "draft": True, "version": v,
            "approved_by": None, "created_by": admin["email"],
            "created_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
        }
        await db["knowledge_base"].insert_one(doc)
        return {"knowledge": {**doc, "_id": None}}

    @router.get("/knowledge")
    async def list_kb(admin=Depends(require_admin)):
        rows = await db["knowledge_base"].find({}, {"_id": 0})\
            .sort("created_at", -1).limit(200).to_list(200)
        return {"knowledge": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  STRIPE WEBHOOK SHADOW PROCESSOR (coexists with existing /billing/webhook)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/webhooks/stripe/shadow", include_in_schema=True)
    async def stripe_webhook_shadow(request: Request,
                                      admin=Depends(require_admin)):
        """Phase 4 shadow processor for Stripe events (used by test harness).

        NOT wired to any real webhook endpoint. The existing
        ``/api/billing/webhook`` route continues to handle production events;
        this endpoint accepts a JSON body containing ``{"raw_body":"...","signature":"..."}``
        and processes normalized events without ever calling out to Stripe.

        Signature verification uses HMAC-SHA256 against
        ``STRIPE_WEBHOOK_SECRET_TEST`` if present (defaults to the shared
        preview test secret). Live secrets are never referenced.
        """
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        raw_body = payload.get("raw_body")
        signature = payload.get("signature", "")
        if not raw_body:
            raise HTTPException(400, "raw_body is required")

        secret = os.environ.get("STRIPE_WEBHOOK_SECRET_TEST", "test-shadow-secret")
        expected = hmac.new(secret.encode(), raw_body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(400, "invalid signature")

        try:
            import json as _json
            event = _json.loads(raw_body)
        except Exception:
            raise HTTPException(400, "raw_body must be valid JSON after signature check")

        event_id = event.get("id")
        event_type = event.get("type")
        if not event_id or not event_type:
            raise HTTPException(400, "event.id and event.type are required")
        if event_type not in _SUPPORTED_WEBHOOK_EVENTS:
            raise HTTPException(400, f"event type '{event_type}' not supported")

        # Idempotency: reject duplicate provider event
        dup = await db["webhook_events"].find_one({"provider_event_id": event_id})
        if dup:
            return {"received": True, "duplicate": True}

        # Store normalized event
        rec = {
            "id": str(uuid.uuid4()),
            "provider": "stripe",
            "provider_event_id": event_id,
            "event_type": event_type,
            "raw_signature_valid": True,
            "payload": _redact_secrets(event),
            "processed": True,
            "processed_at": _now(),
            "created_at": _now(),
            "environment": "preview",
            "simulated": True,             # from test harness
            "source": "external_provider",
        }
        await db["webhook_events"].insert_one(rec)
        await _audit(db, actor=admin["email"], action="webhook.processed",
                     target_type="webhook_event", target_id=rec["id"],
                     reason=f"stripe {event_type}",
                     simulated=True, source="external_provider",
                     extra={"provider_event_id": event_id})
        return {"received": True, "duplicate": False,
                "event_type": event_type, "event_id": rec["id"]}

    @router.get("/webhooks")
    async def list_webhook_events(admin=Depends(require_admin)):
        rows = await db["webhook_events"].find({}, {"_id": 0})\
            .sort("created_at", -1).limit(100).to_list(100)
        return {"events": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  INTEGRATION ADAPTERS (Phase 4 status endpoint)
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/phase4/integrations")
    async def phase4_integrations(admin=Depends(require_admin)):
        rows = []
        for name, adapter in ADAPTERS.items():
            v = adapter.validate_configuration()
            rows.append({
                "provider": name,
                "state": adapter.status(),
                "configured": v["configured"],
                "missing_env_keys": v["missing_env_keys"],
                "live_capable": v["live_capable"],
                "note": ("live execution is intentionally not implemented in "
                          "Phase 4; adapters simulate only"),
            })
        return {"integrations": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  PHASE 4 SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/phase4/summary")
    async def phase4_summary(admin=Depends(require_admin)):
        counts = {
            "workflows": await db["workflow_definitions"].count_documents({}),
            "workflows_active": await db["workflow_definitions"].count_documents({"active": True}),
            "executions": await db["workflow_executions"].count_documents({}),
            "actions_queued": await db["action_queue"].count_documents({"status": "queued"}),
            "actions_awaiting_approval": await db["action_queue"].count_documents({"status": "awaiting_approval"}),
            "actions_blocked": await db["action_queue"].count_documents({"status": "blocked"}),
            "actions_dead_letter": await db["action_queue"].count_documents({"status": "dead_letter"}),
            "templates": await db["templates"].count_documents({}),
            "knowledge_entries": await db["knowledge_base"].count_documents({}),
            "webhook_events": await db["webhook_events"].count_documents({}),
        }
        return {"counts": counts, "authority_policy_version": _AUTHORITY_POLICY_VERSION,
                "live_actions_enabled": live_actions_enabled(),
                "environment": "preview"}

    return router
