"""
social_media_signer.py — HMAC-signed public URLs for social platforms to fetch our
generated slides/videos WITHOUT admin JWT auth.

Meta and TikTok fetch media by URL directly (PULL_FROM_URL). Those calls come
from their servers (not our admin's browser) and have NO Authorization header.
So we mint short-TTL signed URLs that the platform can hit anonymously.

Security model:
- Sign (post_id, kind, index, expiry) with HMAC-SHA256 using SOCIAL_MEDIA_SIGNING_SECRET.
- Signature has a short TTL (default 30 min) to prevent enumeration/replay.
- No secret data leaves the server; the signed URL is opaque to Meta/TikTok.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional


def _secret() -> bytes:
    s = os.environ.get("SOCIAL_MEDIA_SIGNING_SECRET", "").strip()
    if not s:
        # Fall back to JWT_SECRET (already set) so we always have SOMETHING
        s = os.environ.get("JWT_SECRET", "ascendra-dev-secret-do-not-use")
    return s.encode("utf-8")


def sign(post_id: str, kind: str, index: int = 0, ttl_seconds: int = 1800) -> str:
    """kind: 'slide' or 'video'. Returns url-safe base64 signature blob."""
    expiry = int(time.time()) + ttl_seconds
    payload = f"{post_id}|{kind}|{index}|{expiry}".encode("utf-8")
    mac = hmac.new(_secret(), payload, hashlib.sha256).digest()
    body = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    sig = base64.urlsafe_b64encode(mac).decode("ascii").rstrip("=")
    return f"{body}.{sig}"


def verify(token: str) -> Optional[dict]:
    """Return {'post_id', 'kind', 'index'} if valid + unexpired, else None."""
    try:
        body_b64, sig_b64 = token.split(".", 1)
        # Restore padding for base64
        def _pad(s: str) -> str: return s + "=" * (-len(s) % 4)
        payload = base64.urlsafe_b64decode(_pad(body_b64))
        expected = hmac.new(_secret(), payload, hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(_pad(sig_b64))
        if not hmac.compare_digest(expected, actual):
            return None
        pid, kind, idx, expiry = payload.decode("utf-8").split("|")
        if int(expiry) < int(time.time()):
            return None
        return {"post_id": pid, "kind": kind, "index": int(idx)}
    except Exception:
        return None


def make_slide_url(base_url: str, post_id: str, idx: int, ttl_seconds: int = 1800) -> str:
    tok = sign(post_id, "slide", idx, ttl_seconds)
    return f"{base_url.rstrip('/')}/api/social/media/{tok}/slide/{idx}.png"


def make_video_url(base_url: str, post_id: str, ttl_seconds: int = 1800) -> str:
    tok = sign(post_id, "video", 0, ttl_seconds)
    return f"{base_url.rstrip('/')}/api/social/media/{tok}/video.mp4"
