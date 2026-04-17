"""Agent registration and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from brain.src.api.auth.jwt import create_agent_token
from brain.src.api.websocket.handler import manager
from brain.src.logger import get_logger

log = get_logger("agents_api")

router = APIRouter(prefix="/api/v1/agent", tags=["agents"])


class RegisterRequest(BaseModel):
    device_id: str
    platform: str
    device_name: str = ""
    capabilities: list[str] = []


class RegisterResponse(BaseModel):
    token: str
    device_id: str
    message: str


@router.post("/register", response_model=RegisterResponse)
async def register_agent(req: RegisterRequest, request: Request) -> RegisterResponse:
    """Register a new device agent and return a JWT token."""
    from brain.src.api.server import get_config
    config = get_config()

    token = create_agent_token(
        device_id=req.device_id,
        platform=req.platform,
        secret=config.jwt_secret,
        capabilities=req.capabilities,
    )

    log.info("agent_registered", device=req.device_id, platform=req.platform)

    return RegisterResponse(
        token=token,
        device_id=req.device_id,
        message=f"Agent {req.device_id} registered. Store this token securely.",
    )


@router.get("/status")
async def agent_status() -> dict:
    """Get online agents status."""
    return {
        "online_devices": manager.get_online_devices(),
        "count": len(manager.get_online_devices()),
    }
