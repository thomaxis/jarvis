"""Layer 3: Long-Term Memory -- persistent knowledge. PostgreSQL via repository."""

from __future__ import annotations

from datetime import datetime

from brain.src.cognitive.models import Knowledge, KnowledgeCategory
from brain.src.db.repositories import KnowledgeRepo
from brain.src.logger import get_logger

log = get_logger("long_term")


class LongTermMemory:
    """Persistent knowledge store backed by PostgreSQL (prod) or SQLite (dev)."""

    async def store(self, knowledge: Knowledge) -> Knowledge:
        result = await KnowledgeRepo.create(knowledge)
        log.info(
            "knowledge_stored",
            id=result.id,
            category=result.category.value,
            content=result.content[:80],
        )
        return result

    async def recall(self, knowledge_id: str) -> Knowledge | None:
        return await KnowledgeRepo.get(knowledge_id, record_access=True)

    async def search(
        self,
        query: str,
        category: KnowledgeCategory | None = None,
        limit: int = 20,
    ) -> list[Knowledge]:
        cat_str = category.value if category else None
        return await KnowledgeRepo.search(query, category=cat_str, limit=limit)

    async def update(self, knowledge: Knowledge) -> None:
        knowledge.updated_at = datetime.utcnow()
        await KnowledgeRepo.update(knowledge)
        log.info("knowledge_updated", id=knowledge.id, content=knowledge.content[:80])

    async def update_with_contradiction(
        self, knowledge: Knowledge, new_content: str
    ) -> None:
        """Update content and preserve old value in history."""
        knowledge.previous_values.append(knowledge.content)
        knowledge.content = new_content
        knowledge.updated_at = datetime.utcnow()
        knowledge.confidence = max(0.5, knowledge.confidence - 0.1)
        await KnowledgeRepo.update(knowledge)
        log.info(
            "knowledge_contradiction_resolved",
            id=knowledge.id,
            old=knowledge.previous_values[-1][:60],
            new=new_content[:60],
        )

    async def boost_confidence(self, knowledge_id: str, amount: float = 0.05) -> None:
        knowledge = await KnowledgeRepo.get(knowledge_id)
        if knowledge:
            knowledge.confidence = min(1.0, knowledge.confidence + amount)
            await KnowledgeRepo.update(knowledge)

    async def get_all(self, limit: int = 100) -> list[Knowledge]:
        return await KnowledgeRepo.get_all(limit=limit)

    async def forget(self, knowledge_id: str) -> None:
        await KnowledgeRepo.delete(knowledge_id)
        log.info("knowledge_deleted", id=knowledge_id)
