"""Tests for Layer 3: Long-Term Memory."""

from __future__ import annotations

import pytest
import pytest_asyncio

from brain.src.cognitive.long_term import LongTermMemory
from brain.src.cognitive.models import Knowledge, KnowledgeCategory


@pytest_asyncio.fixture
async def ltm(setup_db) -> LongTermMemory:
    return LongTermMemory()


@pytest.mark.asyncio
async def test_store_and_recall(ltm: LongTermMemory) -> None:
    k = Knowledge(
        content="User prefers dark mode",
        category=KnowledgeCategory.PREFERENCE,
        confidence=0.9,
    )
    stored = await ltm.store(k)

    recalled = await ltm.recall(stored.id)
    assert recalled is not None
    assert recalled.content == "User prefers dark mode"
    assert recalled.access_count == 1


@pytest.mark.asyncio
async def test_search(ltm: LongTermMemory) -> None:
    k = Knowledge(
        content="User works at night usually 10pm to 2am",
        category=KnowledgeCategory.HABIT,
    )
    await ltm.store(k)

    results = await ltm.search("night")
    assert len(results) >= 1
    assert any("night" in r.content for r in results)


@pytest.mark.asyncio
async def test_contradiction_resolution(ltm: LongTermMemory) -> None:
    k = Knowledge(
        content="User prefers Chrome",
        category=KnowledgeCategory.PREFERENCE,
        confidence=0.8,
    )
    stored = await ltm.store(k)

    recalled = await ltm.recall(stored.id)
    assert recalled is not None
    await ltm.update_with_contradiction(recalled, "User prefers Firefox")

    updated = await ltm.recall(stored.id)
    assert updated is not None
    assert updated.content == "User prefers Firefox"
    assert "User prefers Chrome" in updated.previous_values
    assert updated.confidence < 0.8


@pytest.mark.asyncio
async def test_forget(ltm: LongTermMemory) -> None:
    k = Knowledge(content="temporary fact", category=KnowledgeCategory.PERSONAL)
    stored = await ltm.store(k)

    await ltm.forget(stored.id)
    recalled = await ltm.recall(stored.id)
    assert recalled is None


@pytest.mark.asyncio
async def test_boost_confidence(ltm: LongTermMemory) -> None:
    k = Knowledge(
        content="User likes Python",
        category=KnowledgeCategory.PREFERENCE,
        confidence=0.7,
    )
    stored = await ltm.store(k)

    await ltm.boost_confidence(stored.id, 0.1)
    recalled = await ltm.recall(stored.id)
    assert recalled is not None
    assert recalled.confidence == pytest.approx(0.8, abs=0.01)
