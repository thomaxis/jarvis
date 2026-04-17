"""Tests for Layer 10: Retrieval Pipeline."""

from __future__ import annotations

import pytest

from brain.src.cognitive.manager import BrainManager


@pytest.mark.asyncio
async def test_full_retrieval(setup_db) -> None:
    brain = BrainManager()

    # Process an input to populate some state
    context = await brain.process_input("test-device", "Open my design projects")

    assert context["device_id"] == "test-device"
    assert context["input"] == "Open my design projects"
    assert "relevant_knowledge" in context
    assert "associations" in context
    assert "personality" in context
    assert context["personality"]["tone"] == "direct"


@pytest.mark.asyncio
async def test_retrieval_with_prior_knowledge(setup_db) -> None:
    brain = BrainManager()

    # Store some knowledge first
    await brain.process_response(
        device_id="test-device",
        response_text="Opening Chrome for you.",
        facts=[{"content": "User prefers Chrome for browsing", "category": "preference", "confidence": 0.9}],
        associations=[["Chrome", "browsing"]],
        topic="browser",
    )

    # Now retrieve with related query
    context = await brain.process_input("test-device", "Open my browser")
    assert len(context["recent_messages"]) > 0


@pytest.mark.asyncio
async def test_consolidation(setup_db) -> None:
    brain = BrainManager()
    stats = await brain.consolidate()
    assert "decayed_knowledge" in stats
    assert "rescored" in stats
