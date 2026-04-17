"""JWT token generation and validation for agent authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt

from brain.src.logger import get_logger

log = get_logger("jwt")

_ALGORITHM = "HS256"
_TOKEN_EXPIRY_DAYS = 365  # Agent tokens are long-lived


def create_agent_token(
    device_id: str,
    platform: str,
    secret: str,
    capabilities: list[str] | None = None,
    expiry_days: int = _TOKEN_EXPIRY_DAYS,
) -> str:
    """Create a signed JWT for a device agent."""
    now = datetime.utcnow()
    payload = {
        "sub": device_id,
        "platform": platform,
        "capabilities": capabilities or [],
        "iat": now,
        "exp": now + timedelta(days=expiry_days),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, secret, algorithm=_ALGORITHM)
    log.info("token_created", device=device_id, platform=platform)
    return token


def verify_agent_token(token: str, secret: str) -> dict[str, Any] | None:
    """Verify and decode a JWT. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        log.warning("token_expired")
        return None
    except jwt.InvalidTokenError as e:
        log.warning("token_invalid", error=str(e))
        return None


def extract_token(authorization: str) -> str | None:
    """Extract token from 'Bearer <token>' header value."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None
