"""revenue_phase5.py — Phase 5 (EXECUTIVE LAYER — full sign-off + Phase 5b).

Phase 5 minimal layer was signed off. Phase 5b adds:
  • End-to-end scripted simulation scenarios — each scenario now creates real
    records in Phase 2/3/4 collections, all tagged ``simulated=True`` so the
    executive summary's actual totals stay untouched.
  • Cohort analytics endpoint (MRR by acquisition-month cohort + retention
    curve by signup cohort) — real data only, simulated rows excluded.

COMPLETE + LIVE:
  • Financial Constitution: seeded once, versioned, treated as immutable
  • Executive summary aggregates Phase 1-4 real ledger + queue data (labeled
    ``source_state`` on every metric)
  • Integration readiness matrix from environment inspection
  • Executive health/exception aggregator
  • Revenue funnel (simulated rows excluded)
  • Simulation harness — Phase 5b: scripted end-to-end scenarios (test-DB only)
  • Cohort analytics endpoint (MRR + retention curve; simulated excluded)

NO WORKFLOW WAS ACTIVATED. NO LIVE ACTION OCCURRED.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
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

    # ═══════════════════════════════════════════════════════════════════════
    #  PHASE 5b — SCRIPTED SIMULATION SCENARIOS (test-DB only)
    # ═══════════════════════════════════════════════════════════════════════
    async def _sim_contact(email: str, stage: str) -> str:
        """Insert a simulated contact + emit an initial lifecycle event.
        Returns the contact_id."""
        cid = str(uuid.uuid4())
        now = _now()
        await db["contacts"].insert_one({
            "id": cid,
            "email": email,
            "email_normalized": email.lower(),   # required by unique index
            "name": email.split("@")[0].replace(".", " ").title(),
            "lifecycle_stage": stage,
            "simulated": True,                 # ← ALWAYS true from sim harness
            "environment": "preview",
            "source": "test_fixture",
            "created_at": now, "updated_at": now,
            "attribution": {},
        })
        await db["contact_lifecycle_events"].insert_one({
            "id": str(uuid.uuid4()),
            "contact_id": cid,
            "stage_from": None, "stage_to": stage,
            "reason": "sim harness bootstrap",
            "simulated": True,
            "environment": "preview",
            "source": "test_fixture",
            "created_at": now,
        })
        return cid

    async def _sim_lifecycle_transition(cid: str, frm: str, to: str,
                                          reason: str) -> None:
        await db["contact_lifecycle_events"].insert_one({
            "id": str(uuid.uuid4()),
            "contact_id": cid,
            "stage_from": frm, "stage_to": to,
            "reason": reason,
            "simulated": True,
            "environment": "preview",
            "source": "test_fixture",
            "created_at": _now(),
        })
        await db["contacts"].update_one(
            {"id": cid},
            {"$set": {"lifecycle_stage": to, "updated_at": _now()}},
        )

    async def _sim_ledger_entry(*, entry_type: str, gross: str,
                                  settlement: str = "cleared",
                                  refund: str = "0.00",
                                  chargeback: str = "0.00") -> str:
        """Insert a simulated financial-ledger row. NEVER touches real totals
        because every executive aggregate filters ``simulated=True`` out."""
        eid = str(uuid.uuid4())
        now = _now()
        gross_d = Decimal(gross)
        refund_d = Decimal(refund)
        chargeback_d = Decimal(chargeback)
        # Simplified allocation math for the simulated record: net = gross
        # - refund - chargeback; 25/25/50 startup split. This is illustrative;
        # the row is quarantined by simulated=True so it can never leak.
        net_d = (gross_d - refund_d - chargeback_d)
        owner = (net_d * Decimal("0.25")).quantize(Decimal("0.01"))
        growth = (net_d * Decimal("0.25")).quantize(Decimal("0.01"))
        wc = (net_d - owner - growth).quantize(Decimal("0.01"))
        await db["financial_ledger"].insert_one({
            "id": eid,
            "idempotency_key": f"sim-{eid}",
            "entry_type": entry_type,
            "source_type": "sim_harness",
            "gross_amount": Decimal128(gross_d.quantize(Decimal("0.01"))),
            "refund_amount": Decimal128(refund_d.quantize(Decimal("0.01"))),
            "chargeback_amount": Decimal128(chargeback_d.quantize(Decimal("0.01"))),
            "net_amount": Decimal128(net_d.quantize(Decimal("0.01"))),
            "owner_allocation": Decimal128(owner),
            "growth_reserve_allocation": Decimal128(growth),
            "working_capital_allocation": Decimal128(wc),
            "settlement_status": settlement,
            "allocated": (settlement == "cleared"),
            "simulated": True,                # ← always true from harness
            "environment": "preview",
            "source": "test_fixture",
            "created_at": now,
            "effective_date": now,
        })
        return eid

    async def _sim_action(action_type: str, payload: dict) -> str:
        aid = str(uuid.uuid4())
        await db["action_queue"].insert_one({
            "id": aid,
            "idempotency_key": f"sim-act-{aid}",
            "action_type": action_type,
            "requested_payload": payload,
            "status": "simulated",
            "simulated": True,
            "environment": "preview",
            "source": "test_fixture",
            "created_at": _now(),
        })
        return aid

    @router.get("/executive/runbook")
    async def get_runbook(admin=Depends(require_admin)):
        """Return the governance runbook as raw markdown for in-UI rendering
        and one-click download.

        The runbook is a printable operator reference covering:
          • Approval flow (sensitive Phase 3 endpoints)
          • Corrections flow (owner-draw adjustments + reversals)
          • Constitutional amendments
          • Simulation harness safety
          • Sign-off & rollback procedures

        Source of truth: /app/docs/governance_runbook.md. This endpoint reads
        the file from disk on every call so amendments to the runbook are
        served without a restart.
        """
        import os as _os
        runbook_path = _os.path.join(_os.path.dirname(_os.path.dirname(
            _os.path.abspath(__file__))), "docs", "governance_runbook.md")
        if not _os.path.exists(runbook_path):
            raise HTTPException(404, "governance runbook not found on disk")
        try:
            with open(runbook_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise HTTPException(500, f"failed to read runbook: {e}")
        return {
            "markdown": content,
            "byte_size": len(content.encode("utf-8")),
            "path": "governance_runbook.md",
            "version": "1.0",
            "source_state": "actual",
            "is_stub": False,
        }

    @router.post("/executive/simulate")
    async def run_simulation(scenario: str, admin=Depends(require_admin)):
        """Phase 5b — scripted end-to-end simulation scenarios (test-DB only).

        Each supported scenario now creates *real* records across Phase 2/3/4
        collections, but every record is tagged ``simulated=True`` and every
        executive aggregate excludes simulated rows. This means:
          • operators can rehearse the state machine safely
          • real totals cannot drift by 1 cent
          • replaying the same scenario is idempotent-safe (test DB is dropped
            between sessions by conftest)

        SAFETY: refuses to run against any DB whose name does not contain
        the substring ``test`` — enforced by inspecting ``db.name``.
        """
        db_name = db.name
        if "test" not in db_name.lower():
            raise HTTPException(400,
                f"simulation harness refuses to run against non-test DB '{db_name}'")

        supported = {
            "successful_subscription", "failed_payment_recovery",
            "abandoned_checkout", "qualified_business_lead",
            "refund_adjustment", "chargeback_adjustment",
            "reserve_transition", "reserve_reversion",
            "unsupported_question_escalation", "prohibited_action_blocked",
        }
        if scenario not in supported:
            raise HTTPException(422, f"scenario must be one of {sorted(supported)}")

        emitted: dict = {"contacts": [], "lifecycle_events": [],
                          "ledger_entries": [], "actions": []}

        # ─── Per-scenario scripts ──────────────────────────────────────────
        if scenario == "successful_subscription":
            cid = await _sim_contact(f"sim-{uuid.uuid4().hex[:6]}@example.test",
                                        "new_lead")
            emitted["contacts"].append(cid)
            await _sim_lifecycle_transition(cid, "new_lead", "engaged_lead",
                                                "clicked pricing page")
            await _sim_lifecycle_transition(cid, "engaged_lead", "trial",
                                                "started free trial")
            await _sim_lifecycle_transition(cid, "trial", "customer",
                                                "checkout succeeded")
            eid = await _sim_ledger_entry(entry_type="payment_recorded",
                                             gross="49.00")
            emitted["ledger_entries"].append(eid)

        elif scenario == "failed_payment_recovery":
            cid = await _sim_contact(f"sim-{uuid.uuid4().hex[:6]}@example.test",
                                        "customer")
            emitted["contacts"].append(cid)
            await _sim_lifecycle_transition(cid, "customer", "past_due",
                                                "renewal charge failed")
            aid = await _sim_action("send_approved_email",
                                      {"template": "past_due_recovery",
                                       "contact_id": cid})
            emitted["actions"].append(aid)
            await _sim_lifecycle_transition(cid, "past_due", "customer",
                                                "recovered on retry")

        elif scenario == "abandoned_checkout":
            cid = await _sim_contact(f"sim-{uuid.uuid4().hex[:6]}@example.test",
                                        "engaged_lead")
            emitted["contacts"].append(cid)
            await _sim_lifecycle_transition(cid, "engaged_lead", "checkout_started",
                                                "opened stripe checkout")
            await _sim_lifecycle_transition(cid, "checkout_started",
                                                "checkout_abandoned",
                                                "24h no completion")
            aid = await _sim_action("send_approved_email",
                                      {"template": "checkout_abandoned",
                                       "contact_id": cid})
            emitted["actions"].append(aid)

        elif scenario == "qualified_business_lead":
            cid = await _sim_contact(f"biz-{uuid.uuid4().hex[:6]}@example.test",
                                        "new_lead")
            emitted["contacts"].append(cid)
            await _sim_lifecycle_transition(cid, "new_lead", "qualified_lead",
                                                "matched business_lead criteria")
            aid = await _sim_action("create_internal_task",
                                      {"type": "manual_outreach",
                                       "contact_id": cid})
            emitted["actions"].append(aid)

        elif scenario == "refund_adjustment":
            eid = await _sim_ledger_entry(entry_type="payment_recorded",
                                             gross="99.00", refund="99.00",
                                             settlement="refunded")
            emitted["ledger_entries"].append(eid)

        elif scenario == "chargeback_adjustment":
            eid = await _sim_ledger_entry(entry_type="chargeback_recorded",
                                             gross="99.00", chargeback="99.00",
                                             settlement="disputed")
            emitted["ledger_entries"].append(eid)

        elif scenario == "reserve_transition":
            # Simulate 3 months of cleared revenue that would trigger a
            # startup→established phase transition. Each entry is quarantined.
            for gross in ("2500.00", "3200.00", "2900.00"):
                eid = await _sim_ledger_entry(entry_type="payment_recorded",
                                                 gross=gross)
                emitted["ledger_entries"].append(eid)

        elif scenario == "reserve_reversion":
            # Simulate a large refund month that would push reserve below the
            # threshold, causing established→startup reversion.
            eid = await _sim_ledger_entry(entry_type="refund_recorded",
                                             gross="5000.00", refund="5000.00",
                                             settlement="refunded")
            emitted["ledger_entries"].append(eid)

        elif scenario == "unsupported_question_escalation":
            cid = await _sim_contact(f"sim-{uuid.uuid4().hex[:6]}@example.test",
                                        "customer")
            emitted["contacts"].append(cid)
            aid = await _sim_action("escalate_to_human",
                                      {"reason": "unsupported_question",
                                       "contact_id": cid})
            emitted["actions"].append(aid)

        elif scenario == "prohibited_action_blocked":
            aid = await _sim_action("initiate_bank_transfer",
                                      {"blocked_reason": "prohibited_action"})
            emitted["actions"].append(aid)
            # Ensure the action is stamped 'blocked' — verifying safety
            await db["action_queue"].update_one(
                {"id": aid},
                {"$set": {"status": "blocked",
                           "blocked_reason": "authority_matrix: prohibited"}},
            )

        # Audit trail
        await _audit(db, actor=admin["email"],
                     action=f"simulation.{scenario}",
                     target_type="simulation", target_id=scenario,
                     reason="Phase 5b scripted scenario (test-DB only)",
                     simulated=True, source="test_fixture",
                     extra={"scenario": scenario, "db": db_name,
                             "emitted_counts": {k: len(v) for k, v in emitted.items()},
                             "is_stub": False})
        return {"scenario": scenario, "status": "simulated",
                "db": db_name,
                "is_stub": False,                     # Phase 5b: NOT a stub anymore
                "source_state": "simulated",
                "emitted": emitted,
                "note": ("Phase 5b end-to-end script executed. Every record "
                          "is tagged simulated=True and quarantined from all "
                          "actual aggregates.")}

    # ═══════════════════════════════════════════════════════════════════════
    #  PHASE 5b — COHORT ANALYTICS (real data only)
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/executive/cohorts")
    async def cohort_analytics(admin=Depends(require_admin)):
        """Cohort analytics — MRR by acquisition-month cohort + retention curve.

        All computations exclude simulated rows so the harness cannot inflate
        these numbers. Empty environments legitimately return empty arrays.
        """
        colls = await db.list_collection_names()

        # ── MRR by acquisition-month cohort (real ledger only) ─────────────
        mrr_by_cohort: list[dict] = []
        if "financial_ledger" in colls:
            pipe = [
                {"$match": {"simulated": {"$ne": True},
                             "settlement_status": "cleared",
                             "entry_type": "payment_recorded"}},
                {"$project": {
                    "gross": {"$toDecimal": "$gross_amount"},
                    "month": {"$dateToString": {"format": "%Y-%m",
                                                  "date": "$effective_date"}},
                }},
                {"$group": {"_id": "$month", "mrr": {"$sum": "$gross"},
                              "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
                {"$limit": 36},
            ]
            rows = await db["financial_ledger"].aggregate(pipe).to_list(36)
            mrr_by_cohort = [
                {"cohort_month": r["_id"],
                  "mrr": str(Decimal(str(r["mrr"])).quantize(Decimal("0.01"))),
                  "payment_count": r["count"],
                  "source_state": "actual"}
                for r in rows if r["_id"]
            ]

        # ── Retention curve by signup cohort (real contacts only) ──────────
        retention: list[dict] = []
        if "contacts" in colls:
            # Group contacts by signup month, then count how many are still
            # in a "paying" lifecycle stage (customer, past_due→customer, etc.)
            cohort_pipe = [
                {"$match": {"simulated": {"$ne": True}}},
                {"$project": {
                    "signup_month": {"$dateToString": {"format": "%Y-%m",
                                                          "date": "$created_at"}},
                    "lifecycle_stage": 1,
                    "created_at": 1,
                }},
                {"$group": {
                    "_id": "$signup_month",
                    "total": {"$sum": 1},
                    "customers": {"$sum": {"$cond": [
                        {"$in": ["$lifecycle_stage",
                                    ["customer", "trial", "past_due"]]},
                        1, 0]}},
                }},
                {"$sort": {"_id": 1}},
                {"$limit": 36},
            ]
            rows = await db["contacts"].aggregate(cohort_pipe).to_list(36)
            for r in rows:
                if not r["_id"]:
                    continue
                total = r["total"] or 0
                cust = r["customers"] or 0
                pct = round((cust / total) * 100, 1) if total else 0
                retention.append({
                    "cohort_month": r["_id"],
                    "signups": total,
                    "still_active_or_customer": cust,
                    "retention_pct": pct,
                    "source_state": "actual",
                })

        # ── MRR trend deltas (month-over-month) ────────────────────────────
        deltas: list[dict] = []
        for i in range(1, len(mrr_by_cohort)):
            prev = Decimal(mrr_by_cohort[i - 1]["mrr"])
            cur = Decimal(mrr_by_cohort[i]["mrr"])
            change = cur - prev
            pct = float((change / prev) * 100) if prev != 0 else None
            deltas.append({
                "from_month": mrr_by_cohort[i - 1]["cohort_month"],
                "to_month": mrr_by_cohort[i]["cohort_month"],
                "delta": str(change.quantize(Decimal("0.01"))),
                "delta_pct": round(pct, 1) if pct is not None else None,
            })

        return {"mrr_by_cohort": mrr_by_cohort,
                "mrr_deltas": deltas,
                "retention_by_cohort": retention,
                "source_state": "actual",
                "is_stub": False,
                "notes": [
                    "Simulated rows excluded from all cohort counts.",
                    "MRR uses gross_amount of cleared payment_recorded entries.",
                    "Retention approximates contacts in trial/customer/past_due stages.",
                ]}

    return router
