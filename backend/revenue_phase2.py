"""
revenue_phase2.py — Phase 2 of the Revenue Control Center.

Adds, on top of Phase 1:
  • Approved Offer Catalog (with Decimal-safe pricing, versioning, approval gating)
  • Deterministic Lead Scoring engine (configurable rules, versioned, score history)
  • Source & Campaign Attribution (append-only touches, first/last preservation,
    UTM/URL sanitization, correction audit)
  • Contact Lifecycle + Detail administration (with safeguarded merge)

Reuses Phase 1 infrastructure:
  • Audit log (via revenue._audit) — no direct writes
  • Internal event engine (db["internal_events"])
  • Approval queue (db["approval_queue"]) for gated changes to ACTIVE offers
  • Contacts + Organizations collections
  • Admin authorization gate (passed in from server.py)
  • Safety gate (AUTOMATION_LIVE_ACTIONS_ENABLED)

SAFETY
──────
No Phase 2 route performs any external side-effect. All integrations remain
simulated or unavailable while the safety gate is false. In particular, this
module NEVER creates Stripe products, prices, Payment Links, subscriptions,
sends email, or publishes content.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Optional
from urllib.parse import urlparse, urlunparse

from bson.decimal128 import Decimal128
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator

# ─── Reuse Phase 1 helpers (do NOT duplicate audit/event schemas) ──────────
from revenue import (  # noqa: E402
    _audit,
    _now,
    live_actions_enabled,
)


# ─── Offer catalog models ──────────────────────────────────────────────────
BillingFrequency = Literal["monthly", "annual", "quarterly", "one_time", "usage_based"]
OfferCategory = Literal[
    "subscription", "digital_product", "training", "implementation",
    "organization_license", "add_on",
]
FulfillmentType = Literal[
    "self_serve_saas", "managed_service", "digital_download",
    "instructor_led", "hybrid",
]

_MAX_OFFER_PRICE = Decimal("1000000.00")


class EligibilityRule(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    op: Literal["eq", "in", "gte", "lte", "exists", "not_in"]
    value: Any = None

    @field_validator("key")
    @classmethod
    def _key_charset(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_.]+$", v):
            raise ValueError("eligibility key must be [a-z0-9_.]")
        return v


class DiscountRule(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    kind: Literal["percent_off", "amount_off"]
    value: str  # Decimal-safe: string
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    max_redemptions: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("value")
    @classmethod
    def _decimal_ok(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except (InvalidOperation, TypeError):
            raise ValueError("discount value must be a decimal string")
        if d < 0:
            raise ValueError("discount value cannot be negative")
        return str(d.quantize(Decimal("0.01")))


class OfferIn(BaseModel):
    offer_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: OfferCategory
    price: str  # Decimal-safe string (e.g. "9.99")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_frequency: BillingFrequency
    included_features: list[str] = Field(default_factory=list)
    seat_limit: Optional[int] = None
    eligibility_rules: list[EligibilityRule] = Field(default_factory=list)
    display_priority: int = 100
    fulfillment_type: FulfillmentType = "self_serve_saas"
    discount_rules: list[DiscountRule] = Field(default_factory=list)
    external_price_id: Optional[str] = None       # existing Stripe/etc price id
    external_product_id: Optional[str] = None     # existing Stripe/etc product id
    external_annual_price_id: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("offer_code")
    @classmethod
    def _code_shape(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,63}$", v):
            raise ValueError("offer_code must match [a-z0-9][a-z0-9_.-]{1,63}")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_upper(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("currency must be ISO-4217 3-letter code")
        return v

    @field_validator("price")
    @classmethod
    def _price_ok(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except (InvalidOperation, TypeError):
            raise ValueError("price must be a decimal string like '9.99'")
        if d < 0:
            raise ValueError("price cannot be negative")
        if d.as_tuple().exponent < -2:
            raise ValueError("price cannot have more than 2 decimal places")
        if d > _MAX_OFFER_PRICE:
            raise ValueError(f"price exceeds approved bound (${_MAX_OFFER_PRICE})")
        return str(d.quantize(Decimal("0.01")))


class OfferPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    billing_frequency: Optional[BillingFrequency] = None
    included_features: Optional[list[str]] = None
    seat_limit: Optional[int] = None
    eligibility_rules: Optional[list[EligibilityRule]] = None
    display_priority: Optional[int] = None
    fulfillment_type: Optional[FulfillmentType] = None
    discount_rules: Optional[list[DiscountRule]] = None
    external_price_id: Optional[str] = None
    external_product_id: Optional[str] = None
    external_annual_price_id: Optional[str] = None
    notes: Optional[str] = None
    change_reason: Optional[str] = None


# ─── Lead scoring models ───────────────────────────────────────────────────
_DEFAULT_SCORING_WEIGHTS = {
    "assessment_score": {"weight": 25, "type": "linear_0_100"},
    "business_type": {"weight": 20, "type": "map",
                       "values": {"b2b": 20, "agency": 15, "solopreneur": 15,
                                  "b2c": 10, "nonprofit": 8, "other": 0}},
    "organization_size": {"weight": 25, "type": "map",
                           "values": {"enterprise": 25, "mid": 20,
                                      "small": 15, "solo": 10}},
    "employee_count": {"weight": 20, "type": "linear_cap",
                        "per_unit": 10, "cap": 20},
    "urgency": {"weight": 20, "type": "map",
                 "values": {"asap": 20, "quarter": 12, "year": 6, "explore": 0}},
    "engagement_recent_events": {"weight": 15, "type": "linear_cap",
                                  "per_unit": 1, "cap": 15},
    "checkout_started": {"weight": 15, "type": "bool"},
    "existing_customer": {"weight": 20, "type": "bool"},
    "source_quality": {"weight": 15, "type": "map",
                        "values": {"referral": 20, "email": 15,
                                   "organic_search": 15, "direct": 12,
                                   "paid": 10, "social": 8, "unknown": 0}},
}
_DEFAULT_BAND_THRESHOLDS = {
    "unqualified": [0, 9],
    "early_interest": [10, 24],
    "engaged": [25, 49],
    "qualified": [50, 74],
    "high_intent": [75, 100],
}


class ScoringRuleSet(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: Optional[str] = None
    weights: dict = Field(default_factory=lambda: dict(_DEFAULT_SCORING_WEIGHTS))
    band_thresholds: dict = Field(default_factory=lambda: dict(_DEFAULT_BAND_THRESHOLDS))
    notes: Optional[str] = None

    @field_validator("band_thresholds")
    @classmethod
    def _band_shape(cls, v: dict) -> dict:
        if not v:
            raise ValueError("band_thresholds cannot be empty")
        last_hi = -1
        for band, rng in sorted(v.items(), key=lambda kv: kv[1][0]):
            if not (isinstance(rng, (list, tuple)) and len(rng) == 2):
                raise ValueError(f"band {band}: expected [low, high]")
            lo, hi = rng
            if lo > hi:
                raise ValueError(f"band {band}: lo>hi")
            if lo <= last_hi:
                raise ValueError(f"band {band}: overlaps prior band")
            last_hi = hi
        return v


class ScoreInputs(BaseModel):
    contact_id: str
    inputs: dict = Field(default_factory=dict)
    notes: Optional[str] = None


# ─── Attribution models ────────────────────────────────────────────────────
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
_SAFE_URL_SCHEMES = ("http", "https")
_URL_MAX = 512
_NOTE_MAX = 500


class AttributionTouch(BaseModel):
    contact_id: str
    lead_source: Optional[str] = None
    referral_source: Optional[str] = None
    campaign_source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    source_url: Optional[str] = None
    source_notes: Optional[str] = None
    referred_by_name: Optional[str] = None
    referred_by_email: Optional[EmailStr] = None
    occurred_at: Optional[datetime] = None


class AttributionCorrection(BaseModel):
    contact_id: str
    which: Literal["first_touch", "last_touch"]
    new_source: dict = Field(default_factory=dict)
    reason: str = Field(min_length=8, max_length=500)


# ─── Contact administration models ─────────────────────────────────────────
class LifecycleChange(BaseModel):
    new_stage: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=8, max_length=500)


class ContactPatch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    organization_size: Optional[str] = None
    employee_count: Optional[int] = None
    stated_needs: Optional[str] = None
    consent_marketing: Optional[bool] = None
    change_reason: str = Field(min_length=4, max_length=500)


class ContactNote(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ContactMerge(BaseModel):
    surviving_id: str
    merged_id: str
    reason: str = Field(min_length=8, max_length=500)
    dry_run: bool = True
    force_conflicting_external_ids: bool = False


# ─── Utilities ─────────────────────────────────────────────────────────────
def _sanitize_url(u: Optional[str]) -> Optional[str]:
    """Return a safe, length-bounded URL or None."""
    if not u:
        return None
    u = u.strip()
    if len(u) > _URL_MAX:
        u = u[:_URL_MAX]
    try:
        p = urlparse(u)
    except Exception:
        return None
    if p.scheme.lower() not in _SAFE_URL_SCHEMES:
        return None
    if not p.netloc:
        return None
    # Rebuild without fragment (fragments often carry PII/session data)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))


def _sanitize_note(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    if len(s) > _NOTE_MAX:
        s = s[:_NOTE_MAX]
    # Strip control characters (kept whitespace + printable ASCII/unicode letters)
    s = "".join(ch for ch in s if ch.isprintable() or ch in ("\n", "\t"))
    return s


def _norm_utm(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip().lower()
    v = re.sub(r"[^a-z0-9_\-.]", "_", v)
    return v[:80] or None


def _decimal_to_128(d: Decimal) -> Decimal128:
    return Decimal128(d.quantize(Decimal("0.01")))


def _offer_public(doc: dict) -> dict:
    """Convert an offer document to a JSON-safe representation."""
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(out.get("price"), Decimal128):
        out["price"] = str(out["price"].to_decimal())
    return out


def _fingerprint_score_input(rule_set_id: str, inputs: dict) -> str:
    """Deterministic hash of inputs — proves consistent scoring for identical inputs."""
    canonical = json.dumps({"rs": rule_set_id, "in": inputs},
                            sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─── Deterministic scoring engine ──────────────────────────────────────────
class DeterministicScorer:
    """Pure-function scoring engine. Same inputs + same rule set → same outputs."""

    def __init__(self, rule_set: dict):
        self.rule_set = rule_set
        self.weights = rule_set.get("weights", _DEFAULT_SCORING_WEIGHTS)
        self.bands = rule_set.get("band_thresholds", _DEFAULT_BAND_THRESHOLDS)

    def _score_one(self, key: str, val: Any) -> tuple[int, str]:
        cfg = self.weights.get(key)
        if not cfg:
            return 0, f"{key}: no rule → 0"
        t = cfg.get("type")
        if t == "linear_0_100":
            try:
                v = max(0, min(100, int(val)))
            except (TypeError, ValueError):
                return 0, f"{key}: invalid value → 0"
            score = int(v * cfg["weight"] / 100)
            return score, f"{key}={v} → +{score}"
        if t == "map":
            mp = cfg.get("values") or {}
            s = int(mp.get(str(val).lower(), 0))
            s = min(s, cfg["weight"])
            return s, f"{key}={val} → +{s}"
        if t == "linear_cap":
            try:
                v = int(val or 0)
            except (TypeError, ValueError):
                return 0, f"{key}: invalid value → 0"
            per = cfg.get("per_unit", 1) or 1
            cap = cfg.get("cap", cfg["weight"])
            s = min(v // per, cap)
            return s, f"{key}={v} → +{s} (cap {cap})"
        if t == "bool":
            s = cfg["weight"] if bool(val) else 0
            return s, f"{key}={bool(val)} → +{s}"
        return 0, f"{key}: unknown rule type → 0"

    def score(self, inputs: dict) -> dict:
        total = 0
        reasons: list[str] = []
        breakdown: dict[str, int] = {}
        for key in self.weights.keys():
            val = inputs.get(key)
            s, msg = self._score_one(key, val)
            breakdown[key] = s
            total += s
            reasons.append(msg)
        total = max(0, min(100, total))
        band = "unqualified"
        for b, (lo, hi) in self.bands.items():
            if lo <= total <= hi:
                band = b
                break
        if inputs.get("existing_customer"):
            band = "existing_customer"
        return {
            "score": total,
            "band": band,
            "breakdown": breakdown,
            "reasons": reasons,
        }


# ─── Router setup ──────────────────────────────────────────────────────────
router = APIRouter(prefix="/admin/revenue", tags=["revenue-phase2"])


async def ensure_indexes_phase2(db) -> None:
    """Idempotent Phase 2 indexes."""
    await db["offers"].create_index("id", unique=True)
    await db["offers"].create_index("offer_code", unique=True)
    await db["offers"].create_index("active_status")
    await db["offers"].create_index("category")
    await db["offer_versions"].create_index("offer_id")
    await db["offer_versions"].create_index("created_at")
    await db["scoring_rules"].create_index("id", unique=True)
    await db["scoring_rules"].create_index("active")
    await db["scoring_rules"].create_index("created_at")
    await db["contact_scores"].create_index("contact_id")
    await db["contact_scores"].create_index("created_at")
    await db["attribution_touches"].create_index("contact_id")
    await db["attribution_touches"].create_index("created_at")
    await db["contact_notes"].create_index("contact_id")
    await db["contact_notes"].create_index("created_at")


# ─── Route registration ────────────────────────────────────────────────────
def register_routes(db, require_admin):
    """Attach db- and auth-bound routes. Called from server.py after db is ready."""

    # ═══════════════════════════════════════════════════════════════════════
    #  OFFER CATALOG
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/offers")
    async def create_offer(body: OfferIn, admin=Depends(require_admin)):
        """Create a new DRAFT offer. All new offers start as draft/inactive."""
        # Duplicate offer_code check (protects existing imported offers)
        if await db["offers"].find_one({"offer_code": body.offer_code}, {"_id": 0}):
            raise HTTPException(409, f"offer_code '{body.offer_code}' already exists")
        doc = {
            "id": str(uuid.uuid4()),
            "offer_code": body.offer_code,
            "name": body.name,
            "description": body.description,
            "category": body.category,
            "price": _decimal_to_128(Decimal(body.price)),
            "currency": body.currency,
            "billing_frequency": body.billing_frequency,
            "included_features": body.included_features,
            "seat_limit": body.seat_limit,
            "eligibility_rules": [r.model_dump() for r in body.eligibility_rules],
            "display_priority": body.display_priority,
            "active_status": False,     # never active on creation
            "draft_status": True,       # every new offer starts as draft
            "fulfillment_type": body.fulfillment_type,
            "discount_rules": [r.model_dump() for r in body.discount_rules],
            "external_price_id": body.external_price_id,
            "external_product_id": body.external_product_id,
            "external_annual_price_id": body.external_annual_price_id,
            "notes": body.notes,
            "policy_version": 1,
            "created_at": _now(), "updated_at": _now(),
            "created_by": admin["email"], "updated_by": admin["email"],
            "source": "admin_created",
            "environment": "preview",
            "simulated": False,
        }
        await db["offers"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="offer.created",
                     target_type="offer", target_id=doc["id"],
                     reason=f"draft offer {body.offer_code} created",
                     simulated=False, source="admin_created",
                     extra={"offer_code": body.offer_code})
        return {"offer": _offer_public(doc)}

    @router.get("/offers")
    async def list_offers(active: Optional[bool] = None, draft: Optional[bool] = None,
                          admin=Depends(require_admin)):
        q: dict = {}
        if active is not None:
            q["active_status"] = active
        if draft is not None:
            q["draft_status"] = draft
        rows = await db["offers"].find(q, {"_id": 0}).sort("display_priority", 1).to_list(500)
        return {"offers": [_offer_public(r) for r in rows], "count": len(rows)}

    @router.get("/offers/{offer_id}")
    async def get_offer(offer_id: str, admin=Depends(require_admin)):
        doc = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "offer not found")
        versions = await db["offer_versions"].find(
            {"offer_id": offer_id}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
        return {"offer": _offer_public(doc), "versions": versions,
                "version_count": len(versions)}

    @router.patch("/offers/{offer_id}")
    async def patch_offer(offer_id: str, body: OfferPatch, admin=Depends(require_admin)):
        current = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        if not current:
            raise HTTPException(404, "offer not found")

        # Validate patch fields via a synthetic OfferIn where possible for price.
        patch: dict = body.model_dump(exclude_none=True)
        change_reason = patch.pop("change_reason", None) or "no reason provided"

        if "price" in patch:
            try:
                d = Decimal(patch["price"])
            except (InvalidOperation, TypeError):
                raise HTTPException(422, "price must be a decimal string")
            if d < 0 or d.as_tuple().exponent < -2 or d > _MAX_OFFER_PRICE:
                raise HTTPException(422, "price invalid (negative, >2dp, or out of bounds)")
            patch["price"] = _decimal_to_128(d)
        if "currency" in patch:
            patch["currency"] = patch["currency"].strip().upper()
            if not re.match(r"^[A-Z]{3}$", patch["currency"]):
                raise HTTPException(422, "currency must be ISO-4217")
        if "billing_frequency" in patch:
            if patch["billing_frequency"] not in ("monthly", "annual", "quarterly",
                                                   "one_time", "usage_based"):
                raise HTTPException(422, "invalid billing_frequency")
        if "eligibility_rules" in patch:
            # revalidate individual rules
            for r in patch["eligibility_rules"]:
                EligibilityRule(**r)
        if "discount_rules" in patch:
            for r in patch["discount_rules"]:
                DiscountRule(**r)

        # If offer is currently ACTIVE and the patch touches material fields,
        # the change must go through the approval queue instead of applying now.
        MATERIAL_FIELDS = {"price", "currency", "billing_frequency",
                           "external_price_id", "external_annual_price_id",
                           "external_product_id", "seat_limit", "eligibility_rules",
                           "discount_rules"}
        touches_material = any(k in patch for k in MATERIAL_FIELDS)

        if current.get("active_status") and touches_material:
            # Enqueue approval; do NOT apply the change yet.
            approval_doc = {
                "id": str(uuid.uuid4()),
                "request_type": "offer.change_material",
                "requested_action": f"patch offer {current['offer_code']}",
                "reason": change_reason,
                "risk_level": "high",
                "financial_amount_usd": None,
                "related_contact_id": None,
                "related_organization_id": None,
                "supporting_records": {"offer_id": offer_id, "patch": _jsonable(patch)},
                "correlation_id": str(uuid.uuid4()),
                "status": "pending",
                "decided_by": None, "decided_at": None, "notes": None,
                "expires_at": None,
                # simulated=False, source="admin_created": this represents a MODELED action; the queued
                # change would only trigger an external effect if the safety
                # gate were on. The audit entry below is simulated=False
                # because the *request* itself was really made by an admin.
                "simulated": True,
                "source": "admin_created",
                "environment": "preview",
                "created_at": _now(),
            }
            await db["approval_queue"].insert_one(approval_doc)
            await _audit(db, actor=admin["email"],
                         action="offer.change_material.requested",
                         target_type="offer", target_id=offer_id,
                         correlation_id=approval_doc["correlation_id"],
                         approval_required=True, approval_status="pending",
                         reason=change_reason, simulated=False,
                         source="admin_created",
                         extra={"fields": sorted(list(set(patch.keys()) & MATERIAL_FIELDS))})
            return {"queued": True, "approval": {**approval_doc, "_id": None},
                    "note": ("Material change to active offer queued for approval; "
                             "offer document unchanged.")}

        # Non-material or draft offer → apply immediately + create version record.
        version_doc = {
            "id": str(uuid.uuid4()),
            "offer_id": offer_id,
            "prior": _offer_public(current),
            "changes": _jsonable(patch),
            "change_reason": change_reason,
            "changed_by": admin["email"],
            "created_at": _now(),
        }
        await db["offer_versions"].insert_one(version_doc)

        patch["updated_at"] = _now()
        patch["updated_by"] = admin["email"]
        await db["offers"].update_one({"id": offer_id}, {"$set": patch})
        updated = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        await _audit(db, actor=admin["email"], action="offer.updated",
                     target_type="offer", target_id=offer_id,
                     reason=change_reason, simulated=False, source="admin_created",
                     extra={"fields": sorted(list(patch.keys()))})
        return {"offer": _offer_public(updated), "version_id": version_doc["id"]}

    @router.post("/offers/{offer_id}/activate")
    async def activate_offer(offer_id: str, admin=Depends(require_admin)):
        doc = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "offer not found")
        if doc.get("active_status"):
            return {"offer": _offer_public(doc), "note": "already active"}
        await db["offers"].update_one(
            {"id": offer_id},
            {"$set": {"active_status": True, "draft_status": False,
                       "updated_at": _now(), "updated_by": admin["email"]}},
        )
        updated = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        await _audit(db, actor=admin["email"], action="offer.activated",
                     target_type="offer", target_id=offer_id,
                     reason=f"activated offer {doc.get('offer_code')}",
                     simulated=False, source="admin_created")
        return {"offer": _offer_public(updated)}

    @router.post("/offers/{offer_id}/deactivate")
    async def deactivate_offer(offer_id: str, admin=Depends(require_admin)):
        doc = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "offer not found")
        await db["offers"].update_one(
            {"id": offer_id},
            {"$set": {"active_status": False,
                       "updated_at": _now(), "updated_by": admin["email"]}},
        )
        updated = await db["offers"].find_one({"id": offer_id}, {"_id": 0})
        await _audit(db, actor=admin["email"], action="offer.deactivated",
                     target_type="offer", target_id=offer_id,
                     reason=f"deactivated offer {doc.get('offer_code')}",
                     simulated=False, source="admin_created")
        return {"offer": _offer_public(updated)}

    @router.post("/offers/import-existing")
    async def import_existing_offers(admin=Depends(require_admin)):
        """One-shot import of the four existing Ascendra tiers.

        Idempotent: on re-run, offers already present (matched by offer_code) are
        SKIPPED, not duplicated or overwritten.
        """
        # Import here to avoid a circular import at module load.
        import sys
        sys.path.insert(0, "/app/backend")
        try:
            from server import TIERS  # canonical source of truth for existing tiers
        except Exception:
            TIERS = {}

        # Load Stripe config for existing price IDs
        stripe_cfg_path = os.path.join(os.path.dirname(__file__), "stripe_config.json")
        stripe_cfg: dict = {}
        try:
            with open(stripe_cfg_path) as f:
                stripe_cfg = json.load(f)
        except Exception:
            stripe_cfg = {"tiers": {}}

        imported: list[dict] = []
        skipped: list[dict] = []

        for tier_id, tier in TIERS.items():
            # Some tiers may have no Stripe price yet (e.g. "business")
            stripe_ids = stripe_cfg.get("tiers", {}).get(tier_id, {})
            monthly_price_id = (stripe_ids.get("prices") or {}).get("monthly", "") or None
            annual_price_id = (stripe_ids.get("prices") or {}).get("annual", "") or None
            product_id = stripe_ids.get("product_id", "") or None

            # We create ONE canonical monthly offer per tier here. The annual
            # equivalent is exposed via external_annual_price_id + a second
            # implicit "annual" plan; keep the ledger simple in Phase 2.
            has_stripe = bool(monthly_price_id and product_id)
            code = f"{tier_id}_monthly"

            existing = await db["offers"].find_one({"offer_code": code}, {"_id": 0})
            if existing:
                skipped.append({"offer_code": code, "id": existing["id"],
                                 "reason": "already present"})
                continue

            price_str = str(Decimal(str(tier.get("price_monthly") or 0)).quantize(Decimal("0.01")))
            doc = {
                "id": str(uuid.uuid4()),
                "offer_code": code,
                "name": f"{tier.get('name', tier_id).title()} (monthly)",
                "description": tier.get("blurb"),
                "category": "subscription",
                "price": _decimal_to_128(Decimal(price_str)),
                "currency": "USD",
                "billing_frequency": "monthly",
                "included_features": list(tier.get("features") or []),
                "seat_limit": 5 if tier_id == "business" else 1,
                "eligibility_rules": [],
                "display_priority": {"ascender": 100, "pathfinder": 200,
                                       "sage": 300, "business": 400}.get(tier_id, 500),
                # If Stripe is configured for this tier, we import it as ACTIVE
                # (this reflects reality: it is being sold today).
                # If Stripe is NOT configured (business tier at time of writing),
                # import it as DRAFT + inactive per user policy.
                "active_status": bool(has_stripe),
                "draft_status": not has_stripe,
                "fulfillment_type": "self_serve_saas",
                "discount_rules": [],
                "external_price_id": monthly_price_id,
                "external_product_id": product_id,
                "external_annual_price_id": annual_price_id,
                "notes": ("Imported from existing Ascendra tier configuration. "
                          "Do not modify externally-managed price IDs without approval."),
                "policy_version": 1,
                "created_at": _now(), "updated_at": _now(),
                "created_by": admin["email"], "updated_by": admin["email"],
                "imported": True,
                "source": "existing_application",
                "environment": "preview",
                "simulated": False,
                "source_tier": tier_id,
            }
            await db["offers"].insert_one(doc)
            await _audit(db, actor=admin["email"], action="offer.imported",
                         target_type="offer", target_id=doc["id"],
                         reason=f"imported existing tier {tier_id}",
                         simulated=False, source="existing_application",
                         extra={"offer_code": code,
                                "active": bool(has_stripe),
                                "has_stripe_ids": bool(has_stripe)})
            imported.append({"offer_code": code, "id": doc["id"],
                              "active": bool(has_stripe)})

        return {"imported": imported, "skipped": skipped,
                "note": "Existing tiers imported from /app/backend/server.py TIERS + stripe_config.json."}

    # ═══════════════════════════════════════════════════════════════════════
    #  SCORING RULES
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/scoring/rules")
    async def create_scoring_rules(body: ScoringRuleSet, admin=Depends(require_admin)):
        # Highest version across ALL rule sets (not just active ones)
        latest = await db["scoring_rules"].find_one(
            {}, {"version": 1}, sort=[("version", -1)])
        prev_version = latest.get("version", 0) if latest else 0
        doc = {
            "id": str(uuid.uuid4()),
            "name": body.name, "description": body.description,
            "weights": body.weights, "band_thresholds": body.band_thresholds,
            "notes": body.notes,
            "active": False,
            "version": prev_version + 1,
            "created_at": _now(), "created_by": admin["email"],
        }
        await db["scoring_rules"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="scoring_rules.created",
                     target_type="scoring_rules", target_id=doc["id"],
                     reason=f"rule set v{doc['version']}", simulated=False, source="admin_created")
        return {"rule_set": {**doc, "_id": None}}

    @router.get("/scoring/rules")
    async def list_scoring_rules(admin=Depends(require_admin)):
        rows = await db["scoring_rules"].find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
        return {"rule_sets": rows, "count": len(rows)}

    @router.get("/scoring/rules/current")
    async def current_scoring_rules(admin=Depends(require_admin)):
        cur = await db["scoring_rules"].find_one({"active": True}, {"_id": 0})
        if not cur:
            # Return an in-memory default set (not yet persisted).
            return {"rule_set": {
                "id": None, "name": "defaults", "active": False,
                "version": 0,
                "weights": _DEFAULT_SCORING_WEIGHTS,
                "band_thresholds": _DEFAULT_BAND_THRESHOLDS,
            }, "note": "no persisted rule set — using library defaults"}
        return {"rule_set": cur}

    @router.post("/scoring/rules/{rule_id}/activate")
    async def activate_scoring_rules(rule_id: str, admin=Depends(require_admin)):
        doc = await db["scoring_rules"].find_one({"id": rule_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "rule set not found")
        # Deactivate all others (versioned history stays in place)
        await db["scoring_rules"].update_many({}, {"$set": {"active": False}})
        await db["scoring_rules"].update_one({"id": rule_id}, {"$set": {"active": True}})
        await _audit(db, actor=admin["email"], action="scoring_rules.activated",
                     target_type="scoring_rules", target_id=rule_id,
                     reason=f"activated v{doc.get('version')}", simulated=False, source="admin_created")
        return {"rule_set": {**doc, "active": True}}

    # ═══════════════════════════════════════════════════════════════════════
    #  SCORING EXECUTION
    # ═══════════════════════════════════════════════════════════════════════
    async def _current_rule_set() -> dict:
        cur = await db["scoring_rules"].find_one({"active": True}, {"_id": 0})
        if cur:
            return cur
        return {"id": "defaults", "version": 0, "weights": _DEFAULT_SCORING_WEIGHTS,
                "band_thresholds": _DEFAULT_BAND_THRESHOLDS}

    async def _recommend_offer(band: str, contact: dict) -> Optional[dict]:
        """Recommend an ACTIVE, non-draft offer whose eligibility matches the band."""
        band_priority = {"high_intent": 300, "qualified": 300, "engaged": 200,
                         "early_interest": 100, "unqualified": 0, "existing_customer": 400}
        target = band_priority.get(band, 0)
        offers = await db["offers"].find(
            {"active_status": True, "draft_status": False},
            {"_id": 0}).sort("display_priority", 1).to_list(200)
        if not offers:
            return None
        # Simple: pick highest priority ≤ target
        best = None
        for o in offers:
            if o["display_priority"] <= target:
                best = o
        if not best:
            best = offers[0]
        return _offer_public(best)

    async def _persist_score(contact_id: str, admin_email: str,
                              rule_set: dict, inputs: dict, result: dict,
                              reason: str, correlation_id: str) -> dict:
        prior = await db["contact_scores"].find_one(
            {"contact_id": contact_id}, {"_id": 0}, sort=[("created_at", -1)])
        prior_score = prior.get("score") if prior else None
        history_doc = {
            "id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "rule_set_id": rule_set.get("id"),
            "rule_set_version": rule_set.get("version", 0),
            "inputs": inputs,
            "input_fingerprint": _fingerprint_score_input(str(rule_set.get("id")), inputs),
            "score": result["score"],
            "band": result["band"],
            "breakdown": result["breakdown"],
            "reasons": result["reasons"],
            "confidence": "deterministic",
            "prior_score": prior_score,
            "delta": None if prior_score is None else result["score"] - prior_score,
            "notes": reason,
            "created_at": _now(),
            "created_by": admin_email,
        }
        await db["contact_scores"].insert_one(history_doc)
        # Mirror the latest score into the contact document.
        await db["contacts"].update_one(
            {"id": contact_id},
            {"$set": {"lead_score": result["score"],
                       "lifecycle_stage": result["band"] if result["band"] != "existing_customer" else "customer",
                       "qualification_reason": "; ".join(result["reasons"][:5]),
                       "updated_at": _now()}},
        )
        # Record a scoring event
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "lead.scored",
            "source": "revenue.scoring",
            "payload": {"score": result["score"], "band": result["band"],
                         "delta": history_doc["delta"]},
            "contact_id": contact_id,
            "organization_id": None,
            "idempotency_key": history_doc["id"],  # unique per score run
            "correlation_id": correlation_id,
            "processing_status": "processed",
            "retry_count": 0, "error": None,
            "simulated": False, "source": "admin_created", "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        return history_doc

    @router.post("/scoring/score")
    async def score_contact(body: ScoreInputs, admin=Depends(require_admin)):
        contact = await db["contacts"].find_one({"id": body.contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")
        rule_set = await _current_rule_set()
        scorer = DeterministicScorer(rule_set)
        result = scorer.score(body.inputs)
        rec_offer = await _recommend_offer(result["band"], contact)
        correlation_id = str(uuid.uuid4())
        history = await _persist_score(
            contact["id"], admin["email"], rule_set, body.inputs, result,
            body.notes or "manual score", correlation_id,
        )
        await _audit(db, actor=admin["email"], action="lead.scored",
                     target_type="contact", target_id=contact["id"],
                     correlation_id=correlation_id,
                     reason=(body.notes or "manual score"),
                     simulated=False, source="admin_created",
                     extra={"score": result["score"], "band": result["band"],
                             "rule_set_version": rule_set.get("version", 0)})
        return {
            "score": result["score"],
            "band": result["band"],
            "breakdown": result["breakdown"],
            "reasons": result["reasons"],
            "recommended_offer": rec_offer,
            "rule_set_version": rule_set.get("version", 0),
            "history_id": history["id"],
        }

    @router.get("/contacts/{contact_id}/score-history")
    async def contact_score_history(contact_id: str, admin=Depends(require_admin)):
        rows = await db["contact_scores"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        return {"entries": rows, "count": len(rows)}

    # ═══════════════════════════════════════════════════════════════════════
    #  ATTRIBUTION
    # ═══════════════════════════════════════════════════════════════════════
    async def _append_touch(contact_id: str, admin_email: str, kind: str,
                             sanitized: dict, correlation_id: str) -> dict:
        touch = {
            "id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "kind": kind,          # 'automatic' | 'manual' | 'correction'
            **sanitized,
            "correlation_id": correlation_id,
            "created_at": _now(),
            "created_by": admin_email,
        }
        await db["attribution_touches"].insert_one(touch)
        return touch

    @router.post("/contacts/{contact_id}/attribution/touch")
    async def record_touch(contact_id: str, body: AttributionTouch,
                             admin=Depends(require_admin)):
        if body.contact_id != contact_id:
            raise HTTPException(422, "contact_id path/body mismatch")
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")

        sanitized = {
            "lead_source": _norm_utm(body.lead_source),
            "referral_source": _norm_utm(body.referral_source),
            "campaign_source": _norm_utm(body.campaign_source),
            "utm_source": _norm_utm(body.utm_source),
            "utm_medium": _norm_utm(body.utm_medium),
            "utm_campaign": _norm_utm(body.utm_campaign),
            "utm_content": _norm_utm(body.utm_content),
            "utm_term": _norm_utm(body.utm_term),
            "source_url": _sanitize_url(body.source_url),
            "source_notes": _sanitize_note(body.source_notes),
            "referred_by_name": _sanitize_note(body.referred_by_name),
            "referred_by_email": body.referred_by_email,
            "occurred_at": body.occurred_at or _now(),
        }
        correlation_id = str(uuid.uuid4())
        touch = await _append_touch(contact_id, admin["email"], "manual",
                                      sanitized, correlation_id)

        # First-touch preservation: only set if not already present.
        current_attr = contact.get("attribution") or {}
        update: dict = {"updated_at": _now()}
        if not current_attr.get("first_touch_source"):
            update["attribution.first_touch_source"] = (
                sanitized["utm_source"] or sanitized["lead_source"]
                or sanitized["referral_source"] or sanitized["campaign_source"]
            )
            update["attribution.first_touch_at"] = touch["created_at"]
        # Last-touch always updates on a valid new touch.
        update["attribution.last_touch_source"] = (
            sanitized["utm_source"] or sanitized["lead_source"]
            or sanitized["referral_source"] or sanitized["campaign_source"]
        )
        update["attribution.last_touch_at"] = touch["created_at"]
        await db["contacts"].update_one({"id": contact_id}, {"$set": update})

        # Internal event (idempotent per touch id)
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "attribution.touch_recorded",
            "source": "revenue.attribution",
            "payload": {"touch_id": touch["id"]},
            "contact_id": contact_id, "organization_id": None,
            "idempotency_key": f"touch-{touch['id']}",
            "correlation_id": correlation_id,
            "processing_status": "processed", "retry_count": 0, "error": None,
            "simulated": False, "source": "admin_created", "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        await _audit(db, actor=admin["email"], action="attribution.touch_recorded",
                     target_type="contact", target_id=contact_id,
                     correlation_id=correlation_id,
                     reason="manual attribution touch appended",
                     simulated=False, source="admin_created", extra={"touch_id": touch["id"]})
        return {"touch": {**touch, "_id": None}}

    @router.get("/contacts/{contact_id}/attribution/touches")
    async def list_touches(contact_id: str, admin=Depends(require_admin)):
        rows = await db["attribution_touches"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", 1).limit(200).to_list(200)
        return {"touches": rows, "count": len(rows)}

    @router.post("/contacts/{contact_id}/attribution/correct")
    async def correct_attribution(contact_id: str, body: AttributionCorrection,
                                    admin=Depends(require_admin)):
        if body.contact_id != contact_id:
            raise HTTPException(422, "contact_id path/body mismatch")
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")

        sanitized_source = _norm_utm(body.new_source.get("source"))
        which = body.which
        correlation_id = str(uuid.uuid4())

        # Append correction as a touch record (append-only history).
        touch = await _append_touch(contact_id, admin["email"], "correction", {
            "correction_target": which,
            "new_source": sanitized_source,
            "reason": _sanitize_note(body.reason),
            "occurred_at": _now(),
        }, correlation_id)

        update = {"updated_at": _now()}
        if which == "first_touch":
            update["attribution.first_touch_source"] = sanitized_source
            update["attribution.first_touch_corrected_at"] = _now()
            update["attribution.first_touch_corrected_by"] = admin["email"]
        else:
            update["attribution.last_touch_source"] = sanitized_source
            update["attribution.last_touch_corrected_at"] = _now()
            update["attribution.last_touch_corrected_by"] = admin["email"]
        await db["contacts"].update_one({"id": contact_id}, {"$set": update})

        await _audit(db, actor=admin["email"], action="attribution.corrected",
                     target_type="contact", target_id=contact_id,
                     correlation_id=correlation_id,
                     reason=body.reason, simulated=False, source="admin_created",
                     extra={"which": which, "new_source": sanitized_source,
                             "touch_id": touch["id"]})
        return {"correction": {"which": which, "new_source": sanitized_source},
                "touch": {**touch, "_id": None}}

    # ═══════════════════════════════════════════════════════════════════════
    #  CONTACT DETAIL + LIFECYCLE + NOTES + MERGE
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/contacts/{contact_id}")
    async def contact_detail(contact_id: str, admin=Depends(require_admin)):
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")
        scores = await db["contact_scores"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
        touches = await db["attribution_touches"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", 1).limit(50).to_list(50)
        events = await db["internal_events"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        audits = await db["audit_log"].find(
            {"target_id": contact_id, "target_type": "contact"}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        notes = await db["contact_notes"].find(
            {"contact_id": contact_id}, {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)
        # Recommended offer per current band
        cur_band = None
        if scores:
            cur_band = scores[0].get("band")
        rec = await _recommend_offer(cur_band or "unqualified", contact)
        return {
            "contact": contact,
            "score_history": scores,
            "attribution_touches": touches,
            "internal_events": events,
            "audit_log": audits,
            "notes": notes,
            "recommended_offer": rec,
            "next_recommended_action": _next_action(cur_band),
        }

    @router.patch("/contacts/{contact_id}")
    async def patch_contact(contact_id: str, body: ContactPatch, admin=Depends(require_admin)):
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")
        patch = body.model_dump(exclude_none=True)
        change_reason = patch.pop("change_reason", "manual edit")
        patch["updated_at"] = _now()
        await db["contacts"].update_one({"id": contact_id}, {"$set": patch})
        correlation_id = str(uuid.uuid4())
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "contact.updated",
            "source": "revenue.contact",
            "payload": {"fields": sorted(list(patch.keys()))},
            "contact_id": contact_id, "organization_id": None,
            "idempotency_key": f"upd-{contact_id}-{_now().isoformat()}",
            "correlation_id": correlation_id,
            "processing_status": "processed", "retry_count": 0, "error": None,
            "simulated": False, "source": "admin_created", "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        await _audit(db, actor=admin["email"], action="contact.updated",
                     target_type="contact", target_id=contact_id,
                     correlation_id=correlation_id, reason=change_reason,
                     simulated=False, source="admin_created", extra={"fields": sorted(list(patch.keys()))})
        updated = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        return {"contact": updated}

    @router.post("/contacts/{contact_id}/lifecycle")
    async def change_lifecycle(contact_id: str, body: LifecycleChange,
                                 admin=Depends(require_admin)):
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")
        prev = contact.get("lifecycle_stage")
        await db["contacts"].update_one(
            {"id": contact_id},
            {"$set": {"lifecycle_stage": body.new_stage, "updated_at": _now()}},
        )
        correlation_id = str(uuid.uuid4())
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "contact.lifecycle_changed",
            "source": "revenue.contact",
            "payload": {"from": prev, "to": body.new_stage, "reason": body.reason},
            "contact_id": contact_id, "organization_id": None,
            "idempotency_key": f"lc-{contact_id}-{_now().timestamp()}",
            "correlation_id": correlation_id,
            "processing_status": "processed", "retry_count": 0, "error": None,
            "simulated": False, "source": "admin_created", "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        await _audit(db, actor=admin["email"], action="contact.lifecycle_changed",
                     target_type="contact", target_id=contact_id,
                     correlation_id=correlation_id, reason=body.reason,
                     simulated=False, source="admin_created", extra={"from": prev, "to": body.new_stage})
        return {"contact_id": contact_id, "from": prev, "to": body.new_stage}

    @router.post("/contacts/{contact_id}/notes")
    async def add_note(contact_id: str, body: ContactNote, admin=Depends(require_admin)):
        contact = await db["contacts"].find_one({"id": contact_id}, {"_id": 0})
        if not contact:
            raise HTTPException(404, "contact not found")
        doc = {
            "id": str(uuid.uuid4()),
            "contact_id": contact_id,
            "body": _sanitize_note(body.body),
            "created_at": _now(),
            "created_by": admin["email"],
        }
        await db["contact_notes"].insert_one(doc)
        await _audit(db, actor=admin["email"], action="contact.note_added",
                     target_type="contact", target_id=contact_id,
                     reason="note added", simulated=False, source="admin_created")
        return {"note": {**doc, "_id": None}}

    @router.post("/contacts/merge")
    async def merge_contacts(body: ContactMerge, admin=Depends(require_admin)):
        if body.surviving_id == body.merged_id:
            raise HTTPException(422, "surviving_id and merged_id must differ")
        surviving = await db["contacts"].find_one({"id": body.surviving_id}, {"_id": 0})
        merged = await db["contacts"].find_one({"id": body.merged_id}, {"_id": 0})
        if not surviving or not merged:
            raise HTTPException(404, "one or both contacts not found")
        if merged.get("merged_into"):
            raise HTTPException(409, "merged_id has already been merged")

        # Conflicting external identities?
        conflict = bool(
            surviving.get("stripe_customer_id") and merged.get("stripe_customer_id")
            and surviving["stripe_customer_id"] != merged["stripe_customer_id"]
        )
        if conflict and not body.force_conflicting_external_ids:
            raise HTTPException(409, "conflicting external customer IDs — set "
                                       "force_conflicting_external_ids=true to override")

        preview = {
            "surviving_id": body.surviving_id,
            "merged_id": body.merged_id,
            "events_to_move": await db["internal_events"].count_documents(
                {"contact_id": body.merged_id}),
            "touches_to_move": await db["attribution_touches"].count_documents(
                {"contact_id": body.merged_id}),
            "notes_to_move": await db["contact_notes"].count_documents(
                {"contact_id": body.merged_id}),
            "scores_to_move": await db["contact_scores"].count_documents(
                {"contact_id": body.merged_id}),
            "audits_to_move": await db["audit_log"].count_documents(
                {"target_id": body.merged_id, "target_type": "contact"}),
            "conflict_resolved": conflict and body.force_conflicting_external_ids,
        }
        if body.dry_run:
            return {"preview": preview, "merged": False,
                    "note": "dry_run=true; no changes applied."}

        correlation_id = str(uuid.uuid4())
        # Move history: keep audit target_id as-is (immutable) but tag merged
        # events/touches/notes/scores with a duplicate contact_id_history entry.
        await db["internal_events"].update_many(
            {"contact_id": body.merged_id},
            {"$set": {"contact_id": body.surviving_id,
                       "merged_from_contact_id": body.merged_id}},
        )
        await db["attribution_touches"].update_many(
            {"contact_id": body.merged_id},
            {"$set": {"contact_id": body.surviving_id,
                       "merged_from_contact_id": body.merged_id}},
        )
        await db["contact_notes"].update_many(
            {"contact_id": body.merged_id},
            {"$set": {"contact_id": body.surviving_id,
                       "merged_from_contact_id": body.merged_id}},
        )
        await db["contact_scores"].update_many(
            {"contact_id": body.merged_id},
            {"$set": {"contact_id": body.surviving_id,
                       "merged_from_contact_id": body.merged_id}},
        )
        # Mark the merged contact — soft-delete pattern (never remove)
        await db["contacts"].update_one(
            {"id": body.merged_id},
            {"$set": {
                "merged_into": body.surviving_id,
                "merged_at": _now(),
                "merged_by": admin["email"],
                "merge_reason": body.reason,
            }},
        )
        # Event + audit
        await db["internal_events"].insert_one({
            "id": str(uuid.uuid4()),
            "event_type": "contact.merged",
            "source": "revenue.contact",
            "payload": preview,
            "contact_id": body.surviving_id,
            "organization_id": None,
            "idempotency_key": f"merge-{body.merged_id}-{body.surviving_id}",
            "correlation_id": correlation_id,
            "processing_status": "processed", "retry_count": 0, "error": None,
            "simulated": False, "source": "admin_created", "environment": "preview",
            "created_at": _now(), "processed_at": _now(),
        })
        await _audit(db, actor=admin["email"], action="contact.merged",
                     target_type="contact", target_id=body.surviving_id,
                     correlation_id=correlation_id, reason=body.reason,
                     simulated=False, source="admin_created",
                     extra={"merged_from": body.merged_id, **preview})
        return {"preview": preview, "merged": True,
                "correlation_id": correlation_id}

    # Return the router so server.py can include it
    return router


# ─── Helpers used above (kept outside register_routes so they're testable) ─
def _jsonable(x):
    """Recursively convert Decimal128/Decimal to strings for JSON logging."""
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_jsonable(v) for v in x]
    if isinstance(x, Decimal128):
        return str(x.to_decimal())
    if isinstance(x, Decimal):
        return str(x)
    return x


def _next_action(band: Optional[str]) -> str:
    return {
        "unqualified": "no action recommended",
        "early_interest": "send educational content (route via approval queue)",
        "engaged": "invite to assessment (route via approval queue)",
        "qualified": "recommend offer + follow-up email (route via approval queue)",
        "high_intent": "immediate outreach + offer (route via approval queue)",
        "existing_customer": "check retention / upsell (route via approval queue)",
    }.get(band or "unqualified", "review contact")
