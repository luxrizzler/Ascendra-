"""Pytest conftest — Phase 1 hardening: isolated test database + safety guards.

ORCHESTRATION
─────────────
This file runs once per pytest session, BEFORE any test module imports the
backend. It:

  1. Reads /app/backend/.env safely (strips quoted values) and captures the
     original file contents for restoration at teardown.
  2. Refuses to proceed unless the MongoDB URI parses and the target test DB
     name clearly contains "test" (default: ``ascendra_revenue_test``).
  3. Rewrites /app/backend/.env so the live backend uses the isolated test DB
     while tests run.
  4. Sets TESTING=true in the process environment so any destructive
     ``_env_utils.assert_safe_test_db`` guard will actually allow cleanup.
  5. Restarts the backend via ``supervisorctl`` and polls the public API
     until the /api/ health endpoint responds.
  6. Yields control to the test session.
  7. Teardown ALWAYS runs (including on test failure / KeyboardInterrupt):
        • drops the isolated test DB (guarded by ``assert_safe_test_db``)
        • restores /app/backend/.env to its exact prior contents
        • restarts the backend and re-polls health

SAFETY GUARANTEES
─────────────────
• Never modifies MONGO_URL — only DB_NAME.
• Never drops any database whose name does not contain "test".
• Never logs the URI value; only a redacted scheme+host summary.
• Aborts if the ordinary DB_NAME already contains "test" (indicates the
  environment was left in a partial state and needs manual attention).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

# Make the shared helpers importable in every test file
sys.path.insert(0, str(Path(__file__).parent))

from _env_utils import (  # noqa: E402
    BACKEND_ENV,
    assert_safe_test_db,
    assert_valid_mongo_uri,
    read_backend_env,
    redact_uri,
    restore_env_file,
    rewrite_env_key,
)


# Constants
TEST_DB_NAME_DEFAULT = "ascendra_revenue_test"
BACKEND_HEALTH_URL_KEY = "REACT_APP_BACKEND_URL"
FRONTEND_ENV = Path("/app/frontend/.env")
HEALTH_TIMEOUT_S = 30
POLL_INTERVAL_S = 1.0


def _load_frontend_backend_url() -> str:
    """Read the public preview URL from /app/frontend/.env (safely)."""
    for line in FRONTEND_ENV.read_text().splitlines():
        s = line.strip()
        if s.startswith(f"{BACKEND_HEALTH_URL_KEY}="):
            _, _, v = s.partition("=")
            # Strip any wrapping quotes
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            return v.rstrip("/")
    raise RuntimeError(f"{BACKEND_HEALTH_URL_KEY} not present in {FRONTEND_ENV}")


def _supervisor_restart_backend() -> None:
    subprocess.run(
        ["supervisorctl", "restart", "backend"],
        check=True,
        capture_output=True,
        text=True,
    )


def _poll_backend_health(base_url: str, expect_db_test: bool = False) -> None:
    """Poll /api/ until it returns 200. Raises if it never comes up in time."""
    deadline = time.time() + HEALTH_TIMEOUT_S
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/api/", timeout=3)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return
        except Exception as e:
            last_err = e
        time.sleep(POLL_INTERVAL_S)
    raise RuntimeError(
        f"Backend health check never returned 200 within {HEALTH_TIMEOUT_S}s "
        f"(last error: {type(last_err).__name__ if last_err else 'none'})"
    )


@pytest.fixture(scope="session", autouse=True)
def _isolated_test_database():
    """Session-wide isolated MongoDB test database.

    Any test that hits the running backend automatically inherits this isolation
    because the backend itself is restarted against the test DB for the session.
    """
    test_db = os.environ.get("TEST_DB_NAME", TEST_DB_NAME_DEFAULT).strip()

    # Pre-flight — refuse to proceed if the target name doesn't look like a test DB.
    if "test" not in test_db.lower():
        pytest.exit(
            f"Refusing to swap backend DB to '{test_db}': name does not contain 'test'.",
            returncode=2,
        )
    prod = ("prod", "production", "live")
    if any(p in test_db.lower() for p in prod):
        pytest.exit(
            f"Refusing to swap backend DB to '{test_db}': name matches a production indicator.",
            returncode=2,
        )

    env = read_backend_env()
    mongo_url = env.get("MONGO_URL", "")
    original_db_name = env.get("DB_NAME", "")

    # Fail loudly on malformed URI (do NOT print the URI itself).
    try:
        assert_valid_mongo_uri(mongo_url)
    except AssertionError as e:
        pytest.exit(str(e), returncode=2)

    # If the current DB name already contains "test", the environment is in a
    # partial/leftover state — abort so a human can inspect it.
    if "test" in original_db_name.lower():
        pytest.exit(
            f"Backend .env DB_NAME already looks like a test DB ('{original_db_name}'); "
            "manual inspection required to avoid destroying prior state.",
            returncode=2,
        )

    print(
        f"\n[phase1-conftest] Swapping backend DB → '{test_db}' "
        f"(mongo host summary: {redact_uri(mongo_url)})",
        flush=True,
    )

    # Publish variables the tests will consume (via _env_utils.get_test_mongo_config)
    os.environ["MONGO_URL"] = mongo_url  # canonical, unquoted
    os.environ["TEST_DB_NAME"] = test_db
    os.environ["TESTING"] = "true"
    # AUTOMATION_LIVE_ACTIONS_ENABLED default remains false regardless of test mode

    # Also patch the .env for the backend process so that it uses the test DB
    original_env_contents = rewrite_env_key(BACKEND_ENV, "DB_NAME", test_db)

    try:
        _supervisor_restart_backend()
        base_url = _load_frontend_backend_url()
        _poll_backend_health(base_url)
        print(
            f"[phase1-conftest] Backend restarted; healthy on "
            f"{base_url}/api/ using test DB '{test_db}'.",
            flush=True,
        )
        yield {
            "mongo_url": mongo_url,
            "test_db": test_db,
            "base_url": base_url,
            "original_db_name": original_db_name,
        }
    finally:
        # ── Guarded teardown — ALWAYS runs, even on failure ────────────────
        # 1. Drop the isolated test DB (double-guarded).
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import asyncio

            async def _drop():
                assert_safe_test_db(test_db)  # last-line guard
                client = AsyncIOMotorClient(mongo_url)
                try:
                    await client.drop_database(test_db)
                finally:
                    client.close()

            asyncio.run(_drop())
            print(
                f"[phase1-conftest] Dropped isolated test DB '{test_db}'.",
                flush=True,
            )
        except Exception as e:
            # Don't hide the error — but also don't leak URIs into logs.
            print(
                f"[phase1-conftest][WARN] Failed to drop test DB '{test_db}': "
                f"{type(e).__name__}: {str(e)[:200]}",
                flush=True,
            )

        # 2. Restore /app/backend/.env exactly.
        try:
            restore_env_file(BACKEND_ENV, original_env_contents)
        except Exception as e:
            print(
                f"[phase1-conftest][FATAL] Failed to restore .env: "
                f"{type(e).__name__}: {e}. Manual restore required!",
                flush=True,
            )
            raise

        # 3. Restore process-level TESTING flag so any subsequent tools don't
        #    think they're still in test mode.
        os.environ.pop("TESTING", None)
        os.environ.pop("TEST_DB_NAME", None)

        # 4. Restart backend against the original DB and verify health.
        try:
            _supervisor_restart_backend()
            base_url = _load_frontend_backend_url()
            _poll_backend_health(base_url)
            print(
                f"[phase1-conftest] Backend restored to DB '{original_db_name}'; "
                f"healthy on {base_url}/api/.",
                flush=True,
            )
        except Exception as e:
            print(
                f"[phase1-conftest][WARN] Backend restart/health check after "
                f"restore failed: {type(e).__name__}: {e}",
                flush=True,
            )


# ─── Shared fixtures re-exported for tests ─────────────────────────────────
@pytest.fixture(scope="session")
def isolated_env(_isolated_test_database):
    """Read-only view of the isolated test environment."""
    return _isolated_test_database
