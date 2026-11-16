"""Simple in-memory sliding-window rate limiting middleware.

Per-IP limit (default 120 requests/minute, env RATE_LIMIT_PER_MINUTE).
This protects the API from accidental floods; for multi-worker production
deployments use a shared store (Redis) — see README.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("zoya.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int | None = None):
        super().__init__(app)
        self.per_minute = per_minute or get_settings().rate_limit_per_minute
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Health checks and the docs are exempt from rate limiting.
        if request.url.path in ("/health", "/health/ready", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[client]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= self.per_minute:
            log.warning("Rate limit hit for %s", client)
            return JSONResponse({"detail": "Rate limit exceeded, try again later"}, status_code=429)
        window.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.per_minute - len(window)))
        return response
