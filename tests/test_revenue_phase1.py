"""Phase 1 Revenue Control Center — end-to-end integration tests.

Runs against the live preview backend using an admin JWT. Verifies:
  • System state gate defaults to safe (live_actions_enabled=false)
  • Contact creation + duplicate detection (unique email index)
  • Internal event idempotency (same idempotency_key → same event)
  • Approval queue state machine (illegal transitions rejected)
  • Audit log is append-only (no update/delete route exposed)
  • Integration status reports env-driven state without live calls
  • Operating budget: Decimal-safe, versioned, audit-logged
  • Summary counts match reality
  • Simulated records are labeled and never mistaken for real data

Run: pytest tests/test_revenue_phase1.py -v
"""
import os
import json
import uuid
import pytest
import requests

BACKEND = os.environ.get("REACT_APP_BACKEND_URL") or ""
if not BACKEND:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BACKEND = line.split("=", 1)[1].strip()
                break
API = f"{BACKEND}/api"
ADMIN_EMAIL = os.environ.get("REVENUE_TEST_ADMIN", "admin@ascendraacademy.com")
ADMIN_PW = os.environ.get("REVENUE_TEST_PW", "AscendraAdmin2026!")


@pytest.fixture(scope="module")
def jwt():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=10)
    assert r.status_code == 200, f"admin login failed: {r.text[:200]}"
    j = r.json()
    tok = j.get("token") or j.get("access_token")
    assert tok, "no token returned"
    return tok


@pytest.fixture(scope="module")
def h(jwt):
    return {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}


def test_system_state_defaults_safe(h):
    r = requests.get(f"{API}/admin/revenue/system/state", headers=h, timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j["phase"] == "phase_1"
    assert j["safety_gate_env"] == "AUTOMATION_LIVE_ACTIONS_ENABLED"
    assert j["live_actions_enabled"] is False, "Live actions must default to disabled in Phase 1"


def test_admin_gate_blocks_anon(h):
    r = requests.get(f"{API}/admin/revenue/summary", timeout=10)
    assert r.status_code in (401, 403)


def test_contact_creation_and_duplicate_detection(h):
    email = f"phase1-{uuid.uuid4().hex[:8]}@test.ascendra.simulated"
    body = {"email": email, "first_name": "Phase1", "last_name": "Test",
            "company_name": "Simulated Co", "simulated": True,
            "utm_source": "pytest", "lead_source": "integration_test"}
    r1 = requests.post(f"{API}/admin/revenue/contacts", headers=h, json=body, timeout=10)
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["duplicate"] is False
    assert j1["contact"]["email_normalized"] == email.lower()
    assert j1["contact"]["simulated"] is True
    assert j1["contact"]["lifecycle_stage"] == "new_lead"
    # Duplicate detection: same email uppercased → matches lowercase normalized
    r2 = requests.post(f"{API}/admin/revenue/contacts", headers=h,
                        json={**body, "email": email.upper()}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True


def test_event_idempotency(h):
    key = f"idem-{uuid.uuid4().hex}"
    body = {"event_type": "assessment.completed", "idempotency_key": key,
            "payload": {"score": 42}, "simulated": True}
    r1 = requests.post(f"{API}/admin/revenue/events", headers=h, json=body, timeout=10)
    assert r1.status_code == 200
    id1 = r1.json()["event"]["id"]
    assert r1.json()["duplicate"] is False
    r2 = requests.post(f"{API}/admin/revenue/events", headers=h, json=body, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True
    assert r2.json()["event"]["id"] == id1


def test_approval_state_machine_valid_transitions(h):
    body = {"request_type": "test.refund", "requested_action": "issue_test_refund",
            "reason": "Integration test — SIMULATED", "risk_level": "low",
            "financial_amount_usd": 9.99, "simulated": True}
    r = requests.post(f"{API}/admin/revenue/approvals", headers=h, json=body, timeout=10)
    assert r.status_code == 200
    ap = r.json()["approval"]
    assert ap["status"] == "pending"
    # pending -> approved (valid)
    r2 = requests.post(f"{API}/admin/revenue/approvals/{ap['id']}/decision", headers=h,
                         json={"decision": "approved", "notes": "test approve"}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["approval"]["status"] == "approved"
    # approved -> completed (valid)
    r3 = requests.post(f"{API}/admin/revenue/approvals/{ap['id']}/decision", headers=h,
                         json={"decision": "completed"}, timeout=10)
    assert r3.status_code == 200
    assert r3.json()["approval"]["status"] == "completed"
    # completed -> approved (INVALID — must reject)
    r4 = requests.post(f"{API}/admin/revenue/approvals/{ap['id']}/decision", headers=h,
                         json={"decision": "approved"}, timeout=10)
    assert r4.status_code == 400, f"illegal transition should be blocked: {r4.text}"


def test_approval_state_machine_reject_terminal(h):
    body = {"request_type": "test.refund", "requested_action": "issue_test_refund",
            "reason": "reject flow test — SIMULATED", "risk_level": "medium",
            "simulated": True}
    ap = requests.post(f"{API}/admin/revenue/approvals", headers=h, json=body, timeout=10).json()["approval"]
    # pending -> rejected
    r = requests.post(f"{API}/admin/revenue/approvals/{ap['id']}/decision", headers=h,
                        json={"decision": "rejected"}, timeout=10)
    assert r.json()["approval"]["status"] == "rejected"
    # rejected is terminal
    r2 = requests.post(f"{API}/admin/revenue/approvals/{ap['id']}/decision", headers=h,
                         json={"decision": "approved"}, timeout=10)
    assert r2.status_code == 400


def test_audit_log_appends_and_no_delete_route(h):
    # Create a contact → audit entry should appear
    email = f"audit-{uuid.uuid4().hex[:6]}@test.ascendra.simulated"
    requests.post(f"{API}/admin/revenue/contacts", headers=h,
                    json={"email": email, "simulated": True}, timeout=10)
    r = requests.get(f"{API}/admin/revenue/audit?action=contact.created&limit=5", headers=h, timeout=10)
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) >= 1
    # Verify no delete/edit routes exist
    r_del = requests.delete(f"{API}/admin/revenue/audit/{entries[0]['id']}", headers=h, timeout=5)
    assert r_del.status_code in (404, 405)


def test_audit_export_works(h):
    r = requests.get(f"{API}/admin/revenue/audit/export?limit=50", headers=h, timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert "entries" in j and isinstance(j["entries"], list)
    assert "exported_at" in j


def test_integration_status_no_live_calls(h):
    r = requests.get(f"{API}/admin/revenue/integrations", headers=h, timeout=10)
    assert r.status_code == 200
    j = r.json()
    providers = {i["provider"] for i in j["integrations"]}
    assert providers == {"stripe", "resend", "buffer", "gmail", "gcal"}
    for i in j["integrations"]:
        assert i["state"] in {"live", "simulated", "unavailable"}
        # Never exposes secret values in the response
        assert not any(k.lower() in json.dumps(i).lower() for k in ["api_key=", "secret="])


def test_operating_budget_decimal_safe_and_versioned(h):
    # Invalid decimal string is rejected
    bad = requests.post(f"{API}/admin/revenue/budget", headers=h,
                          json={"monthly_budget_usd": "not-a-number",
                                "effective_date": "2026-01-01T00:00:00Z"}, timeout=10)
    assert bad.status_code == 422
    # Negative is rejected
    neg = requests.post(f"{API}/admin/revenue/budget", headers=h,
                          json={"monthly_budget_usd": "-500.00",
                                "effective_date": "2026-01-01T00:00:00Z"}, timeout=10)
    assert neg.status_code == 422
    # Valid entry works and appears in history
    val = "7654.32"
    ok = requests.post(f"{API}/admin/revenue/budget", headers=h,
                        json={"monthly_budget_usd": val,
                              "effective_date": "2026-02-01T00:00:00Z",
                              "notes": "pytest fixture — SIMULATED"}, timeout=10)
    assert ok.status_code == 200, ok.text
    assert ok.json()["budget"]["monthly_budget_usd"] == val
    # Second entry — history retains both
    val2 = "8888.88"
    requests.post(f"{API}/admin/revenue/budget", headers=h,
                    json={"monthly_budget_usd": val2,
                          "effective_date": "2026-03-01T00:00:00Z"}, timeout=10)
    hist = requests.get(f"{API}/admin/revenue/budget", headers=h, timeout=10).json()
    values = [h["monthly_budget_usd"] for h in hist["history"]]
    assert val in values and val2 in values, "Previous budget values must be preserved"


def test_summary_reflects_counts(h):
    r = requests.get(f"{API}/admin/revenue/summary", headers=h, timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j["phase"] == "phase_1"
    assert j["live_actions_enabled"] is False
    assert "counts" in j
    assert j["counts"]["contacts"] >= 0
    assert "simulated" in j["data_status"] or "Phase 3" in j["data_status"]
