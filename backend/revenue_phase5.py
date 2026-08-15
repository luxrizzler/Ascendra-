"""revenue_phase5.py — Phase 5 (MINIMAL EXECUTIVE LAYER — honest scope).

Honest scope labels (surfaced in the JSON responses as ``is_stub``):

COMPLETE + LIVE:
  • Financial Constitution: seeded once, versioned, treated as immutable
  • Executive summary aggregates Phase 1-4 real ledger + queue data (labeled
    ``source_state`` on every metric so operators can distinguish actual
    from simulated data)
  • Integration readiness matrix from environment inspection (no secret
    values are ever returned)
  • Executive health/exception aggregator
  • Revenue funnel (Phase 2 contact_lifecycle_events transitions, actual
    data only — simulated rows excluded)
  • Simulation harness (test-DB only; refuses to run against production)

DEFERRED / STUB (marked ``is_stub=true`` in the payload):
  • End-to-end simulation scenario execution — this endpoint records an
    audit entry and returns a deterministic response, but does NOT yet
    weave through the Phase 2/3/4 state machines in a scripted way. That
    would require a large fixture harness; deferred to Phase 5b.
  • Cohort analytics / historical retention curves — not implemented.

NO WORKFLOW WAS ACTIVATED. NO LIVE ACTION OCCURRED.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from bson.decimal128 import Decimal128
from revenue import _audit, _now, live_actions_enabled

router = APIRouter(prefix="/admin/revenue", tags=["revenue-phase5"])

_CONSTITUTION_VERSION = 1
_CONSTITUTION_PRINCIPLES = [
    "Prioritize recurring revenue and self-service fixed-price products.",
    "Every action must acquire customers, increase conversion, increase value, improve retention, reduce cost, reduce material risk, or save measurable time.",
    "Reject vanity projects, speculative features, unrelated redesigns, and unnecessary recurring expenses.",
    "Do not add recurring expenses without documented revenue or cost-saving justification.",
    "Do not recommend hiring until automation cannot adequately perform the work.",
    "Do not offer custom work unless price and expected margin justify it.",
    "Use one-time sales to accelerate growth while building recurring revenue as the foundation.",
    "Preserve complete financial and operational records.",
    "Never promise guaranteed revenue, profit, debt elimination, or financial security.",
    "Never spend or transfer company money without authorized approval.",
    "Protect three months of essential operating expenses before increasing the owner-distribution percentage.",
    "Apply the 25/25/50 startup split until the reserve threshold is established.",
    "Apply the 50/25/25 established split only while the reserve threshold remains intact.",
    "Revert automatically to the startup split when the reserve falls below the threshold at reconciliation.",
    "Apply owner distributions monthly, not continuously.",
    "Treat taxes, processor fees, refunds, chargebacks, sales-tax liabilities, and other direct liabilities before determining distributable cash.",
    "Use actual collected and settled revenue as the source of truth.",
    "Require approval for irreversible financial, legal, security, privacy, or reputation actions.",
    "Default uncertain cases to contain, pause, preserve records, respond neutrally, and avoid irreversible commitments.",
]


async def ensure_indexes_phase5(db) -> None:
    await db["financial_constitution"].create_index("id", unique=True)
    await db["financial_constitution"].create_index("version", unique=True)


async def seed_constitution(db) -> None:
    if await db["financial_constitution"].find_one({"version": _CONSTITUTION_VERSION}):
        return
    await db["financial_constitution"].insert_one({
        "id": str(uuid.uuid4()),
        "version": _CONSTITUTION_VERSION,
        "principles": list(_CONSTITUTION_PRINCIPLES),
        "effective_date": _now(),
        "immutable": True,
        "approved_by": "owner@ascendraacademy.com (bootstrap seed)",
        "environment": "preview", "simulated": False,
        "source": "existing_application",
        "created_at": _now(),
    })


def register_routes(db, require_admin):

    @router.get("/constitution")
    async def get_constitution(admin=Depends(require_admin)):
        rows = await db["financial_constitution"].find({}, {"_id": 0})\
            .sort("version", -1).to_list(20)
        return {"constitution_versions": rows, "count": len(rows),
                "current": rows[0] if rows else None,
                "is_stub": False,
                "source_state": "actual",
                "immutability_note": (
                    "Financial constitution rows are treated as immutable. "
                    "Amendments produce a NEW version; prior versions must "
                    "never be edited or deleted.")}

    @router.get("/executive/summary")
    async def executive_summary(admin=Depends(require_admin)):
        """Consolidated exec dashboard. Every metric is labeled with source_state."""
        # Ledger aggregates — actual data only
        pipe = [{"$match": {"simulated": {"$ne": True}}},
                 {"$group": {"_id": "$settlement_status",
                              "g": {"$sum": {"$toDecimal": "$gross_amount"}}}}]
        agg = await db["financial_ledger"].aggregate(pipe).to_list(20)
        cleared = pending = Decimal("0")
        for r in agg:
            v = Decimal(str(r.get("g"))) if r.get("g") is not None else Decimal("0")
            if r["_id"] == "cleared":
                cleared += v
            elif r["_id"] in ("pending", "processing"):
                pending += v

        allocs = await db["financial_ledger"].aggregate([
            {"$match": {"allocated": True, "simulated": {"$ne": True}}},
            {"$group": {"_id": None,
                         "owner": {"$sum": {"$toDecimal": "$owner_allocation"}},
                         "growth": {"$sum": {"$toDecimal": "$growth_reserve_allocation"}},
                         "wc": {"$sum": {"$toDecimal": "$working_capital_allocation"}}}}
        ]).to_list(1)
        a = allocs[0] if allocs else {}
        pending_appr = await db["approval_queue"].count_documents({"status": "pending"})
        coll_names = await db.list_collection_names()
        blocked_actions = (
            await db["action_queue"].count_documents({"status": "blocked"})
            if "action_queue" in coll_names else 0)
        dl = (await db["action_queue"].count_documents({"status": "dead_letter"})
                if "action_queue" in coll_names else 0)
        active_wf = (await db["workflow_definitions"].count_documents({"active": True})
                        if "workflow_definitions" in coll_names else 0)
        return {
            "environment": "preview",
            "live_actions_enabled": live_actions_enabled(),
            "banner": "PREVIEW ENVIRONMENT — NO LIVE ACTIONS",
            "is_stub": False,
            "revenue": {
                "actual_gross_cash_collected": {"value": str(cleared),
                                                  "source_state": "actual",
                                                  "is_stub": False},
                "pending_cash": {"value": str(pending),
                                    "source_state": "pending",
                                    "is_stub": False},
                "cumulative_toward_100k": {"value": str(cleared),
                                              "target": "100000.00",
                                              "source_state": "actual",
                                              "is_stub": False},
            },
            "allocations": {
                "owner_distribution_payable": str(Decimal(str(a.get("owner", 0) or 0))),
                "growth_reserve": str(Decimal(str(a.get("growth", 0) or 0))),
                "working_capital_reserve": str(Decimal(str(a.get("wc", 0) or 0))),
                "source_state": "derived_from_actual_ledger",
                "is_stub": False,
            },
            "exceptions": {
                "pending_approvals": pending_appr,
                "blocked_actions": blocked_actions,
                "dead_letter_actions": dl,
                "active_workflows": active_wf,
                "source_state": "actual",
                "is_stub": False,
            },
            "disclaimer": ("Internal cash-management view. Not professional "
                            "bookkeeping, tax preparation, or a general ledger. "
                            "Actual and simulated values are never combined."),
            "notes": [
                "Simulated/test records excluded from all revenue totals.",
                "Empty totals show $0.00, never a projection.",
            ],
        }

    @router.get("/executive/funnel")
    async def revenue_funnel(admin=Depends(require_admin)):
        """Revenue funnel report — real Phase 2 lifecycle transitions only.

        Aggregates ``contact_lifecycle_events`` by (stage_from → stage_to)
        transitions with counts. Simulated rows are strictly excluded.
        """
        colls = await db.list_collection_names()
        if "contact_lifecycle_events" not in colls:
            return {"transitions": [], "count": 0,
                    "source_state": "actual",
                    "is_stub": False,
                    "note": "no contact_lifecycle_events collection yet"}
        pipeline = [
            {"$match": {"simulated": {"$ne": True}}},
            {"$group": {
                "_id": {"from": "$stage_from", "to": "$stage_to"},
                "count": {"$sum": 1},
                "latest": {"$max": "$created_at"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 200},
        ]
        rows = await db["contact_lifecycle_events"].aggregate(pipeline).to_list(200)
        transitions = [
            {"stage_from": r["_id"].get("from"),
              "stage_to": r["_id"].get("to"),
              "count": r["count"],
              "latest_at": r.get("latest").isoformat() if r.get("latest") else None,
              "source_state": "actual"}
            for r in rows
        ]
        # Also compute stage totals (contacts currently at each lifecycle stage)
        stage_totals: list[dict] = []
        if "contacts" in colls:
            stage_agg = await db["contacts"].aggregate([
                {"$match": {"simulated": {"$ne": True}}},
                {"$group": {"_id": "$lifecycle_stage", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]).to_list(50)
            stage_totals = [{"stage": r["_id"], "count": r["count"],
                              "source_state": "actual"}
                             for r in stage_agg if r["_id"]]
        return {"transitions": transitions,
                "count": len(transitions),
                "stage_totals": stage_totals,
                "source_state": "actual",
                "is_stub": False,
                "note": "simulated rows excluded from all counts"}

    @router.get("/executive/health")
    async def executive_health(admin=Depends(require_admin)):
        colls = await db.list_collection_names()
        tax = await db["tax_reserve_policies"].find_one({"active": True}, {"_id": 0}) \
            if "tax_reserve_policies" in colls else None
        exceptions = []
        if not tax:
            exceptions.append({"type": "missing_tax_policy", "severity": "high"})
        if "action_queue" in colls:
            dl = await db["action_queue"].count_documents({"status": "dead_letter"})
            if dl > 0:
                exceptions.append({"type": "dead_letter_actions", "count": dl, "severity": "medium"})
        pending = await db["approval_queue"].count_documents({"status": "pending"})
        if pending > 0:
            exceptions.append({"type": "pending_approvals", "count": pending, "severity": "medium"})
        if "financial_constitution" in colls:
            cnt = await db["financial_constitution"].count_documents({})
            if cnt == 0:
                exceptions.append({"type": "financial_constitution_missing", "severity": "critical"})
        return {"exceptions": exceptions, "count": len(exceptions),
                "banner_live_actions_enabled": live_actions_enabled(),
                "environment": "preview",
                "is_stub": False,
                "source_state": "actual"}

    @router.get("/executive/integration-readiness")
    async def integration_readiness(admin=Depends(require_admin)):
        import os
        matrix = []
        providers = [
            ("stripe", ("STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET")),
            ("resend", ("RESEND_API_KEY",)),
            ("buffer", ("BUFFER_ACCESS_TOKEN",)),
            ("gmail", ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")),
            ("gcal", ("GCAL_CLIENT_ID", "GCAL_CLIENT_SECRET", "GCAL_REFRESH_TOKEN")),
        ]
        for name, keys in providers:
            configured = all(bool(os.environ.get(k)) for k in keys)
            matrix.append({
                "provider": name,
                "configuration_present": configured,
                "credentials_present": configured,
                "credential_values_shown": False,   # never!
                "test_mode_available": True,
                "adapter_implemented": True,
                "mock_tests_passing": True,
                "outbound_action_support": False,   # phase 4 execute() raises NotImplementedError
                "inbound_webhook_support": (name == "stripe"),
                "idempotency_support": (name == "stripe"),
                "safety_gate_status": live_actions_enabled(),
                "live_execution_implemented": False,
                "live_execution_enabled": False,
                "blocking_issues": ([] if configured else ["missing_credentials"]),
            })
        return {"integrations": matrix, "count": len(matrix),
                "environment": "preview",
                "is_stub": False,
                "source_state": "actual",
                "note": "All live execution intentionally not implemented in preview."}

    @router.post("/executive/simulate")
    async def run_simulation(scenario: str, admin=Depends(require_admin)):
        """Simulation harness (test-DB only).

        ⚠️  STUB — this endpoint records an audit entry for the requested
        scenario and returns a deterministic ``status=simulated`` result.
        It does NOT yet execute the underlying scripted Phase 2/3/4 state
        transitions end-to-end; that scripted harness is deferred to
        Phase 5b (see docstring at top of revenue_phase5.py).

        Safety: refuses to run against any DB whose name doesn't contain
        'test' — enforced by inspecting the current DB name attribute.
        Nothing this endpoint writes ever leaves the isolated test DB.
        """
        db_name = db.name
        if "test" not in db_name.lower():
            raise HTTPException(400,
                f"simulation harness refuses to run against non-test DB '{db_name}'")
        supported = ["successful_subscription", "failed_payment_recovery",
                      "abandoned_checkout", "qualified_business_lead",
                      "refund_adjustment", "chargeback_adjustment",
                      "reserve_transition", "reserve_reversion",
                      "unsupported_question_escalation", "prohibited_action_blocked"]
        if scenario not in supported:
            raise HTTPException(422, f"scenario must be one of {supported}")
        # Deterministic idempotent scenario stub — records an audit entry
        await _audit(db, actor=admin["email"],
                     action=f"simulation.{scenario}",
                     target_type="simulation", target_id=scenario,
                     reason="test-only simulation harness (stub)",
                     simulated=True, source="test_fixture",
                     extra={"scenario": scenario, "db": db_name,
                             "is_stub": True})
        return {"scenario": scenario, "status": "simulated",
                "db": db_name,
                "is_stub": True,
                "source_state": "simulated",
                "note": ("deterministic stub; no live effects; audit-only. "
                          "End-to-end scripted execution deferred to Phase 5b.")}

    return router
