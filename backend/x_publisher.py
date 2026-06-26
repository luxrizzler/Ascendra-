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
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
from typing import Optional

log = logging.getLogger("x_publisher")


def is_configured() -> bool:
    return all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"))


def handle() -> str:
    return os.environ.get("X_HANDLE", "").strip().lstrip("@") or "your-brand"


def _clients():
    """Build tweepy v1.1 API (for media upload) + v2 Client (for tweets)."""
    import tweepy
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_TOKEN_SECRET"]
    # v1.1 for media upload
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    # v2 client for posting tweets
    client_v2 = tweepy.Client(
        consumer_key=api_key, consumer_secret=api_secret,
        access_token=access_token, access_token_secret=access_secret,
    )
    return api_v1, client_v2


def verify_credentials() -> dict:
    """Verify the 4 X tokens work. Returns {ok, screen_name, user_id} or {ok:false, error}."""
    if not is_configured():
        return {"ok": False, "error": "X credentials not set in .env"}
    try:
        api_v1, _ = _clients()
        me = api_v1.verify_credentials()
        return {"ok": True, "screen_name": me.screen_name, "user_id": me.id_str, "name": getattr(me, "name", None)}
    except Exception as e:
        log.exception("X verify_credentials failed")
        return {"ok": False, "error": str(e)[:300]}


def _upload_image_bytes(api_v1, png_bytes: bytes, filename: str = "slide.png") -> Optional[str]:
    """Upload a PNG via v1.1 media/upload. Returns media_id_string."""
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
    """
    if not tweets:
        return {"ok": False, "error": "No tweets to post"}
    if not is_configured():
        return {"ok": False, "error": "X not configured. Add X_API_KEY etc to .env"}
    try:
        api_v1, client_v2 = _clients()
    except Exception as e:
        return {"ok": False, "error": f"Auth init failed: {e}"}

    # Upload up to 4 images for the first tweet
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
        # Try to append to last tweet; if too long, leave alone
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
            return {"ok": False, "error": f"Tweet {i+1} failed: {str(e)[:300]}", "tweet_ids": tweet_ids}

    first_url = f"https://x.com/{handle()}/status/{tweet_ids[0]}" if tweet_ids else None
    return {"ok": True, "tweet_ids": tweet_ids, "first_url": first_url, "count": len(tweet_ids)}
