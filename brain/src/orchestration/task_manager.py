"""Task orchestration: multi-step task breakdown, dependency tracking, status management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from brain.src.cognitive.models import Action, Task, TaskStatus
from brain.src.logger import get_logger

log = get_logger("task_manager")


class TaskManager:
    """Breaks down complex requests into sub-tasks and tracks execution."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(
        self,
        description: str,
        target_device: str | None = None,
        actions: list[dict] | None = None,
        parent_id: str | None = None,
        dependencies: list[str] | None = None,
    ) -> Task:
        task = Task(
            description=description,
            target_device=target_device,
            parent_id=parent_id,
            dependencies=dependencies or [],
            actions=[
                Action(
                    type=a.get("type", ""),
                    target=a.get("target", ""),
                    device=a.get("device", ""),
                    params=a.get("params", {}),
                )
                for a in (actions or [])
            ],
        )
        self._tasks[task.id] = task
        log.info("task_created", id=task.id, desc=description[:60])
        return task

    def create_subtasks(self, parent_id: str, steps: list[dict]) -> list[Task]:
        """Create ordered sub-tasks for a parent task."""
        subtasks = []
        prev_id: str | None = None

        for step in steps:
            deps = [prev_id] if prev_id else []
            task = self.create_task(
                description=step.get("description", ""),
                target_device=step.get("device"),
                actions=step.get("actions", []),
                parent_id=parent_id,
                dependencies=deps,
            )
            subtasks.append(task)
            prev_id = task.id

        return subtasks

    def update_status(self, task_id: str, status: TaskStatus, result: str = "") -> None:
        task = self._tasks.get(task_id)
        if not task:
            log.warning("task_not_found", id=task_id)
            return

        task.status = status
        if result:
            task.result = result
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.utcnow()

        log.info("task_updated", id=task_id, status=status.value)

        # Check if parent task is complete
        if task.parent_id:
            self._check_parent_completion(task.parent_id)

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> list[Task]:
        """Get leaf tasks (non-parent) whose dependencies are all completed."""
        parent_ids = {t.parent_id for t in self._tasks.values() if t.parent_id}
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            # Skip parent tasks (they complete via subtask completion)
            if task.id in parent_ids:
                continue
            deps_met = all(
                self._tasks.get(dep_id, Task()).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready

    def get_subtasks(self, parent_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if t.parent_id == parent_id]

    def _check_parent_completion(self, parent_id: str) -> None:
        subtasks = self.get_subtasks(parent_id)
        if not subtasks:
            return

        all_done = all(t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) for t in subtasks)
        if all_done:
            any_failed = any(t.status == TaskStatus.FAILED for t in subtasks)
            parent = self._tasks.get(parent_id)
            if parent:
                parent.status = TaskStatus.FAILED if any_failed else TaskStatus.COMPLETED
                parent.completed_at = datetime.utcnow()
                log.info("parent_task_complete", id=parent_id, status=parent.status.value)

    def get_status_summary(self) -> dict:
        statuses = {}
        for task in self._tasks.values():
            s = task.status.value
            statuses[s] = statuses.get(s, 0) + 1
        return {"total": len(self._tasks), "by_status": statuses}
