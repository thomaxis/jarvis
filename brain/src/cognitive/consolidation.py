"""Layer 9: Memory Consolidation -- background 'sleep' process for memory maintenance."""

from __future__ import annotations

from datetime import datetime, timedelta

from brain.src.cognitive.associations import AssociativeMemory
from brain.src.cognitive.long_term import LongTermMemory
from brain.src.cognitive.semantic import SemanticMemory
from brain.src.cognitive.short_term import ShortTermMemory
from brain.src.logger import get_logger

log = get_logger("consolidation")


class ConsolidationEngine:
    """Processes raw experiences into structured knowledge. Runs periodically."""

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        associations: AssociativeMemory,
        semantic: SemanticMemory,
        decay_threshold_days: int = 30,
    ) -> None:
        self._stm = short_term
        self._ltm = long_term
        self._associations = associations
        self._semantic = semantic
        self._decay_threshold_days = decay_threshold_days

    async def run_full(self) -> dict:
        """Run full consolidation cycle. Returns stats."""
        log.info("consolidation_started")
        stats: dict[str, int] = {}

        stats["decayed_knowledge"] = await self._decay_knowledge()
        stats["decayed_associations"] = self._decay_associations()
        stats["deduplicated"] = await self._deduplicate()
        stats["rescored"] = await self._rescore()

        self._associations.save()

        log.info("consolidation_complete", **stats)
        return stats

    async def _decay_knowledge(self) -> int:
        """Reduce decay_score on old unused knowledge."""
        all_knowledge = await self._ltm.get_all(limit=10000)
        now = datetime.utcnow()
        threshold = timedelta(days=self._decay_threshold_days)
        decayed = 0

        for k in all_knowledge:
            if k.last_accessed and (now - k.last_accessed) > threshold:
                k.decay_score = max(0.0, k.decay_score - 0.1)
                if k.decay_score < 0.1:
                    log.info("knowledge_archived", id=k.id, content=k.content[:60])
                    await self._ltm.forget(k.id)
                else:
                    await self._ltm.update(k)
                decayed += 1

        return decayed

    def _decay_associations(self) -> int:
        return self._associations.decay(threshold_days=self._decay_threshold_days * 2)

    async def _deduplicate(self) -> int:
        """Remove near-duplicate knowledge entries using semantic similarity."""
        if not self._semantic.enabled:
            return 0

        all_knowledge = await self._ltm.get_all(limit=1000)
        removed = 0
        seen_ids: set[str] = set()

        for k in all_knowledge:
            if k.id in seen_ids:
                continue
            dup_id = self._semantic.check_duplicate(k.content, threshold=0.92)
            if dup_id and dup_id != k.id and dup_id not in seen_ids:
                # Keep the one with higher importance
                dup = await self._ltm.recall(dup_id)
                if dup and dup.importance <= k.importance:
                    await self._ltm.forget(dup_id)
                    self._semantic.delete(dup_id)
                    seen_ids.add(dup_id)
                    removed += 1

        return removed

    async def _rescore(self) -> int:
        """Re-score importance using the formula: 0.3*frequency + 0.3*recency + 0.2*task_relevance + 0.2*user_emphasis."""
        all_knowledge = await self._ltm.get_all(limit=1000)
        now = datetime.utcnow()
        rescored = 0

        for k in all_knowledge:
            freq = min(1.0, k.access_count / 50.0)
            days_since = (now - k.last_accessed).days if k.last_accessed else 999
            recency = max(0.0, 1.0 - (days_since / 90.0))
            emphasis = k.confidence

            new_importance = 0.3 * freq + 0.3 * recency + 0.2 * 0.5 + 0.2 * emphasis
            if abs(new_importance - k.importance) > 0.01:
                k.importance = round(new_importance, 3)
                await self._ltm.update(k)
                rescored += 1

        return rescored
