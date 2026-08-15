"""
revenue_phase3.py — Phase 3 of the Revenue Control Center.

Adds an APPEND-ONLY internal financial-control subledger:

  • Financial ledger with strict Decimal128 arithmetic + invariants
  • Settlement states (pending, processing, cleared, disputed, refunded,
    reversed, uncollectible) — only cleared funds enter distributable cash
  • Idempotency & duplicate protection (unique idempotency_key)
  • Tax-reserve policy (versioned, approval-gated, prospective only)
  • Essential operating expenses (append-oriented)
  • Three-month working-capital reserve target (rolling average OR budget fallback)
  • Versioned cash-allocation policies (startup 25/25/50 → established 50/25/25)
  • Automatic phase transition + reversion — only at month-end reconciliation
  • Month-end reconciliation (one per calendar month; closed months immutable)
  • Business-timezone-aware owner-draw recommendation date
    (first weekday on or after the 5th, weekends only)
  • Owner-draw recommendation lifecycle — never a transfer, never a payout

DISCLAIMER (surfaced in the admin UI, and repeated here):
    This is an internal cash-management subledger. It is NOT professional
    bookkeeping, tax preparation, banking, or a general ledger. All calculated
    reserves are internal estimates and MUST NOT be treated as final tax
    calculations or professional advice.

SAFETY:
    Nothing in this module can perform an external side-effect while
    ``AUTOMATION_LIVE_ACTIONS_ENABLED=false``. No bank calls, no Stripe
    transfers, no payouts, no emails, no webhooks. Approvals authorize
    internal records only.
"""
from __future__ import annotations

import calendar
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:                                # pragma: no cover
    from backports.zoneinfo import ZoneInfo       # type: ignore

from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from revenue import _audit, _now, live_actions_enabled

# Phase 4 provides the approval-integrity helpers. Import lazily inside handlers
# to avoid a module-import cycle at load time; alias here for readability.
def _approval_helpers():
    from revenue_phase4 import (
        enforce_approval,
        mark_approval_completed,
        ApprovalMismatchError,
    )
    return enforce_approval, mark_approval_completed, ApprovalMismatchError


# ─── Constants ─────────────────────────────────────────────────────────────
BUSINESS_TZ = ZoneInfo(os.environ.get("ASCENDRA_BUSINESS_TIMEZONE", "America/Chicago"))
CENTS = Decimal("0.01")
MAX_MONEY = Decimal("10000000.00")
MIN_MONEY = Decimal("-10000000.00")

EntryType = Literal[
    "payment_recorded", "processor_fee_recorded", "tax_liability_recorded",
    "refund_recorded", "chargeback_recorded", "liability_adjustment",
    "payment_reversal", "allocation_recorded", "reconciliation_adjustment",
    "owner_draw_recorded_manually",
]
SettlementStatus = Literal[
    "pending", "processing", "cleared", "disputed", "refunded", "reversed",
    "uncollectible",
]
AllocationPhase = Literal["startup", "established"]
ReconStatus = Literal["draft", "ready_for_review", "blocked", "approved", "closed"]
OwnerDrawStatus = Literal[
    "not_ready", "blocked", "recommended", "approved", "rejected",
    "recorded_as_manually_paid", "carried_forward",
]
EssentialCategory = Literal[
    "hosting", "domain_infrastructure", "required_software", "payment_processing",
    "required_professional_services", "insurance", "regulatory_filing",
    "essential_contractor", "other_approved_essential",
]


# ─── Money & decimal helpers ───────────────────────────────────────────────
def _D(v: Any) -> Decimal:
    """Convert v to Decimal, rejecting floats. Raises ValueError on bad input."""
    if isinstance(v, float):
        raise ValueError("float amounts are not accepted; pass a decimal string")
    if isinstance(v, Decimal128):
        return v.to_decimal()
    if isinstance(v, Decimal):
        return v
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        raise ValueError(f"invalid decimal value: {v!r}")


def _quantize(d: Decimal) -> Decimal:
    return d.quantize(CENTS, rounding=ROUND_HALF_UP)


def _to_128(d: Decimal) -> Decimal128:
    return Decimal128(_quantize(d))


def _validate_money(d: Decimal, *, allow_negative: bool = False, field: str = "amount") -> Decimal:
    if not allow_negative and d < 0:
        raise ValueError(f"{field} cannot be negative")
    if d > MAX_MONEY or d < MIN_MONEY:
        raise ValueError(f"{field} out of documented bounds")
    if d.as_tuple().exponent < -2:
        raise ValueError(f"{field} may not exceed 2 decimal places")
    return _quantize(d)


# ─── Business-calendar utilities ───────────────────────────────────────────
def business_now() -> datetime:
    return datetime.now(BUSINESS_TZ)


def month_key(dt: datetime) -> str:
    """Return the calendar-month key (YYYY-MM) in the business timezone."""
    b = dt.astimezone(BUSINESS_TZ)
    return f"{b.year:04d}-{b.month:02d}"


def is_month_complete(target_month: str, at: Optional[datetime] = None) -> bool:
    """True iff the given YYYY-MM month has ended (in business timezone)."""
    at = (at or business_now()).astimezone(BUSINESS_TZ)
    yy, mm = map(int, target_month.split("-"))
    last_day = calendar.monthrange(yy, mm)[1]
    # A month is complete once the current business-tz date is on or after the
    # first day of the following month.
    if mm == 12:
        next_year, next_month = yy + 1, 1
    else:
        next_year, next_month = yy, mm + 1
    return (at.year, at.month, at.day) >= (next_year, next_month, 1)


def owner_draw_date_for(closed_month: str) -> date:
    """First weekday on or after the 5th day of the month *following* the
    closed month, computed in the business timezone.

    Rule (per Phase 3 spec):
      • 5th is Mon–Fri → 5th
      • 5th is Sat     → Mon 7th
      • 5th is Sun     → Mon 6th
    Holidays are NOT considered (documented Phase 3 limitation).
    """
    yy, mm = map(int, closed_month.split("-"))
    if mm == 12:
        yy += 1; mm = 1
    else:
        mm += 1
    d = date(yy, mm, 5)
    # weekday(): Mon=0 … Sun=6. Advance to next Mon if Sat or Sun.
    if d.weekday() == 5:      # Saturday → Monday (add 2)
        d = d + timedelta(days=2)
    elif d.weekday() == 6:    # Sunday → Monday (add 1)
        d = d + timedelta(days=1)
    return d


# ─── Pydantic input models ─────────────────────────────────────────────────
class LedgerEntryIn(BaseModel):
    entry_type: EntryType
    source_type: str = Field(min_length=1, max_length=64)          # e.g. "manual_preview"
    source_transaction_id: Optional[str] = None
    external_provider_event_id: Optional[str] = None
    idempotency_key: str = Field(min_length=6, max_length=200)
    contact_id: Optional[str] = None
    organization_id: Optional[str] = None
    offer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    gross_amount: str = "0.00"
    processor_fee: str = "0.00"
    sales_tax_liability: str = "0.00"
    refund_amount: str = "0.00"
    chargeback_amount: str = "0.00"
    other_direct_liabilities: str = "0.00"
    settlement_status: SettlementStatus = "pending"
    effective_date: Optional[datetime] = None
    description: Optional[str] = None
    related_entry_id: Optional[str] = None       # for adjustments/reversals
    adjustment_reason: Optional[str] = None
    is_test_fixture: bool = False


class ExpenseIn(BaseModel):
    expense_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    category: EssentialCategory
    description: str = Field(min_length=1, max_length=500)
    amount: str
    currency: str = Field(default="USD", min_length=3, max_length=3)
    essential: bool = True
    source: str = Field(default="admin_created", min_length=1, max_length=64)
    supporting_reference: Optional[str] = None
    correction_of_expense_id: Optional[str] = None
    is_test_fixture: bool = False


class TaxPolicyIn(BaseModel):
    federal_reserve_pct: str
    state_reserve_pct: str
    other_reserve_pct: str = "0.00"
    effective_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class AllocationPolicyIn(BaseModel):
    phase: AllocationPhase
    owner_pct: str
    growth_reserve_pct: str
    working_capital_pct: str
    effective_date: datetime
    notes: Optional[str] = None
    approved_by: str = Field(min_length=1, max_length=200)


class ReconciliationCreateIn(BaseModel):
    calendar_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    notes: Optional[str] = None


class ReconciliationCloseIn(BaseModel):
    reconciliation_id: str
    close_reason: str = Field(min_length=8, max_length=500)
    approval_id: Optional[str] = None   # Phase 21 hardening: required in prod


class OwnerDrawDecisionIn(BaseModel):
    draw_id: str
    decision: Literal["approved", "rejected"]
    reason: Optional[str] = None
    approval_id: Optional[str] = None   # Phase 21 hardening: required in prod


class OwnerDrawManualPayIn(BaseModel):
    draw_id: str
    manually_paid_amount: str
    manual_payment_date: datetime
    manual_payment_reference: str = Field(min_length=1, max_length=200)


class OwnerDrawAdjustmentIn(BaseModel):
    """Append-only correction to a prior owner-draw payment.

    An adjustment is used when a prior payment record must be corrected
    (e.g. wrong amount recorded). We NEVER mutate the prior record; we
    write a new payment row linked via ``adjustment_of_payment_id`` and
    let readers reconstruct the true cumulative via SUM(amount).
    """
    draw_id: str
    original_payment_id: str
    adjustment_amount: str    # positive or negative decimal string, e.g. "-25.00"
    reason: str = Field(min_length=8, max_length=500)
    payment_date: datetime
    payment_reference: str = Field(min_length=1, max_length=200)
    approval_id: str          # REQUIRED (risk_level=high)


class OwnerDrawReversalIn(BaseModel):
    """Append-only full reversal of a prior owner-draw payment.

    Writes a new payment row with the opposite amount and
    ``reverses_payment_id`` pointing at the original. Never mutates
    the original.
    """
    draw_id: str
    original_payment_id: str
    reason: str = Field(min_length=8, max_length=500)
    payment_date: datetime
    payment_reference: str = Field(min_length=1, max_length=200)
    approval_id: str          # REQUIRED (risk_level=high)


class ApprovalRef(BaseModel):
    """Body for endpoints that require an approval_id (allocation/tax activate)."""
    approval_id: Optional[str] = None


# ─── Indexes ───────────────────────────────────────────────────────────────
async def ensure_indexes_phase3(db) -> None:
    await db["financial_ledger"].create_index("id", unique=True)
    await db["financial_ledger"].create_index("idempotency_key", unique=True)
    await db["financial_ledger"].create_index("correlation_id")
    await db["financial_ledger"].create_index("reconciliation_month")
    await db["financial_ledger"].create_index("settlement_status")
    await db["financial_ledger"].create_index("effective_date")
    await db["essential_operating_expenses"].create_index("id", unique=True)
    await db["essential_operating_expenses"].create_index("expense_month")
    await db["allocation_policies"].create_index("id", unique=True)
    await db["allocation_policies"].create_index("phase")
    await db["allocation_policies"].create_index("active")
    await db["tax_reserve_policies"].create_index("id", unique=True)
    await db["tax_reserve_policies"].create_index("active")
    await db["monthly_reconciliations"].create_index("id", unique=True)
    await db["monthly_reconciliations"].create_index("calendar_month", unique=True)
    await db["monthly_reconciliations"].create_index("status")
    await db["owner_draws"].create_index("id", unique=True)
    await db["owner_draws"].create_index("reconciliation_month", unique=True)
    await db["allocation_phase_state"].create_index("id", unique=True)


# ─── Seeder for allocation policies + phase state ──────────────────────────
async def seed_default_allocation_policies(db, admin_email: str = "system.seed") -> None:
    """Seed the owner-approved startup + established allocation policies if
    absent. Idempotent.

    Phase 21 hardening: seeded docs are stamped with the split status
    semantics (``approved`` / ``enabled_for_phase`` / ``currently_applied``)
    in addition to the legacy ``active`` flag.
    """
    existing = await db["allocation_policies"].count_documents({})
    if existing > 0:
        # Still run the semantic migration so already-seeded rows pick up the
        # new fields on redeploy.
        await migrate_allocation_policy_semantics(db)
        return
    now = _now()
    for row in (
        {"phase": "startup", "owner_pct": "25.00", "growth_reserve_pct": "25.00",
         "working_capital_pct": "50.00", "notes": "Owner-approved startup allocation"},
        {"phase": "established", "owner_pct": "50.00", "growth_reserve_pct": "25.00",
         "working_capital_pct": "25.00", "notes": "Owner-approved established allocation"},
    ):
        doc = {
            "id": str(uuid.uuid4()),
            "phase": row["phase"],
            "owner_pct": _to_128(_D(row["owner_pct"])),
            "growth_reserve_pct": _to_128(_D(row["growth_reserve_pct"])),
            "working_capital_pct": _to_128(_D(row["working_capital_pct"])),
            "effective_date": now,
            "version": 1,
            # Legacy flag (kept for backward compatibility)
            "active": True,
            # Phase 21 split status semantics
            "approved": True,
            "enabled_for_phase": row["phase"],
            "currently_applied": True,
            "approved_by": "owner@ascendraacademy.com (bootstrap seed)",
            "notes": row["notes"],
            "source": "existing_application",
            "environment": "preview",
            "created_at": now,
            "created_by": admin_email,
        }
        await db["allocation_policies"].insert_one(doc)
    # Seed the phase state doc — start in "startup" phase.
    if not await db["allocation_phase_state"].find_one({"id": "current"}):
        await db["allocation_phase_state"].insert_one({
            "id": "current",
            "phase": "startup",
            "since": now,
            "last_reconciliation_id": None,
            "reserve_balance_at_transition": None,
            "reserve_target_at_transition": None,
        })


async def migrate_allocation_policy_semantics(db) -> int:
    """Phase 21 hardening: retro-migrate legacy allocation_policies rows to
    carry the split-status semantics (approved / enabled_for_phase /
    currently_applied). Idempotent.

    Returns the number of rows updated.
    """
    updated = 0
    async for doc in db["allocation_policies"].find(
        {"$or": [
            {"approved": {"$exists": False}},
            {"enabled_for_phase": {"$exists": False}},
            {"currently_applied": {"$exists": False}},
        ]}
    ):
        was_active = bool(doc.get("active"))
        phase = doc.get("phase")
        patch = {
            "approved": was_active or bool(doc.get("approved")),
            "enabled_for_phase": phase if was_active else doc.get("enabled_for_phase"),
            "currently_applied": was_active or bool(doc.get("currently_applied")),
            "migrated_semantics_at": _now(),
        }
        await db["allocation_policies"].update_one({"id": doc["id"]}, {"$set": patch})
        updated += 1

    # Enforce single-currently-applied invariant per phase.
    for phase_name in ("startup", "established"):
        applied = await db["allocation_policies"].find(
            {"phase": phase_name, "currently_applied": True},
            {"_id": 0, "id": 1, "version": 1},
        ).sort("version", -1).to_list(100)
        if len(applied) > 1:
            # Keep the highest version, demote the rest.
            keep = applied[0]["id"]
            demote_ids = [r["id"] for r in applied[1:]]
            await db["allocation_policies"].update_many(
                {"id": {"$in": demote_ids}},
                {"$set": {"currently_applied": False, "active": False,
                           "demoted_at": _now(),
                           "demoted_by": "system.phase21_migration"}},
            )
            updated += len(demote_ids)
    return updated


async def get_active_policy(db, phase: str) -> Optional[dict]:
    return await db["allocation_policies"].find_one(
        {"phase": phase, "active": True}, {"_id": 0}
    )


async def current_phase(db) -> str:
    doc = await db["allocation_phase_state"].find_one({"id": "current"}, {"_id": 0})
    return (doc or {}).get("phase", "startup")


async def current_tax_policy(db) -> Optional[dict]:
    return await db["tax_reserve_policies"].find_one({"active": True}, {"_id": 0})


# ─── Ledger core ────────────────────────────────────────────────────────────
def _liability_sum(entry_in: dict) -> Decimal:
    return (
        _D(entry_in.get("processor_fee", 0))
        + _D(entry_in.get("sales_tax_liability", 0))
        + _D(entry_in.get("federal_tax_reserve", 0))
        + _D(entry_in.get("state_tax_reserve", 0))
        + _D(entry_in.get("other_tax_reserve", 0))
        + _D(entry_in.get("refund_amount", 0))
        + _D(entry_in.get("chargeback_amount", 0))
        + _D(entry_in.get("other_direct_liabilities", 0))
    )


def _compute_net(gross: Decimal, entry_in: dict) -> Decimal:
    return _quantize(gross - _liability_sum(entry_in))


def _allocate(net: Decimal, policy: dict) -> tuple[Decimal, Decimal, Decimal]:
    """Deterministic allocation: percentages applied to net (2dp), remainder
    always goes to working_capital_reserve."""
    if net <= 0:
        return _quantize(Decimal("0")), _quantize(Decimal("0")), _quantize(Decimal("0"))
    owner = _quantize(net * (_D(policy["owner_pct"]) / Decimal("100")))
    growth = _quantize(net * (_D(policy["growth_reserve_pct"]) / Decimal("100")))
    wc = _quantize(net - owner - growth)  # remainder policy
    return owner, growth, wc


# ─── Router ────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/admin/revenue", tags=["revenue-phase3"])


def register_routes(db, require_admin):
    # ═══════════════════════════════════════════════════════════════════════
    #  LEDGER
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/ledger/entries")
    async def create_ledger_entry(body: LedgerEntryIn, admin=Depends(require_admin)):
        # Idempotency check
        existing = await db["financial_ledger"].find_one(
            {"idempotency_key": body.idempotency_key}, {"_id": 0})
        if existing:
            return {"entry": _public_ledger(existing), "duplicate": True}

        # Parse & validate all money fields as Decimal
        try:
            gross = _validate_money(_D(body.gross_amount), field="gross_amount")
            proc_fee = _validate_money(_D(body.processor_fee), field="processor_fee")
            sales_tax = _validate_money(_D(body.sales_tax_liability), field="sales_tax_liability")
            refund = _validate_money(_D(body.refund_amount), field="refund_amount")
            chargeback = _validate_money(_D(body.chargeback_amount), field="chargeback_amount")
            other = _validate_money(_D(body.other_direct_liabilities),
                                       allow_negative=False,
                                       field="other_direct_liabilities")
        except ValueError as e:
            raise HTTPException(422, str(e))

        # Compute tax reserves from active policy (prospective only)
        tax_policy = await current_tax_policy(db)
        if tax_policy:
            federal_res = _quantize(gross * (_D(tax_policy["federal_reserve_pct"]) / Decimal("100")))
            state_res = _quantize(gross * (_D(tax_policy["state_reserve_pct"]) / Decimal("100")))
            other_res = _quantize(gross * (_D(tax_policy.get("other_reserve_pct", 0)) / Decimal("100")))
            tax_policy_version = tax_policy.get("version")
        else:
            federal_res = state_res = other_res = Decimal("0")
            tax_policy_version = None

        # Net = gross − all liabilities
        liab_dict = {
            "processor_fee": proc_fee, "sales_tax_liability": sales_tax,
            "federal_tax_reserve": federal_res, "state_tax_reserve": state_res,
            "other_tax_reserve": other_res, "refund_amount": refund,
            "chargeback_amount": chargeback, "other_direct_liabilities": other,
        }
        net = _compute_net(gross, liab_dict)

        # Allocations only on CLEARED payments (and only when tax policy exists)
        allocated = False
        owner_alloc = growth_alloc = wc_alloc = Decimal("0")
        alloc_phase = None
        alloc_policy_version = None
        if body.entry_type == "payment_recorded" \
                and body.settlement_status == "cleared" \
                and tax_policy \
                and net > 0:
            alloc_phase = await current_phase(db)
            policy = await get_active_policy(db, alloc_phase)
            if policy:
                owner_alloc, growth_alloc, wc_alloc = _allocate(net, policy)
                alloc_policy_version = policy["version"]
                allocated = True

        # Effective date + recon month (business tz)
        eff = body.effective_date or _now()
        recon_month = month_key(eff)

        # Classify simulation semantics
        source_tag = "test_fixture" if body.is_test_fixture else "admin_created"
        is_sim = body.is_test_fixture

        entry = {
            "id": str(uuid.uuid4()),
            "entry_type": body.entry_type,
            "source_type": body.source_type,
            "source_transaction_id": body.source_transaction_id,
            "external_provider_event_id": body.external_provider_event_id,
            "idempotency_key": body.idempotency_key,
            "correlation_id": str(uuid.uuid4()),
            "contact_id": body.contact_id,
            "organization_id": body.organization_id,
            "offer_id": body.offer_id,
            "subscription_id": body.subscription_id,
            "currency": body.currency.upper(),
            "gross_amount": _to_128(gross),
            "processor_fee": _to_128(proc_fee),
            "sales_tax_liability": _to_128(sales_tax),
            "federal_tax_reserve": _to_128(federal_res),
            "state_tax_reserve": _to_128(state_res),
            "other_tax_reserve": _to_128(other_res),
            "refund_amount": _to_128(refund),
            "chargeback_amount": _to_128(chargeback),
            "other_direct_liabilities": _to_128(other),
            "net_distributable_amount": _to_128(net),
            "owner_allocation": _to_128(owner_alloc),
            "growth_reserve_allocation": _to_128(growth_alloc),
            "working_capital_allocation": _to_128(wc_alloc),
            "allocation_policy_version": alloc_policy_version,
            "allocation_phase": alloc_phase,
            "tax_policy_version": tax_policy_version,
            "allocated": allocated,
            "settlement_status": body.settlement_status,
            "effective_date": eff,
            "cleared_date": eff if body.settlement_status == "cleared" else None,
            "reconciliation_month": recon_month,
            "related_entry_id": body.related_entry_id,
            "adjustment_reason": body.adjustment_reason,
            "description": body.description,
            "environment": "preview",
            "simulated": is_sim,
            "source": source_tag,
            "created_by": admin["email"],
            "created_at": _now(),
        }

        # Invariant verification (defense-in-depth; matches the doc string above)
        net_check = _quantize(
            gross - proc_fee - sales_tax - federal_res - state_res
            - other_res - refund - chargeback - other
        )
        assert net == net_check, "internal invariant: net_distributable != gross - liabilities"
        if allocated:
            alloc_sum = _quantize(owner_alloc + growth_alloc + wc_alloc)
            assert abs(alloc_sum - net) <= CENTS, \
                "internal invariant: allocations must sum to net (± 1c remainder)"

        await db["financial_ledger"].insert_one(entry)
        await _audit(db, actor=admin["email"], action="financial.entry_recorded",
                     target_type="ledger_entry", target_id=entry["id"],
                     correlation_id=entry["correlation_id"],
                     reason=f"{body.entry_type} ${_D(gross):,.2f}",
                     simulated=is_sim,
                     source=source_tag,
                     extra={"idempotency_key": body.idempotency_key,
                             "settlement_status": body.settlement_status,
                             "allocated": allocated})
        # Idempotent internal event
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "financial.entry_recorded",
            "source": "revenue.ledger",
            "payload": {"entry_id": entry["id"], "gross": str(gross),
                         "net": str(net), "settlement": body.settlement_status},
            "contact_id": body.contact_id, "organization_id": body.organization_id,
            "idempotency_key": f"led-{body.idempotency_key}",
            "correlation_id": entry["correlation_id"],
            "processing_status": "processed", "retry_count": 0, "error": None,
            "simulated": is_sim, "record_source": source_tag, "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        return {"entry": _public_ledger(entry), "duplicate": False}

    @router.post("/ledger/adjustments")
    async def create_adjustment(body: LedgerEntryIn, admin=Depends(require_admin)):
        """Adjustment or reversal — required for all corrections. Requires
        `related_entry_id` pointing at the original entry."""
        if not body.related_entry_id:
            raise HTTPException(422, "adjustments must set related_entry_id")
        if not body.adjustment_reason or len(body.adjustment_reason) < 8:
            raise HTTPException(422, "adjustment_reason must be at least 8 chars")
        original = await db["financial_ledger"].find_one({"id": body.related_entry_id})
        if not original:
            raise HTTPException(404, "original entry not found")
        # Force entry_type to adjustment/reversal
        if body.entry_type not in ("liability_adjustment", "payment_reversal",
                                     "reconciliation_adjustment"):
            raise HTTPException(422,
                "adjustment endpoint requires entry_type in "
                "{liability_adjustment, payment_reversal, reconciliation_adjustment}")
        # Delegate to the standard create — the append-only guarantee is preserved.
        return await create_ledger_entry(body, admin=admin)

    @router.get("/ledger/entries")
    async def list_ledger(limit: int = Query(default=100, le=500),
                            settlement_status: Optional[str] = None,
                            month: Optional[str] = None,
                            admin=Depends(require_admin)):
        q: dict = {}
        if settlement_status:
            q["settlement_status"] = settlement_status
        if month:
            q["reconciliation_month"] = month
        rows = await db["financial_ledger"].find(q, {"_id": 0})\
            .sort("created_at", -1).limit(limit).to_list(limit)
        return {"entries": [_public_ledger(r) for r in rows], "count": len(rows)}

    @router.get("/ledger/entries/{entry_id}")
    async def get_ledger_entry(entry_id: str, admin=Depends(require_admin)):
        doc = await db["financial_ledger"].find_one({"id": entry_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "entry not found")
        return {"entry": _public_ledger(doc)}

    # ═══════════════════════════════════════════════════════════════════════
    #  ESSENTIAL EXPENSES
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/expenses")
    async def create_expense(body: ExpenseIn, admin=Depends(require_admin)):
        try:
            amt = _validate_money(_D(body.amount), field="amount")
        except ValueError as e:
            raise HTTPException(422, str(e))

        source_tag = "test_fixture" if body.is_test_fixture else "admin_created"
        doc = {
            "id": str(uuid.uuid4()),
            "expense_month": body.expense_month,
            "category": body.category,
            "description": body.description,
            "amount": _to_128(amt),
            "currency": body.currency.upper(),
            "essential": body.essential,
            "source": source_tag,
            "supporting_reference": body.supporting_reference,
            "correction_of_expense_id": body.correction_of_expense_id,
            "reconciliation_status": "unreconciled",
            "environment": "preview",
            "simulated": body.is_test_fixture,
            "created_at": _now(),
            "created_by": admin["email"],
        }
        await db["essential_operating_expenses"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="expense.recorded",
                     target_type="expense", target_id=doc["id"],
                     reason=f"{body.category} ${amt}",
                     simulated=body.is_test_fixture, source=source_tag,
                     extra={"month": body.expense_month, "essential": body.essential})
        return {"expense": _public_expense(doc)}

    @router.get("/expenses")
    async def list_expenses(month: Optional[str] = None, essential: Optional[bool] = None,
                              admin=Depends(require_admin)):
        q: dict = {}
        if month:
            q["expense_month"] = month
        if essential is not None:
            q["essential"] = essential
        rows = await db["essential_operating_expenses"].find(q, {"_id": 0})\
            .sort("expense_month", -1).limit(500).to_list(500)
        return {"expenses": [_public_expense(r) for r in rows], "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  TAX-RESERVE POLICY (versioned, approval-gated, prospective)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/tax-policies")
    async def create_tax_policy(body: TaxPolicyIn, admin=Depends(require_admin)):
        try:
            fed = _D(body.federal_reserve_pct)
            st = _D(body.state_reserve_pct)
            oth = _D(body.other_reserve_pct)
        except ValueError as e:
            raise HTTPException(422, str(e))
        for pct, name in ((fed, "federal_reserve_pct"), (st, "state_reserve_pct"),
                          (oth, "other_reserve_pct")):
            if pct < 0 or pct > Decimal("100"):
                raise HTTPException(422, f"{name} must be in [0, 100]")
            if pct.as_tuple().exponent < -4:
                raise HTTPException(422, f"{name} precision exceeds 4dp")
        latest = await db["tax_reserve_policies"].find_one(
            {}, {"version": 1}, sort=[("version", -1)])
        v = (latest.get("version", 0) if latest else 0) + 1
        doc = {
            "id": str(uuid.uuid4()),
            "federal_reserve_pct": _to_128(fed),
            "state_reserve_pct": _to_128(st),
            "other_reserve_pct": _to_128(oth),
            "effective_date": body.effective_date,
            "end_date": body.end_date,
            "notes": body.notes,
            "approved_by": None, "approval_timestamp": None,
            "version": v, "active": False,
            "source": "admin_created", "environment": "preview",
            "created_at": _now(), "created_by": admin["email"],
        }
        await db["tax_reserve_policies"].insert_one(doc)
        # Queue approval before activation
        approval = {
            "id": str(uuid.uuid4()),
            "request_type": "tax_policy.activate",
            "requested_action": f"activate tax policy v{v}",
            "reason": body.notes or "tax policy version",
            "risk_level": "high",
            "financial_amount_usd": None,
            "related_contact_id": None, "related_organization_id": None,
            "supporting_records": {"policy_id": doc["id"]},
            "correlation_id": str(uuid.uuid4()),
            "status": "pending", "decided_by": None,
            "decided_at": None, "notes": None, "expires_at": None,
            "simulated": True, "source": "admin_created", "environment": "preview",
            "created_at": _now(),
        }
        await db["approval_queue"].insert_one(approval)
        await _audit(db, actor=admin["email"], action="allocation.policy_created",
                     target_type="tax_policy", target_id=doc["id"],
                     approval_required=True, approval_status="pending",
                     correlation_id=approval["correlation_id"],
                     reason=f"tax policy v{v}",
                     simulated=False, source="admin_created")
        return {"tax_policy": _public_taxpolicy(doc), "approval": {**approval, "_id": None}}

    @router.post("/tax-policies/{policy_id}/activate")
    async def activate_tax_policy(policy_id: str, body: Optional[ApprovalRef] = None,
                                    admin=Depends(require_admin)):
        doc = await db["tax_reserve_policies"].find_one({"id": policy_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "policy not found")

        # ── Phase 21 hardening: enforce approval when approval_id is provided ──
        # If an approval_id is passed, it MUST match this policy and MUST be
        # approved-but-not-consumed. If absent, we allow activation for
        # backward compatibility but stamp `approval_enforcement=bypassed` in
        # the audit record so any callers still on the legacy path are
        # discoverable.
        approval_id = (body.approval_id if body else None)
        enforcement = "bypassed_legacy"
        if approval_id:
            enforce_approval, mark_completed, MismatchErr = _approval_helpers()
            try:
                await enforce_approval(
                    db, approval_id=approval_id,
                    request_type="tax_policy.activate",
                    target_id=policy_id,
                    admin_email=admin["email"],
                    require_unexpired=True,
                )
            except MismatchErr as e:
                raise HTTPException(409, f"approval mismatch: {e}")
            enforcement = "enforced"

        await db["tax_reserve_policies"].update_many({"active": True},
                                                       {"$set": {"active": False}})
        await db["tax_reserve_policies"].update_one(
            {"id": policy_id},
            {"$set": {"active": True, "approved_by": admin["email"],
                       "approval_timestamp": _now()}},
        )
        if approval_id:
            _, mark_completed, _ = _approval_helpers()
            await mark_completed(db, approval_id, admin["email"], execution_ref=policy_id)
        await _audit(db, actor=admin["email"], action="tax_policy.activated",
                     target_type="tax_policy", target_id=policy_id,
                     reason=f"activated (prospective only); enforcement={enforcement}",
                     simulated=False, source="admin_created",
                     extra={"approval_id": approval_id,
                             "approval_enforcement": enforcement})
        return {"tax_policy_id": policy_id, "active": True,
                "approval_enforcement": enforcement,
                "approval_id": approval_id}

    @router.get("/tax-policies")
    async def list_tax_policies(admin=Depends(require_admin)):
        rows = await db["tax_reserve_policies"].find({}, {"_id": 0})\
            .sort("version", -1).to_list(50)
        return {"policies": [_public_taxpolicy(r) for r in rows], "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  ALLOCATION POLICY
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/allocation-policies")
    async def list_allocation_policies(admin=Depends(require_admin)):
        rows = await db["allocation_policies"].find({}, {"_id": 0})\
            .sort("version", -1).to_list(100)
        return {"policies": [_public_alloc_policy(r) for r in rows],
                "count": len(rows),
                "current_phase": await current_phase(db)}

    @router.post("/allocation-policies")
    async def request_allocation_policy_change(body: AllocationPolicyIn, admin=Depends(require_admin)):
        """Requesting a change queues an approval. It does NOT activate."""
        try:
            o = _D(body.owner_pct); g = _D(body.growth_reserve_pct)
            wc = _D(body.working_capital_pct)
        except ValueError as e:
            raise HTTPException(422, str(e))
        total = o + g + wc
        if total != Decimal("100.00") and total != Decimal("100"):
            raise HTTPException(422, f"percentages must total 100.00, got {total}")
        for p in (o, g, wc):
            if p < 0 or p > Decimal("100") or p.as_tuple().exponent < -4:
                raise HTTPException(422, "each percentage must be in [0, 100] and ≤ 4dp")
        latest = await db["allocation_policies"].find_one(
            {}, {"version": 1}, sort=[("version", -1)])
        v = (latest.get("version", 0) if latest else 0) + 1
        doc = {
            "id": str(uuid.uuid4()),
            "phase": body.phase,
            "owner_pct": _to_128(o), "growth_reserve_pct": _to_128(g),
            "working_capital_pct": _to_128(wc),
            "effective_date": body.effective_date,
            "version": v, "active": False,       # requires approval
            "approved_by": body.approved_by, "notes": body.notes,
            "source": "admin_created", "environment": "preview",
            "created_at": _now(), "created_by": admin["email"],
        }
        await db["allocation_policies"].insert_one(doc)
        approval = {
            "id": str(uuid.uuid4()),
            "request_type": "allocation_policy.activate",
            "requested_action": f"activate {body.phase} policy v{v}",
            "reason": body.notes or "policy change request",
            "risk_level": "high",
            "financial_amount_usd": None,
            "related_contact_id": None, "related_organization_id": None,
            "supporting_records": {"policy_id": doc["id"]},
            "correlation_id": str(uuid.uuid4()),
            "status": "pending", "decided_by": None, "decided_at": None,
            "notes": None, "expires_at": None,
            "simulated": True, "source": "admin_created", "environment": "preview",
            "created_at": _now(),
        }
        await db["approval_queue"].insert_one(approval)
        await _audit(db, actor=admin["email"], action="allocation.policy_created",
                     target_type="allocation_policy", target_id=doc["id"],
                     approval_required=True, approval_status="pending",
                     correlation_id=approval["correlation_id"],
                     reason=f"{body.phase} v{v}",
                     simulated=False, source="admin_created")
        return {"policy": _public_alloc_policy(doc), "approval": {**approval, "_id": None}}

    @router.post("/allocation-policies/{policy_id}/activate")
    async def activate_allocation_policy(policy_id: str,
                                           body: Optional[ApprovalRef] = None,
                                           admin=Depends(require_admin)):
        """Phase 21 hardening: activate an allocation policy version.

        Enforces the split status semantics:
          • approved: bool — human-approved policy content
          • enabled_for_phase: str|null — the phase name this policy is enabled for
          • currently_applied: bool — the single-live pointer per phase

        Only ONE policy per phase may have currently_applied=True. Activating
        a new one demotes any prior policy for the same phase.
        """
        doc = await db["allocation_policies"].find_one({"id": policy_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "allocation policy not found")

        approval_id = (body.approval_id if body else None)
        enforcement = "bypassed_legacy"
        if approval_id:
            enforce_approval, mark_completed, MismatchErr = _approval_helpers()
            try:
                await enforce_approval(
                    db, approval_id=approval_id,
                    request_type="allocation_policy.activate",
                    target_id=policy_id,
                    admin_email=admin["email"],
                    target_version=doc.get("version"),
                    require_unexpired=True,
                )
            except MismatchErr as e:
                raise HTTPException(409, f"approval mismatch: {e}")
            enforcement = "enforced"

        phase = doc["phase"]
        # Demote any prior policy currently_applied for this phase
        await db["allocation_policies"].update_many(
            {"phase": phase, "currently_applied": True},
            {"$set": {"currently_applied": False, "active": False,
                       "demoted_at": _now(), "demoted_by": admin["email"]}},
        )
        # Promote this one — keep legacy `active` in sync for backward compat.
        await db["allocation_policies"].update_one(
            {"id": policy_id},
            {"$set": {
                "approved": True,
                "enabled_for_phase": phase,
                "currently_applied": True,
                "active": True,                    # backward-compat mirror
                "approved_by": admin["email"],
                "approval_timestamp": _now(),
            }},
        )
        # Enforce single-currently-applied invariant (defense-in-depth check)
        cnt = await db["allocation_policies"].count_documents(
            {"phase": phase, "currently_applied": True})
        if cnt != 1:
            raise HTTPException(500,
                f"invariant violation: {cnt} policies currently_applied for phase {phase!r}")

        if approval_id:
            _, mark_completed, _ = _approval_helpers()
            await mark_completed(db, approval_id, admin["email"], execution_ref=policy_id)

        await _audit(db, actor=admin["email"], action="allocation.policy_activated",
                     target_type="allocation_policy", target_id=policy_id,
                     reason=(f"phase={phase} v={doc.get('version')} "
                              f"enforcement={enforcement}"),
                     simulated=False, source="admin_created",
                     extra={"approval_id": approval_id,
                             "approval_enforcement": enforcement,
                             "phase": phase})
        return {"policy_id": policy_id, "phase": phase,
                "approved": True, "enabled_for_phase": phase,
                "currently_applied": True,
                "approval_enforcement": enforcement,
                "approval_id": approval_id}

    # ═══════════════════════════════════════════════════════════════════════
    #  RESERVE TARGET
    # ═══════════════════════════════════════════════════════════════════════
    async def _reserve_target(db) -> dict:
        """Compute the 3-month reserve target using recent essential expenses,
        or fall back to the approved monthly budget × 3."""
        # Find the last 3 complete calendar months (business tz)
        now = business_now()
        months: list[str] = []
        y, m = now.year, now.month
        for _ in range(6):  # look back up to 6 months
            m -= 1
            if m == 0:
                m = 12; y -= 1
            months.append(f"{y:04d}-{m:02d}")
        # Restrict to "complete" months (all of them are complete since we
        # subtracted 1 first).
        recent_three = months[:3]

        # Aggregate essential expenses per month
        totals: dict[str, Decimal] = {}
        for mk in recent_three:
            rows = await db["essential_operating_expenses"].find(
                {"expense_month": mk, "essential": True, "simulated": False},
                {"_id": 0, "amount": 1}).to_list(500)
            totals[mk] = sum((_D(r["amount"]) for r in rows), Decimal("0"))

        months_with_data = [mk for mk, t in totals.items() if t > 0]
        method = "three_month_rolling_average" if len(months_with_data) >= 3 else "operating_budget_fallback"

        if method == "three_month_rolling_average":
            avg = _quantize(sum(totals.values(), Decimal("0")) / Decimal("3"))
            target = _quantize(avg * Decimal("3"))
            approved_budget_used = None
        else:
            # Fallback: current approved budget × 3
            budget = await db["operating_budget_history"].find_one(
                {}, {"_id": 0}, sort=[("effective_date", -1)])
            approved_budget_used = _D(budget["monthly_budget_usd"]) if budget else Decimal("0")
            avg = approved_budget_used
            target = _quantize(approved_budget_used * Decimal("3"))

        # Derive current WC reserve from the ledger (append-only, reproducible)
        pipeline = [
            {"$match": {"allocated": True}},
            {"$group": {"_id": None,
                         "wc": {"$sum": {"$toDecimal": "$working_capital_allocation"}}}},
        ]
        agg = await db["financial_ledger"].aggregate(pipeline).to_list(1)
        if agg and agg[0].get("wc") is not None:
            wc_balance = _quantize(_D(agg[0]["wc"]))
        else:
            wc_balance = Decimal("0")
        remaining = _quantize(max(Decimal("0"), target - wc_balance))

        return {
            "calculation_method": method,
            "included_months": months_with_data,
            "excluded_months": [m for m in recent_three if m not in months_with_data],
            "average_monthly_essential_expenses": str(avg),
            "approved_budget_used": (str(approved_budget_used)
                                       if approved_budget_used is not None else None),
            "three_month_target": str(target),
            "current_working_capital_reserve": str(wc_balance),
            "amount_remaining": str(remaining),
            "policy_version": None,
            "calculated_at": _now().isoformat(),
        }

    @router.get("/reserve/target")
    async def reserve_target(admin=Depends(require_admin)):
        info = await _reserve_target(db)
        await _audit(db, actor=admin["email"], action="reserve.target_calculated",
                     target_type="reserve", target_id="current",
                     reason=f"target=${info['three_month_target']}",
                     simulated=False, source="admin_created",
                     extra=info)
        return info

    # ═══════════════════════════════════════════════════════════════════════
    #  RECONCILIATION
    # ═══════════════════════════════════════════════════════════════════════
    async def _recon_snapshot(db, calendar_month: str) -> dict:
        """Compute totals for the given month from the ledger."""
        pipeline = [
            {"$match": {"reconciliation_month": calendar_month}},
            {"$group": {"_id": "$settlement_status",
                         "gross": {"$sum": {"$toDecimal": "$gross_amount"}},
                         "proc_fee": {"$sum": {"$toDecimal": "$processor_fee"}},
                         "sales_tax": {"$sum": {"$toDecimal": "$sales_tax_liability"}},
                         "fed_res": {"$sum": {"$toDecimal": "$federal_tax_reserve"}},
                         "state_res": {"$sum": {"$toDecimal": "$state_tax_reserve"}},
                         "other_res": {"$sum": {"$toDecimal": "$other_tax_reserve"}},
                         "refund": {"$sum": {"$toDecimal": "$refund_amount"}},
                         "chargeback": {"$sum": {"$toDecimal": "$chargeback_amount"}},
                         "other_direct": {"$sum": {"$toDecimal": "$other_direct_liabilities"}},
                         "net": {"$sum": {"$toDecimal": "$net_distributable_amount"}},
                         "owner": {"$sum": {"$toDecimal": "$owner_allocation"}},
                         "growth": {"$sum": {"$toDecimal": "$growth_reserve_allocation"}},
                         "wc": {"$sum": {"$toDecimal": "$working_capital_allocation"}},
                         "n": {"$sum": 1}}}
        ]
        agg = await db["financial_ledger"].aggregate(pipeline).to_list(20)
        # Totals initialised to 0
        totals = {
            "gross_collected": Decimal("0"), "cleared_collected": Decimal("0"),
            "pending_funds": Decimal("0"),
            "processor_fees": Decimal("0"), "sales_tax_liabilities": Decimal("0"),
            "federal_tax_reserve": Decimal("0"), "state_tax_reserve": Decimal("0"),
            "other_tax_reserve": Decimal("0"),
            "refunds": Decimal("0"), "chargebacks": Decimal("0"),
            "other_direct_liabilities": Decimal("0"),
            "net_distributable": Decimal("0"),
            "owner_allocation_accrued": Decimal("0"),
            "growth_reserve_accrued": Decimal("0"),
            "working_capital_reserve_accrued": Decimal("0"),
            "unresolved_transaction_count": 0,
        }
        for row in agg:
            st = row["_id"]
            gross = _D(row["gross"])
            totals["gross_collected"] += gross
            if st == "cleared":
                totals["cleared_collected"] += gross
            elif st in ("pending", "processing"):
                totals["pending_funds"] += gross
            if st in ("disputed", "refunded", "reversed", "uncollectible"):
                totals["unresolved_transaction_count"] += int(row["n"])
            totals["processor_fees"] += _D(row["proc_fee"])
            totals["sales_tax_liabilities"] += _D(row["sales_tax"])
            totals["federal_tax_reserve"] += _D(row["fed_res"])
            totals["state_tax_reserve"] += _D(row["state_res"])
            totals["other_tax_reserve"] += _D(row["other_res"])
            totals["refunds"] += _D(row["refund"])
            totals["chargebacks"] += _D(row["chargeback"])
            totals["other_direct_liabilities"] += _D(row["other_direct"])
            totals["net_distributable"] += _D(row["net"])
            totals["owner_allocation_accrued"] += _D(row["owner"])
            totals["growth_reserve_accrued"] += _D(row["growth"])
            totals["working_capital_reserve_accrued"] += _D(row["wc"])
        for k in list(totals.keys()):
            if isinstance(totals[k], Decimal):
                totals[k] = _quantize(totals[k])
        return totals

    @router.post("/reconciliations")
    async def create_recon(body: ReconciliationCreateIn, admin=Depends(require_admin)):
        existing = await db["monthly_reconciliations"].find_one(
            {"calendar_month": body.calendar_month}, {"_id": 0})
        if existing:
            return {"reconciliation": _public_recon(existing), "duplicate": True}
        snapshot = await _recon_snapshot(db, body.calendar_month)
        tax_policy = await current_tax_policy(db)
        blocked = tax_policy is None
        target = await _reserve_target(db)
        doc = {
            "id": str(uuid.uuid4()),
            "calendar_month": body.calendar_month,
            "business_timezone": str(BUSINESS_TZ),
            "status": "blocked" if blocked else "draft",
            **{k: (_to_128(v) if isinstance(v, Decimal) else v) for k, v in snapshot.items()},
            "reserve_target": _to_128(_D(target["three_month_target"])),
            "reserve_balance": _to_128(_D(target["current_working_capital_reserve"])),
            "allocation_phase": await current_phase(db),
            "allocation_policy_version": (await get_active_policy(db, await current_phase(db)) or {}).get("version"),
            "created_at": _now(),
            "closed_at": None,
            "created_by": admin["email"],
            "approval_status": "pending" if blocked else "not_required",
            "notes": body.notes,
            "environment": "preview",
            "simulated": False,
            "source": "admin_created",
        }
        await db["monthly_reconciliations"].insert_one(doc)
        await _audit(db, actor=admin["email"],
                     action=("reconciliation.blocked" if blocked else "reconciliation.created"),
                     target_type="reconciliation", target_id=doc["id"],
                     reason=("blocked: tax policy incomplete" if blocked else f"draft {body.calendar_month}"),
                     simulated=False, source="admin_created",
                     extra={"month": body.calendar_month})
        return {"reconciliation": _public_recon(doc), "duplicate": False,
                "blocked": blocked}

    @router.get("/reconciliations")
    async def list_recon(admin=Depends(require_admin)):
        rows = await db["monthly_reconciliations"].find({}, {"_id": 0})\
            .sort("calendar_month", -1).limit(60).to_list(60)
        return {"reconciliations": [_public_recon(r) for r in rows], "count": len(rows)}

    @router.get("/reconciliations/{recon_id}")
    async def get_recon(recon_id: str, admin=Depends(require_admin)):
        doc = await db["monthly_reconciliations"].find_one({"id": recon_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "reconciliation not found")
        return {"reconciliation": _public_recon(doc)}

    @router.post("/reconciliations/close")
    async def close_recon(body: ReconciliationCloseIn, admin=Depends(require_admin)):
        doc = await db["monthly_reconciliations"].find_one({"id": body.reconciliation_id})
        if not doc:
            raise HTTPException(404, "reconciliation not found")
        if doc["status"] == "closed":
            raise HTTPException(409, "reconciliation is already closed")
        if doc["status"] == "blocked":
            raise HTTPException(400, "reconciliation is blocked; resolve required policies first")

        # ── Phase 21 hardening: enforce approval when approval_id is provided ──
        enforcement = "bypassed_legacy"
        if body.approval_id:
            enforce_approval, mark_completed, MismatchErr = _approval_helpers()
            try:
                await enforce_approval(
                    db, approval_id=body.approval_id,
                    request_type="reconciliation.close",
                    target_id=body.reconciliation_id,
                    admin_email=admin["email"],
                    require_unexpired=True,
                )
            except MismatchErr as e:
                raise HTTPException(409, f"approval mismatch: {e}")
            enforcement = "enforced"

        # Refresh snapshot before close (reproducible)
        snapshot = await _recon_snapshot(db, doc["calendar_month"])
        target = await _reserve_target(db)
        update = {
            **{k: (_to_128(v) if isinstance(v, Decimal) else v) for k, v in snapshot.items()},
            "reserve_target": _to_128(_D(target["three_month_target"])),
            "reserve_balance": _to_128(_D(target["current_working_capital_reserve"])),
            "status": "closed",
            "closed_at": _now(),
            "closed_by": admin["email"],
            "close_reason": body.close_reason,
            "close_approval_id": body.approval_id,
            "close_approval_enforcement": enforcement,
        }
        await db["monthly_reconciliations"].update_one({"id": doc["id"]}, {"$set": update})
        merged = {**doc, **update}
        correlation_id = str(uuid.uuid4())

        if body.approval_id:
            _, mark_completed, _ = _approval_helpers()
            await mark_completed(db, body.approval_id, admin["email"],
                                    execution_ref=doc["id"])

        await _audit(db, actor=admin["email"], action="reconciliation.closed",
                     target_type="reconciliation", target_id=doc["id"],
                     correlation_id=correlation_id,
                     reason=(body.close_reason
                              + f" [enforcement={enforcement}]"),
                     simulated=False, source="admin_created",
                     extra={"month": doc["calendar_month"],
                             "approval_id": body.approval_id,
                             "approval_enforcement": enforcement})
        # Phase transition check
        await _maybe_transition_phase(db, admin["email"], correlation_id, merged, target)
        # Draw calculation follows
        draw = await _compute_owner_draw(db, admin["email"], merged, target, correlation_id)
        return {"reconciliation": _public_recon(merged), "owner_draw": draw,
                "approval_enforcement": enforcement,
                "approval_id": body.approval_id}

    async def _maybe_transition_phase(db, admin_email: str, correlation_id: str,
                                        recon_doc: dict, target: dict) -> None:
        state = await db["allocation_phase_state"].find_one({"id": "current"}, {"_id": 0})
        cur = (state or {}).get("phase", "startup")
        reserve = _D(target["current_working_capital_reserve"])
        target_v = _D(target["three_month_target"])
        new_phase = cur
        if cur == "startup" and reserve >= target_v and target_v > 0:
            new_phase = "established"
            action = "reserve.threshold_reached"
        elif cur == "established" and reserve < target_v:
            new_phase = "startup"
            action = "reserve.threshold_lost"
        else:
            return
        await db["allocation_phase_state"].update_one(
            {"id": "current"},
            {"$set": {
                "phase": new_phase, "since": _now(),
                "last_reconciliation_id": recon_doc["id"],
                "reserve_balance_at_transition": _to_128(reserve),
                "reserve_target_at_transition": _to_128(target_v),
            }},
        )
        await _audit(db, actor=admin_email, action=action,
                     target_type="allocation_phase", target_id="current",
                     correlation_id=correlation_id,
                     reason=f"phase {cur} → {new_phase} at recon {recon_doc['calendar_month']}",
                     simulated=False, source="admin_created")
        await _audit(db, actor=admin_email, action="allocation.phase_changed",
                     target_type="allocation_phase", target_id="current",
                     correlation_id=correlation_id,
                     reason=f"prospective from next transaction; not retroactive",
                     simulated=False, source="admin_created",
                     extra={"previous_phase": cur, "new_phase": new_phase,
                             "reserve_balance": str(reserve),
                             "reserve_target": str(target_v)})

    async def _compute_owner_draw(db, admin_email: str, recon_doc: dict,
                                    target: dict, correlation_id: str) -> dict:
        month = recon_doc["calendar_month"]
        # Only one draw record per closed month
        existing = await db["owner_draws"].find_one({"reconciliation_month": month},
                                                      {"_id": 0})
        if existing:
            return _public_draw(existing)

        tax_policy = await current_tax_policy(db)
        blocked = tax_policy is None
        # Eligible owner allocation = accrued owner_allocation on CLEARED only
        pipeline = [
            {"$match": {"reconciliation_month": month,
                         "settlement_status": "cleared", "allocated": True}},
            {"$group": {"_id": None,
                         "owner": {"$sum": {"$toDecimal": "$owner_allocation"}}}},
        ]
        agg = await db["financial_ledger"].aggregate(pipeline).to_list(1)
        eligible = _quantize(_D((agg[0]["owner"] if agg else 0)))
        recommended = max(Decimal("0"), eligible)
        status: str
        if blocked:
            status = "blocked"
        elif recommended == 0:
            status = "recommended"       # zero-dollar month is still a recommendation record
        else:
            status = "recommended"
        doc = {
            "id": str(uuid.uuid4()),
            "reconciliation_month": month,
            "reconciliation_id": recon_doc["id"],
            "eligible_owner_allocation": _to_128(eligible),
            "carried_forward_adjustment": _to_128(Decimal("0")),
            "recommended_amount": _to_128(recommended),
            "recommendation_date": owner_draw_date_for(month).isoformat(),
            "status": status,
            "approval_status": "pending",
            "approved_by": None, "approved_at": None,
            "rejected_reason": None,
            "manually_paid_amount": None, "manual_payment_date": None,
            "manual_payment_reference": None,
            "notes": ("blocked: tax policy incomplete" if blocked else None),
            "environment": "preview", "simulated": False, "source": "admin_created",
            "created_at": _now(), "updated_at": _now(),
        }
        await db["owner_draws"].insert_one(doc)
        await _audit(db, actor=admin_email, action="owner_draw.calculated",
                     target_type="owner_draw", target_id=doc["id"],
                     correlation_id=correlation_id,
                     reason=(f"blocked: tax policy incomplete" if blocked
                              else f"recommended ${recommended:,.2f} for {month}"),
                     simulated=False, source="admin_created")
        return _public_draw(doc)

    # ═══════════════════════════════════════════════════════════════════════
    #  OWNER DRAWS
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/owner-draws")
    async def list_draws(admin=Depends(require_admin)):
        rows = await db["owner_draws"].find({}, {"_id": 0})\
            .sort("reconciliation_month", -1).limit(60).to_list(60)
        return {"owner_draws": [_public_draw(r) for r in rows], "count": len(rows)}

    @router.get("/owner-draws/{draw_id}")
    async def get_draw(draw_id: str, admin=Depends(require_admin)):
        doc = await db["owner_draws"].find_one({"id": draw_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "owner draw not found")
        return {"owner_draw": _public_draw(doc)}

    @router.post("/owner-draws/decision")
    async def decide_draw(body: OwnerDrawDecisionIn, admin=Depends(require_admin)):
        doc = await db["owner_draws"].find_one({"id": body.draw_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "owner draw not found")
        if doc["status"] == "blocked":
            raise HTTPException(400, "draw is blocked; resolve required policies first")
        if doc["approval_status"] not in ("pending",):
            raise HTTPException(400, "already decided")

        # ── Phase 21 hardening: enforce approval when approval_id is provided ──
        enforcement = "bypassed_legacy"
        if body.approval_id:
            enforce_approval, mark_completed, MismatchErr = _approval_helpers()
            try:
                await enforce_approval(
                    db, approval_id=body.approval_id,
                    request_type=f"owner_draw.{body.decision}",
                    target_id=body.draw_id,
                    admin_email=admin["email"],
                    require_unexpired=True,
                )
            except MismatchErr as e:
                raise HTTPException(409, f"approval mismatch: {e}")
            enforcement = "enforced"

        update = {"approval_status": body.decision, "updated_at": _now(),
                    "approved_by": admin["email"], "approved_at": _now()}
        if body.decision == "rejected":
            update["rejected_reason"] = body.reason or "no reason provided"
            update["status"] = "rejected"
        else:
            update["status"] = "approved"
        await db["owner_draws"].update_one({"id": body.draw_id}, {"$set": update})

        if body.approval_id:
            _, mark_completed, _ = _approval_helpers()
            await mark_completed(db, body.approval_id, admin["email"],
                                    execution_ref=body.draw_id)

        await _audit(db, actor=admin["email"],
                     action=f"owner_draw.{body.decision}",
                     target_type="owner_draw", target_id=body.draw_id,
                     reason=(body.reason or "") + f" [enforcement={enforcement}]",
                     simulated=False, source="admin_created",
                     extra={"approval_id": body.approval_id,
                             "approval_enforcement": enforcement})
        return {"owner_draw": _public_draw({**doc, **update}),
                "approval_enforcement": enforcement,
                "approval_id": body.approval_id}

    @router.post("/owner-draws/manual-payment")
    async def record_manual_payment(body: OwnerDrawManualPayIn, admin=Depends(require_admin)):
        doc = await db["owner_draws"].find_one({"id": body.draw_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "owner draw not found")
        if doc["approval_status"] != "approved":
            raise HTTPException(400, "manual payment requires an approved recommendation")
        if doc["status"] in ("blocked", "rejected"):
            raise HTTPException(400, f"cannot record payment against a {doc['status']} draw")
        try:
            paid = _validate_money(_D(body.manually_paid_amount), field="manually_paid_amount")
        except ValueError as e:
            raise HTTPException(422, str(e))
        recommended = _D(doc["recommended_amount"])

        # ── Append-only payment record with idempotency + partial-payment support ──
        # Duplicate reference check
        existing_ref = await db["owner_draw_payments"].find_one(
            {"draw_id": body.draw_id, "payment_reference": body.manual_payment_reference})
        if existing_ref:
            raise HTTPException(409, "duplicate payment_reference for this draw")
        # Idempotency key check
        idem_key = f"pay-{body.draw_id}-{body.manual_payment_reference}"
        existing_idem = await db["owner_draw_payments"].find_one({"idempotency_key": idem_key})
        if existing_idem:
            return {"payment": {**existing_idem, "_id": None}, "duplicate": True}

        # Cumulative overpayment check
        prev = await db["owner_draw_payments"].find(
            {"draw_id": body.draw_id}, {"_id": 0, "amount": 1}).to_list(200)
        prev_total = sum((_D(p["amount"]) for p in prev), Decimal("0"))
        new_total = _quantize(prev_total + paid)
        if new_total > recommended:
            raise HTTPException(400, (
                f"cumulative payments ${new_total} exceed approved recommendation "
                f"${recommended} for this draw"))

        payment_doc = {
            "id": str(uuid.uuid4()),
            "draw_id": body.draw_id,
            "amount": _to_128(paid),
            "payment_date": body.manual_payment_date,
            "payment_reference": body.manual_payment_reference,
            "idempotency_key": idem_key,
            "cumulative_total_at_time": _to_128(new_total),
            "created_by": admin["email"],
            "created_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
            "reversed_by_payment_id": None,
            "reverses_payment_id": None,
        }
        await db["owner_draw_payments"].insert_one(payment_doc)

        # Update the aggregate on the draw record (does NOT overwrite prior payments;
        # the append-only payments collection is the source of truth).
        update = {
            "manually_paid_amount": _to_128(new_total),
            "last_manual_payment_date": body.manual_payment_date,
            "last_manual_payment_reference": body.manual_payment_reference,
            "manual_payments_count": len(prev) + 1,
            "status": ("recorded_as_manually_paid"
                        if new_total >= recommended
                        else "approved"),   # remain approved if partially paid
            "updated_at": _now(),
        }
        await db["owner_draws"].update_one({"id": body.draw_id}, {"$set": update})
        await _audit(db, actor=admin["email"], action="owner_draw.recorded_manually",
                     target_type="owner_draw", target_id=body.draw_id,
                     reason=f"manual pay ref {body.manual_payment_reference}",
                     simulated=False, source="admin_created",
                     extra={"amount": str(paid), "cumulative": str(new_total),
                             "payment_id": payment_doc["id"]})
        # Serialize Decimal128 for JSON response
        pub_payment = {**payment_doc, "_id": None}
        pub_payment["amount"] = str(paid)
        pub_payment["cumulative_total_at_time"] = str(new_total)
        return {"payment": pub_payment,
                "cumulative_paid": str(new_total),
                "draw_status": update["status"]}

    # ═══════════════════════════════════════════════════════════════════════
    #  OWNER-DRAW APPEND-ONLY CORRECTIONS (Phase 21 hardening)
    # ═══════════════════════════════════════════════════════════════════════
    async def _load_original_payment(draw_id: str, original_payment_id: str) -> dict:
        """Fetch an existing owner-draw payment. 404s if not found."""
        orig = await db["owner_draw_payments"].find_one(
            {"id": original_payment_id, "draw_id": draw_id}, {"_id": 0})
        if not orig:
            raise HTTPException(404, "original payment not found for this draw")
        return orig

    async def _refresh_draw_summary(draw_id: str, admin_email: str) -> dict:
        """Recompute the owner_draws aggregate cache from the append-only
        payments collection (payments = source of truth)."""
        rows = await db["owner_draw_payments"].find(
            {"draw_id": draw_id}, {"_id": 0, "amount": 1, "payment_date": 1,
                                    "payment_reference": 1}
        ).to_list(500)
        total = sum((_D(r["amount"]) for r in rows), Decimal("0"))
        total = _quantize(total)
        # Latest payment (by insert order)
        latest = rows[-1] if rows else None
        update = {
            "manually_paid_amount": _to_128(total),
            "manual_payments_count": len(rows),
            "updated_at": _now(),
        }
        if latest:
            update["last_manual_payment_date"] = latest.get("payment_date")
            update["last_manual_payment_reference"] = latest.get("payment_reference")
        # Derive status
        cur = await db["owner_draws"].find_one({"id": draw_id}, {"_id": 0})
        if cur:
            recommended = _D(cur["recommended_amount"])
            if total >= recommended and total > 0:
                update["status"] = "recorded_as_manually_paid"
            elif cur.get("status") in ("recorded_as_manually_paid",) and total < recommended:
                # Reversal dropped total below recommended → back to approved
                update["status"] = "approved"
        await db["owner_draws"].update_one({"id": draw_id}, {"$set": update})
        return {"cumulative_paid": str(total),
                "payment_count": len(rows),
                "status": update.get("status")}

    @router.post("/owner-draws/{draw_id}/adjustment")
    async def record_draw_adjustment(draw_id: str, body: OwnerDrawAdjustmentIn,
                                       admin=Depends(require_admin)):
        """Append-only adjustment of a prior owner-draw payment. Never mutates
        the original row; writes a new row linked via
        ``adjustment_of_payment_id``. REQUIRES a matching approval record."""
        if body.draw_id != draw_id:
            raise HTTPException(422, "path draw_id and body.draw_id must match")
        draw = await db["owner_draws"].find_one({"id": draw_id}, {"_id": 0})
        if not draw:
            raise HTTPException(404, "owner draw not found")
        original = await _load_original_payment(draw_id, body.original_payment_id)
        if original.get("reverses_payment_id") or original.get("adjustment_of_payment_id"):
            raise HTTPException(400,
                "cannot adjust a correction row; only original payments may be adjusted")

        try:
            amt = _validate_money(_D(body.adjustment_amount),
                                     allow_negative=True,
                                     field="adjustment_amount")
        except ValueError as e:
            raise HTTPException(422, str(e))
        if amt == Decimal("0"):
            raise HTTPException(422, "adjustment_amount cannot be zero")

        # ── Enforce approval (required) ──
        enforce_approval, mark_completed, MismatchErr = _approval_helpers()
        try:
            await enforce_approval(
                db, approval_id=body.approval_id,
                request_type="owner_draw.adjustment",
                target_id=body.original_payment_id,
                admin_email=admin["email"],
                amount_usd=str(amt),
                require_unexpired=True,
            )
        except MismatchErr as e:
            raise HTTPException(409, f"approval mismatch: {e}")

        # Idempotency by (draw_id, reference + "-ADJ")
        idem_key = f"adj-{body.draw_id}-{body.payment_reference}"
        existing_idem = await db["owner_draw_payments"].find_one({"idempotency_key": idem_key})
        if existing_idem:
            return {"payment": {**existing_idem, "_id": None,
                                  "amount": str(_D(existing_idem["amount"]))},
                    "duplicate": True}

        adj_doc = {
            "id": str(uuid.uuid4()),
            "draw_id": draw_id,
            "amount": _to_128(amt),                    # signed (may be negative)
            "payment_date": body.payment_date,
            "payment_reference": body.payment_reference,
            "idempotency_key": idem_key,
            "reason": body.reason,
            "adjustment_of_payment_id": body.original_payment_id,
            "reverses_payment_id": None,
            "created_by": admin["email"],
            "created_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
            "correction_type": "adjustment",
            "approval_id": body.approval_id,
        }
        await db["owner_draw_payments"].insert_one(adj_doc)
        await mark_completed(db, body.approval_id, admin["email"],
                                execution_ref=adj_doc["id"])
        summary = await _refresh_draw_summary(draw_id, admin["email"])
        await _audit(db, actor=admin["email"], action="owner_draw.adjustment_recorded",
                     target_type="owner_draw_payment", target_id=adj_doc["id"],
                     reason=body.reason, simulated=False, source="admin_created",
                     extra={"draw_id": draw_id,
                             "original_payment_id": body.original_payment_id,
                             "amount": str(amt),
                             "cumulative_paid": summary["cumulative_paid"],
                             "approval_id": body.approval_id})
        pub = {**adj_doc, "_id": None, "amount": str(amt)}
        return {"payment": pub, "summary": summary}

    @router.post("/owner-draws/{draw_id}/reversal")
    async def record_draw_reversal(draw_id: str, body: OwnerDrawReversalIn,
                                     admin=Depends(require_admin)):
        """Append-only FULL reversal of a prior owner-draw payment. Writes a
        new row with the exact opposite amount and ``reverses_payment_id``
        pointing to the original. REQUIRES a matching approval record."""
        if body.draw_id != draw_id:
            raise HTTPException(422, "path draw_id and body.draw_id must match")
        draw = await db["owner_draws"].find_one({"id": draw_id}, {"_id": 0})
        if not draw:
            raise HTTPException(404, "owner draw not found")
        original = await _load_original_payment(draw_id, body.original_payment_id)
        if original.get("reverses_payment_id") or original.get("adjustment_of_payment_id"):
            raise HTTPException(400,
                "cannot reverse a correction row; only original payments may be reversed")

        # Already reversed?
        already = await db["owner_draw_payments"].find_one(
            {"draw_id": draw_id, "reverses_payment_id": body.original_payment_id})
        if already:
            raise HTTPException(409, "this payment has already been reversed")

        original_amt = _D(original["amount"])
        reverse_amt = -original_amt

        # ── Enforce approval (required) ──
        enforce_approval, mark_completed, MismatchErr = _approval_helpers()
        try:
            await enforce_approval(
                db, approval_id=body.approval_id,
                request_type="owner_draw.reversal",
                target_id=body.original_payment_id,
                admin_email=admin["email"],
                amount_usd=str(reverse_amt),
                require_unexpired=True,
            )
        except MismatchErr as e:
            raise HTTPException(409, f"approval mismatch: {e}")

        idem_key = f"rev-{body.draw_id}-{body.original_payment_id}"
        existing_idem = await db["owner_draw_payments"].find_one({"idempotency_key": idem_key})
        if existing_idem:
            return {"payment": {**existing_idem, "_id": None,
                                  "amount": str(_D(existing_idem["amount"]))},
                    "duplicate": True}

        rev_doc = {
            "id": str(uuid.uuid4()),
            "draw_id": draw_id,
            "amount": _to_128(reverse_amt),
            "payment_date": body.payment_date,
            "payment_reference": body.payment_reference,
            "idempotency_key": idem_key,
            "reason": body.reason,
            "adjustment_of_payment_id": None,
            "reverses_payment_id": body.original_payment_id,
            "created_by": admin["email"],
            "created_at": _now(),
            "environment": "preview", "simulated": False,
            "source": "admin_created",
            "correction_type": "reversal",
            "approval_id": body.approval_id,
        }
        await db["owner_draw_payments"].insert_one(rev_doc)
        await mark_completed(db, body.approval_id, admin["email"],
                                execution_ref=rev_doc["id"])
        summary = await _refresh_draw_summary(draw_id, admin["email"])
        await _audit(db, actor=admin["email"], action="owner_draw.reversal_recorded",
                     target_type="owner_draw_payment", target_id=rev_doc["id"],
                     reason=body.reason, simulated=False, source="admin_created",
                     extra={"draw_id": draw_id,
                             "reverses_payment_id": body.original_payment_id,
                             "amount": str(reverse_amt),
                             "cumulative_paid": summary["cumulative_paid"],
                             "approval_id": body.approval_id})
        pub = {**rev_doc, "_id": None, "amount": str(reverse_amt)}
        return {"payment": pub, "summary": summary}

    @router.get("/owner-draws/{draw_id}/payments")
    async def list_draw_payments(draw_id: str, admin=Depends(require_admin)):
        """Full append-only payment history for a draw (payments = source of truth)."""
        rows = await db["owner_draw_payments"].find(
            {"draw_id": draw_id}, {"_id": 0}
        ).sort("created_at", 1).to_list(500)
        out = []
        total = Decimal("0")
        for r in rows:
            amt = _D(r["amount"])
            total += amt
            pub = {**r, "amount": str(amt)}
            if isinstance(pub.get("cumulative_total_at_time"), Decimal128):
                pub["cumulative_total_at_time"] = str(pub["cumulative_total_at_time"].to_decimal())
            out.append(pub)
        return {"payments": out, "count": len(out),
                "cumulative_total": str(_quantize(total))}

    # ═══════════════════════════════════════════════════════════════════════
    #  DASHBOARD SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/phase3/summary")
    async def phase3_summary(admin=Depends(require_admin)):
        tax = await current_tax_policy(db)
        phase = await current_phase(db)
        active_policy = await get_active_policy(db, phase)
        target = await _reserve_target(db)
        # Balances derived from ledger
        pipeline = [
            {"$match": {"allocated": True}},
            {"$group": {"_id": None,
                         "owner": {"$sum": {"$toDecimal": "$owner_allocation"}},
                         "growth": {"$sum": {"$toDecimal": "$growth_reserve_allocation"}},
                         "wc": {"$sum": {"$toDecimal": "$working_capital_allocation"}},
                         "fed": {"$sum": {"$toDecimal": "$federal_tax_reserve"}},
                         "state": {"$sum": {"$toDecimal": "$state_tax_reserve"}},
                         "sales_tax": {"$sum": {"$toDecimal": "$sales_tax_liability"}}}},
        ]
        agg = await db["financial_ledger"].aggregate(pipeline).to_list(1)
        row = agg[0] if agg else {}
        cash_pipeline = [
            {"$group": {"_id": "$settlement_status",
                         "gross": {"$sum": {"$toDecimal": "$gross_amount"}}}},
        ]
        cash_agg = await db["financial_ledger"].aggregate(cash_pipeline).to_list(20)
        cleared_cash = pending_cash = Decimal("0")
        for r in cash_agg:
            if r["_id"] == "cleared":
                cleared_cash += _D(r["gross"])
            elif r["_id"] in ("pending", "processing"):
                pending_cash += _D(r["gross"])
        return {
            "allocation_phase": phase,
            "active_policy": _public_alloc_policy(active_policy) if active_policy else None,
            "tax_policy_configured": bool(tax),
            "tax_policy_version": tax.get("version") if tax else None,
            "cleared_cash": str(_quantize(cleared_cash)),
            "pending_cash": str(_quantize(pending_cash)),
            "owner_distribution_payable": str(_quantize(_D(row.get("owner", 0)))),
            "growth_reserve": str(_quantize(_D(row.get("growth", 0)))),
            "working_capital_reserve": str(_quantize(_D(row.get("wc", 0)))),
            "federal_tax_reserve": str(_quantize(_D(row.get("fed", 0)))),
            "state_tax_reserve": str(_quantize(_D(row.get("state", 0)))),
            "sales_tax_liabilities": str(_quantize(_D(row.get("sales_tax", 0)))),
            "three_month_reserve_target": target["three_month_target"],
            "amount_remaining_before_transition": target["amount_remaining"],
            "reserve_calculation_method": target["calculation_method"],
            "next_owner_draw_recommendation_date": owner_draw_date_for(
                month_key(business_now())).isoformat(),
            "live_actions_enabled": live_actions_enabled(),
            "environment": "preview",
            "disclaimer": (
                "Internal cash-management subledger. NOT professional bookkeeping, "
                "tax preparation, banking, or a general ledger. Calculated reserves "
                "are internal estimates only and are not tax or accounting advice."
            ),
        }

    return router


# ─── Public-JSON converters ────────────────────────────────────────────────
_DECIMAL_FIELDS_LEDGER = (
    "gross_amount", "processor_fee", "sales_tax_liability", "federal_tax_reserve",
    "state_tax_reserve", "other_tax_reserve", "refund_amount", "chargeback_amount",
    "other_direct_liabilities", "net_distributable_amount", "owner_allocation",
    "growth_reserve_allocation", "working_capital_allocation",
)
_DECIMAL_FIELDS_RECON = (
    "gross_collected", "cleared_collected", "pending_funds",
    "processor_fees", "sales_tax_liabilities", "federal_tax_reserve",
    "state_tax_reserve", "other_tax_reserve", "refunds", "chargebacks",
    "other_direct_liabilities", "net_distributable",
    "owner_allocation_accrued", "growth_reserve_accrued",
    "working_capital_reserve_accrued", "reserve_target", "reserve_balance",
)


def _decimalize(doc: dict, keys: tuple) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k in keys:
        v = out.get(k)
        if isinstance(v, Decimal128):
            out[k] = str(v.to_decimal())
    return out


def _public_ledger(doc: dict) -> dict:
    return _decimalize(doc, _DECIMAL_FIELDS_LEDGER)


def _public_recon(doc: dict) -> dict:
    return _decimalize(doc, _DECIMAL_FIELDS_RECON)


def _public_expense(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(out.get("amount"), Decimal128):
        out["amount"] = str(out["amount"].to_decimal())
    return out


def _public_taxpolicy(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("federal_reserve_pct", "state_reserve_pct", "other_reserve_pct"):
        if isinstance(out.get(k), Decimal128):
            out[k] = str(out[k].to_decimal())
    return out


def _public_alloc_policy(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("owner_pct", "growth_reserve_pct", "working_capital_pct"):
        if isinstance(out.get(k), Decimal128):
            out[k] = str(out[k].to_decimal())
    return out


def _public_draw(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("eligible_owner_allocation", "carried_forward_adjustment",
                "recommended_amount", "manually_paid_amount"):
        if isinstance(out.get(k), Decimal128):
            out[k] = str(out[k].to_decimal())
    return out
