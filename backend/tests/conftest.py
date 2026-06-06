import os
import pytest
import requests
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API_URL = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def test_user(client):
    """Use seeded user or signup a fresh one."""
    email = "test@aiacademy.app"
    password = "testpass123"
    r = client.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        # Sign up
        r = client.post(f"{API_URL}/auth/signup", json={
            "email": email, "password": password, "name": "Test", "goal": "business"
        })
    assert r.status_code == 200, f"login/signup failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    return {"email": email, "password": password, "token": token}


@pytest.fixture(scope="session")
def fresh_user(client):
    """Sign up a brand-new user (clean progress)."""
    email = f"qa+{uuid.uuid4().hex[:8]}@aiacademy.app"
    password = "testpass123"
    r = client.post(f"{API_URL}/auth/signup", json={
        "email": email, "password": password, "name": "QA", "goal": "career"
    })
    assert r.status_code == 200, f"signup failed: {r.text}"
    return {"email": email, "password": password, "token": r.json()["access_token"]}


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest.fixture
def fresh_auth_headers(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}"}
