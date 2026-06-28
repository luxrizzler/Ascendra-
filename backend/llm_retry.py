"""
llm_retry.py — Centralized retry-with-backoff for LLM calls.

The Emergent LLM proxy (and the providers behind it — OpenAI, Anthropic,
Google) all return 429 / 503 on transient overload. Every callsite in
Ascendra needs the same retry behavior. This module gives them one.

Use as a decorator OR a direct async wrapper:

    from llm_retry import with_llm_retry

    @with_llm_retry(max_retries=4)
    async def call_claude(...):
        ...

    # or

    result = await llm_call_with_retry(lambda: do_the_thing(), max_retries=4)

It also exposes `is_transient_llm_error(exc)` for callers that just want to
classify an error.
"""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Awaitable, Callable, TypeVar, Optional

log = logging.getLogger("ascendra.llm_retry")

T = TypeVar("T")

# Backoff schedule (seconds): grows from 2s → 30s. Total worst-case ~62s
# over 5 attempts — large enough to ride out a brief Emergent rate-limit
# burst (caps are typically per-minute).
DEFAULT_BACKOFF = [2, 5, 10, 20, 30]


def is_transient_llm_error(exc: BaseException) -> bool:
    """Return True if the exception looks like a retry-worthy LLM transient.

    Recognizes:
      - 429 rate limits (incl. Emergent concurrent_request_limit)
      - 502 / 503 / 504 transient gateway errors
      - Connection timeouts / reset errors
      - Provider-side "overloaded_error" (Anthropic)
    """
    msg = str(exc).lower()
    return (
        "429" in msg
        or "rate" in msg
        or "concurren" in msg                 # "concurrent_request_limit"
        or "timeout" in msg
        or "timed out" in msg
        or "503" in msg
        or "502" in msg
        or "504" in msg
        or "overloaded" in msg
        or "service unavailable" in msg
        or "connection reset" in msg
    )


async def llm_call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 4,
    backoff: Optional[list[int]] = None,
    label: str = "llm",
) -> T:
    """Run an async LLM call with exponential backoff on transient errors.

    Raises the last exception if all attempts fail.
    """
    schedule = backoff or DEFAULT_BACKOFF
    last_err: Optional[BaseException] = None
    for attempt in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            last_err = e
            if not is_transient_llm_error(e) or attempt == max_retries - 1:
                log.warning(f"[{label}] final failure on attempt {attempt+1}: {str(e)[:240]}")
                raise
            wait = schedule[min(attempt, len(schedule) - 1)]
            log.info(f"[{label}] transient error attempt {attempt+1}/{max_retries}, retrying in {wait}s — {str(e)[:140]}")
            await asyncio.sleep(wait)
    # Unreachable, but mypy peace of mind
    assert last_err is not None
    raise last_err


def with_llm_retry(
    *,
    max_retries: int = 4,
    backoff: Optional[list[int]] = None,
    label: Optional[str] = None,
):
    """Decorator form of `llm_call_with_retry`. Usage:

        @with_llm_retry(max_retries=4, label="lesson-draft")
        async def generate_lesson_draft(...):
            ...
    """
    def deco(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            lbl = label or fn.__name__
            return await llm_call_with_retry(
                lambda: fn(*args, **kwargs),
                max_retries=max_retries,
                backoff=backoff,
                label=lbl,
            )
        return wrapper
    return deco


def friendly_llm_error(exc: BaseException) -> str:
    """Convert an LLM exception into a user-facing message (no stack traces)."""
    if is_transient_llm_error(exc):
        msg = str(exc).lower()
        if "concurren" in msg or "rate" in msg or "429" in msg:
            return "The AI is busy right now. Please wait ~30 seconds and try again."
        if "overloaded" in msg:
            return "The AI provider is overloaded. Please try again in a minute."
        if "timeout" in msg or "timed out" in msg:
            return "The AI took too long to respond. Please try again."
        return "Temporary AI hiccup. Please try again in a moment."
    # Non-transient — leak a trimmed message but no stack
    return f"AI generation failed: {str(exc)[:200]}"
