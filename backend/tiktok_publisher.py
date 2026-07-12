"""
tiktok_publisher.py — Post videos to TikTok via Content Posting API (Direct Post).

Credentials required in /app/backend/.env:
  TIKTOK_CLIENT_KEY
  TIKTOK_CLIENT_SECRET
  TIKTOK_REDIRECT_URI      # e.g. https://ascendraacademy.com/api/social/tiktok/callback

OAuth 2.0 with PKCE. Access tokens live 24h, refresh tokens 365d.
Stored in Mongo `social_credentials` with docs like:
  {
    "provider": "tiktok", "admin_id": <uuid>, "open_id": ..., "union_id": ...,
    "access_token": ..., "refresh_token": ...,
    "token_expires_at": datetime, "refresh_expires_at": datetime,
    "scope": "user.info.basic,video.upload,video.publish",
  }
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger("tiktok_publisher")

TIKTOK_AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_CREATOR_INFO = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_POST_INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

SCOPES = "user.info.basic,video.upload,video.publish"


def is_app_configured() -> bool:
    return all(os.environ.get(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REDIRECT_URI"))


def make_pkce() -> tuple:
    """(code_verifier, code_challenge_b64url)."""
    verifier = secrets.token_urlsafe(64)[:64]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


def build_auth_url(state: str, code_challenge: str) -> str:
    params = {
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": os.environ["TIKTOK_REDIRECT_URI"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{TIKTOK_AUTH}?{urlencode(params)}"


async def exchange_code_and_store(db, admin_id: str, code: str, code_verifier: str) -> dict:
    if not is_app_configured():
        raise RuntimeError("TikTok app not configured (TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET missing).")

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(TIKTOK_TOKEN, data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": os.environ["TIKTOK_REDIRECT_URI"],
            "code_verifier": code_verifier,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    data = r.json()
    if "error" in data and data.get("error"):
        raise RuntimeError(f"TikTok token exchange failed: {data.get('error_description') or data.get('error')}")

    now = datetime.now(timezone.utc)
    doc = {
        "provider": "tiktok",
        "admin_id": admin_id,
        "open_id": data.get("open_id"),
        "union_id": data.get("union_id"),
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "scope": data.get("scope", SCOPES),
        "token_expires_at": now + timedelta(seconds=int(data.get("expires_in", 86400))),
        "refresh_expires_at": now + timedelta(seconds=int(data.get("refresh_expires_in", 31536000))),
        "connected_at": now,
    }
    await db["social_credentials"].update_one(
        {"provider": "tiktok", "admin_id": admin_id},
        {"$set": doc}, upsert=True,
    )
    return {"open_id": doc["open_id"], "scope": doc["scope"], "connected_at": now.isoformat()}


async def _refresh_if_needed(db, admin_id: str, creds: dict) -> dict:
    """Refresh TikTok access token if within 5 min of expiring. Returns fresh creds dict."""
    expires = creds.get("token_expires_at")
    if expires and isinstance(expires, datetime) and expires - datetime.now(timezone.utc) > timedelta(minutes=5):
        return creds
    # Refresh
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(TIKTOK_TOKEN, data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": creds["refresh_token"],
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = r.json()
    if "error" in data and data.get("error"):
        raise RuntimeError(f"TikTok refresh failed: {data.get('error_description') or data.get('error')}")
    now = datetime.now(timezone.utc)
    updates = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", creds["refresh_token"]),
        "token_expires_at": now + timedelta(seconds=int(data.get("expires_in", 86400))),
        "refresh_expires_at": now + timedelta(seconds=int(data.get("refresh_expires_in", 31536000))),
    }
    await db["social_credentials"].update_one(
        {"provider": "tiktok", "admin_id": admin_id},
        {"$set": updates},
    )
    creds.update(updates)
    return creds


async def get_credentials(db, admin_id: str, refresh: bool = True) -> Optional[dict]:
    doc = await db["social_credentials"].find_one({"provider": "tiktok", "admin_id": admin_id}, {"_id": 0})
    if not doc:
        return None
    if refresh:
        return await _refresh_if_needed(db, admin_id, doc)
    return doc


async def disconnect(db, admin_id: str) -> bool:
    r = await db["social_credentials"].delete_one({"provider": "tiktok", "admin_id": admin_id})
    return r.deleted_count > 0


async def verify_connection(db, admin_id: str) -> dict:
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "Not connected"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(TIKTOK_CREATOR_INFO, headers={
                "Authorization": f"Bearer {creds['access_token']}",
                "Content-Type": "application/json; charset=UTF-8",
            })
        j = r.json()
        err = j.get("error", {}).get("code", "ok")
        if err != "ok":
            return {"ok": False, "error": j.get("error", {}).get("message", "unknown")}
        data = j.get("data", {})
        return {"ok": True, "nickname": data.get("creator_nickname"),
                "username": data.get("creator_username"),
                "privacy_level_options": data.get("privacy_level_options", []),
                "can_public": "PUBLIC_TO_EVERYONE" in (data.get("privacy_level_options") or [])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def direct_post_video(db, admin_id: str, *, video_url: str, caption: str,
                              privacy: str = "SELF_ONLY") -> dict:
    """Init a Direct Post using PULL_FROM_URL. Returns publish_id + share URL.
    privacy: SELF_ONLY | MUTUAL_FOLLOW_FRIENDS | PUBLIC_TO_EVERYONE (audit required for public).
    """
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "TikTok not connected. Connect in Platform Settings first."}

    payload = {
        "post_info": {
            "title": (caption or "")[:2200],
            "privacy_level": privacy,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(TIKTOK_POST_INIT, headers={
                "Authorization": f"Bearer {creds['access_token']}",
                "Content-Type": "application/json; charset=UTF-8",
            }, json=payload)
        j = r.json()
        err = j.get("error", {}).get("code", "ok")
        if err != "ok":
            msg = j.get("error", {}).get("message", "unknown")
            return {"ok": False, "error": f"TikTok publish init failed ({err}): {msg}"}
        publish_id = j.get("data", {}).get("publish_id")
        return {"ok": True, "publish_id": publish_id}
    except Exception as e:
        log.exception("tiktok direct_post_video failed")
        return {"ok": False, "error": str(e)[:500]}


async def fetch_publish_status(db, admin_id: str, publish_id: str) -> dict:
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "Not connected"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(TIKTOK_STATUS, headers={
                "Authorization": f"Bearer {creds['access_token']}",
                "Content-Type": "application/json; charset=UTF-8",
            }, json={"publish_id": publish_id})
        j = r.json()
        err = j.get("error", {}).get("code", "ok")
        if err != "ok":
            return {"ok": False, "error": j.get("error", {}).get("message")}
        data = j.get("data", {})
        return {"ok": True, "status": data.get("status"), "public_available_post_id": data.get("publicly_available_post_id"),
                "raw": data}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
