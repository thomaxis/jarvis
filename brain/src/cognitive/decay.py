"""Importance scoring and memory decay. Archival to archive table."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import sqlalchemy as sa

from brain.src.db.database import ArchiveTable, KnowledgeTable, get_session
from brain.src.db.repositories import KnowledgeRepo
from brain.src.logger import get_logger

log = get_logger("decay")


def compute_importance(
    access_count: int,
    last_accessed: datetime,
    confidence: float,
    task_relevance: float = 0.5,
) -> float:
    """Importance = 0.3*frequency + 0.3*recency + 0.2*task_relevance + 0.2*user_emphasis."""
    freq = min(1.0, access_count / 50.0)
    days_since = (datetime.utcnow() - last_accessed).days if last_accessed else 999
    recency = max(0.0, 1.0 - (days_since / 90.0))
    emphasis = confidence

    return round(0.3 * freq + 0.3 * recency + 0.2 * task_relevance + 0.2 * emphasis, 4)


async def process_decay(threshold_days: int = 30, decay_rate: float = 0.1) -> dict[str, int]:
    """Run decay on all knowledge entries. Returns stats."""
    all_knowledge = await KnowledgeRepo.get_all(limit=10000)
    now = datetime.utcnow()
    threshold = timedelta(days=threshold_days)

    stats = {"decayed": 0, "archived": 0, "rescored": 0}

    for k in all_knowledge:
        # Rescore importance
        new_importance = compute_importance(k.access_count, k.last_accessed, k.confidence)
        if abs(new_importance - k.importance) > 0.01:
            k.importance = new_importance
            stats["rescored"] += 1

        # Apply decay to old unused entries
        if k.last_accessed and (now - k.last_accessed) > threshold:
            k.decay_score = max(0.0, k.decay_score - decay_rate)
            stats["decayed"] += 1

            if k.decay_score < 0.1:
                await _archive_knowledge(k)
                await KnowledgeRepo.delete(k.id)
                stats["archived"] += 1
                continue

        await KnowledgeRepo.update(k)

    log.info("decay_complete", **stats)
    return stats


async def _archive_knowledge(knowledge) -> None:
    """Move a knowledge entry to the archive table."""
    async with await get_session() as session:
        archive_row = ArchiveTable(
            id=str(uuid.uuid4()),
            original_table="knowledge",
            original_id=knowledge.id,
            data=json.dumps({
                "content": knowledge.content,
                "category": knowledge.category.value,
                "importance": knowledge.importance,
                "confidence": knowledge.confidence,
                "access_count": knowledge.access_count,
                "tags": knowledge.tags,
            }),
            archived_at=datetime.utcnow(),
            reason="decay",
        )
        session.add(archive_row)
        await session.commit()
    log.info("knowledge_archived", id=knowledge.id, content=knowledge.content[:60])
