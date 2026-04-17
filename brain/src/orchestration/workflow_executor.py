"""Executes procedural routines and multi-step workflows across devices."""

from __future__ import annotations

from typing import Any

from brain.src.cognitive.models import TaskStatus
from brain.src.orchestration.device_router import DeviceRouter
from brain.src.orchestration.task_manager import TaskManager
from brain.src.logger import get_logger

log = get_logger("workflow")


class WorkflowExecutor:
    """Executes workflows by dispatching tasks to device agents."""

    def __init__(self, task_manager: TaskManager, device_router: DeviceRouter) -> None:
        self._tasks = task_manager
        self._router = device_router

    async def execute_workflow(
        self,
        name: str,
        steps: list[dict],
    ) -> str:
        """Execute a multi-step workflow. Returns parent task ID."""
        parent = self._tasks.create_task(description=f"Workflow: {name}")
        subtasks = self._tasks.create_subtasks(parent.id, [
            {
                "description": step.get("description", f"Step {i+1}"),
                "device": step.get("device"),
                "actions": [{"type": step.get("action", ""), "target": step.get("target", ""), "params": step.get("params", {})}],
            }
            for i, step in enumerate(steps)
        ])

        # Execute ready tasks
        await self._dispatch_ready_tasks()
        return parent.id

    async def execute_procedure(self, procedure) -> str:
        """Execute a learned procedure (from procedural memory)."""
        return await self.execute_workflow(procedure.name, procedure.steps)

    async def _dispatch_ready_tasks(self) -> None:
        """Dispatch all tasks whose dependencies are met."""
        ready = self._tasks.get_ready_tasks()
        for task in ready:
            self._tasks.update_status(task.id, TaskStatus.DISPATCHED)

            for action in task.actions:
                sent = await self._router.route_action(
                    action_type=action.type,
                    target=action.target,
                    preferred_device=task.target_device,
                    params=action.params,
                )

                if sent:
                    self._tasks.update_status(task.id, TaskStatus.IN_PROGRESS)
                else:
                    self._tasks.update_status(
                        task.id, TaskStatus.FAILED,
                        result="No device available for action",
                    )

    async def on_action_result(self, action_id: str, status: str) -> None:
        """Handle action completion. Advance workflow if needed."""
        # Find task by action_id prefix (workflow tasks use "wf-{parent}-{index}")
        for task in self._tasks._tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                task_status = TaskStatus.COMPLETED if status == "success" else TaskStatus.FAILED
                self._tasks.update_status(task.id, task_status)
                break

        # Dispatch next ready tasks
        await self._dispatch_ready_tasks()
