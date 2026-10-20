"""Small security helpers shared by API routes and middleware."""

from __future__ import annotations

import hmac
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowRateLimiter:
    """In-process rate limiter suitable for a single-instance deployment.

    For multi-instance production deployments use a shared store (for example
    Redis) so limits apply across workers.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._events[key]
            while bucket and now - bucket[0] > window_s:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = SlidingWindowRateLimiter()


def client_key(request: Request, scope: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return f"{scope}:{host}"


def enforce_rate_limit(request: Request, scope: str, limit: int, window_s: float) -> None:
    if not rate_limiter.allow(client_key(request, scope), limit, window_s):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {scope}. Try again later.",
            headers={"Retry-After": str(int(window_s))},
        )


def configured_ingest_key() -> str:
    return os.environ.get("IOT_INGEST_API_KEY", "").strip()


def verify_ingest_key(candidate: str | None) -> bool:
    expected = configured_ingest_key()
    if not expected:
        return False
    if not candidate:
        return False
    return hmac.compare_digest(candidate, expected)


