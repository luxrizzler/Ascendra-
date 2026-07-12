"""
x_publisher.py — Post tweet threads with media to X (Twitter) brand account.

Uses tweepy with OAuth 1.0a User Context (the only auth that lets Free tier
post tweets). Tweet creation goes via API v2 (Client); media upload still
goes via API v1.1 (API) per X's current architecture.

Env vars (all required):
  X_API_KEY                # Consumer Key
  X_API_SECRET             # Consumer Secret (Secret Key)
  X_ACCESS_TOKEN           # User Access Token (the brand account's token)
  X_ACCESS_TOKEN_SECRET    # User Access Token Secret
  X_HANDLE                 # e.g. "AscendraAcademy" (no @) — display only

Free-tier posture (Ascendra runs on X Free tier by choice):
  • Free tier allows ~500 tweets/month per app (verify current at developer.x.com)
  • We track every posted tweet in Mongo (`x_post_log`) so the UI can show usage
    and hard-refuse to post when the monthly budget is exhausted.
  • Rate-limit ceiling per 24h is ~50 tweets; we soft-warn at 40/day.
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger("x_publisher")

# Free-tier budget knobs (env-overridable if X changes their pricing)
MONTHLY_POST_LIMIT = int(os.environ.get("X_MONTHLY_POST_LIMIT", "500"))
DAILY_POST_LIMIT = int(os.environ.get("X_DAILY_POST_LIMIT", "50"))
WARN_MONTHLY_REMAINING = int(os.environ.get("X_WARN_MONTHLY_REMAINING", "50"))
WARN_DAILY_REMAINING = int(os.environ.get("X_WARN_DAILY_REMAINING", "10"))


def is_configured() -> bool:
    return all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"))


def handle() -> str:
    return os.environ.get("X_HANDLE", "").strip().lstrip("@") or "your-brand"


def _clients():
    """Build tweepy v1.1 API (for media upload) + v2 Client (for tweets/verify)."""
    import tweepy
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_TOKEN_SECRET"]
    # v1.1 for media upload (still supported on Free tier)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    # v2 client for posting tweets AND verifying credentials (v2 users/me is free-tier friendly)
    client_v2 = tweepy.Client(
        consumer_key=api_key, consumer_secret=api_secret,
        access_token=access_token, access_token_secret=access_secret,
    )
    return api_v1, client_v2


def verify_credentials() -> dict:
    """Verify the 4 X tokens work by calling v2 users/me (free-tier-safe read).
    Returns {ok, screen_name, user_id, name} or {ok:false, error}.
    """
    if not is_configured():
        return {"ok": False, "error": "X credentials not set in .env"}
    try:
        _, client_v2 = _clients()
        me = client_v2.get_me(user_auth=True, user_fields=["username", "name"])
        if not me or not getattr(me, "data", None):
            return {"ok": False, "error": "Empty response from X users/me"}
        u = me.data
        return {"ok": True, "screen_name": u.username, "user_id": str(u.id), "name": u.name}
    except Exception as e:
        log.exception("X verify_credentials failed")
        return {"ok": False, "error": str(e)[:300]}


def _upload_image_bytes(api_v1, png_bytes: bytes, filename: str = "slide.png") -> Optional[str]:
    """Upload a PNG via v1.1 media/upload. Returns media_id_string.
    Media uploads DO NOT count against the monthly tweet quota on Free tier.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(png_bytes)
        tmp_path = tf.name
    try:
        media = api_v1.media_upload(filename=tmp_path)
        return media.media_id_string
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def post_thread(tweets: list, image_bytes_list: Optional[list] = None,
                 hashtags: Optional[list] = None) -> dict:
    """Post a tweet thread (each tweet replies to the previous).
    Tweet 1 gets up to 4 images (X limit). Returns dict with tweet_ids + first_url.
    NOTE: Budget checking + logging is done in the calling endpoint (has db access).
    """
    if not tweets:
        return {"ok": False, "error": "No tweets to post"}
    if not is_configured():
        return {"ok": False, "error": "X not configured. Add X_API_KEY etc to .env"}
    try:
        api_v1, client_v2 = _clients()
    except Exception as e:
        return {"ok": False, "error": f"Auth init failed: {e}"}

    # Upload up to 4 images for the first tweet (free)
    media_ids: list = []
    if image_bytes_list:
        for i, png in enumerate(image_bytes_list[:4]):
            try:
                mid = _upload_image_bytes(api_v1, png, filename=f"slide_{i}.png")
                if mid:
                    media_ids.append(mid)
            except Exception as e:
                log.warning(f"media upload {i} failed: {e}")

    # Append hashtags to last tweet if room
    tweets = list(tweets)
    if hashtags:
        tag_line = " ".join([h if h.startswith("#") else f"#{h}" for h in hashtags])
        if len(tweets[-1]) + len(tag_line) + 2 <= 270:
            tweets[-1] = tweets[-1].rstrip() + "\n\n" + tag_line

    tweet_ids: list = []
    reply_to: Optional[str] = None
    for i, text in enumerate(tweets):
        text = (text or "").strip()
        if not text:
            continue
        if len(text) > 280:
            text = text[:277] + "..."
        kwargs: dict = {"text": text}
        if i == 0 and media_ids:
            kwargs["media_ids"] = media_ids
        if reply_to:
            kwargs["in_reply_to_tweet_id"] = reply_to
        try:
            resp = client_v2.create_tweet(**kwargs)
            tid = resp.data.get("id") if hasattr(resp, "data") else None
            if not tid:
                return {"ok": False, "error": f"Unexpected response on tweet {i+1}: {resp}", "tweet_ids": tweet_ids}
            tweet_ids.append(tid)
            reply_to = tid
        except Exception as e:
            log.exception(f"create_tweet {i} failed")
            err = str(e)[:300]
            # Detect free-tier limit errors and surface them clearly
            if "429" in err or "rate limit" in err.lower() or "usage cap" in err.lower() or "monthly" in err.lower():
                return {"ok": False, "error": f"X free-tier limit hit: {err}",
                         "tweet_ids": tweet_ids, "quota_error": True}
            return {"ok": False, "error": f"Tweet {i+1} failed: {err}", "tweet_ids": tweet_ids}

    first_url = f"https://x.com/{handle()}/status/{tweet_ids[0]}" if tweet_ids else None
    return {"ok": True, "tweet_ids": tweet_ids, "first_url": first_url, "count": len(tweet_ids)}


# ─── Free-tier budget tracking (uses Mongo `x_post_log` collection) ───────────────
async def get_budget(db) -> dict:
    """Return current usage vs. Free tier limits (monthly + daily).
    Reads from `x_post_log` collection where each document represents one
    successfully-posted tweet.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    month_used = await db["x_post_log"].count_documents({
        "posted_at": {"$gte": month_start}, "success": True,
    })
    day_used = await db["x_post_log"].count_documents({
        "posted_at": {"$gte": day_start}, "success": True,
    })
    month_remaining = max(0, MONTHLY_POST_LIMIT - month_used)
    day_remaining = max(0, DAILY_POST_LIMIT - day_used)

    return {
        "month": {
            "used": month_used,
            "limit": MONTHLY_POST_LIMIT,
            "remaining": month_remaining,
            "percent": round(month_used / MONTHLY_POST_LIMIT * 100, 1),
            "warn": month_remaining <= WARN_MONTHLY_REMAINING,
            "blocked": month_remaining <= 0,
            "resets_at": (month_start + timedelta(days=32)).replace(day=1).isoformat(),
        },
        "day": {
            "used": day_used,
            "limit": DAILY_POST_LIMIT,
            "remaining": day_remaining,
            "percent": round(day_used / DAILY_POST_LIMIT * 100, 1),
            "warn": day_remaining <= WARN_DAILY_REMAINING,
            "blocked": day_remaining <= 0,
            "resets_at": (day_start + timedelta(days=1)).isoformat(),
        },
        "can_post": month_remaining > 0 and day_remaining > 0,
    }


async def check_budget_or_reason(db, needed: int = 1) -> Optional[str]:
    """Return None if we can safely post `needed` tweets, else a human-readable
    reason string explaining which limit blocks us.
    """
    b = await get_budget(db)
    if b["month"]["remaining"] < needed:
        return (f"Monthly X free-tier budget exhausted: {b['month']['used']}/{b['month']['limit']} used. "
                f"Resets on the 1st of next month. Upgrade to Basic ($200/mo) at developer.x.com or wait for reset.")
    if b["day"]["remaining"] < needed:
        return (f"Daily X posting cap reached: {b['day']['used']}/{b['day']['limit']} tweets today. "
                f"Tomorrow the daily counter resets. (Monthly quota still has {b['month']['remaining']} left.)")
    return None


async def log_tweets_posted(db, count: int, tweet_ids: list, source: str = "manual",
                              post_id: Optional[str] = None) -> None:
    """Insert one document per successfully-posted tweet for accurate budget accounting."""
    if count <= 0:
        return
    now = datetime.now(timezone.utc)
    docs = []
    for i in range(count):
        docs.append({
            "posted_at": now,
            "success": True,
            "source": source,           # "manual" | "scheduled" | "test" etc.
            "post_id": post_id,          # link back to social post row if applicable
            "tweet_id": tweet_ids[i] if i < len(tweet_ids) else None,
        })
    if docs:
        await db["x_post_log"].insert_many(docs)
