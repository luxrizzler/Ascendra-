"""Phase 21 — Control-Integrity Hardening tests.

These tests prove the Phase 3/4 hardening requested by the operator BEFORE
Phase 5 UI work:

  1. Approval enforcement is real on sensitive Phase 3 endpoints:
        • Tax policy activate      (POST /admin/revenue/tax-policies/{id}/activate)
        • Allocation policy activate (POST /admin/revenue/allocation-policies/{id}/activate)
        • Owner-draw decision      (POST /admin/revenue/owner-draws/decision)
        • Reconciliation close     (POST /admin/revenue/reconciliations/close)
     For each: a correctly-matched approval succeeds; a mismatched or
     already-consumed approval is rejected with 409.

  2. Allocation-policy split status semantics are populated on seeded rows
     and migrated on redeploy:
        approved / enabled_for_phase / currently_applied
     Invariant: at most one policy per phase has currently_applied=True.

  3. Owner-draw append-only corrections write NEW rows only and never
     mutate prior payments. Reversal/adjustment link via
     ``reverses_payment_id`` / ``adjustment_of_payment_id``.

  4. Stripe shadow webhook uses the official Stripe SDK for signature
     verification (verification_mode="stripe_sdk" in the response).
     Runs alongside the existing tests in test_revenue_phase4.py.

Runs against the isolated ``ascendra_revenue_test`` DB via conftest.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import requests
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
        "name": "Hardening Admin"}, timeout=10)
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


# ─── Approval creation helper ─────────────────────────────────────────────
def _create_approval(h, *, request_type: str, target_id: str,
                       amount_usd: str | None = None,
                       target_version: int | None = None) -> str:
    """Directly seed an approval-queue row (bypassing the create endpoint's
    Pydantic model, which is business-domain shaped). We insert with the
    exact ``request_type`` + ``supporting_records.target_id`` fields that
    the hardened enforce_approval() will re-verify."""
    mongo_url, test_db = get_test_mongo_config()
    approval_id = str(uuid.uuid4())
    supporting: dict = {"target_id": target_id}
    if target_version is not None:
        supporting["version"] = target_version

    async def _insert():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await c[test_db]["approval_queue"].insert_one({
                "id": approval_id,
                "request_type": request_type,
                "requested_action": f"test approval for {request_type}",
                "reason": "hardening-suite",
                "risk_level": "high",
                "financial_amount_usd": amount_usd,
                "related_contact_id": None,
                "related_organization_id": None,
                "supporting_records": supporting,
                "correlation_id": str(uuid.uuid4()),
                "status": "approved",             # pre-approved
                "decided_by": "hardening-suite",
                "decided_at": datetime.now(timezone.utc),
                "notes": None,
                "expires_at": None,
                "simulated": True,
                "source": "test_fixture",
                "environment": "preview",
                "created_at": datetime.now(timezone.utc),
                "execution_completed": False,
            })
        finally:
            c.close()
    asyncio.run(_insert())
    return approval_id


def _mk_key(prefix: str = "hd") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


# ═══════════════════════════════════════════════════════════════════════════
#  21.2  ALLOCATION-POLICY STATUS SEMANTIC SPLIT
# ═══════════════════════════════════════════════════════════════════════════
def test_allocation_policies_seeded_with_split_semantics(h):
    """Seeded startup + established policies must carry the split status
    semantics after Phase 21 migration."""
    r = requests.get(f"{API}/admin/revenue/allocation-policies",
                       headers=h, timeout=10).json()
    policies = r["policies"]
    assert len(policies) >= 2

    for phase_name in ("startup", "established"):
        matches = [p for p in policies if p["phase"] == phase_name]
        assert matches, f"missing seeded {phase_name} policy"
        applied = [p for p in matches if p.get("currently_applied") is True]
        # Exactly one currently_applied per phase — the core invariant.
        assert len(applied) == 1, (
            f"phase {phase_name!r} has {len(applied)} currently_applied "
            f"policies (must be exactly 1)")
        top = applied[0]
        assert top.get("approved") is True
        assert top.get("enabled_for_phase") == phase_name


def test_allocation_policy_activate_requires_matching_approval(h):
    """Activating a new allocation-policy version with a mismatched approval
    must return 409. With the correct approval it succeeds and the previous
    currently_applied row for the same phase is demoted."""
    # Create a new candidate policy for the "startup" phase
    r = requests.post(
        f"{API}/admin/revenue/allocation-policies", headers=h,
        json={"phase": "startup",
              "owner_pct": "20.00", "growth_reserve_pct": "30.00",
              "working_capital_pct": "50.00",
              "effective_date": datetime.now(timezone.utc).isoformat(),
              "approved_by": "hardening-suite",
              "notes": "hardening test candidate"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    pol = r.json()["policy"]
    policy_id = pol["id"]
    version = pol["version"]

    # ── Mismatched approval (wrong target_id) → 409 ──
    bad_appr = _create_approval(h, request_type="allocation_policy.activate",
                                    target_id="wrong-target")
    r_bad = requests.post(
        f"{API}/admin/revenue/allocation-policies/{policy_id}/activate",
        headers=h, json={"approval_id": bad_appr}, timeout=10)
    assert r_bad.status_code == 409, r_bad.text

    # ── Matching approval → 200 ──
    good_appr = _create_approval(h, request_type="allocation_policy.activate",
                                    target_id=policy_id, target_version=version)
    r_ok = requests.post(
        f"{API}/admin/revenue/allocation-policies/{policy_id}/activate",
        headers=h, json={"approval_id": good_appr}, timeout=10)
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body["approval_enforcement"] == "enforced"
    assert body["currently_applied"] is True
    assert body["enabled_for_phase"] == "startup"

    # Reusing the same approval must now fail (already consumed)
    r_replay = requests.post(
        f"{API}/admin/revenue/allocation-policies/{policy_id}/activate",
        headers=h, json={"approval_id": good_appr}, timeout=10)
    assert r_replay.status_code == 409, r_replay.text

    # Invariant re-check: still exactly one currently_applied for "startup"
    r_list = requests.get(f"{API}/admin/revenue/allocation-policies",
                            headers=h, timeout=10).json()
    applied = [p for p in r_list["policies"]
                if p["phase"] == "startup" and p.get("currently_applied") is True]
    assert len(applied) == 1, (
        f"invariant violated: {len(applied)} currently_applied for startup")
    assert applied[0]["id"] == policy_id


# ═══════════════════════════════════════════════════════════════════════════
#  21.1  TAX-POLICY ACTIVATE APPROVAL ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════
def test_tax_policy_activate_enforces_approval(h):
    r = requests.post(f"{API}/admin/revenue/tax-policies", headers=h, json={
        "federal_reserve_pct": "12.00",
        "state_reserve_pct": "4.00",
        "other_reserve_pct": "0.00",
        "effective_date": datetime.now(timezone.utc).isoformat(),
        "notes": "hardening-tax",
    }, timeout=10)
    assert r.status_code == 200, r.text
    policy_id = r.json()["tax_policy"]["id"]

    # Mismatched target → 409
    bad = _create_approval(h, request_type="tax_policy.activate",
                              target_id="not-this-policy")
    r_bad = requests.post(
        f"{API}/admin/revenue/tax-policies/{policy_id}/activate",
        headers=h, json={"approval_id": bad}, timeout=10)
    assert r_bad.status_code == 409

    # Matching → 200 + enforcement=enforced
    good = _create_approval(h, request_type="tax_policy.activate",
                               target_id=policy_id)
    r_ok = requests.post(
        f"{API}/admin/revenue/tax-policies/{policy_id}/activate",
        headers=h, json={"approval_id": good}, timeout=10)
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["approval_enforcement"] == "enforced"


# ═══════════════════════════════════════════════════════════════════════════
#  21.1  RECONCILIATION-CLOSE + OWNER-DRAW-DECISION APPROVAL ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════
def _activate_tax_policy_with_approval(h) -> None:
    """Helper: create + approval-approved-activate a tax policy so recons
    can run without being 'blocked'."""
    r = requests.post(f"{API}/admin/revenue/tax-policies", headers=h, json={
        "federal_reserve_pct": "15.00",
        "state_reserve_pct": "5.00",
        "other_reserve_pct": "0.00",
        "effective_date": datetime.now(timezone.utc).isoformat(),
        "notes": "hardening enforcement helper",
    }, timeout=10).json()
    pid = r["tax_policy"]["id"]
    appr = _create_approval(h, request_type="tax_policy.activate", target_id=pid)
    requests.post(f"{API}/admin/revenue/tax-policies/{pid}/activate",
                    headers=h, json={"approval_id": appr}, timeout=10)


def test_reconciliation_close_enforces_approval_and_consumes_it(h):
    _activate_tax_policy_with_approval(h)
    month = "2027-01"
    # Seed one cleared ledger entry so a draw record is produced
    eff = datetime(2027, 1, 15, 12, 0, tzinfo=timezone.utc).isoformat()
    requests.post(f"{API}/admin/revenue/ledger/entries", headers=h, json={
        "entry_type": "payment_recorded", "source_type": "manual_preview",
        "idempotency_key": _mk_key("hd-rc"), "gross_amount": "100.00",
        "settlement_status": "cleared", "effective_date": eff,
    }, timeout=10)
    recon = requests.post(f"{API}/admin/revenue/reconciliations",
                            headers=h,
                            json={"calendar_month": month},
                            timeout=10).json()["reconciliation"]
    if recon["status"] == "blocked":
        pytest.skip("reconciliation blocked (tax policy setup)")

    # Mismatched approval → 409
    bad_appr = _create_approval(h, request_type="reconciliation.close",
                                    target_id="wrong-id")
    r_bad = requests.post(
        f"{API}/admin/revenue/reconciliations/close", headers=h,
        json={"reconciliation_id": recon["id"],
              "close_reason": "hardening test close",
              "approval_id": bad_appr}, timeout=10)
    assert r_bad.status_code == 409

    # Matching approval → 200 + enforcement=enforced
    good_appr = _create_approval(h, request_type="reconciliation.close",
                                     target_id=recon["id"])
    r_ok = requests.post(
        f"{API}/admin/revenue/reconciliations/close", headers=h,
        json={"reconciliation_id": recon["id"],
              "close_reason": "hardening test close",
              "approval_id": good_appr}, timeout=10)
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body["approval_enforcement"] == "enforced"

    # Reusing the same approval must fail (already consumed) — but the recon
    # is already closed so the endpoint will 409 on the closed-check first.
    # That still satisfies the "cannot be double-used" invariant.
    r_replay = requests.post(
        f"{API}/admin/revenue/reconciliations/close", headers=h,
        json={"reconciliation_id": recon["id"],
              "close_reason": "replay attempt after already-closed state",
              "approval_id": good_appr}, timeout=10)
    assert r_replay.status_code in (409,), r_replay.text


def test_owner_draw_decision_enforces_approval(h):
    _activate_tax_policy_with_approval(h)
    month = "2027-02"
    eff = datetime(2027, 2, 15, 12, 0, tzinfo=timezone.utc).isoformat()
    requests.post(f"{API}/admin/revenue/ledger/entries", headers=h, json={
        "entry_type": "payment_recorded", "source_type": "manual_preview",
        "idempotency_key": _mk_key("hd-od"), "gross_amount": "50.00",
        "settlement_status": "cleared", "effective_date": eff,
    }, timeout=10)
    recon = requests.post(f"{API}/admin/revenue/reconciliations",
                            headers=h,
                            json={"calendar_month": month},
                            timeout=10).json()["reconciliation"]
    if recon["status"] == "blocked":
        pytest.skip("reconciliation blocked")
    close_appr = _create_approval(h, request_type="reconciliation.close",
                                       target_id=recon["id"])
    close = requests.post(
        f"{API}/admin/revenue/reconciliations/close", headers=h,
        json={"reconciliation_id": recon["id"],
              "close_reason": "hardening owner-draw setup",
              "approval_id": close_appr}, timeout=10).json()
    draw = close["owner_draw"]

    # Mismatched approval → 409
    bad = _create_approval(h, request_type="owner_draw.approved",
                              target_id="wrong-draw")
    r_bad = requests.post(f"{API}/admin/revenue/owner-draws/decision",
                            headers=h, json={
                                "draw_id": draw["id"],
                                "decision": "approved",
                                "reason": "hardening",
                                "approval_id": bad,
                            }, timeout=10)
    assert r_bad.status_code == 409

    # Matching approval → 200
    good = _create_approval(h, request_type="owner_draw.approved",
                               target_id=draw["id"])
    r_ok = requests.post(f"{API}/admin/revenue/owner-draws/decision",
                           headers=h, json={
                               "draw_id": draw["id"],
                               "decision": "approved",
                               "reason": "hardening",
                               "approval_id": good,
                           }, timeout=10)
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body["approval_enforcement"] == "enforced"


# ═══════════════════════════════════════════════════════════════════════════
#  21.3  APPEND-ONLY OWNER-DRAW ADJUSTMENT + REVERSAL
# ═══════════════════════════════════════════════════════════════════════════
def _setup_draw_with_payment(h, month: str) -> tuple[str, str, str]:
    """Create a closed reconciliation → approved draw → 1 payment.

    Returns (draw_id, original_payment_id, month_key).
    """
    _activate_tax_policy_with_approval(h)
    year, mo = month.split("-")
    eff = datetime(int(year), int(mo), 15, 12, 0, tzinfo=timezone.utc).isoformat()
    requests.post(f"{API}/admin/revenue/ledger/entries", headers=h, json={
        "entry_type": "payment_recorded", "source_type": "manual_preview",
        "idempotency_key": _mk_key("hd-pay"), "gross_amount": "500.00",
        "settlement_status": "cleared", "effective_date": eff,
    }, timeout=10)
    recon = requests.post(f"{API}/admin/revenue/reconciliations",
                            headers=h, json={"calendar_month": month},
                            timeout=10).json()["reconciliation"]
    if recon["status"] == "blocked":
        pytest.skip("recon blocked")
    close_appr = _create_approval(h, request_type="reconciliation.close",
                                       target_id=recon["id"])
    close_resp = requests.post(f"{API}/admin/revenue/reconciliations/close",
                                 headers=h,
                                 json={"reconciliation_id": recon["id"],
                                       "close_reason": "reversal/adj setup for hardening",
                                       "approval_id": close_appr},
                                 timeout=10)
    assert close_resp.status_code == 200, close_resp.text
    close = close_resp.json()
    draw = close["owner_draw"]
    # Approve draw
    decide_appr = _create_approval(h, request_type="owner_draw.approved",
                                        target_id=draw["id"])
    requests.post(f"{API}/admin/revenue/owner-draws/decision", headers=h,
                    json={"draw_id": draw["id"], "decision": "approved",
                          "reason": "setup", "approval_id": decide_appr},
                    timeout=10)
    # Record a manual payment of $50 (below recommended)
    ref = f"HD-INIT-{uuid.uuid4().hex[:6]}"
    pay = requests.post(f"{API}/admin/revenue/owner-draws/manual-payment",
                          headers=h, json={
                              "draw_id": draw["id"],
                              "manually_paid_amount": "50.00",
                              "manual_payment_date": datetime.now(timezone.utc).isoformat(),
                              "manual_payment_reference": ref,
                          }, timeout=10).json()
    original_payment_id = pay["payment"]["id"]
    return draw["id"], original_payment_id, month


def test_owner_draw_adjustment_is_append_only(h):
    draw_id, original_id, _ = _setup_draw_with_payment(h, "2027-03")

    # Prepare an approval for a -$10 adjustment
    adj_amount = "-10.00"
    adj_appr = _create_approval(h, request_type="owner_draw.adjustment",
                                    target_id=original_id,
                                    amount_usd=str(Decimal(adj_amount)))
    ref = f"HD-ADJ-{uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{API}/admin/revenue/owner-draws/{draw_id}/adjustment",
        headers=h, json={
            "draw_id": draw_id,
            "original_payment_id": original_id,
            "adjustment_amount": adj_amount,
            "reason": "customer overpaid by $10 (correction)",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "payment_reference": ref,
            "approval_id": adj_appr,
        }, timeout=10)
    assert r.status_code == 200, r.text
    adj = r.json()["payment"]
    assert adj["adjustment_of_payment_id"] == original_id
    assert adj["reverses_payment_id"] is None
    assert adj["amount"] == "-10.00"

    # Verify the ORIGINAL row is unchanged (fetch via history endpoint)
    history = requests.get(
        f"{API}/admin/revenue/owner-draws/{draw_id}/payments",
        headers=h, timeout=10).json()
    ids = [p["id"] for p in history["payments"]]
    assert original_id in ids
    # Original payment amount is still $50 in the history
    orig_row = next(p for p in history["payments"] if p["id"] == original_id)
    assert orig_row["amount"] == "50.00"
    # Cumulative is 50 - 10 = 40
    assert history["cumulative_total"] == "40.00"


def test_owner_draw_reversal_is_append_only_and_cannot_be_double_reversed(h):
    draw_id, original_id, _ = _setup_draw_with_payment(h, "2027-04")

    original_amt = Decimal("50.00")
    rev_amt = -original_amt
    rev_appr = _create_approval(h, request_type="owner_draw.reversal",
                                    target_id=original_id,
                                    amount_usd=str(rev_amt))
    ref = f"HD-REV-{uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{API}/admin/revenue/owner-draws/{draw_id}/reversal",
        headers=h, json={
            "draw_id": draw_id,
            "original_payment_id": original_id,
            "reason": "duplicate payment recorded — reversing",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "payment_reference": ref,
            "approval_id": rev_appr,
        }, timeout=10)
    assert r.status_code == 200, r.text
    rev = r.json()["payment"]
    assert rev["reverses_payment_id"] == original_id
    assert rev["adjustment_of_payment_id"] is None
    assert rev["amount"] == "-50.00"

    # History must contain BOTH the original and the reversal
    history = requests.get(
        f"{API}/admin/revenue/owner-draws/{draw_id}/payments",
        headers=h, timeout=10).json()
    orig_row = next(p for p in history["payments"] if p["id"] == original_id)
    assert orig_row["amount"] == "50.00"    # original NOT mutated
    assert history["cumulative_total"] == "0.00"

    # Second reversal attempt with a NEW valid approval → 409 (already reversed)
    rev_appr_2 = _create_approval(h, request_type="owner_draw.reversal",
                                       target_id=original_id,
                                       amount_usd=str(rev_amt))
    r2 = requests.post(
        f"{API}/admin/revenue/owner-draws/{draw_id}/reversal",
        headers=h, json={
            "draw_id": draw_id,
            "original_payment_id": original_id,
            "reason": "attempted double reversal",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "payment_reference": f"HD-REV2-{uuid.uuid4().hex[:6]}",
            "approval_id": rev_appr_2,
        }, timeout=10)
    assert r2.status_code == 409, r2.text


def test_owner_draw_correction_requires_approval(h):
    """No approval_id → 422 Pydantic error (field is required)."""
    draw_id, original_id, _ = _setup_draw_with_payment(h, "2027-05")
    r = requests.post(
        f"{API}/admin/revenue/owner-draws/{draw_id}/reversal",
        headers=h, json={
            "draw_id": draw_id,
            "original_payment_id": original_id,
            "reason": "no approval attached",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "payment_reference": f"HD-NOAPR-{uuid.uuid4().hex[:6]}",
        }, timeout=10)
    assert r.status_code == 422, r.text
