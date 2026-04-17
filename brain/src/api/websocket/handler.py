"""WebSocket connection manager for agent communication."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from brain.src.api.websocket.events import dispatch_event
from brain.src.logger import get_logger

log = get_logger("websocket")


class ConnectionManager:
    """Manages active WebSocket connections from device agents."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}  # device_id -> websocket

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[device_id] = websocket
        log.info("agent_connected", device=device_id, total=len(self._connections))

    def disconnect(self, device_id: str) -> None:
        self._connections.pop(device_id, None)
        log.info("agent_disconnected", device=device_id, total=len(self._connections))

    async def send_to_device(self, device_id: str, data: dict) -> bool:
        ws = self._connections.get(device_id)
        if ws:
            try:
                await ws.send_json(data)
                return True
            except Exception as e:
                log.error("send_failed", device=device_id, error=str(e))
                self.disconnect(device_id)
        return False

    async def broadcast(self, data: dict, exclude: str | None = None) -> None:
        for device_id, ws in list(self._connections.items()):
            if device_id == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(device_id)

    def get_online_devices(self) -> list[str]:
        return list(self._connections.keys())

    def is_online(self, device_id: str) -> bool:
        return device_id in self._connections


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, brain: Any, jwt_secret: str = "") -> None:
    """Main WebSocket endpoint. Handles agent lifecycle with JWT auth."""
    device_id: str | None = None

    try:
        # First message must be agent_connect
        await websocket.accept()
        raw = await websocket.receive_text()
        data = json.loads(raw)

        if data.get("event") != "agent_connect":
            await websocket.send_json({"event": "error", "detail": "First message must be agent_connect"})
            await websocket.close()
            return

        device_id = data.get("device_id", "")
        if not device_id:
            await websocket.send_json({"event": "error", "detail": "device_id required"})
            await websocket.close()
            return

        # JWT auth (if secret is configured)
        token = data.get("token", "")
        agent_payload: dict = {}
        if jwt_secret:
            from brain.src.api.auth.jwt import verify_agent_token
            if not token:
                await websocket.send_json({"event": "error", "detail": "Authentication required. Include 'token' in agent_connect."})
                await websocket.close()
                return
            agent_payload = verify_agent_token(token, jwt_secret) or {}
            if not agent_payload:
                await websocket.send_json({"event": "error", "detail": "Invalid or expired token."})
                await websocket.close()
                return
            # Verify device_id matches token
            if agent_payload.get("sub") != device_id:
                await websocket.send_json({"event": "error", "detail": "Token device_id mismatch."})
                await websocket.close()
                return
            log.info("agent_authenticated", device=device_id)

        # Re-register with accepted socket
        manager._connections[device_id] = websocket
        await brain.register_device(device_id)

        # Send connection ack
        await websocket.send_json({
            "event": "connected",
            "device_id": device_id,
            "online_devices": manager.get_online_devices(),
        })

        # Check for pending cross-device tasks
        pending = await brain.working.get_cross_device_tasks()
        for task in pending:
            if task.get("trigger_device") == device_id or task.get("trigger_condition") == "device_online":
                await websocket.send_json({
                    "event": "pending_task",
                    "task": task,
                })

        log.info("agent_session_started", device=device_id, platform=data.get("platform", "unknown"))

        # Main message loop
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            event = message.get("event", "")

            response = await dispatch_event(event, message, device_id, brain, manager)
            if response:
                await websocket.send_json(response)

    except WebSocketDisconnect:
        log.info("agent_ws_disconnected", device=device_id)
    except Exception as e:
        log.error("agent_ws_error", device=device_id, error=str(e))
    finally:
        if device_id:
            manager.disconnect(device_id)
            await brain.unregister_device(device_id)
