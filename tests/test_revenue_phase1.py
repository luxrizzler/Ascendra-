"""Phase 1 Revenue Control Center — integration + hardening tests.

Runs against the LIVE backend, but the backend has been session-restarted by
`conftest.py` against an isolated test database (``ascendra_revenue_test`` by
default).  All destructive database access uses ``_env_utils`` helpers that
refuse to run unless the target DB clearly contains ``test`` AND ``TESTING=true``
is set in the process environment.

CONFIRMS
────────
  • System safety gate defaults to safe (``AUTOMATION_LIVE_ACTIONS_ENABLED=false``)
  • Admin gate rejects anonymous callers
  • Contact deduplication is normalized (email case-insensitive)
  • Event idempotency (same idempotency_key → same event.id)
  • Approval state-machine (valid transitions accepted, invalid rejected)
  • Audit log is append-only at the HTTP layer (no DELETE/PUT/PATCH routes)
  • Audit log is append-only at the repository layer (no write methods)
  • Integration status makes no live calls; no secrets appear in the response
  • Operating budget:
        · exact Decimal128 round-trip (no float drift)
        · negative rejected
        · excess precision rejected
        · non-decimal rejected
        · upper bound enforced
  • Organization index NOT globally unique (two orgs may share normalized names)
  • DB the tests are targeting is the isolated test DB (not prod)
"""
from __future__ import annotations

import asyncio
import inspect
import os
import uuid
from pathlib import Path

import pytest
import requests
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient

from _env_utils import (
    assert_safe_test_db,
    assert_valid_mongo_uri,
    get_test_mongo_config,
)


# ─── Backend URL (read once from frontend/.env, safely) ────────────────────
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
ADMIN_EMAIL = os.environ.get("REVENUE_TEST_ADMIN", "admin@ascendraacademy.com")
ADMIN_PW = os.environ.get("REVENUE_TEST_PW", "AscendraAdmin2026!")


# ─── JWT / headers fixtures ────────────────────────────────────────────────
@pytest.fixture(scope="module")
def jwt(isolated_env):
    """Bootstrap: since the backend is running against an empty isolated test
    DB, the admin account does not exist yet — create it, then log in."""
    signup = requests.post(
        f"{API}/auth/signup",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW, "name": "Test Admin"},
        timeout=10,
    )
    # 200 = created; 400/409 = already exists (rare on fresh DB but tolerated)
    assert signup.status_code in (200, 400, 409), (
        f"admin signup unexpected: {signup.status_code} {signup.text[:200]}"
    )

    login = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW},
        timeout=10,
    )
    assert login.status_code == 200, (
        f"admin login failed: {login.status_code} {login.text[:200]}"
    )
    token = login.json().get("token") or login.json().get("access_token")
    assert token, "no token in login response"

    # Promote to admin directly on the test DB (safe: guarded).
    mongo_url, test_db = get_test_mongo_config()
    assert_valid_mongo_uri(mongo_url)
    assert_safe_test_db(test_db)

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


# ─── Individual tests ──────────────────────────────────────────────────────
def test_system_state_defaults_safe(h):
    j = requests.get(f"{API}/admin/revenue/system/state", headers=h, timeout=10).json()
    assert j["live_actions_enabled"] is False
    assert j["safety_gate_env"] == "AUTOMATION_LIVE_ACTIONS_ENABLED"


def test_system_state_reports_accurate_phase(h):
    """Regression: after Phase 3 sign-off, the system-state endpoint reports
    phase_3 as current. Phase 4 must NOT be reported as complete yet."""
    j = requests.get(f"{API}/admin/revenue/system/state", headers=h, timeout=10).json()
    assert j.get("current_phase") == "phase_3", (
        f"current_phase should be 'phase_3', got {j.get('current_phase')!r}"
    )
    completed = j.get("completed_phases") or []
    assert set(completed) == {"phase_1", "phase_2", "phase_3"}
    # Phase 4 must NOT appear as complete
    assert "phase_4" not in completed, (
        "system_state reports Phase 4 complete before Phase 4 is delivered"
    )
    assert j.get("environment") == "preview"


def test_admin_gate_blocks_anon():
    r = requests.get(f"{API}/admin/revenue/summary", timeout=10)
    assert r.status_code in (401, 403)


def test_contact_dedup_and_normalized_email(h):
    email = f"phase1-{uuid.uuid4().hex[:8]}@test.ascendra.simulated"
    r1 = requests.post(
        f"{API}/admin/revenue/contacts",
        headers=h,
        json={"email": email, "simulated": True},
        timeout=10,
    )
    assert r1.status_code == 200 and r1.json()["duplicate"] is False
    r2 = requests.post(
        f"{API}/admin/revenue/contacts",
        headers=h,
        json={"email": email.upper(), "simulated": True},
        timeout=10,
    )
    assert r2.json()["duplicate"] is True


def test_event_idempotency(h):
    key = f"idem-{uuid.uuid4().hex}"
    body = {
        "event_type": "assessment.completed",
        "idempotency_key": key,
        "payload": {"score": 42},
        "simulated": True,
    }
    r1 = requests.post(f"{API}/admin/revenue/events", headers=h, json=body, timeout=10)
    r2 = requests.post(f"{API}/admin/revenue/events", headers=h, json=body, timeout=10)
    assert r1.json()["event"]["id"] == r2.json()["event"]["id"]
    assert r2.json()["duplicate"] is True


def test_approval_state_machine(h):
    r = requests.post(
        f"{API}/admin/revenue/approvals",
        headers=h,
        json={
            "request_type": "test.refund",
            "requested_action": "test",
            "reason": "hardening test",
            "risk_level": "low",
            "simulated": True,
        },
        timeout=10,
    )
    ap = r.json()["approval"]
    # pending → approved → completed (both valid transitions)
    assert requests.post(
        f"{API}/admin/revenue/approvals/{ap['id']}/decision",
        headers=h, json={"decision": "approved"}, timeout=10,
    ).status_code == 200
    assert requests.post(
        f"{API}/admin/revenue/approvals/{ap['id']}/decision",
        headers=h, json={"decision": "completed"}, timeout=10,
    ).status_code == 200
    # completed is a terminal state → any further decision must be rejected
    assert requests.post(
        f"{API}/admin/revenue/approvals/{ap['id']}/decision",
        headers=h, json={"decision": "approved"}, timeout=10,
    ).status_code == 400


def test_audit_log_no_mutation_routes(h):
    """HTTP layer: no DELETE / PUT / PATCH endpoints exist for audit entries."""
    entries = requests.get(
        f"{API}/admin/revenue/audit?limit=1", headers=h, timeout=10
    ).json()["entries"]
    assert entries, "expected at least one audit entry from prior tests"
    audit_id = entries[0]["id"]
    r_del = requests.delete(
        f"{API}/admin/revenue/audit/{audit_id}", headers=h, timeout=5
    )
    r_put = requests.put(
        f"{API}/admin/revenue/audit/{audit_id}", headers=h, json={}, timeout=5
    )
    r_patch = requests.patch(
        f"{API}/admin/revenue/audit/{audit_id}", headers=h, json={}, timeout=5
    )
    assert r_del.status_code in (404, 405)
    assert r_put.status_code in (404, 405)
    assert r_patch.status_code in (404, 405)


def test_audit_log_repository_has_no_write_methods():
    """Application layer: repository class exposes ONLY insert + read."""
    import sys
    sys.path.insert(0, "/app/backend")
    import revenue as rev

    repo_cls = rev.AuditLogRepository
    disallowed = {"update", "replace", "delete", "remove", "modify", "patch", "upsert"}
    methods = {
        name for name, _ in inspect.getmembers(repo_cls, predicate=inspect.isfunction)
    }
    leak = methods & disallowed
    assert not leak, (
        f"AuditLogRepository must not expose mutating methods, found: {leak}"
    )
    # Also verify the whitelist explicitly.
    allowed = {"__init__", "insert", "find", "count"}
    unexpected = methods - allowed
    assert not unexpected, (
        f"AuditLogRepository exposed an unexpected public method: {unexpected}"
    )


def test_integration_status_no_secrets_leaked(h):
    j = requests.get(f"{API}/admin/revenue/integrations", headers=h, timeout=10).json()
    import json as _json

    body = _json.dumps(j).lower()
    # Real credential values must never appear (only env-key names should)
    assert "sk_live_" not in body and "sk_test_" not in body
    assert "eyj" not in body  # JWT prefix — a real token would start with this
    assert "whsec_" not in body  # Stripe webhook secret prefix
    for i in j["integrations"]:
        assert i["state"] in {"live", "simulated", "unavailable"}


def test_budget_decimal128_storage_and_precision(h):
    """Exact Decimal round-trip + validation limits + BSON native storage."""
    note = f"pytest-budget-{uuid.uuid4().hex[:6]}"

    # (a) Exact two-decimal-place round-trip
    r = requests.post(
        f"{API}/admin/revenue/budget",
        headers=h,
        json={
            "monthly_budget_usd": "12345.67",
            "effective_date": "2026-04-01T00:00:00Z",
            "notes": note,
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["budget"]["monthly_budget_usd"] == "12345.67"

    # (b) Excess precision rejected
    bad = requests.post(
        f"{API}/admin/revenue/budget",
        headers=h,
        json={"monthly_budget_usd": "100.123", "effective_date": "2026-04-01T00:00:00Z"},
        timeout=10,
    )
    assert bad.status_code == 422

    # (c) Negative rejected
    neg = requests.post(
        f"{API}/admin/revenue/budget",
        headers=h,
        json={"monthly_budget_usd": "-5.00", "effective_date": "2026-04-01T00:00:00Z"},
        timeout=10,
    )
    assert neg.status_code == 422

    # (d) Non-decimal string rejected
    bad2 = requests.post(
        f"{API}/admin/revenue/budget",
        headers=h,
        json={"monthly_budget_usd": "abc", "effective_date": "2026-04-01T00:00:00Z"},
        timeout=10,
    )
    assert bad2.status_code == 422

    # (e) Upper bound enforced ($10,000,000)
    huge = requests.post(
        f"{API}/admin/revenue/budget",
        headers=h,
        json={
            "monthly_budget_usd": "20000000.00",
            "effective_date": "2026-04-01T00:00:00Z",
        },
        timeout=10,
    )
    assert huge.status_code == 422

    # (f) Verify native BSON Decimal128 storage — NOT float — round-trips exactly.
    mongo_url, test_db = get_test_mongo_config()

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        try:
            doc = await c[test_db]["operating_budget_history"].find_one({"notes": note})
            assert doc is not None, "budget record not persisted"
            assert isinstance(doc["monthly_budget_usd"], Decimal128), (
                f"budget must be Decimal128, got {type(doc['monthly_budget_usd']).__name__}"
            )
            # Exact round-trip: no float drift
            assert str(doc["monthly_budget_usd"].to_decimal()) == "12345.67"
        finally:
            c.close()

    asyncio.run(_check())


def test_organization_index_not_globally_unique():
    """`name_normalized` index must be searchable but NOT globally unique."""
    mongo_url, test_db = get_test_mongo_config()

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        try:
            d = c[test_db]
            idx = await d["organizations"].index_information()
            name_idx = None
            for spec in idx.values():
                keys = [k for k, _ in spec["key"]]
                if keys == ["name_normalized"]:
                    name_idx = spec
                    break
            assert name_idx is not None, "name_normalized index missing"
            assert not name_idx.get("unique", False), (
                "name_normalized must NOT be a unique index (multiple orgs may share names)"
            )
            # Prove two docs with same normalized name coexist.
            id1, id2 = str(uuid.uuid4()), str(uuid.uuid4())
            try:
                await d["organizations"].insert_one(
                    {"id": id1, "name_normalized": "acme corp", "_test": True}
                )
                await d["organizations"].insert_one(
                    {"id": id2, "name_normalized": "acme corp", "_test": True}
                )
                n = await d["organizations"].count_documents(
                    {"name_normalized": "acme corp", "_test": True}
                )
                assert n == 2, f"expected 2 orgs with same normalized name, got {n}"
            finally:
                assert_safe_test_db(test_db)  # last-line guard
                await d["organizations"].delete_many({"_test": True})
        finally:
            c.close()

    asyncio.run(_check())


def test_organization_index_stale_unique_is_migrated():
    """Regression: an older build shipped `name_normalized_1` as UNIQUE. The
    Phase 1 hardening pass added a self-healing migration in ensure_indexes()
    that drops + recreates the index as non-unique. This test simulates that
    stale state on the isolated test DB and confirms the migration runs."""
    import sys
    sys.path.insert(0, "/app/backend")
    from revenue import ensure_indexes

    mongo_url, test_db = get_test_mongo_config()

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        try:
            d = c[test_db]
            # Drop existing, then create as unique to simulate legacy state.
            assert_safe_test_db(test_db)
            try:
                await d["organizations"].drop_index("name_normalized_1")
            except Exception:
                pass  # Index may not exist yet
            await d["organizations"].create_index("name_normalized", unique=True)
            info = await d["organizations"].index_information()
            assert info["name_normalized_1"].get("unique") is True, (
                "test setup failed to create legacy unique index"
            )
            # Now invoke the production migration path.
            await ensure_indexes(d)
            info = await d["organizations"].index_information()
            assert info["name_normalized_1"].get("unique", False) is False, (
                "ensure_indexes() failed to migrate stale unique index → non-unique"
            )
        finally:
            c.close()

    asyncio.run(_check())


def test_target_db_is_isolated_test_db():
    """Sanity: the process is actually pointed at an isolated test DB, not the
    ordinary preview/dev database. This is what makes cleanup safe."""
    _, test_db = get_test_mongo_config()
    assert "test" in test_db.lower()
    for prod in ("prod", "production", "live"):
        assert prod not in test_db.lower(), (
            f"Refusing: DB name '{test_db}' contains production indicator '{prod}'"
        )


def test_safety_gate_env_default_is_false(h):
    """AUTOMATION_LIVE_ACTIONS_ENABLED must default to false, and the system
    state endpoint must reflect that. This guarantees no integration will
    perform a live external action."""
    j = requests.get(f"{API}/admin/revenue/system/state", headers=h, timeout=10).json()
    assert j["live_actions_enabled"] is False
    # And in the parent test process the same must hold — proves the swap did
    # not accidentally enable live actions.
    v = os.environ.get("AUTOMATION_LIVE_ACTIONS_ENABLED", "false").strip().lower()
    assert v != "true"


def test_no_credentials_logged_in_integrations(h):
    """Redaction sanity: raw env values must not appear in integration output."""
    j = requests.get(f"{API}/admin/revenue/integrations", headers=h, timeout=10).json()
    body = str(j)
    # Ensure any real secret pattern is absent (belt-and-braces alongside
    # test_integration_status_no_secrets_leaked, which uses a lowercased body).
    for pat in ("sk_live_", "sk_test_", "whsec_", "eyJ"):
        assert pat not in body, f"integration payload leaked pattern '{pat}'"
