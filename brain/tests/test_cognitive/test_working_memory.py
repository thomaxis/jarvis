"""Tests for Layer 1: Working Memory."""

from __future__ import annotations

import pytest
import pytest_asyncio

from brain.src.cognitive.models import Goal, Message, PendingTask, TaskStatus
from brain.src.cognitive.working_memory import WorkingMemory


@pytest_asyncio.fixture
async def wm(setup_db) -> WorkingMemory:
    return WorkingMemory()


@pytest.mark.asyncio
async def test_add_and_get_message(wm: WorkingMemory) -> None:
    msg = Message(role="user", content="Hello Jarvis", device_id="test-device")
    await wm.add_message("test-device", msg)

    ctx = await wm.get_device_context("test-device")
    assert len(ctx.context_window) >= 1
    assert ctx.context_window[-1].content == "Hello Jarvis"


@pytest.mark.asyncio
async def test_context_window_cap(wm: WorkingMemory) -> None:
    for i in range(10):
        msg = Message(role="user", content=f"msg {i}", device_id="cap-device")
        await wm.add_message("cap-device", msg)

    ctx = await wm.get_device_context("cap-device")
    assert len(ctx.context_window) <= 5  # CONTEXT_WINDOW_SIZE


@pytest.mark.asyncio
async def test_set_topic(wm: WorkingMemory) -> None:
    await wm.set_topic("topic-device", "project planning")
    ctx = await wm.get_device_context("topic-device")
    assert ctx.current_topic == "project planning"


@pytest.mark.asyncio
async def test_goals(wm: WorkingMemory) -> None:
    goal = Goal(description="Finish the brain core")
    await wm.add_goal(goal)

    goals = await wm.get_goals()
    assert len(goals) >= 1
    assert any(g.description == "Finish the brain core" for g in goals)


@pytest.mark.asyncio
async def test_focus_entity(wm: WorkingMemory) -> None:
    await wm.set_focus_entity("Jarvis project")
    entity = await wm.get_focus_entity()
    assert entity == "Jarvis project"

    await wm.set_focus_entity(None)
    entity = await wm.get_focus_entity()
    assert entity is None


@pytest.mark.asyncio
async def test_cross_device_tasks(wm: WorkingMemory) -> None:
    task = PendingTask(
        description="Open investor deck",
        trigger_device="windows-main",
        trigger_condition="device_online",
    )
    await wm.add_cross_device_task(task)

    tasks = await wm.get_cross_device_tasks()
    assert len(tasks) >= 1
    assert tasks[-1]["description"] == "Open investor deck"


@pytest.mark.asyncio
async def test_clear_device(wm: WorkingMemory) -> None:
    msg = Message(role="user", content="test clear", device_id="clear-device")
    await wm.add_message("clear-device", msg)
    await wm.clear_device("clear-device")

    ctx = await wm.get_device_context("clear-device")
    assert len(ctx.context_window) == 0


@pytest.mark.asyncio
async def test_unresolved_questions(wm: WorkingMemory) -> None:
    await wm.add_unresolved("q-device", "What time is the meeting?")
    ctx = await wm.get_device_context("q-device")
    assert "What time is the meeting?" in ctx.unresolved

    await wm.resolve_question("q-device", "What time is the meeting?")
    ctx = await wm.get_device_context("q-device")
    assert "What time is the meeting?" not in ctx.unresolved
