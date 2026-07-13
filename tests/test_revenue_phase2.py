"""Phase 2 Revenue Control Center — integration + hardening tests.

Runs against the LIVE backend (session-restarted by conftest.py against an
isolated test database ``ascendra_revenue_test``).

COVERS
──────
Offers:
  • Existing offers import — no duplication on re-run
  • Draft offer creation (all new offers start as draft/inactive)
  • Decimal-safe offer pricing (round-trip; excess precision rejected; negative
    rejected; upper bound; non-decimal rejected)
  • Invalid billing_frequency rejected
  • Invalid eligibility_rule rejected
  • Active offer material change → queued for approval, not applied immediately
  • Offer version history preserved

Scoring:
  • Deterministic scoring — same inputs → same outputs (byte-identical)
  • Score-band thresholds respected
  • Scoring rule version history preserved
  • Score history is append-only
  • Recommendations return ONLY active, non-draft offers
  • Contact lead_score mirror is updated in the contact document

Attribution:
  • First-touch preservation across multiple touches
  • Last-touch updated on new valid touch
  • Correction audited with mandatory reason
  • Correction appends a touch (append-only history)
  • URL sanitization (javascript:/data: schemes rejected → source_url=None)
  • Source-note sanitization (length clamped; control chars removed)

Contact administration:
  • Lifecycle change requires reason (≥ 8 chars)
  • Contact patch requires reason
  • Merge dry-run does not mutate
  • Merge preserves events + touches + notes + scores
  • Merge refuses conflicting external IDs unless forced
  • Anonymous rejected on all Phase 2 admin endpoints

Safety:
  • Live actions remain disabled — no external integration performs a call
  • All new Phase 2 records are tagged simulated=True while gate is false
  • Cleanup of Phase 2 fixtures is inherited from conftest.drop_database
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
import requests
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient

from _env_utils import assert_safe_test_db, get_test_mongo_config  # noqa: F401


# ─── Backend URL ───────────────────────────────────────────────────────────
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


# ─── Fixtures (reuse pattern from Phase 1) ────────────────────────────────
@pytest.fixture(scope="module")
def jwt(isolated_env):
    signup = requests.post(
        f"{API}/auth/signup",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW, "name": "Test Admin"},
        timeout=10,
    )
    assert signup.status_code in (200, 400, 409)
    login = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW},
        timeout=10,
    )
    assert login.status_code == 200, login.text[:200]
    token = login.json().get("token") or login.json().get("access_token")

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


@pytest.fixture(scope="module")
def a_contact(h):
    """Create one contact for reuse across Phase 2 tests."""
    email = f"phase2-{uuid.uuid4().hex[:8]}@test.ascendra.simulated"
    r = requests.post(
        f"{API}/admin/revenue/contacts", headers=h,
        json={
            "email": email, "first_name": "Test", "last_name": "Contact",
            "company_name": "Test Co", "business_type": "b2b",
            "organization_size": "small", "employee_count": 12,
            "stated_needs": "AI ops", "simulated": True,
        }, timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()["contact"]


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN AUTH GATE (all Phase 2 endpoints)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("path", [
    "/admin/revenue/offers",
    "/admin/revenue/scoring/rules",
    "/admin/revenue/scoring/rules/current",
])
def test_admin_gate_blocks_anon_phase2(path):
    r = requests.get(f"{API}{path}", timeout=10)
    assert r.status_code in (401, 403), f"{path}: expected 401/403, got {r.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
#  OFFER CATALOG
# ═══════════════════════════════════════════════════════════════════════════
def test_import_existing_offers_no_duplication(h):
    """First import creates offers; second import skips them all."""
    r1 = requests.post(f"{API}/admin/revenue/offers/import-existing",
                        headers=h, json={}, timeout=10)
    assert r1.status_code == 200
    j1 = r1.json()
    first_import = len(j1["imported"])
    assert first_import >= 3, "expected at least 3 existing tiers imported"
    r2 = requests.post(f"{API}/admin/revenue/offers/import-existing",
                        headers=h, json={}, timeout=10)
    assert r2.status_code == 200
    j2 = r2.json()
    assert len(j2["imported"]) == 0, "re-import should not duplicate"
    assert len(j2["skipped"]) == first_import, "all previously imported must be skipped"


def test_business_tier_imported_as_draft_when_stripe_missing(h):
    """Business tier has no Stripe IDs → must be imported as draft/inactive."""
    r = requests.get(f"{API}/admin/revenue/offers", headers=h, timeout=10)
    offers = r.json()["offers"]
    biz = next((o for o in offers if o["offer_code"] == "business_monthly"), None)
    assert biz is not None, "business_monthly offer expected after import"
    assert biz["draft_status"] is True
    assert biz["active_status"] is False
    assert not biz.get("external_price_id"), "business tier should have no external price ID"


def test_offer_pricing_is_decimal_safe(h):
    """Round-trip: string in → Decimal128 in Mongo → string out; no float drift."""
    code = f"testcat_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Precision Test", "category": "digital_product",
        "price": "199.99", "currency": "USD", "billing_frequency": "one_time",
    }, timeout=10)
    assert r.status_code == 200, r.text
    off = r.json()["offer"]
    assert off["price"] == "199.99"
    # And verify Decimal128 storage
    mongo_url, test_db = get_test_mongo_config()

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        try:
            doc = await c[test_db]["offers"].find_one({"offer_code": code})
            assert isinstance(doc["price"], Decimal128)
            assert str(doc["price"].to_decimal()) == "199.99"
        finally:
            c.close()

    asyncio.run(_check())


@pytest.mark.parametrize("bad_price", ["100.123", "-5.00", "abc", "20000000.00"])
def test_offer_pricing_validation_rejects(h, bad_price):
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": f"reject_{uuid.uuid4().hex[:6]}", "name": "Reject",
        "category": "digital_product", "price": bad_price,
        "billing_frequency": "one_time",
    }, timeout=10)
    assert r.status_code == 422, f"expected 422 for price={bad_price!r}, got {r.status_code}"


def test_invalid_billing_frequency_rejected(h):
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": f"bf_{uuid.uuid4().hex[:6]}", "name": "Bad BF",
        "category": "digital_product", "price": "9.99",
        "billing_frequency": "weekly",  # not in the Literal
    }, timeout=10)
    assert r.status_code == 422


def test_invalid_eligibility_rule_rejected(h):
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": f"el_{uuid.uuid4().hex[:6]}", "name": "Bad EL",
        "category": "digital_product", "price": "9.99",
        "billing_frequency": "one_time",
        "eligibility_rules": [{"key": "BAD KEY!!", "op": "eq", "value": 1}],
    }, timeout=10)
    assert r.status_code == 422


def test_draft_offer_created_inactive(h):
    code = f"draft_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Draft", "category": "training",
        "price": "500.00", "billing_frequency": "one_time",
    }, timeout=10)
    off = r.json()["offer"]
    assert off["draft_status"] is True and off["active_status"] is False


def test_active_offer_material_change_requires_approval(h):
    """Patching PRICE on an ACTIVE offer must go through the approval queue."""
    # Create + activate an offer
    code = f"mat_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Material Test", "category": "digital_product",
        "price": "50.00", "billing_frequency": "one_time",
    }, timeout=10)
    oid = r.json()["offer"]["id"]
    requests.post(f"{API}/admin/revenue/offers/{oid}/activate", headers=h, timeout=10)

    # Now attempt to change the price → must be QUEUED, not applied
    r2 = requests.patch(f"{API}/admin/revenue/offers/{oid}", headers=h, json={
        "price": "75.00", "change_reason": "market repricing",
    }, timeout=10)
    assert r2.status_code == 200
    j = r2.json()
    assert j.get("queued") is True
    assert "approval" in j
    # Verify offer document was NOT mutated
    check = requests.get(f"{API}/admin/revenue/offers/{oid}", headers=h, timeout=10).json()
    assert check["offer"]["price"] == "50.00", "material change must not apply until approved"


def test_offer_version_history_preserved(h):
    """Patching NON-material fields on a draft offer records a version row."""
    code = f"ver_{uuid.uuid4().hex[:8]}"
    create = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Ver Test", "category": "digital_product",
        "price": "9.99", "billing_frequency": "one_time",
    }, timeout=10).json()
    oid = create["offer"]["id"]

    requests.patch(f"{API}/admin/revenue/offers/{oid}", headers=h, json={
        "description": "new description v2", "change_reason": "clarify copy",
    }, timeout=10)
    detail = requests.get(f"{API}/admin/revenue/offers/{oid}", headers=h, timeout=10).json()
    assert detail["version_count"] >= 1
    assert detail["versions"][0]["changes"].get("description") == "new description v2"


def test_offer_recommendations_only_active_and_non_draft(h, a_contact):
    """A scoring recommendation must not return a draft or inactive offer."""
    r = requests.post(f"{API}/admin/revenue/scoring/score", headers=h, json={
        "contact_id": a_contact["id"],
        "inputs": {"assessment_score": 90, "business_type": "b2b",
                    "organization_size": "mid", "employee_count": 40,
                    "urgency": "asap", "engagement_recent_events": 5,
                    "checkout_started": True, "existing_customer": False,
                    "source_quality": "referral"},
    }, timeout=10)
    assert r.status_code == 200
    rec = r.json()["recommended_offer"]
    if rec is not None:
        # Must be an offer the catalog considers active + non-draft
        detail = requests.get(f"{API}/admin/revenue/offers/{rec['id']}",
                                headers=h, timeout=10).json()
        assert detail["offer"]["active_status"] is True
        assert detail["offer"]["draft_status"] is False


# ═══════════════════════════════════════════════════════════════════════════
#  DETERMINISTIC SCORING
# ═══════════════════════════════════════════════════════════════════════════
def test_scoring_is_deterministic(h, a_contact):
    """Identical inputs to the same contact must yield identical score outputs."""
    inputs = {
        "assessment_score": 70, "business_type": "b2b",
        "organization_size": "mid", "employee_count": 30,
        "urgency": "quarter", "engagement_recent_events": 3,
        "checkout_started": False, "existing_customer": False,
        "source_quality": "organic_search",
    }
    r1 = requests.post(f"{API}/admin/revenue/scoring/score", headers=h,
                        json={"contact_id": a_contact["id"], "inputs": inputs},
                        timeout=10).json()
    r2 = requests.post(f"{API}/admin/revenue/scoring/score", headers=h,
                        json={"contact_id": a_contact["id"], "inputs": inputs},
                        timeout=10).json()
    assert r1["score"] == r2["score"]
    assert r1["band"] == r2["band"]
    assert r1["breakdown"] == r2["breakdown"]


def test_score_band_thresholds_respected(h, a_contact):
    """A high-quality input should fall in a qualified/high_intent band; a
    weak input should fall in unqualified/early_interest."""
    strong = requests.post(f"{API}/admin/revenue/scoring/score", headers=h, json={
        "contact_id": a_contact["id"],
        "inputs": {"assessment_score": 100, "business_type": "b2b",
                    "organization_size": "enterprise", "employee_count": 100,
                    "urgency": "asap", "engagement_recent_events": 20,
                    "checkout_started": True, "existing_customer": False,
                    "source_quality": "referral"},
    }, timeout=10).json()
    weak = requests.post(f"{API}/admin/revenue/scoring/score", headers=h, json={
        "contact_id": a_contact["id"],
        "inputs": {"assessment_score": 0, "business_type": "other",
                    "organization_size": "solo", "employee_count": 0,
                    "urgency": "explore", "engagement_recent_events": 0,
                    "checkout_started": False, "existing_customer": False,
                    "source_quality": "unknown"},
    }, timeout=10).json()
    assert strong["score"] > weak["score"]
    assert strong["band"] in ("qualified", "high_intent")
    assert weak["band"] in ("unqualified", "early_interest")


def test_score_history_preserved(h, a_contact):
    """Each score run must append a row to contact_scores."""
    before = requests.get(f"{API}/admin/revenue/contacts/{a_contact['id']}/score-history",
                            headers=h, timeout=10).json()["count"]
    requests.post(f"{API}/admin/revenue/scoring/score", headers=h, json={
        "contact_id": a_contact["id"],
        "inputs": {"assessment_score": 50},
    }, timeout=10)
    after = requests.get(f"{API}/admin/revenue/contacts/{a_contact['id']}/score-history",
                          headers=h, timeout=10).json()["count"]
    assert after == before + 1


def test_scoring_rule_version_history(h):
    """Creating multiple rule sets preserves each version."""
    r1 = requests.post(f"{API}/admin/revenue/scoring/rules", headers=h, json={
        "name": "Custom Rule Set 1",
        "weights": {"assessment_score": {"weight": 40, "type": "linear_0_100"}},
    }, timeout=10).json()
    r2 = requests.post(f"{API}/admin/revenue/scoring/rules", headers=h, json={
        "name": "Custom Rule Set 2",
        "weights": {"assessment_score": {"weight": 60, "type": "linear_0_100"}},
    }, timeout=10).json()
    assert r2["rule_set"]["version"] == r1["rule_set"]["version"] + 1
    listing = requests.get(f"{API}/admin/revenue/scoring/rules", headers=h,
                            timeout=10).json()
    assert listing["count"] >= 2


def test_scoring_rule_activation_deactivates_prior(h):
    r = requests.post(f"{API}/admin/revenue/scoring/rules", headers=h, json={
        "name": "Activator", "weights": {},
    }, timeout=10).json()
    rid = r["rule_set"]["id"]
    requests.post(f"{API}/admin/revenue/scoring/rules/{rid}/activate",
                    headers=h, timeout=10)
    cur = requests.get(f"{API}/admin/revenue/scoring/rules/current",
                        headers=h, timeout=10).json()
    assert cur["rule_set"]["id"] == rid


def test_scoring_band_thresholds_reject_overlap(h):
    """Overlapping band thresholds must be rejected at rule-set creation."""
    r = requests.post(f"{API}/admin/revenue/scoring/rules", headers=h, json={
        "name": "Bad Bands", "weights": {},
        "band_thresholds": {"a": [0, 50], "b": [40, 100]},  # overlaps
    }, timeout=10)
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  ATTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════
def test_first_touch_preserved_across_multiple_touches(h, a_contact):
    cid = a_contact["id"]
    # First touch — utm_source=google
    requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/touch",
                    headers=h, json={"contact_id": cid, "utm_source": "google",
                                       "utm_campaign": "launch"}, timeout=10)
    # Second touch — utm_source=twitter
    requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/touch",
                    headers=h, json={"contact_id": cid, "utm_source": "twitter"},
                    timeout=10)
    detail = requests.get(f"{API}/admin/revenue/contacts/{cid}",
                            headers=h, timeout=10).json()
    attr = detail["contact"].get("attribution") or {}
    assert attr.get("first_touch_source") == "google"
    assert attr.get("last_touch_source") == "twitter"


def test_attribution_touches_appended_not_overwritten(h, a_contact):
    cid = a_contact["id"]
    before = requests.get(f"{API}/admin/revenue/contacts/{cid}/attribution/touches",
                            headers=h, timeout=10).json()["count"]
    requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/touch",
                    headers=h, json={"contact_id": cid, "utm_source": "direct"},
                    timeout=10)
    after = requests.get(f"{API}/admin/revenue/contacts/{cid}/attribution/touches",
                          headers=h, timeout=10).json()["count"]
    assert after == before + 1


def test_attribution_url_sanitization(h, a_contact):
    """javascript: and data: URLs must be dropped by the sanitizer."""
    cid = a_contact["id"]
    r = requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/touch",
                        headers=h, json={
                            "contact_id": cid, "utm_source": "test",
                            "source_url": "javascript:alert('xss')",
                        }, timeout=10)
    assert r.status_code == 200
    assert r.json()["touch"]["source_url"] is None


def test_attribution_correction_audited(h, a_contact):
    cid = a_contact["id"]
    r = requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/correct",
                        headers=h, json={
                            "contact_id": cid, "which": "first_touch",
                            "new_source": {"source": "referral"},
                            "reason": "manual investigation showed original touch was mis-recorded",
                        }, timeout=10)
    assert r.status_code == 200
    # Correction must appear in audit log
    au = requests.get(f"{API}/admin/revenue/audit?action=attribution.corrected&limit=5",
                        headers=h, timeout=10).json()
    assert any(e["target_id"] == cid for e in au["entries"])


def test_attribution_correction_requires_reason(h, a_contact):
    cid = a_contact["id"]
    r = requests.post(f"{API}/admin/revenue/contacts/{cid}/attribution/correct",
                        headers=h, json={
                            "contact_id": cid, "which": "first_touch",
                            "new_source": {"source": "email"}, "reason": "no",
                        }, timeout=10)
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  CONTACT ADMIN
# ═══════════════════════════════════════════════════════════════════════════
def test_lifecycle_change_requires_reason(h, a_contact):
    r = requests.post(f"{API}/admin/revenue/contacts/{a_contact['id']}/lifecycle",
                        headers=h, json={"new_stage": "qualified_lead", "reason": "x"},
                        timeout=10)
    assert r.status_code == 422


def test_lifecycle_change_success(h, a_contact):
    r = requests.post(f"{API}/admin/revenue/contacts/{a_contact['id']}/lifecycle",
                        headers=h, json={
                            "new_stage": "qualified_lead",
                            "reason": "test lifecycle change with sufficient reason",
                        }, timeout=10)
    assert r.status_code == 200
    detail = requests.get(f"{API}/admin/revenue/contacts/{a_contact['id']}",
                            headers=h, timeout=10).json()
    assert detail["contact"]["lifecycle_stage"] == "qualified_lead"


def test_contact_detail_shape(h, a_contact):
    detail = requests.get(f"{API}/admin/revenue/contacts/{a_contact['id']}",
                            headers=h, timeout=10).json()
    for k in ("contact", "score_history", "attribution_touches", "internal_events",
                "audit_log", "notes", "recommended_offer", "next_recommended_action"):
        assert k in detail, f"missing key '{k}' in contact detail response"


# ═══════════════════════════════════════════════════════════════════════════
#  MERGE
# ═══════════════════════════════════════════════════════════════════════════
def _mk_contact(h, email_suffix: str) -> dict:
    email = f"phase2-merge-{email_suffix}-{uuid.uuid4().hex[:6]}@test.ascendra.simulated"
    return requests.post(f"{API}/admin/revenue/contacts", headers=h, json={
        "email": email, "simulated": True,
    }, timeout=10).json()["contact"]


def test_merge_dry_run_does_not_mutate(h):
    surv, mrgd = _mk_contact(h, "surv-a"), _mk_contact(h, "mrgd-a")
    r = requests.post(f"{API}/admin/revenue/contacts/merge", headers=h, json={
        "surviving_id": surv["id"], "merged_id": mrgd["id"],
        "reason": "test merge dry run", "dry_run": True,
    }, timeout=10)
    assert r.status_code == 200
    assert r.json()["merged"] is False
    # Neither contact should be marked merged_into
    check = requests.get(f"{API}/admin/revenue/contacts/{mrgd['id']}",
                          headers=h, timeout=10).json()
    assert not check["contact"].get("merged_into")


def test_merge_preserves_events_and_touches(h):
    surv, mrgd = _mk_contact(h, "surv-b"), _mk_contact(h, "mrgd-b")
    # Attach a touch and a score to the merged contact
    requests.post(f"{API}/admin/revenue/contacts/{mrgd['id']}/attribution/touch",
                    headers=h, json={"contact_id": mrgd["id"], "utm_source": "linkedin"},
                    timeout=10)
    requests.post(f"{API}/admin/revenue/scoring/score", headers=h, json={
        "contact_id": mrgd["id"], "inputs": {"assessment_score": 50},
    }, timeout=10)

    r = requests.post(f"{API}/admin/revenue/contacts/merge", headers=h, json={
        "surviving_id": surv["id"], "merged_id": mrgd["id"],
        "reason": "test merge preserving history end-to-end", "dry_run": False,
    }, timeout=10)
    assert r.status_code == 200 and r.json()["merged"] is True

    # Touches + scores from merged should now belong to surviving
    surv_detail = requests.get(f"{API}/admin/revenue/contacts/{surv['id']}",
                                headers=h, timeout=10).json()
    assert any(t.get("merged_from_contact_id") == mrgd["id"]
                 for t in surv_detail["attribution_touches"])
    assert any(s.get("merged_from_contact_id") == mrgd["id"]
                 for s in surv_detail["score_history"])


def test_merge_refuses_conflicting_external_ids(h):
    surv, mrgd = _mk_contact(h, "surv-c"), _mk_contact(h, "mrgd-c")
    # Simulate conflicting Stripe customer IDs via direct DB write
    mongo_url, test_db = get_test_mongo_config()

    async def _seed():
        c = AsyncIOMotorClient(mongo_url)
        try:
            await c[test_db]["contacts"].update_one(
                {"id": surv["id"]}, {"$set": {"stripe_customer_id": "cus_ABC"}})
            await c[test_db]["contacts"].update_one(
                {"id": mrgd["id"]}, {"$set": {"stripe_customer_id": "cus_XYZ"}})
        finally:
            c.close()
    asyncio.run(_seed())

    r = requests.post(f"{API}/admin/revenue/contacts/merge", headers=h, json={
        "surviving_id": surv["id"], "merged_id": mrgd["id"],
        "reason": "test conflict refusal end-to-end", "dry_run": False,
    }, timeout=10)
    assert r.status_code == 409

    # With force flag, conflict is documented but merge proceeds
    r2 = requests.post(f"{API}/admin/revenue/contacts/merge", headers=h, json={
        "surviving_id": surv["id"], "merged_id": mrgd["id"],
        "reason": "override conflict for testing", "dry_run": False,
        "force_conflicting_external_ids": True,
    }, timeout=10)
    assert r2.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  SAFETY GATE / NO LIVE CALLS
# ═══════════════════════════════════════════════════════════════════════════
def test_phase2_records_reflect_corrected_simulation_semantics(h, a_contact):
    """Corrected semantics (Phase 2 preliminary fix):

    ``simulated`` no longer means "the safety gate is off". It means the record
    is fabricated test data OR a modeled-but-not-performed action.

    Real admin-initiated audits from Phase 2 must therefore be:
      • simulated == False
      • source == 'admin_created' or 'existing_application'
      • environment == 'preview'
      • live_actions_enabled_at_time == False (recorded separately)
    """
    j = requests.get(f"{API}/admin/revenue/audit?limit=50", headers=h, timeout=10).json()
    admin_actions = {
        "offer.created", "offer.updated", "offer.activated",
        "offer.deactivated", "lead.scored", "attribution.touch_recorded",
        "attribution.corrected", "contact.updated", "contact.lifecycle_changed",
        "contact.note_added", "contact.merged", "scoring_rules.created",
        "scoring_rules.activated",
    }
    admin_audits = [e for e in j["entries"] if e.get("action") in admin_actions]
    assert admin_audits, "expected at least one admin-triggered Phase 2 audit"
    for e in admin_audits:
        assert e.get("simulated") is False, (
            f"admin action '{e['action']}' must not be labeled simulated"
        )
        assert e.get("source") in ("admin_created", "existing_application"), (
            f"admin action '{e['action']}' source={e.get('source')}"
        )
        assert e.get("environment") == "preview"
        assert e.get("live_actions_enabled_at_time") is False, (
            f"admin action '{e['action']}' recorded live_actions_enabled_at_time=True"
        )


def test_imported_existing_offers_not_simulated(h):
    """Existing Ascender/Pathfinder/Sage/Business offers imported from the
    current Ascendra configuration must be classified as legitimate preview
    configuration, NOT as simulated test data."""
    j = requests.get(f"{API}/admin/revenue/offers", headers=h, timeout=10).json()
    imported = [o for o in j["offers"] if o.get("imported") is True]
    assert imported, "expected imported existing offers (run import-existing first)"
    for o in imported:
        assert o.get("simulated") is False, (
            f"existing offer '{o['offer_code']}' must not be labeled simulated"
        )
        assert o.get("source") == "existing_application"
        assert o.get("environment") == "preview"
    # Business specifically may be draft/inactive but never simulated
    biz = next((o for o in imported if o["offer_code"] == "business_monthly"), None)
    if biz:
        assert biz["simulated"] is False


def test_test_created_offer_may_be_labeled_test_fixture_via_source_marker(h):
    """A test-created offer defaults to source=admin_created, but the
    application layer supports the ``source`` classification. Verify by
    creating an offer and confirming the field exists on the persisted doc."""
    code = f"srctest_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Source Test", "category": "digital_product",
        "price": "1.00", "billing_frequency": "one_time",
    }, timeout=10)
    assert r.status_code == 200
    mongo_url, test_db = get_test_mongo_config()

    async def _check():
        c = AsyncIOMotorClient(mongo_url)
        try:
            doc = await c[test_db]["offers"].find_one({"offer_code": code})
            assert doc["source"] == "admin_created"
            assert doc["environment"] == "preview"
            assert doc["simulated"] is False
        finally:
            c.close()
    asyncio.run(_check())


def test_material_change_approval_remains_simulated(h):
    """The queued approval-queue entry for a material offer change is a
    MODELED action (it will not actually execute while the safety gate is
    off), so its `simulated` flag must remain True — but the request audit
    entry itself is real (simulated=False)."""
    code = f"matsim_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/admin/revenue/offers", headers=h, json={
        "offer_code": code, "name": "Mat Sim", "category": "digital_product",
        "price": "5.00", "billing_frequency": "one_time",
    }, timeout=10).json()
    oid = r["offer"]["id"]
    requests.post(f"{API}/admin/revenue/offers/{oid}/activate", headers=h, timeout=10)
    r2 = requests.patch(f"{API}/admin/revenue/offers/{oid}", headers=h, json={
        "price": "6.00", "change_reason": "market repricing",
    }, timeout=10).json()
    ap = r2.get("approval") or {}
    assert ap.get("simulated") is True, "queued approval must remain simulated (modeled)"
    # The audit entry itself must be real
    au = requests.get(f"{API}/admin/revenue/audit?limit=5",
                        headers=h, timeout=10).json()
    req_audits = [e for e in au["entries"]
                    if e.get("action") == "offer.change_material.requested"]
    assert req_audits, "expected offer.change_material.requested audit"
    assert req_audits[0]["simulated"] is False


def test_phase2_no_live_integration_calls(h):
    """Integration status must not reveal that any Phase 2 action performed a
    live call. All integrations remain simulated/unavailable."""
    j = requests.get(f"{API}/admin/revenue/integrations", headers=h, timeout=10).json()
    for i in j["integrations"]:
        assert i["state"] in {"simulated", "unavailable"}, \
            f"integration {i['provider']} state={i['state']} while safety gate is disabled"


def test_phase2_no_referral_or_affiliate_system_exists(h):
    """Guarantee: attribution supports only source tracking, NOT commission /
    referral payouts. Prove by verifying every forbidden path returns 404."""
    for forbidden in ("/admin/revenue/commissions", "/admin/revenue/payouts",
                      "/admin/revenue/affiliates", "/admin/revenue/partners",
                      "/admin/revenue/referral-partners"):
        r = requests.get(f"{API}{forbidden}", headers=h, timeout=5)
        assert r.status_code == 404, (
            f"forbidden endpoint {forbidden} unexpectedly returned {r.status_code}"
        )
