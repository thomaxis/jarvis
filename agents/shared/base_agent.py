"""Abstract base class for all device agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from agents.shared.connection import BrainConnection
from agents.shared.models import ActionRequest, ActionResult

log = logging.getLogger("jarvis.agent")


class BaseAgent(ABC):
    """Base class for device agents. Subclasses implement platform-specific actions."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.device_id = config.get("device_id", "unknown")
        self.platform = config.get("platform", "unknown")

        self.connection = BrainConnection(
            ws_url=config.get("brain_ws_url", "ws://localhost:8400/ws"),
            rest_url=config.get("brain_rest_url", "http://localhost:8400"),
            device_id=self.device_id,
            platform=self.platform,
            capabilities=self.get_capabilities(),
            token=config.get("token", ""),
            on_message=self._handle_message,
        )

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return list of capabilities this agent supports."""
        ...

    @abstractmethod
    async def execute_action(self, action: ActionRequest) -> ActionResult:
        """Execute a platform-specific action."""
        ...

    async def _handle_message(self, message: dict) -> None:
        """Handle incoming messages from the brain."""
        event = message.get("event", "")

        if event == "execute_action":
            action = ActionRequest(
                action_id=message.get("action_id", ""),
                type=message.get("type", ""),
                target=message.get("target", ""),
                device=message.get("device", self.device_id),
                params=message.get("params", {}),
            )
            result = await self.execute_action(action)
            await self.connection.send_action_result(
                action_id=result.action_id,
                status=result.status,
                details=result.details,
            )

        elif event == "execute_workflow":
            steps = message.get("steps", [])
            for step in steps:
                if step.get("device", self.device_id) != self.device_id:
                    continue
                action = ActionRequest(
                    action_id=f"wf-{message.get('procedure_id', '')}-{steps.index(step)}",
                    type=step.get("action", ""),
                    target=step.get("target", ""),
                    device=self.device_id,
                    params=step.get("params", {}),
                )
                result = await self.execute_action(action)
                await self.connection.send_action_result(
                    action_id=result.action_id,
                    status=result.status,
                    details=result.details,
                )

        elif event == "response":
            text = message.get("text", "")
            if text:
                log.info("Jarvis: %s", text)

        elif event == "notification":
            log.info("Notification: %s", message.get("message", ""))

        elif event == "context_ready":
            pass  # Agent doesn't need to act on raw context

        elif event == "pending_task":
            task = message.get("task", {})
            log.info("Pending task: %s", task.get("description", ""))

    async def run(self) -> None:
        """Start the agent and connect to the brain."""
        log.info("Starting %s agent (%s)", self.platform, self.device_id)
        await self.connection.connect()
