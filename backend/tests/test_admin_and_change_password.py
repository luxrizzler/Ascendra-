"""Tests for admin endpoints, forced password change, anonymous pageview tracking,
and Sage seed accounts. Run AFTER seed_accounts.py so admin + sage1..sage6 exist.

NOTE: This test SUITE will reset the admin/sage account passwords back to the
seeded defaults at the end so the test_credentials.md table remains valid.
"""
import os
import uuid
import pytest
import requests

API_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"

ADMIN_EMAIL = "admin@ascendraacademy.com"
ADMIN_TEMP_PASSWORD = "AscendraAdmin2026!"
SAGE1_EMAIL = "sage1@ascendraacademy.com"
SAGE1_TEMP_PASSWORD = "test1"


@pytest.fixture(scope="module", autouse=True)
def reseed_after_module():
    """After the module finishes, re-run seed_accounts.py so admin + sage1..6
    passwords are restored to the values listed in test_credentials.md."""
    yield
    import subprocess
    subprocess.run(["python", "seed_accounts.py"], cwd="/app/backend", check=False,
                   capture_output=True, timeout=60)


def _login(client, email, password):
    r = client.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
    return r


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ─── Seed-account login + forced password change ───────────────────────────
class TestSeedAccountsAndForcedPasswordChange:
    def test_admin_login_returns_must_change_password(self, client):
        r = _login(client, ADMIN_EMAIL, ADMIN_TEMP_PASSWORD)
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        me = client.get(f"{API_URL}/auth/me", headers=_hdr(token))
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["is_admin"] is True
        assert body["must_change_password"] is True

    def test_sage1_login_must_change_password(self, client):
        r = _login(client, SAGE1_EMAIL, SAGE1_TEMP_PASSWORD)
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        me = client.get(f"{API_URL}/auth/me", headers=_hdr(token))
        assert me.status_code == 200
        body = me.json()
        assert body["tier"] == "sage"
        assert body["must_change_password"] is True

    def test_forced_change_password_no_current_required(self, client):
        # Login as sage2 (forced)
        r = _login(client, "sage2@ascendraacademy.com", "test2")
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]

        # Forced flow: no current_password
        new_pw = f"NewPw_{uuid.uuid4().hex[:8]}!"
        rc = client.post(f"{API_URL}/auth/change-password",
                         json={"new_password": new_pw},
                         headers=_hdr(token))
        assert rc.status_code == 200, rc.text

        # must_change_password cleared
        me = client.get(f"{API_URL}/auth/me", headers=_hdr(token)).json()
        assert me["must_change_password"] is False

        # Login with new password works
        rl = _login(client, "sage2@ascendraacademy.com", new_pw)
        assert rl.status_code == 200

        # Now current_password IS required
        rc2 = client.post(f"{API_URL}/auth/change-password",
                          json={"new_password": "AnotherPw_99!"},
                          headers=_hdr(rl.json()["access_token"]))
        assert rc2.status_code == 400  # current password required

        # Wrong current_password → 401
        rc3 = client.post(f"{API_URL}/auth/change-password",
                          json={"current_password": "WRONG", "new_password": "AnotherPw_99!"},
                          headers=_hdr(rl.json()["access_token"]))
        assert rc3.status_code == 401

        # NOTE: cannot reset to seeded "test2" (5 chars < 6 min). seed_accounts.py
        # is the canonical way to restore seeded defaults; we run it in the
        # module finalizer below.


# ─── Anonymous pageview tracking ──────────────────────────────────────────
class TestPageviewTracking:
    def test_pageview_anonymous_no_auth(self, client):
        r = client.post(f"{API_URL}/track/pageview",
                        json={"path": "/qa-test-path", "referrer": "https://test.local"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_pageview_invalid_payload(self, client):
        r = client.post(f"{API_URL}/track/pageview", json={})
        # path is required → 422
        assert r.status_code in (400, 422)


# ─── Admin endpoints (require admin) ──────────────────────────────────────
@pytest.fixture(scope="module")
def admin_token():
    """Login as admin (we always log in with seeded temp password since
    test_credentials.md says it's the current password)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API_URL}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_TEMP_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def sage1_token():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API_URL}/auth/login",
               json={"email": SAGE1_EMAIL, "password": SAGE1_TEMP_PASSWORD})
    assert r.status_code == 200, f"sage1 login failed: {r.text}"
    return r.json()["access_token"]


class TestAdminGuards:
    def test_stats_requires_admin_sage_403(self, client, sage1_token):
        r = client.get(f"{API_URL}/admin/stats", headers=_hdr(sage1_token))
        assert r.status_code == 403

    def test_stats_no_auth(self, client):
        r = client.get(f"{API_URL}/admin/stats")
        assert r.status_code in (401, 403)


class TestAdminStats:
    def test_admin_stats_shape(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/stats", headers=_hdr(admin_token))
        assert r.status_code == 200, r.text
        d = r.json()
        for block in ("users", "revenue", "engagement", "traffic"):
            assert block in d, f"missing block {block}"
        assert "by_tier" in d["users"]
        for t in ("free", "ascender", "pathfinder", "sage"):
            assert t in d["users"]["by_tier"]
        # sage tier should now have 6 sage seeded friends
        assert d["users"]["by_tier"]["sage"] >= 6
        # admin exists → total >= 7
        assert d["users"]["total"] >= 7


class TestAdminUsers:
    def test_list_users(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?limit=200", headers=_hdr(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert "users" in body and "total" in body
        emails = {u["email"] for u in body["users"]}
        assert ADMIN_EMAIL in emails
        assert SAGE1_EMAIL in emails

    def test_search_users_by_email(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?q=sage1", headers=_hdr(admin_token))
        assert r.status_code == 200
        users = r.json()["users"]
        assert any(u["email"] == SAGE1_EMAIL for u in users)

    def test_filter_users_by_tier(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?tier=sage", headers=_hdr(admin_token))
        assert r.status_code == 200
        users = r.json()["users"]
        assert len(users) >= 6
        assert all(u["tier"] == "sage" for u in users)

    def test_user_detail_includes_progress_and_payments(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?q=sage1", headers=_hdr(admin_token))
        sage1 = next(u for u in r.json()["users"] if u["email"] == SAGE1_EMAIL)
        uid = sage1["id"]
        rd = client.get(f"{API_URL}/admin/users/{uid}", headers=_hdr(admin_token))
        assert rd.status_code == 200
        body = rd.json()
        assert body["user"]["email"] == SAGE1_EMAIL
        assert "progress" in body
        assert "certificates" in body
        assert "payments" in body

    def test_patch_user_tier_and_revert(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?q=sage1", headers=_hdr(admin_token))
        sage1 = next(u for u in r.json()["users"] if u["email"] == SAGE1_EMAIL)
        uid = sage1["id"]
        # sage → pathfinder
        rp = client.patch(f"{API_URL}/admin/users/{uid}",
                          json={"tier": "pathfinder"},
                          headers=_hdr(admin_token))
        assert rp.status_code == 200, rp.text
        assert rp.json()["user"]["tier"] == "pathfinder"
        # back → sage
        rp2 = client.patch(f"{API_URL}/admin/users/{uid}",
                           json={"tier": "sage"},
                           headers=_hdr(admin_token))
        assert rp2.status_code == 200
        assert rp2.json()["user"]["tier"] == "sage"

    def test_patch_user_set_new_password_forces_change(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/users?q=sage3", headers=_hdr(admin_token))
        sage3 = next(u for u in r.json()["users"] if u["email"] == "sage3@ascendraacademy.com")
        uid = sage3["id"]
        new_pw = f"AdminReset_{uuid.uuid4().hex[:6]}!"
        rp = client.patch(f"{API_URL}/admin/users/{uid}",
                          json={"new_password": new_pw},
                          headers=_hdr(admin_token))
        assert rp.status_code == 200
        # Must change password auto-flipped to true
        assert rp.json()["user"]["must_change_password"] is True
        # Login with admin-set password works
        rl = client.post(f"{API_URL}/auth/login",
                         json={"email": "sage3@ascendraacademy.com", "password": new_pw})
        assert rl.status_code == 200
        # Reset back to seeded default
        rp2 = client.patch(f"{API_URL}/admin/users/{uid}",
                           json={"new_password": "ResetSeed_test3!"},
                           headers=_hdr(admin_token))
        assert rp2.status_code == 200

    def test_admin_cannot_delete_self(self, client, admin_token):
        # find admin id
        r = client.get(f"{API_URL}/admin/users?q=admin", headers=_hdr(admin_token))
        admin = next(u for u in r.json()["users"] if u["email"] == ADMIN_EMAIL)
        rd = client.delete(f"{API_URL}/admin/users/{admin['id']}",
                           headers=_hdr(admin_token))
        assert rd.status_code == 400


class TestAdminSales:
    def test_admin_sales_shape(self, client, admin_token):
        r = client.get(f"{API_URL}/admin/sales", headers=_hdr(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert "sales" in body
        # Each sale (if any) is enriched with user_email
        for s in body["sales"]:
            assert "session_id" in s
            assert "amount_usd" in s


class TestAdminTraffic:
    def test_admin_traffic_aggregation(self, client, admin_token):
        # Insert a pageview so aggregation has at least one row
        client.post(f"{API_URL}/track/pageview", json={"path": "/qa-traffic-test"})
        r = client.get(f"{API_URL}/admin/traffic?days=14", headers=_hdr(admin_token))
        assert r.status_code == 200
        body = r.json()
        assert "daily" in body and "top_paths" in body
        assert body["days"] == 14
        # top_paths should have at least one entry now
        assert any(tp["path"] for tp in body["top_paths"])


# ─── Regression: existing endpoints still work ────────────────────────────
class TestRegression:
    def test_auth_me_legacy_user(self, client):
        r = client.post(f"{API_URL}/auth/login",
                        json={"email": "test@aiacademy.app", "password": "testpass123"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        me = client.get(f"{API_URL}/auth/me", headers=_hdr(token))
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == "test@aiacademy.app"
        # must_change_password must exist (and false for legacy)
        assert "must_change_password" in body

    def test_progress_legacy_user(self, client):
        r = client.post(f"{API_URL}/auth/login",
                        json={"email": "test@aiacademy.app", "password": "testpass123"})
        token = r.json()["access_token"]
        rp = client.get(f"{API_URL}/progress", headers=_hdr(token))
        assert rp.status_code == 200
        assert "total_xp" in rp.json()

    def test_billing_info_still_ok(self, client):
        r = client.get(f"{API_URL}/billing/info")
        assert r.status_code == 200
        assert "uses_real_stripe" in r.json()
