"""Per-agent rate limiting middleware via Redis."""

from __future__ import annotations

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from brain.src.logger import get_logger
from brain.src.redis_client import get_redis

log = get_logger("rate_limit")

WINDOW_SECONDS = 60
MAX_REQUESTS = 120  # Per device per minute
RATE_LIMIT_PREFIX = "rl:"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Identify client by device_id from body or IP fallback
        client_id = request.client.host if request.client else "unknown"

        redis = get_redis()
        key = f"{RATE_LIMIT_PREFIX}{client_id}:{int(time.time()) // WINDOW_SECONDS}"

        current = await redis.get(key)
        count = int(current) if current else 0

        if count >= MAX_REQUESTS:
            log.warning("rate_limit_exceeded", client=client_id, count=count)
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        await redis.set(key, str(count + 1), ex=WINDOW_SECONDS)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(MAX_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(MAX_REQUESTS - count - 1)
        return response
