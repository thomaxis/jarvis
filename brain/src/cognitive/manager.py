"""Brain orchestrator. Wires cognitive layers together. All layer access goes through here."""

from __future__ import annotations

from brain.src.cognitive.long_term import LongTermMemory
from brain.src.cognitive.models import Knowledge, KnowledgeCategory, Message
from brain.src.cognitive.short_term import ShortTermMemory
from brain.src.cognitive.working_memory import WorkingMemory
from brain.src.logger import get_logger

log = get_logger("manager")


class BrainManager:
    """Orchestrates all cognitive layers. Entry point for brain operations."""

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    async def process_input(self, device_id: str, text: str) -> dict:
        """Process user input through the cognitive pipeline. Returns context for LLM."""
        message = Message(role="user", content=text, device_id=device_id)

        # Update working and short-term memory
        await self.working.add_message(device_id, message)
        await self.short_term.add_message(device_id, message)

        # Gather context from all layers
        device_ctx = await self.working.get_device_context(device_id)
        recent_msgs = await self.short_term.get_messages(device_id, limit=10)
        corrections = await self.short_term.get_corrections()
        goals = await self.working.get_goals()
        cross_tasks = await self.working.get_cross_device_tasks()

        # Search long-term for relevant knowledge
        knowledge = await self.long_term.search(text, limit=5)

        return {
            "device_id": device_id,
            "input": text,
            "current_topic": device_ctx.current_topic,
            "unresolved": device_ctx.unresolved,
            "recent_messages": [
                {"role": m.role, "content": m.content} for m in recent_msgs
            ],
            "corrections": corrections,
            "active_goals": [{"id": g.id, "description": g.description} for g in goals],
            "cross_device_tasks": cross_tasks,
            "relevant_knowledge": [
                {
                    "id": k.id,
                    "content": k.content,
                    "category": k.category.value,
                    "confidence": k.confidence,
                }
                for k in knowledge
            ],
        }

    async def process_response(
        self,
        device_id: str,
        response_text: str,
        facts: list[dict] | None = None,
        topic: str | None = None,
    ) -> None:
        """Process brain response -- store assistant message and extracted facts."""
        message = Message(role="assistant", content=response_text, device_id=device_id)
        await self.working.add_message(device_id, message)
        await self.short_term.add_message(device_id, message)

        if topic:
            await self.working.set_topic(device_id, topic)

        if facts:
            for fact in facts:
                knowledge = Knowledge(
                    content=fact.get("content", ""),
                    category=KnowledgeCategory(fact.get("category", "personal")),
                    confidence=fact.get("confidence", 0.7),
                    source_device=device_id,
                )
                await self.long_term.store(knowledge)

    async def register_device(self, device_id: str) -> None:
        await self.short_term.register_device(device_id)
        log.info("device_connected", device=device_id)

    async def unregister_device(self, device_id: str) -> None:
        await self.short_term.unregister_device(device_id)
        log.info("device_disconnected", device=device_id)

    async def get_status(self) -> dict:
        """Return brain status for health checks."""
        devices = await self.short_term.get_active_devices()
        goals = await self.working.get_goals()
        knowledge_count = len(await self.long_term.get_all(limit=1000))
        return {
            "active_devices": devices,
            "active_goals": len(goals),
            "knowledge_entries": knowledge_count,
        }
