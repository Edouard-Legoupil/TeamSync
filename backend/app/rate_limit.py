"""Simple in-process rate limiting.

This is a per-worker sliding window (no Redis). It is a reasonable first line
of defense for auth and upload endpoints; for a multi-instance deployment put
the limit at the API gateway or back it with a shared store.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.max_calls:
            return False
        dq.append(now)
        return True


_limiter: SlidingWindowLimiter | None = None


def _get_limiter() -> SlidingWindowLimiter:
    global _limiter
    if _limiter is None:
        _limiter = SlidingWindowLimiter(max(1, settings.RATE_LIMIT_PER_MINUTE))
    return _limiter


def rate_limit(request: Request) -> None:
    """FastAPI dependency: reject a client IP over the configured rate."""
    if settings.RATE_LIMIT_PER_MINUTE <= 0:
        return
    key = request.client.host if request.client else "unknown"
    if not _get_limiter().allow(key):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
