"""Tests for Task Orchestration."""

from __future__ import annotations

from brain.src.cognitive.models import TaskStatus
from brain.src.orchestration.task_manager import TaskManager


def test_create_task() -> None:
    tm = TaskManager()
    task = tm.create_task("Open Chrome and Slack")
    assert task.id
    assert task.status == TaskStatus.PENDING
    assert task.description == "Open Chrome and Slack"


def test_create_subtasks() -> None:
    tm = TaskManager()
    parent = tm.create_task("Morning routine")
    subtasks = tm.create_subtasks(parent.id, [
        {"description": "Open Chrome", "actions": [{"type": "open_app", "target": "chrome"}]},
        {"description": "Open Slack", "actions": [{"type": "open_app", "target": "slack"}]},
        {"description": "Open VS Code", "actions": [{"type": "open_app", "target": "code"}]},
    ])
    assert len(subtasks) == 3
    assert subtasks[0].parent_id == parent.id
    assert subtasks[1].dependencies == [subtasks[0].id]
    assert subtasks[2].dependencies == [subtasks[1].id]


def test_ready_tasks() -> None:
    tm = TaskManager()
    parent = tm.create_task("Workflow")
    subtasks = tm.create_subtasks(parent.id, [
        {"description": "Step 1"},
        {"description": "Step 2"},
    ])

    ready = tm.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == subtasks[0].id  # Only first step is ready


def test_task_completion_unlocks_next() -> None:
    tm = TaskManager()
    parent = tm.create_task("Workflow")
    subtasks = tm.create_subtasks(parent.id, [
        {"description": "Step 1"},
        {"description": "Step 2"},
    ])

    tm.update_status(subtasks[0].id, TaskStatus.COMPLETED)

    ready = tm.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == subtasks[1].id


def test_parent_completion() -> None:
    tm = TaskManager()
    parent = tm.create_task("Workflow")
    subtasks = tm.create_subtasks(parent.id, [
        {"description": "Step 1"},
        {"description": "Step 2"},
    ])

    tm.update_status(subtasks[0].id, TaskStatus.COMPLETED)
    tm.update_status(subtasks[1].id, TaskStatus.COMPLETED)

    assert tm.get_task(parent.id).status == TaskStatus.COMPLETED


def test_parent_failure() -> None:
    tm = TaskManager()
    parent = tm.create_task("Workflow")
    subtasks = tm.create_subtasks(parent.id, [
        {"description": "Step 1"},
        {"description": "Step 2"},
    ])

    tm.update_status(subtasks[0].id, TaskStatus.COMPLETED)
    tm.update_status(subtasks[1].id, TaskStatus.FAILED)

    assert tm.get_task(parent.id).status == TaskStatus.FAILED


def test_status_summary() -> None:
    tm = TaskManager()
    tm.create_task("Task 1")
    t2 = tm.create_task("Task 2")
    tm.update_status(t2.id, TaskStatus.COMPLETED)

    summary = tm.get_status_summary()
    assert summary["total"] == 2
    assert summary["by_status"]["pending"] == 1
    assert summary["by_status"]["completed"] == 1
