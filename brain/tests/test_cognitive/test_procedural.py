"""Tests for Layer 6: Procedural Memory."""

from __future__ import annotations

import pytest

from brain.src.cognitive.models import ProcedureStatus, TriggerType
from brain.src.cognitive.procedural import ProceduralMemory


@pytest.mark.asyncio
async def test_suggest_and_activate(setup_db) -> None:
    pm = ProceduralMemory()
    proc = await pm.suggest_routine(
        name="morning_routine",
        steps=[
            {"device": "windows", "action": "open_app", "target": "Chrome"},
            {"device": "windows", "action": "open_app", "target": "Slack"},
        ],
        trigger_description="morning setup",
        trigger_type=TriggerType.VERBAL,
        trigger_conditions={"phrase": "morning setup"},
    )
    assert proc.status == ProcedureStatus.SUGGESTED

    await pm.activate_routine(proc.id)
    active = await pm.get_active_routines()
    assert any(r.name == "morning_routine" for r in active)


@pytest.mark.asyncio
async def test_match_trigger(setup_db) -> None:
    pm = ProceduralMemory()
    await pm.suggest_routine(
        name="coding_setup",
        steps=[{"device": "windows", "action": "open_app", "target": "VS Code"}],
        trigger_description="start coding",
        trigger_type=TriggerType.VERBAL,
        trigger_conditions={"phrase": "start coding"},
    )
    # Need to activate for match to work
    routines = await pm.get_active_routines()
    # Not yet active, so match should return None
    match = await pm.match_trigger("let's start coding")
    assert match is None


@pytest.mark.asyncio
async def test_disable_routine(setup_db) -> None:
    pm = ProceduralMemory()
    proc = await pm.suggest_routine(
        name="test_disable",
        steps=[{"action": "test"}],
    )
    await pm.activate_routine(proc.id)
    await pm.disable_routine(proc.id)

    active = await pm.get_active_routines()
    assert not any(r.id == proc.id for r in active)
