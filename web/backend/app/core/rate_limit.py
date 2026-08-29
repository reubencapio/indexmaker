"""
Request rate limiting.

`RATE_LIMIT_PER_MINUTE` existed as a setting for a long time with nothing reading
it. This implements it, with a tighter separate budget for the endpoints that spend
money per call -- an unmetered path to a paid LLM API is a billing incident waiting
to happen, and the access logs already show bots sweeping the host.

Counters are per-process and in-memory. That is sufficient for the current
single-instance deployment and degrades gracefully: running N instances multiplies
the effective limit by N rather than failing open entirely. Moving to a shared
Redis counter is the natural next step once the worker is split out.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

# Paths that must never be limited: health checks keep the platform from cycling
# the instance, and CORS preflight failures surface as opaque browser errors.
EXEMPT_PATHS = frozenset({"/health", "/", "/api/openapi.json", "/api/docs", "/api/redoc"})

# Endpoints that cost real money per call, limited separately and far more tightly
# than ordinary reads.
EXPENSIVE_PATH_MARKERS = ("/ai/create", "/ai/generate")

# Stop tracking a client once it has been idle for longer than the widest window,
# so the counter map cannot grow without bound under a sweep from many addresses.
IDLE_EVICTION_SECONDS = 3600


class _SlidingWindow:
    """Per-key sliding window counters."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    def allow(self, key: str, limit: int, window_seconds: float, now: float) -> bool:
        hits = self._hits[key]
        cutoff = now - window_seconds

        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= limit:
            return False

        hits.append(now)
        return True

    def retry_after(self, key: str, window_seconds: float, now: float) -> int:
        """Whole seconds until the oldest hit in the window expires."""
        hits = self._hits.get(key)
        if not hits:
            return 1
        return max(1, int(window_seconds - (now - hits[0])) + 1)

    def sweep(self, now: float) -> None:
        """Drop keys that have gone quiet, bounding memory under address sweeps."""
        if now - self._last_sweep < 60:
            return
        self._last_sweep = now
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] > IDLE_EVICTION_SECONDS
        ]
        for key in stale:
            del self._hits[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Fixed budget per client per window, with a separate budget for costly endpoints.

    Must be installed *inside* CORSMiddleware. A 429 returned from outside the CORS
    layer carries no CORS headers, and the browser then reports a misleading cross
    origin failure instead of the rate limit.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int,
        expensive_per_hour: int,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.expensive_per_hour = expensive_per_hour
        self._general = _SlidingWindow()
        self._expensive = _SlidingWindow()

    def _client_key(self, request: Request) -> str:
        """
        Identify the caller.

        Koyeb terminates TLS upstream, so the socket address is the proxy's. The
        left-most X-Forwarded-For entry is the originating client. This trusts the
        proxy to set that header, which holds because the app is not reachable
        except through it.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path

        # Preflight carries no credentials and cannot itself cause load.
        if request.method == "OPTIONS" or path in EXEMPT_PATHS:
            return await call_next(request)

        now = time.monotonic()
        key = self._client_key(request)

        self._general.sweep(now)
        self._expensive.sweep(now)

        if any(marker in path for marker in EXPENSIVE_PATH_MARKERS):
            if not self._expensive.allow(key, self.expensive_per_hour, 3600.0, now):
                return self._too_many(self._expensive.retry_after(key, 3600.0, now))

        if not self._general.allow(key, self.requests_per_minute, 60.0, now):
            return self._too_many(self._general.retry_after(key, 60.0, now))

        return await call_next(request)

    @staticmethod
    def _too_many(retry_after: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down and try again."},
            headers={"Retry-After": str(retry_after)},
        )
