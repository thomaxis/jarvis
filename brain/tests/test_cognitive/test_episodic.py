"""Tests for Layer 5: Episodic Memory."""

from __future__ import annotations

import pytest

from brain.src.cognitive.episodic import EpisodicMemory
from brain.src.cognitive.models import EpisodeOutcome


@pytest.mark.asyncio
async def test_record_and_get_recent(setup_db) -> None:
    em = EpisodicMemory()
    ep = await em.record(
        event_type="task",
        title="Opened Chrome for user",
        description="User asked to open Chrome",
        device="windows-main",
        outcome=EpisodeOutcome.SUCCESS,
    )
    assert ep.id
    assert ep.day_of_week
    assert ep.time_of_day

    recent = await em.get_recent(limit=5)
    assert len(recent) >= 1
    assert any(e.title == "Opened Chrome for user" for e in recent)


@pytest.mark.asyncio
async def test_search_episodes(setup_db) -> None:
    em = EpisodicMemory()
    await em.record(
        event_type="error",
        title="VS Code crashed during debug",
        description="Segfault in extension host",
        device="windows-main",
        outcome=EpisodeOutcome.FAILURE,
    )

    results = await em.search("VS Code crashed")
    assert len(results) >= 1
    assert results[0].outcome == EpisodeOutcome.FAILURE
