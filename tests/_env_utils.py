"""Test helpers for safe .env parsing and destructive-op guards.

DESIGN NOTES
────────────
• `.env` files at /app/backend/.env quote their values (e.g. MONGO_URL="mongodb://…").
  A naive `line.split("=", 1)[1]` leaves the surrounding quotes attached — that was
  the root cause of the InvalidURI crash. `read_backend_env()` strips one matched
  pair of surrounding single or double quotes.

• `assert_safe_test_db()` refuses any destructive operation unless BOTH:
    (a) the env explicitly reports TESTING=true, and
    (b) the target database name contains the substring "test"
  This is the single, load-bearing safeguard that prevents test cleanup from
  ever running against the ordinary development or preview database.

• `redact_uri()` returns a printable summary that never exposes credentials —
  useful in assertion messages without leaking secrets.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


BACKEND_ENV = Path("/app/backend/.env")

_PROD_INDICATORS = ("prod", "production", "live")
_ALLOWED_URI_SCHEMES = ("mongodb://", "mongodb+srv://")


def _unquote(value: str) -> str:
    """Strip a single matching pair of surrounding quotes, if present."""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def read_backend_env(path: Path = BACKEND_ENV) -> dict[str, str]:
    """Parse /app/backend/.env safely.

    • Ignores blank lines and comments.
    • Strips one matched pair of surrounding quotes from each value.
    • Never logs or prints the parsed values.
    """
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            out[key.strip()] = _unquote(val)
    return out


def redact_uri(uri: str) -> str:
    """Return a printable, credential-free summary of a MongoDB URI."""
    try:
        parsed = urlparse(uri)
        scheme = parsed.scheme or "unknown"
        host = parsed.hostname or "unknown"
        return f"{scheme}://{host}"
    except Exception:
        return "<unparseable>"


def assert_valid_mongo_uri(uri: str) -> None:
    """Fail fast if the URI does not start with an allowed scheme.

    IMPORTANT: never include the URI value itself in the message — only the
    redacted summary.
    """
    if not uri or not uri.startswith(_ALLOWED_URI_SCHEMES):
        raise AssertionError(
            "MongoDB URI is missing an allowed scheme "
            "(expected mongodb:// or mongodb+srv://). "
            f"summary={redact_uri(uri or '')}"
        )


def assert_safe_test_db(db_name: str) -> None:
    """Refuse any destructive test operation unless the DB name is clearly a test DB.

    Requires BOTH:
      (a) `TESTING=true` in the process environment
      (b) The DB name contains the substring "test" (case-insensitive)
      (c) The DB name does NOT contain any production indicator
    """
    testing_flag = os.environ.get("TESTING", "").strip().lower()
    if testing_flag != "true":
        raise AssertionError(
            "Refusing destructive test op: TESTING env is not set to 'true'."
        )
    name_lc = (db_name or "").lower()
    if "test" not in name_lc:
        raise AssertionError(
            f"Refusing destructive test op: DB name '{db_name}' does not contain 'test'."
        )
    if any(p in name_lc for p in _PROD_INDICATORS):
        raise AssertionError(
            f"Refusing destructive test op: DB name '{db_name}' looks like production."
        )


def rewrite_env_key(path: Path, key: str, new_value: str) -> str:
    """Rewrite a single KEY="value" line in-place, preserving the rest of the file.

    Returns the original file contents so the caller can restore them at teardown.
    Adds the key with a quoted value if it does not already exist.
    """
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    replaced = False
    quoted = f'{key}="{new_value}"'
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            lines[i] = quoted + ("\n" if line.endswith("\n") else "")
            replaced = True
            break
    if not replaced:
        # Append (with newline if file didn't end with one)
        prefix = "" if not lines or lines[-1].endswith("\n") else "\n"
        lines.append(f"{prefix}{quoted}\n")
    path.write_text("".join(lines), encoding="utf-8")
    return original


def restore_env_file(path: Path, original_contents: str) -> None:
    """Restore a file to its exact prior contents."""
    path.write_text(original_contents, encoding="utf-8")


def get_test_mongo_config() -> tuple[str, str]:
    """Return (mongo_url, test_db_name) for the isolated Phase 1 test database.

    Uses the current process environment (populated by conftest) — never falls back
    to reading .env directly, since .env is expected to have been swapped already.
    """
    mongo_url = os.environ.get("MONGO_URL", "")
    test_db = os.environ.get("TEST_DB_NAME", "").strip()
    assert_valid_mongo_uri(mongo_url)
    assert_safe_test_db(test_db)
    return mongo_url, test_db
