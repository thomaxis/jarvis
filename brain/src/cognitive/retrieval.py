"""Layer 10: Brain Retrieval System -- think-before-speaking pipeline."""

from __future__ import annotations

from typing import Any

from brain.src.cognitive.associations import AssociativeMemory
from brain.src.cognitive.episodic import EpisodicMemory
from brain.src.cognitive.long_term import LongTermMemory
from brain.src.cognitive.personality import PersonalityMemory
from brain.src.cognitive.procedural import ProceduralMemory
from brain.src.cognitive.semantic import SemanticMemory
from brain.src.cognitive.short_term import ShortTermMemory
from brain.src.cognitive.working_memory import WorkingMemory
from brain.src.logger import get_logger

log = get_logger("retrieval")


class RetrievalPipeline:
    """Queries all 10 memory layers and builds context for LLM."""

    def __init__(
        self,
        working: WorkingMemory,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        associations: AssociativeMemory,
        episodic: EpisodicMemory,
        procedural: ProceduralMemory,
        personality: PersonalityMemory,
        semantic: SemanticMemory,
        max_context_memories: int = 10,
    ) -> None:
        self._working = working
        self._stm = short_term
        self._ltm = long_term
        self._associations = associations
        self._episodic = episodic
        self._procedural = procedural
        self._personality = personality
        self._semantic = semantic
        self._max = max_context_memories

    async def retrieve(self, device_id: str, text: str) -> dict[str, Any]:
        """Full retrieval pipeline. Returns enriched context for LLM prompt building."""

        # 1. Working memory -- current device state
        device_ctx = await self._working.get_device_context(device_id)
        goals = await self._working.get_goals()
        cross_tasks = await self._working.get_cross_device_tasks()
        focus = await self._working.get_focus_entity()

        # 2. Short-term -- recent messages across devices
        recent = await self._stm.get_messages(device_id, limit=10)
        corrections = await self._stm.get_corrections()

        # 3. Long-term knowledge
        knowledge = await self._ltm.search(text, limit=5)

        # 4. Semantic search
        semantic_results = self._semantic.search(text, limit=5)

        # 5. Association graph activation
        concepts = _extract_concepts(text)
        associations = self._associations.activate(concepts, depth=2, limit=5)

        # 6. Episodic memory
        episodes = await self._episodic.search(text, limit=3)

        # 7. Procedural match
        routine_match = await self._procedural.match_trigger(text)

        # 8. Personality
        personality = self._personality.profile
        device_style = self._personality.get_device_style(device_id)

        # Rank and select top N memories
        all_memories = _rank_memories(knowledge, semantic_results, episodes, self._max)

        context = {
            "device_id": device_id,
            "input": text,
            "current_topic": device_ctx.current_topic,
            "unresolved": device_ctx.unresolved,
            "focus_entity": focus,
            "active_goals": [{"id": g.id, "description": g.description} for g in goals],
            "cross_device_tasks": cross_tasks,
            "recent_messages": [{"role": m.role, "content": m.content} for m in recent],
            "corrections": corrections[:3],
            "relevant_knowledge": [
                {"content": k.content, "category": k.category.value, "confidence": k.confidence}
                for k in all_memories.get("knowledge", [])
            ],
            "semantic_matches": all_memories.get("semantic", []),
            "associations": associations,
            "recent_episodes": [
                {"title": e.title, "outcome": e.outcome.value, "device": e.device}
                for e in all_memories.get("episodes", [])
            ],
            "matched_routine": {
                "name": routine_match.name,
                "steps": routine_match.steps,
            } if routine_match else None,
            "personality": {
                "tone": personality.get("tone_preference", "direct"),
                "verbosity": personality.get("verbosity", "concise"),
                "device_style": device_style,
            },
        }

        log.debug(
            "retrieval_complete",
            knowledge=len(context["relevant_knowledge"]),
            semantic=len(context["semantic_matches"]),
            associations=len(context["associations"]),
            episodes=len(context["recent_episodes"]),
            routine=bool(routine_match),
        )

        return context


def _extract_concepts(text: str) -> list[str]:
    """Simple concept extraction -- split into significant words."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "up", "about", "into", "through",
        "during", "before", "after", "and", "but", "or", "not", "no", "so",
        "if", "then", "than", "too", "very", "just", "that", "this", "it",
        "my", "me", "i", "you", "your", "we", "our", "they", "them", "what",
        "which", "who", "when", "where", "how", "all", "each", "some", "any",
        "open", "close", "start", "stop", "get", "set", "run", "make",
    }
    words = text.lower().split()
    return [w.strip(".,!?;:'\"") for w in words if len(w) > 2 and w.lower() not in stop_words]


def _rank_memories(
    knowledge: list,
    semantic: list[dict],
    episodes: list,
    max_total: int,
) -> dict[str, list]:
    """Distribute slots across memory types based on relevance."""
    k_count = min(len(knowledge), max_total // 2)
    s_count = min(len(semantic), max_total // 3)
    e_count = min(len(episodes), max_total - k_count - s_count)

    return {
        "knowledge": knowledge[:k_count],
        "semantic": semantic[:s_count],
        "episodes": episodes[:e_count],
    }
