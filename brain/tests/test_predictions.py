"""Tests for predictive suggestions."""

from __future__ import annotations

import pytest
from datetime import datetime

from brain.src.cognitive.predictions import PredictionEngine, _time_of_day
from brain.src.cognitive.procedural import ProceduralMemory
from brain.src.cognitive.models import TriggerType


def test_time_of_day() -> None:
    assert _time_of_day(7) == "morning"
    assert _time_of_day(14) == "afternoon"
    assert _time_of_day(19) == "evening"
    assert _time_of_day(23) == "night"
    assert _time_of_day(3) == "night"


@pytest.mark.asyncio
async def test_time_based_trigger(setup_db) -> None:
    pm = ProceduralMemory()
    proc = await pm.suggest_routine(
        name="morning_setup",
        steps=[{"action": "open_app", "target": "Chrome"}],
        trigger_type=TriggerType.TIME_BASED,
        trigger_conditions={"time_of_day": "morning", "day": "daily"},
    )
    await pm.activate_routine(proc.id)

    engine = PredictionEngine(pm)
    morning = datetime(2026, 4, 17, 8, 0, 0)
    suggestions = await engine.get_suggestions("test-device", now=morning)
    assert len(suggestions) >= 1
    assert suggestions[0]["routine_name"] == "morning_setup"


@pytest.mark.asyncio
async def test_no_trigger_wrong_time(setup_db) -> None:
    pm = ProceduralMemory()
    proc = await pm.suggest_routine(
        name="night_routine",
        steps=[{"action": "system_power", "target": "sleep"}],
        trigger_type=TriggerType.TIME_BASED,
        trigger_conditions={"time_of_day": "night"},
    )
    await pm.activate_routine(proc.id)

    engine = PredictionEngine(pm)
    afternoon = datetime(2026, 4, 17, 14, 0, 0)
    suggestions = await engine.get_suggestions("test-device", now=afternoon)
    night_suggestions = [s for s in suggestions if s["routine_name"] == "night_routine"]
    assert len(night_suggestions) == 0


def test_greeting() -> None:
    engine = PredictionEngine.__new__(PredictionEngine)
    morning = datetime(2026, 4, 17, 8, 0, 0)
    greeting = engine.get_time_greeting(morning)
    assert "morning" in greeting.lower() or "thursday" in greeting.lower()
