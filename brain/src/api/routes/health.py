"""Health check endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from brain.src.__version__ import __version__
from brain.src.redis_client import get_redis

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health(request: Request) -> dict:
    redis = get_redis()
    redis_ok = False
    try:
        redis_ok = await redis.ping()
    except Exception:
        pass

    brain_status = {}
    if hasattr(request.app.state, "brain"):
        brain_status = await request.app.state.brain.get_status()

    return {
        "status": "ok",
        "version": __version__,
        "uptime_seconds": round(time.time() - _start_time),
        "redis": "connected" if redis_ok else "unavailable",
        "brain": brain_status,
    }
