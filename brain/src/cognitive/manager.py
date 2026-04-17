"""Brain orchestrator. Wires all 10 cognitive layers together."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.src.cognitive.associations import AssociativeMemory
from brain.src.cognitive.consolidation import ConsolidationEngine
from brain.src.cognitive.episodic import EpisodicMemory
from brain.src.cognitive.long_term import LongTermMemory
from brain.src.cognitive.models import EpisodeOutcome, Knowledge, KnowledgeCategory, Message
from brain.src.cognitive.personality import PersonalityMemory
from brain.src.cognitive.procedural import ProceduralMemory
from brain.src.cognitive.retrieval import RetrievalPipeline
from brain.src.cognitive.semantic import SemanticMemory
from brain.src.cognitive.short_term import ShortTermMemory
from brain.src.cognitive.working_memory import WorkingMemory
from brain.src.logger import get_logger

log = get_logger("manager")

_BRAIN_ROOT = Path(__file__).resolve().parent.parent.parent


class BrainManager:
    """Orchestrates all 10 cognitive layers. Entry point for brain operations."""

    def __init__(self, data_dir: Path | None = None) -> None:
        data = data_dir or (_BRAIN_ROOT / "data")

        # Layers 1-3 (ephemeral + persistent)
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

        # Layer 4: Association graph
        self.associations = AssociativeMemory(graph_path=data / "associations.graphml")

        # Layer 5: Episodic memory
        self.episodic = EpisodicMemory()

        # Layer 6: Procedural memory
        self.procedural = ProceduralMemory()

        # Layer 7: Personality
        self.personality = PersonalityMemory(profile_path=data / "personality.json")

        # Layer 8: Semantic (optional, graceful if chromadb missing)
        self.semantic = SemanticMemory(persist_dir=str(data / "semantic"))

        # Layer 9: Consolidation engine
        self.consolidation = ConsolidationEngine(
            short_term=self.short_term,
            long_term=self.long_term,
            associations=self.associations,
            semantic=self.semantic,
        )

        # Layer 10: Retrieval pipeline
        self.retrieval = RetrievalPipeline(
            working=self.working,
            short_term=self.short_term,
            long_term=self.long_term,
            associations=self.associations,
            episodic=self.episodic,
            procedural=self.procedural,
            personality=self.personality,
            semantic=self.semantic,
        )

    async def process_input(self, device_id: str, text: str) -> dict[str, Any]:
        """Process user input through the full 10-layer retrieval pipeline."""
        message = Message(role="user", content=text, device_id=device_id)

        # Update layers 1-2
        await self.working.add_message(device_id, message)
        await self.short_term.add_message(device_id, message)

        # Full retrieval (layers 1-10)
        context = await self.retrieval.retrieve(device_id, text)

        return context

    async def process_response(
        self,
        device_id: str,
        response_text: str,
        facts: list[dict] | None = None,
        associations: list[list[str]] | None = None,
        topic: str | None = None,
    ) -> None:
        """Process brain response -- store message, facts, associations, episode."""
        message = Message(role="assistant", content=response_text, device_id=device_id)
        await self.working.add_message(device_id, message)
        await self.short_term.add_message(device_id, message)

        if topic:
            await self.working.set_topic(device_id, topic)

        # Store extracted facts in long-term memory
        if facts:
            for fact in facts:
                knowledge = Knowledge(
                    content=fact.get("content", ""),
                    category=KnowledgeCategory(fact.get("category", "personal")),
                    confidence=fact.get("confidence", 0.7),
                    source_device=device_id,
                )
                stored = await self.long_term.store(knowledge)
                # Also index in semantic memory
                self.semantic.add(stored.id, stored.content, {"category": stored.category.value})

        # Strengthen association graph
        if associations:
            for pair in associations:
                if len(pair) == 2:
                    self.associations.add_association(pair[0], pair[1])

        # Record as episode
        await self.episodic.record(
            event_type="conversation",
            title=topic or "conversation",
            description=f"User: {message.content[:100]}",
            device=device_id,
            outcome=EpisodeOutcome.SUCCESS,
        )

    async def consolidate(self) -> dict:
        """Run consolidation (layer 9). Call on schedule or session end."""
        return await self.consolidation.run_full()

    async def register_device(self, device_id: str) -> None:
        await self.short_term.register_device(device_id)
        log.info("device_connected", device=device_id)

    async def unregister_device(self, device_id: str) -> None:
        await self.short_term.unregister_device(device_id)
        log.info("device_disconnected", device=device_id)

    async def save_state(self) -> None:
        """Persist in-memory state to disk."""
        self.associations.save()
        self.personality.save()

    async def get_status(self) -> dict:
        """Return brain status for health checks."""
        devices = await self.short_term.get_active_devices()
        goals = await self.working.get_goals()
        knowledge_count = len(await self.long_term.get_all(limit=1000))
        return {
            "active_devices": devices,
            "active_goals": len(goals),
            "knowledge_entries": knowledge_count,
            "associations": self.associations.get_stats(),
            "semantic_entries": self.semantic.count(),
        }
