"""WebSocket client with auto-reconnect + REST fallback for agent-to-brain communication."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import websockets
import httpx

log = logging.getLogger("jarvis.connection")


class BrainConnection:
    """Manages the agent's connection to the cloud brain."""

    def __init__(
        self,
        ws_url: str,
        rest_url: str,
        device_id: str,
        platform: str,
        capabilities: list[str],
        token: str = "",
        on_message: Callable | None = None,
    ) -> None:
        self.ws_url = ws_url
        self.rest_url = rest_url
        self.device_id = device_id
        self.platform = platform
        self.capabilities = capabilities
        self.token = token
        self._on_message = on_message
        self._ws: Any = None
        self._connected = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Connect to brain via WebSocket with auto-reconnect."""
        while True:
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                self._ws = await websockets.connect(self.ws_url, additional_headers=headers)

                # Send agent_connect as first message
                await self._ws.send(json.dumps({
                    "event": "agent_connect",
                    "device_id": self.device_id,
                    "platform": self.platform,
                    "capabilities": self.capabilities,
                }))

                # Wait for connected ack
                raw = await self._ws.recv()
                data = json.loads(raw)
                if data.get("event") == "connected":
                    self._connected = True
                    self._reconnect_delay = 1.0
                    log.info("Connected to brain as %s", self.device_id)

                    # Check for pending tasks
                    if data.get("event") == "pending_task":
                        if self._on_message:
                            await self._on_message(data)

                # Main receive loop
                async for raw in self._ws:
                    message = json.loads(raw)
                    if self._on_message:
                        await self._on_message(message)

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                self._connected = False
                log.warning("Connection lost: %s. Reconnecting in %.0fs...", e, self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

            except Exception as e:
                self._connected = False
                log.error("Unexpected error: %s", e)
                await asyncio.sleep(self._reconnect_delay)

    async def send(self, event: str, data: dict | None = None) -> None:
        """Send a message to the brain."""
        payload = {"event": event, "device_id": self.device_id}
        if data:
            payload.update(data)

        if self._ws and self._connected:
            try:
                await self._ws.send(json.dumps(payload))
                return
            except Exception as e:
                log.warning("WebSocket send failed: %s, falling back to REST", e)

        # REST fallback
        await self._rest_send(event, payload)

    async def send_input(self, text: str) -> None:
        await self.send("user_input", {"text": text})

    async def send_action_result(self, action_id: str, status: str, details: str = "") -> None:
        await self.send("action_result", {
            "action_id": action_id,
            "status": status,
            "details": details,
        })

    async def send_context_update(self, active_app: str = "", active_file: str = "") -> None:
        await self.send("context_update", {
            "active_app": active_app,
            "active_file": active_file,
        })

    async def disconnect(self) -> None:
        self._connected = False
        if self._ws:
            await self._ws.close()

    async def _rest_send(self, event: str, payload: dict) -> None:
        """REST fallback for when WebSocket is unavailable."""
        endpoint_map = {
            "user_input": "/api/v1/input",
            "action_result": "/api/v1/action-result",
        }
        url = endpoint_map.get(event)
        if not url:
            log.warning("No REST fallback for event: %s", event)
            return

        try:
            async with httpx.AsyncClient(base_url=self.rest_url, timeout=10.0) as client:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                await client.post(url, json=payload, headers=headers)
        except Exception as e:
            log.error("REST fallback failed: %s", e)
