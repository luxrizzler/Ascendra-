"""Backend API tests for AI Academy."""
import os
import uuid
import time
import pytest
import requests

API_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"


# --- Health ---
class TestHealth:
    def test_root(self, client):
        r = client.get(f"{API_URL}/")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body.get("service") == "ascendra-api"


# --- Auth ---
class TestAuth:
    def test_signup_returns_token(self, client):
        email = f"qa+{uuid.uuid4().hex[:8]}@aiacademy.app"
        r = client.post(f"{API_URL}/auth/signup", json={
            "email": email, "password": "testpass123", "name": "QA"
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data and data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_signup_duplicate(self, client, test_user):
        r = client.post(f"{API_URL}/auth/signup", json={
            "email": test_user["email"], "password": "testpass123"
        })
        assert r.status_code == 400

    def test_login_valid(self, client, test_user):
        r = client.post(f"{API_URL}/auth/login", json={
            "email": test_user["email"], "password": test_user["password"]
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_invalid(self, client, test_user):
        r = client.post(f"{API_URL}/auth/login", json={
            "email": test_user["email"], "password": "WRONG"
        })
        assert r.status_code == 401

    def test_me_with_token(self, client, auth_headers, test_user):
        r = client.get(f"{API_URL}/auth/me", headers=auth_headers)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == test_user["email"]
        assert "id" in u and "tier" in u

    def test_me_without_token(self, client):
        r = client.get(f"{API_URL}/auth/me")
        assert r.status_code in (401, 403)


# --- Curriculum ---
class TestCurriculum:
    def test_paths_list(self, client):
        r = client.get(f"{API_URL}/paths")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert len(paths) == 4
        ids = {p["id"] for p in paths}
        assert ids == {"fundamentals", "business", "creators", "productivity"}
        for p in paths:
            for k in ("title", "color", "level", "duration", "image", "total_lessons", "total_xp"):
                assert k in p

    @pytest.mark.parametrize("pid", ["fundamentals", "business", "creators", "productivity"])
    def test_path_detail(self, client, pid):
        r = client.get(f"{API_URL}/paths/{pid}")
        assert r.status_code == 200
        p = r.json()
        assert p["id"] == pid
        assert len(p["modules"]) > 0
        for m in p["modules"]:
            assert len(m["lessons"]) > 0
            for l in m["lessons"]:
                assert "duration_min" in l and "xp" in l and "card_count" in l
                assert l["card_count"] > 0
                # quiz answers should NOT leak in detail list view
                assert "quiz" not in l

    def test_path_not_found(self, client):
        r = client.get(f"{API_URL}/paths/nonexistent")
        assert r.status_code == 404

    def test_lesson_detail(self, client):
        r = client.get(f"{API_URL}/lessons/f1l1")
        assert r.status_code == 200
        l = r.json()
        assert l["id"] == "f1l1"
        assert isinstance(l["cards"], list) and len(l["cards"]) > 0
        assert "quiz" in l and "answer_index" in l["quiz"]
        assert "options" in l["quiz"] and len(l["quiz"]["options"]) >= 2

    def test_lesson_not_found(self, client):
        r = client.get(f"{API_URL}/lessons/nonexistent")
        assert r.status_code == 404

    def test_models_list(self, client):
        r = client.get(f"{API_URL}/models")
        assert r.status_code == 200
        models = r.json()["models"]
        assert len(models) == 22
        for m in models:
            assert "category" in m and "id" in m and "name" in m


# --- Progress ---
class TestProgress:
    def test_initial_progress_zero(self, client, fresh_auth_headers):
        r = client.get(f"{API_URL}/progress", headers=fresh_auth_headers)
        assert r.status_code == 200
        p = r.json()
        assert p["total_xp"] == 0
        assert p["streak_days"] == 0
        assert p["completed_lesson_ids"] == []

    def test_progress_requires_auth(self, client):
        r = client.get(f"{API_URL}/progress")
        assert r.status_code in (401, 403)

    def test_complete_lesson_idempotent(self, client, fresh_auth_headers):
        # Complete lesson once
        r1 = client.post(f"{API_URL}/progress/complete",
                         json={"lesson_id": "f1l1"}, headers=fresh_auth_headers)
        assert r1.status_code == 200, r1.text
        p1 = r1.json()
        assert "f1l1" in p1["completed_lesson_ids"]
        assert p1["total_xp"] == 50  # f1l1 xp
        assert p1["streak_days"] == 1

        # Complete same lesson again — XP must not double
        r2 = client.post(f"{API_URL}/progress/complete",
                         json={"lesson_id": "f1l1"}, headers=fresh_auth_headers)
        assert r2.status_code == 200
        p2 = r2.json()
        assert p2["total_xp"] == 50  # not 100
        assert p2["completed_lesson_ids"].count("f1l1") == 1

        # Complete a different lesson — XP should increase
        r3 = client.post(f"{API_URL}/progress/complete",
                         json={"lesson_id": "f1l2"}, headers=fresh_auth_headers)
        assert r3.status_code == 200
        p3 = r3.json()
        assert p3["total_xp"] == 110  # 50 + 60

    def test_complete_lesson_invalid_id(self, client, fresh_auth_headers):
        r = client.post(f"{API_URL}/progress/complete",
                        json={"lesson_id": "doesnotexist"}, headers=fresh_auth_headers)
        assert r.status_code == 404


# --- Tutor (Claude Sonnet 4.5) ---
class TestTutor:
    def test_tutor_chat_basic(self, client, auth_headers):
        r = client.post(f"{API_URL}/tutor/chat",
                        json={"message": "In one sentence, what's an LLM?"},
                        headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "session_id" in data and len(data["session_id"]) > 0
        assert "reply" in data and len(data["reply"]) > 5

    def test_tutor_chat_context(self, client, auth_headers):
        # First message
        r1 = client.post(f"{API_URL}/tutor/chat",
                        json={"message": "Remember the number 42. Just say OK."},
                        headers=auth_headers, timeout=60)
        assert r1.status_code == 200
        sid = r1.json()["session_id"]
        time.sleep(1)
        # Second message reusing session_id
        r2 = client.post(f"{API_URL}/tutor/chat",
                        json={"message": "What number did I ask you to remember?",
                              "session_id": sid},
                        headers=auth_headers, timeout=60)
        assert r2.status_code == 200
        assert r2.json()["session_id"] == sid
        assert "42" in r2.json()["reply"]

    def test_tutor_requires_auth(self, client):
        r = client.post(f"{API_URL}/tutor/chat", json={"message": "hi"})
        assert r.status_code in (401, 403)

    def test_tutor_persona_is_ascendra(self, client, auth_headers):
        """Tutor system prompt must introduce itself as Ascendra, NOT Aida."""
        r = client.post(f"{API_URL}/tutor/chat",
                        json={"message": "What is your name? Answer in one short sentence."},
                        headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text
        reply = r.json()["reply"].lower()
        assert "ascendra" in reply, f"Expected 'Ascendra' in reply, got: {reply}"
        assert "aida" not in reply, f"Old persona 'Aida' leaked: {reply}"


# --- Google Auth ---
class TestGoogleAuth:
    def test_google_invalid_session_token(self, client):
        r = client.post(f"{API_URL}/auth/google",
                        json={"session_token": "invalid_bogus_session_token_xyz"},
                        timeout=15)
        # Should reject invalid session — 401 expected; 502 acceptable if upstream throws
        assert r.status_code in (401, 502), r.text
        # Should NOT issue a token
        assert "access_token" not in r.json()

    def test_google_missing_session_token(self, client):
        r = client.post(f"{API_URL}/auth/google", json={})
        assert r.status_code in (400, 422)


# --- Pricing & Stripe ---
class TestPricing:
    def test_pricing_tiers(self, client):
        r = client.get(f"{API_URL}/pricing")
        assert r.status_code == 200
        tiers = r.json()["tiers"]
        assert len(tiers) == 3
        by_id = {t["id"]: t for t in tiers}
        assert by_id["free"]["price_monthly"] == 0
        assert by_id["pro"]["price_monthly"] == 19.99
        assert by_id["business"]["price_monthly"] == 49.99


class TestBilling:
    def test_checkout_creates_session(self, client, auth_headers):
        r = client.post(f"{API_URL}/billing/checkout",
                        json={"tier": "pro",
                              "origin_url": "https://ai-business-academy-2.preview.emergentagent.com"},
                        headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data and "session_id" in data
        assert "stripe.com" in data["url"]
        assert data["session_id"].startswith("cs_test_")
        # Status check
        sid = data["session_id"]
        r2 = client.get(f"{API_URL}/billing/status/{sid}", headers=auth_headers, timeout=30)
        assert r2.status_code == 200
        # Stripe may return 'unpaid' which our code keeps as 'pending'
        assert r2.json()["status"] in ("pending", "unpaid")
        assert r2.json()["tier"] == "pro"

    def test_checkout_invalid_tier(self, client, auth_headers):
        r = client.post(f"{API_URL}/billing/checkout",
                        json={"tier": "freeee",
                              "origin_url": "https://example.com"},
                        headers=auth_headers)
        assert r.status_code in (400, 422)

    def test_checkout_requires_auth(self, client):
        r = client.post(f"{API_URL}/billing/checkout",
                        json={"tier": "pro",
                              "origin_url": "https://example.com"})
        assert r.status_code in (401, 403)
