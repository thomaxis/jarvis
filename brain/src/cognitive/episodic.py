"""Layer 5: Episodic Memory -- specific events Jarvis has experienced."""

from __future__ import annotations

from datetime import datetime

from brain.src.cognitive.models import Episode, EpisodeOutcome
from brain.src.db.repositories import EpisodeRepo
from brain.src.logger import get_logger

log = get_logger("episodic")


def _time_of_day(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


class EpisodicMemory:
    """Autobiographical memory of specific events and outcomes."""

    async def record(
        self,
        event_type: str,
        title: str,
        description: str = "",
        actions: list[dict] | None = None,
        outcome: EpisodeOutcome = EpisodeOutcome.SUCCESS,
        duration_seconds: int = 0,
        device: str = "",
        context: str = "",
        learned: str = "",
        importance: float = 0.5,
    ) -> Episode:
        now = datetime.utcnow()
        episode = Episode(
            event_type=event_type,
            title=title,
            description=description,
            actions=actions or [],
            outcome=outcome,
            duration_seconds=duration_seconds,
            timestamp=now,
            day_of_week=now.strftime("%A"),
            time_of_day=_time_of_day(now),
            device=device,
            context=context,
            learned=learned,
            importance=importance,
        )
        result = await EpisodeRepo.create(episode)
        log.info("episode_recorded", id=result.id, type=event_type, title=title[:60])
        return result

    async def get_recent(self, limit: int = 20, device: str | None = None) -> list[Episode]:
        return await EpisodeRepo.get_recent(limit=limit, device=device)

    async def search(self, query: str, limit: int = 10) -> list[Episode]:
        return await EpisodeRepo.search(query, limit=limit)

    async def get_by_type(self, event_type: str, limit: int = 10) -> list[Episode]:
        return await EpisodeRepo.get_recent(limit=limit)
