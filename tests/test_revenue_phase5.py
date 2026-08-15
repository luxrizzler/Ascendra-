"""Phase 5 — Executive Revenue Control Center tests.

Validates the invariants that make the minimal Phase 5 layer honest:

  1. Executive summary aggregates ONLY actual (non-simulated) ledger data;
     simulated ledger entries never enter revenue totals.
  2. Simulation harness refuses to run against a non-test DB (the guard
     compares db.name against a "test" substring — critical safety property).
  3. Financial constitution seed is idempotent; running seed twice does not
     duplicate rows.
  4. Integration readiness matrix always reports
     ``live_execution_enabled: false`` for every provider (safety gate).
  5. Funnel report excludes simulated rows.
  6. Every executive endpoint returns an ``is_stub`` flag so the UI can
     surface honesty labels on stubbed sections.

Runs against the isolated ``ascendra_revenue_test`` DB via conftest.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import requests
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
from _env_utils import get_test_mongo_config  # noqa: E402


def _load_backend_base() -> str:
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
    for line in Path("/app/frontend/.env").read_text().splitlines():
        s = line.strip()
        if s.startswith("REACT_APP_BACKEND_URL="):
            _, _, v = s.partition("=")
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            return v.rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


BACKEND = _load_backend_base()
API = f"{BACKEND}/api"
ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_PW = "AscendraAdmin2026!"


@pytest.fixture(scope="module")
def jwt(isolated_env):
    requests.post(f"{API}/auth/signup", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PW,
        "name": "Phase5 Admin"}, timeout=10)
    r = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=10)
    assert r.status_code == 200
    token = r.json().get("access_token")
    mongo_url, test_db = get_test_mongo_config()

    async def _promote():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await c[test_db]["users"].update_one(
                {"email": ADMIN_EMAIL},
                {"$set": {"is_admin": True, "role": "admin"}},
            )
        finally:
            c.close()
    asyncio.run(_promote())
    return token


@pytest.fixture(scope="module")
def h(jwt):
    return {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN GATE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("path", [
    "/admin/revenue/constitution",
    "/admin/revenue/executive/summary",
    "/admin/revenue/executive/funnel",
    "/admin/revenue/executive/health",
    "/admin/revenue/executive/integration-readiness",
])
def test_admin_gate_blocks_anon_phase5(path):
    r = requests.get(f"{API}{path}", timeout=10)
    assert r.status_code in (401, 403), f"{path}: got {r.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
#  FINANCIAL CONSTITUTION
# ═══════════════════════════════════════════════════════════════════════════
def test_constitution_seeded_and_immutability_labeled(h):
    r = requests.get(f"{API}/admin/revenue/constitution", headers=h, timeout=10)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["count"] >= 1
    assert j["current"] is not None
    principles = j["current"].get("principles", [])
    assert isinstance(principles, list) and len(principles) >= 15, (
        f"expected at least 15 constitutional principles, got {len(principles)}")
    assert j["current"].get("immutable") is True
    # The endpoint MUST surface the immutability contract in its response.
    assert "immutability_note" in j
    assert "never be edited" in j["immutability_note"].lower()


def test_constitution_seed_is_idempotent(h):
    """Running the seeder repeatedly must NOT duplicate rows."""
    mongo_url, test_db = get_test_mongo_config()
    import revenue_phase5 as p5

    async def _seed_twice():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await p5.seed_constitution(c[test_db])
            await p5.seed_constitution(c[test_db])
            return await c[test_db]["financial_constitution"].count_documents({})
        finally:
            c.close()
    n = asyncio.run(_seed_twice())
    assert n == 1, f"seed_constitution not idempotent: {n} rows after 2 seeds"


# ═══════════════════════════════════════════════════════════════════════════
#  EXECUTIVE SUMMARY — SIMULATED VS ACTUAL ISOLATION (CRITICAL INVARIANT)
# ═══════════════════════════════════════════════════════════════════════════
def test_summary_excludes_simulated_ledger_from_actual_totals(h):
    """The core Phase 5 honesty invariant: simulated ledger entries must
    NEVER contribute to the ``actual_gross_cash_collected`` metric."""
    mongo_url, test_db = get_test_mongo_config()

    # Snapshot: current actual cleared total (before we plant a simulated row)
    before = requests.get(f"{API}/admin/revenue/executive/summary",
                            headers=h, timeout=10).json()
    before_actual = Decimal(
        before["revenue"]["actual_gross_cash_collected"]["value"])

    # Insert a $99,999 simulated (marked simulated=True) cleared entry directly
    async def _plant_simulated():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await c[test_db]["financial_ledger"].insert_one({
                "id": str(uuid.uuid4()),
                "idempotency_key": f"sim-{uuid.uuid4().hex}",
                "entry_type": "payment_recorded",
                "source_type": "test_fixture",
                "gross_amount": Decimal128("99999.00"),
                "settlement_status": "cleared",
                "simulated": True,             # ← the isolation key
                "environment": "preview",
                "source": "test_fixture",
                "allocated": False,
                "created_at": datetime.now(timezone.utc),
                "effective_date": datetime.now(timezone.utc),
            })
        finally:
            c.close()
    asyncio.run(_plant_simulated())

    after = requests.get(f"{API}/admin/revenue/executive/summary",
                           headers=h, timeout=10).json()
    after_actual = Decimal(
        after["revenue"]["actual_gross_cash_collected"]["value"])

    # The simulated $99,999 must NOT have moved the actual total.
    assert after_actual == before_actual, (
        f"simulated ledger row leaked into actual total: "
        f"{before_actual} → {after_actual}")

    # The response envelope must expose the source_state label
    assert after["revenue"]["actual_gross_cash_collected"]["source_state"] == "actual"
    assert after["is_stub"] is False


def test_summary_honestly_labels_allocations_and_exceptions(h):
    r = requests.get(f"{API}/admin/revenue/executive/summary",
                       headers=h, timeout=10).json()
    assert r["allocations"]["source_state"] == "derived_from_actual_ledger"
    assert r["allocations"]["is_stub"] is False
    assert r["exceptions"]["is_stub"] is False
    assert "PREVIEW ENVIRONMENT" in r["banner"]


# ═══════════════════════════════════════════════════════════════════════════
#  SIMULATION HARNESS SAFETY
# ═══════════════════════════════════════════════════════════════════════════
def test_simulation_harness_accepts_supported_scenario_and_labels_it_stub(h):
    r = requests.post(
        f"{API}/admin/revenue/executive/simulate?scenario=successful_subscription",
        headers=h, timeout=10)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["scenario"] == "successful_subscription"
    assert j["status"] == "simulated"
    # The DB the harness ran against MUST contain "test" in its name
    assert "test" in j["db"].lower(), (
        f"simulation harness ran against non-test DB {j['db']!r}")
    assert j["is_stub"] is True
    assert j["source_state"] == "simulated"


def test_simulation_harness_rejects_unsupported_scenario(h):
    r = requests.post(
        f"{API}/admin/revenue/executive/simulate?scenario=arbitrary_not_a_real_scenario",
        headers=h, timeout=10)
    assert r.status_code == 422


def test_simulation_harness_writes_only_audit_records(h):
    """The stub harness must ONLY create an audit_log row — never a ledger or
    allocation record. This proves it can never contaminate actual totals."""
    mongo_url, test_db = get_test_mongo_config()

    async def _snap():
        c = AsyncIOMotorClient(mongo_url)
        try:
            ledger = await c[test_db]["financial_ledger"].count_documents({})
            audit = await c[test_db]["audit_log"].count_documents(
                {"action": "simulation.refund_adjustment"})
            return ledger, audit
        finally:
            c.close()
    ledger_before, audit_before = asyncio.run(_snap())

    r = requests.post(
        f"{API}/admin/revenue/executive/simulate?scenario=refund_adjustment",
        headers=h, timeout=10)
    assert r.status_code == 200

    ledger_after, audit_after = asyncio.run(_snap())
    # Ledger MUST be untouched
    assert ledger_after == ledger_before, (
        f"simulation harness wrote to financial_ledger: "
        f"{ledger_before} → {ledger_after}")
    # An audit_log row was appended
    assert audit_after == audit_before + 1


# ═══════════════════════════════════════════════════════════════════════════
#  INTEGRATION READINESS MATRIX — SAFETY GATE INVARIANT
# ═══════════════════════════════════════════════════════════════════════════
def test_integration_readiness_never_reports_live_execution_enabled(h):
    r = requests.get(f"{API}/admin/revenue/executive/integration-readiness",
                       headers=h, timeout=10).json()
    assert r["is_stub"] is False
    integrations = r["integrations"]
    assert len(integrations) >= 3
    for row in integrations:
        assert row["live_execution_enabled"] is False, (
            f"provider {row['provider']!r} reports live_execution_enabled=True")
        assert row["credential_values_shown"] is False, (
            f"provider {row['provider']!r} may be leaking credential values")
        assert row["outbound_action_support"] is False, (
            "outbound action execution is intentionally not implemented in preview")


def test_integration_readiness_does_not_leak_credentials(h):
    """The response payload must never include the value of any secret env
    var. This is a defense-in-depth test."""
    r = requests.get(f"{API}/admin/revenue/executive/integration-readiness",
                       headers=h, timeout=10)
    body_text = r.text
    # A live Stripe key would start with sk_live_; the test-webhook secret
    # with whsec_. Neither should ever appear in this payload.
    for probe in ("sk_live_", "sk_test_", "whsec_", "re_"):
        assert probe not in body_text, (
            f"integration-readiness leaked a value starting with {probe!r}")


# ═══════════════════════════════════════════════════════════════════════════
#  FUNNEL REPORT — EXCLUDES SIMULATED
# ═══════════════════════════════════════════════════════════════════════════
def test_funnel_excludes_simulated_lifecycle_events(h):
    mongo_url, test_db = get_test_mongo_config()

    # Plant one ACTUAL transition and one SIMULATED transition. Only the
    # actual one may appear in the funnel counts.
    async def _plant():
        c = AsyncIOMotorClient(mongo_url)
        try:
            base = datetime.now(timezone.utc)
            await c[test_db]["contact_lifecycle_events"].insert_one({
                "id": str(uuid.uuid4()),
                "stage_from": "lead", "stage_to": "trial",
                "simulated": False,
                "created_at": base,
                "environment": "preview",
                "source": "test_fixture",
            })
            await c[test_db]["contact_lifecycle_events"].insert_one({
                "id": str(uuid.uuid4()),
                "stage_from": "lead", "stage_to": "trial",
                "simulated": True,
                "created_at": base,
                "environment": "preview",
                "source": "test_fixture",
            })
        finally:
            c.close()
    asyncio.run(_plant())

    r = requests.get(f"{API}/admin/revenue/executive/funnel",
                       headers=h, timeout=10).json()
    assert r["is_stub"] is False
    assert r["source_state"] == "actual"

    # The lead→trial transition should show a count of exactly 1 (the actual
    # row), not 2 (which would indicate leakage of the simulated row).
    lead_trial = [t for t in r["transitions"]
                   if t["stage_from"] == "lead" and t["stage_to"] == "trial"]
    assert lead_trial, "expected lead→trial transition in funnel"
    # Some environments may already have accumulated transitions; require the
    # count to be at least 1 AND ensure we did NOT double-count the simulated.
    assert lead_trial[0]["count"] >= 1
    # The stricter invariant — count did not increase by 2 because of one
    # actual + one simulated row — is validated by re-running with an
    # additional simulated-only row and confirming count is unchanged.
    async def _plant_simulated_only():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await c[test_db]["contact_lifecycle_events"].insert_one({
                "id": str(uuid.uuid4()),
                "stage_from": "lead", "stage_to": "trial",
                "simulated": True,
                "created_at": datetime.now(timezone.utc),
                "environment": "preview", "source": "test_fixture",
            })
        finally:
            c.close()
    asyncio.run(_plant_simulated_only())
    r2 = requests.get(f"{API}/admin/revenue/executive/funnel",
                        headers=h, timeout=10).json()
    lead_trial2 = [t for t in r2["transitions"]
                    if t["stage_from"] == "lead" and t["stage_to"] == "trial"]
    assert lead_trial2[0]["count"] == lead_trial[0]["count"], (
        "funnel count changed after adding a simulated-only row — leak!")


# ═══════════════════════════════════════════════════════════════════════════
#  EXEC HEALTH
# ═══════════════════════════════════════════════════════════════════════════
def test_exec_health_labels_and_liveness(h):
    r = requests.get(f"{API}/admin/revenue/executive/health",
                       headers=h, timeout=10).json()
    assert r["is_stub"] is False
    assert r["source_state"] == "actual"
    assert r["banner_live_actions_enabled"] is False, (
        "AUTOMATION_LIVE_ACTIONS_ENABLED must remain false in preview")


# ═══════════════════════════════════════════════════════════════════════════
#  SYSTEM STATE STILL DOES NOT PREMATURELY MARK PHASE 5 COMPLETE
# ═══════════════════════════════════════════════════════════════════════════
def test_system_state_does_not_mark_phase5_complete(h):
    j = requests.get(f"{API}/admin/revenue/system/state",
                       headers=h, timeout=10).json()
    completed = j.get("completed_phases") or []
    assert "phase_5" not in completed, (
        "system_state prematurely reports phase_5 complete — the minimal "
        "Phase 5 layer is still labeled IN PROGRESS")
