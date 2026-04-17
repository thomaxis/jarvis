"""Routes actions to the correct device agent based on context."""

from __future__ import annotations

from typing import Any

from brain.src.api.websocket.handler import manager
from brain.src.logger import get_logger

log = get_logger("device_router")


class DeviceRouter:
    """Routes actions to the correct device agent."""

    async def route_action(
        self,
        action_type: str,
        target: str,
        preferred_device: str | None = None,
        params: dict | None = None,
    ) -> bool:
        """Route an action to the best available device."""
        device = self._select_device(action_type, preferred_device)
        if not device:
            log.warning("no_device_for_action", action=action_type, target=target)
            return False

        import uuid
        payload = {
            "event": "execute_action",
            "action_id": str(uuid.uuid4()),
            "type": action_type,
            "target": target,
            "device": device,
            "params": params or {},
        }

        sent = await manager.send_to_device(device, payload)
        if sent:
            log.info("action_routed", action=action_type, target=target, device=device)
        else:
            log.warning("action_route_failed", action=action_type, device=device)
        return sent

    async def route_workflow(
        self,
        procedure_name: str,
        steps: list[dict],
    ) -> bool:
        """Route a multi-step workflow to appropriate devices."""
        import uuid
        procedure_id = str(uuid.uuid4())

        for step in steps:
            device = step.get("device")
            if device and not manager.is_online(device):
                log.warning("workflow_device_offline", device=device, step=step.get("action"))
                continue

            target_device = device or self._select_device(step.get("action", ""), None)
            if target_device:
                await manager.send_to_device(target_device, {
                    "event": "execute_action",
                    "action_id": f"wf-{procedure_id}-{steps.index(step)}",
                    "type": step.get("action", ""),
                    "target": step.get("target", ""),
                    "device": target_device,
                    "params": step.get("params", {}),
                })

        return True

    async def notify_all(self, message: str, exclude: str | None = None) -> None:
        """Send a notification to all connected agents."""
        await manager.broadcast(
            {"event": "notification", "message": message},
            exclude=exclude,
        )

    def _select_device(self, action_type: str, preferred: str | None) -> str | None:
        """Select the best device for an action."""
        online = manager.get_online_devices()
        if not online:
            return None

        # If preferred device is online, use it
        if preferred and preferred in online:
            return preferred

        # Desktop actions go to desktop agents
        desktop_actions = {"open_app", "close_app", "terminal", "file_op", "clipboard", "type_text", "screenshot"}
        if action_type in desktop_actions:
            for device in online:
                if any(p in device for p in ("windows", "macos", "linux", "desktop", "pc")):
                    return device

        # Default to first available
        return online[0]
