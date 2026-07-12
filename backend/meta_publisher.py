"""
meta_publisher.py — Post to Facebook Page + Instagram Business account via Meta Graph API v20.0.

Credentials required in /app/backend/.env:
  META_APP_ID              # Meta App ID (dev.facebook.com)
  META_APP_SECRET          # Meta App Secret
  META_REDIRECT_URI        # e.g. https://ascendraacademy.com/api/social/meta/callback

OAuth flow stores in `social_credentials` Mongo collection with docs like:
  {
    "provider": "meta", "admin_id": <admin uuid>,
    "fb_page_id": "...", "fb_page_name": "Ascendra",
    "fb_page_token": "...",         # long-lived (~60 days, refreshes on use)
    "ig_business_id": "..." or None,
    "connected_at": datetime, "expires_at": datetime | None,
  }
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger("meta_publisher")

GRAPH_VERSION = "v20.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
OAUTH_DIALOG = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

PERMISSIONS = [
    "pages_show_list",
    "pages_manage_posts",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
]


def is_app_configured() -> bool:
    """App ID + Secret + redirect URI present in env (enough to start OAuth)."""
    return all(os.environ.get(k) for k in ("META_APP_ID", "META_APP_SECRET", "META_REDIRECT_URI"))


def build_auth_url(state: str) -> str:
    """Build the OAuth dialog URL the admin should be redirected to."""
    params = {
        "client_id": os.environ["META_APP_ID"],
        "redirect_uri": os.environ["META_REDIRECT_URI"],
        "state": state,
        "scope": ",".join(PERMISSIONS),
        "response_type": "code",
    }
    return f"{OAUTH_DIALOG}?{urlencode(params)}"


async def exchange_code_and_store(db, admin_id: str, code: str) -> dict:
    """Full OAuth exchange:
    1. code → short-lived user token
    2. short → long-lived user token (~60 days)
    3. long-lived user token → list of Pages + Page Access Tokens (already long-lived)
    4. For picked Page, fetch linked Instagram Business ID
    5. Persist to Mongo `social_credentials`
    """
    if not is_app_configured():
        raise RuntimeError("Meta app not configured (META_APP_ID/META_APP_SECRET/META_REDIRECT_URI missing).")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. code → short-lived user token
        r = await client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "client_id": os.environ["META_APP_ID"],
            "client_secret": os.environ["META_APP_SECRET"],
            "redirect_uri": os.environ["META_REDIRECT_URI"],
            "code": code,
        })
        _raise_for_meta(r, "token exchange")
        short_token = r.json()["access_token"]

        # 2. → long-lived user token
        r = await client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": os.environ["META_APP_ID"],
            "client_secret": os.environ["META_APP_SECRET"],
            "fb_exchange_token": short_token,
        })
        _raise_for_meta(r, "long-lived user token")
        ll_user_token = r.json()["access_token"]
        expires_in = int(r.json().get("expires_in", 60 * 24 * 3600))

        # 3. → list pages + page tokens
        r = await client.get(f"{GRAPH_BASE}/me/accounts", params={
            "fields": "id,name,access_token,category",
            "access_token": ll_user_token,
        })
        _raise_for_meta(r, "list pages")
        pages = r.json().get("data", [])
        if not pages:
            raise RuntimeError("No Facebook Pages found on this account. Create a Page first in Meta Business Suite.")

        # Use the first Page (most brands have one). For multi-page, we'd offer a picker.
        page = pages[0]
        page_id = page["id"]
        page_name = page.get("name", "Facebook Page")
        page_token = page["access_token"]  # Already long-lived by Graph rules

        # 4. → linked Instagram Business account
        r = await client.get(f"{GRAPH_BASE}/{page_id}", params={
            "fields": "instagram_business_account",
            "access_token": page_token,
        })
        _raise_for_meta(r, "fetch IG business account")
        ig_id = (r.json().get("instagram_business_account") or {}).get("id")

    # 5. Persist
    now = datetime.now(timezone.utc)
    doc = {
        "provider": "meta",
        "admin_id": admin_id,
        "fb_page_id": page_id,
        "fb_page_name": page_name,
        "fb_page_token": page_token,
        "ig_business_id": ig_id,
        "connected_at": now,
        "expires_at": now + timedelta(seconds=expires_in),
        "available_pages": [{"id": p["id"], "name": p.get("name")} for p in pages],
    }
    await db["social_credentials"].update_one(
        {"provider": "meta", "admin_id": admin_id},
        {"$set": doc}, upsert=True,
    )
    return {"fb_page_id": page_id, "fb_page_name": page_name, "ig_business_id": ig_id,
            "available_pages": doc["available_pages"]}


async def get_credentials(db, admin_id: str) -> Optional[dict]:
    doc = await db["social_credentials"].find_one({"provider": "meta", "admin_id": admin_id}, {"_id": 0})
    return doc


async def disconnect(db, admin_id: str) -> bool:
    r = await db["social_credentials"].delete_one({"provider": "meta", "admin_id": admin_id})
    return r.deleted_count > 0


async def verify_connection(db, admin_id: str) -> dict:
    """Ping /me on the stored page token to make sure it still works."""
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "Not connected"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{GRAPH_BASE}/{creds['fb_page_id']}", params={
                "fields": "id,name,followers_count",
                "access_token": creds["fb_page_token"],
            })
        if r.status_code != 200:
            return {"ok": False, "error": r.text[:300]}
        return {"ok": True, "page": r.json(), "ig_business_id": creds.get("ig_business_id")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─── Facebook Page posting ────────────────────────────────────────────────
async def post_to_facebook_page(db, admin_id: str, *, caption: str,
                                  image_urls: Optional[list] = None) -> dict:
    """Post to Facebook Page.
    - No images → simple text post.
    - 1 image → single-image post.
    - 2+ images → multi-photo post (creates unpublished photo objects, then posts w/ attached_media).
    Returns {"ok": True, "post_id": ..., "url": ...} or {"ok": False, "error": ...}.
    """
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "Facebook not connected. Connect in Platform Settings first."}
    page_id = creds["fb_page_id"]
    token = creds["fb_page_token"]
    image_urls = image_urls or []

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if not image_urls:
                # Plain text feed post
                r = await client.post(f"{GRAPH_BASE}/{page_id}/feed", data={
                    "message": caption, "access_token": token,
                })
                _raise_for_meta(r, "FB text post")
                pid = r.json()["id"]
            elif len(image_urls) == 1:
                # Single photo
                r = await client.post(f"{GRAPH_BASE}/{page_id}/photos", data={
                    "url": image_urls[0], "caption": caption, "published": "true",
                    "access_token": token,
                })
                _raise_for_meta(r, "FB single photo")
                pid = r.json().get("post_id") or r.json().get("id")
            else:
                # Multi-photo: upload each as unpublished, then feed-post w/ attached_media
                media_fbids = []
                for url in image_urls[:10]:
                    r = await client.post(f"{GRAPH_BASE}/{page_id}/photos", data={
                        "url": url, "published": "false", "access_token": token,
                    })
                    _raise_for_meta(r, "FB unpublished photo")
                    media_fbids.append({"media_fbid": r.json()["id"]})
                # Attach and post to feed. Meta wants attached_media as JSON string per item.
                import json as _json
                attached = {f"attached_media[{i}]": _json.dumps(m) for i, m in enumerate(media_fbids)}
                r = await client.post(f"{GRAPH_BASE}/{page_id}/feed", data={
                    "message": caption, "access_token": token, **attached,
                })
                _raise_for_meta(r, "FB multi-photo feed post")
                pid = r.json()["id"]

        return {"ok": True, "post_id": pid, "url": f"https://facebook.com/{pid}"}
    except Exception as e:
        log.exception("FB post failed")
        return {"ok": False, "error": str(e)[:500]}


# ─── Instagram posting ────────────────────────────────────────────────────
async def _poll_ig_container(client: httpx.AsyncClient, container_id: str, token: str,
                              tries: int = 20, delay: float = 3.0) -> str:
    """Poll container status until FINISHED or ERROR. Returns final status."""
    import asyncio
    for _ in range(tries):
        r = await client.get(f"{GRAPH_BASE}/{container_id}", params={
            "fields": "status_code", "access_token": token,
        })
        code = r.json().get("status_code")
        if code == "FINISHED":
            return "FINISHED"
        if code == "ERROR":
            return "ERROR"
        await asyncio.sleep(delay)
    return "TIMEOUT"


async def post_to_instagram(db, admin_id: str, *, caption: str,
                              image_urls: Optional[list] = None,
                              video_url: Optional[str] = None,
                              as_reel: bool = False) -> dict:
    """Post to Instagram Business.
    - 1 image → single image
    - 2\u201310 images → carousel
    - video_url + as_reel=True → Reel
    """
    creds = await get_credentials(db, admin_id)
    if not creds:
        return {"ok": False, "error": "Instagram not connected. Connect Facebook first (which pairs with IG)."}
    ig_id = creds.get("ig_business_id")
    if not ig_id:
        return {"ok": False, "error": "No Instagram Business account linked to this Facebook Page. Convert your IG to Business/Creator inside the IG app first."}
    token = creds["fb_page_token"]
    image_urls = image_urls or []

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            if video_url and as_reel:
                # Reel
                r = await client.post(f"{GRAPH_BASE}/{ig_id}/media", data={
                    "media_type": "REELS", "video_url": video_url, "caption": caption,
                    "access_token": token,
                })
                _raise_for_meta(r, "IG reel container")
                cid = r.json()["id"]
                status = await _poll_ig_container(client, cid, token, tries=25, delay=4.0)
                if status != "FINISHED":
                    return {"ok": False, "error": f"Reel processing {status}"}
            elif len(image_urls) == 1:
                r = await client.post(f"{GRAPH_BASE}/{ig_id}/media", data={
                    "image_url": image_urls[0], "caption": caption, "access_token": token,
                })
                _raise_for_meta(r, "IG single image container")
                cid = r.json()["id"]
            elif len(image_urls) >= 2:
                # Carousel (2\u201310 items)
                child_ids = []
                for url in image_urls[:10]:
                    r = await client.post(f"{GRAPH_BASE}/{ig_id}/media", data={
                        "image_url": url, "is_carousel_item": "true", "access_token": token,
                    })
                    _raise_for_meta(r, "IG carousel child")
                    child_ids.append(r.json()["id"])
                r = await client.post(f"{GRAPH_BASE}/{ig_id}/media", data={
                    "media_type": "CAROUSEL", "children": ",".join(child_ids),
                    "caption": caption, "access_token": token,
                })
                _raise_for_meta(r, "IG carousel parent")
                cid = r.json()["id"]
            else:
                return {"ok": False, "error": "Instagram requires at least 1 image or a video."}

            # Publish
            r = await client.post(f"{GRAPH_BASE}/{ig_id}/media_publish", data={
                "creation_id": cid, "access_token": token,
            })
            _raise_for_meta(r, "IG publish")
            media_id = r.json()["id"]

        return {"ok": True, "post_id": media_id, "url": f"https://www.instagram.com/p/{media_id}"}
    except Exception as e:
        log.exception("IG post failed")
        return {"ok": False, "error": str(e)[:500]}


def _raise_for_meta(r: httpx.Response, context: str) -> None:
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
            msg = err.get("message") or r.text[:300]
            code = err.get("code")
            raise RuntimeError(f"Meta {context} failed ({code}): {msg}")
        except (ValueError, KeyError):
            raise RuntimeError(f"Meta {context} failed: HTTP {r.status_code} — {r.text[:300]}")
