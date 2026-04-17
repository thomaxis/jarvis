"""Repository pattern for database access. Cognitive layers call these, never SQLAlchemy directly."""

from __future__ import annotations

import json
from datetime import datetime

import sqlalchemy as sa

from brain.src.cognitive.models import (
    Episode,
    EpisodeOutcome,
    Knowledge,
    KnowledgeCategory,
    Procedure,
    ProcedureStatus,
    TriggerType,
)
from brain.src.db.database import (
    ArchiveTable,
    EpisodeTable,
    KnowledgeTable,
    ProcedureTable,
    get_session,
)
from brain.src.logger import get_logger

log = get_logger("repositories")


class KnowledgeRepo:
    @staticmethod
    async def create(knowledge: Knowledge) -> Knowledge:
        async with await get_session() as session:
            row = KnowledgeTable(
                id=knowledge.id,
                content=knowledge.content,
                category=knowledge.category.value,
                importance=knowledge.importance,
                confidence=knowledge.confidence,
                access_count=knowledge.access_count,
                created_at=knowledge.created_at,
                updated_at=knowledge.updated_at,
                last_accessed=knowledge.last_accessed,
                source_device=knowledge.source_device,
                source_session=knowledge.source_session,
                decay_score=knowledge.decay_score,
                tags=json.dumps(knowledge.tags),
                previous_values=json.dumps(knowledge.previous_values),
            )
            session.add(row)
            await session.commit()
        return knowledge

    @staticmethod
    async def get(knowledge_id: str, record_access: bool = False) -> Knowledge | None:
        async with await get_session() as session:
            if record_access:
                await session.execute(
                    sa.update(KnowledgeTable)
                    .where(KnowledgeTable.id == knowledge_id)
                    .values(
                        access_count=KnowledgeTable.access_count + 1,
                        last_accessed=datetime.utcnow(),
                    )
                )
                await session.commit()
            result = await session.execute(
                sa.select(KnowledgeTable).where(KnowledgeTable.id == knowledge_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            return _row_to_knowledge(row)

    @staticmethod
    async def search(query: str, category: str | None = None, limit: int = 20) -> list[Knowledge]:
        async with await get_session() as session:
            stmt = sa.select(KnowledgeTable).where(
                KnowledgeTable.content.ilike(f"%{query}%")
            )
            if category:
                stmt = stmt.where(KnowledgeTable.category == category)
            stmt = stmt.order_by(KnowledgeTable.importance.desc()).limit(limit)
            result = await session.execute(stmt)
            return [_row_to_knowledge(r) for r in result.scalars().all()]

    @staticmethod
    async def update(knowledge: Knowledge) -> None:
        async with await get_session() as session:
            await session.execute(
                sa.update(KnowledgeTable)
                .where(KnowledgeTable.id == knowledge.id)
                .values(
                    content=knowledge.content,
                    category=knowledge.category.value,
                    importance=knowledge.importance,
                    confidence=knowledge.confidence,
                    access_count=knowledge.access_count,
                    updated_at=datetime.utcnow(),
                    last_accessed=knowledge.last_accessed,
                    decay_score=knowledge.decay_score,
                    tags=json.dumps(knowledge.tags),
                    previous_values=json.dumps(knowledge.previous_values),
                )
            )
            await session.commit()

    @staticmethod
    async def record_access(knowledge_id: str) -> None:
        async with await get_session() as session:
            await session.execute(
                sa.update(KnowledgeTable)
                .where(KnowledgeTable.id == knowledge_id)
                .values(
                    access_count=KnowledgeTable.access_count + 1,
                    last_accessed=datetime.utcnow(),
                )
            )
            await session.commit()

    @staticmethod
    async def get_all(limit: int = 100, min_decay: float = 0.1) -> list[Knowledge]:
        async with await get_session() as session:
            result = await session.execute(
                sa.select(KnowledgeTable)
                .where(KnowledgeTable.decay_score >= min_decay)
                .order_by(KnowledgeTable.importance.desc())
                .limit(limit)
            )
            return [_row_to_knowledge(r) for r in result.scalars().all()]

    @staticmethod
    async def delete(knowledge_id: str) -> None:
        async with await get_session() as session:
            await session.execute(
                sa.delete(KnowledgeTable).where(KnowledgeTable.id == knowledge_id)
            )
            await session.commit()


class EpisodeRepo:
    @staticmethod
    async def create(episode: Episode) -> Episode:
        async with await get_session() as session:
            row = EpisodeTable(
                id=episode.id,
                event_type=episode.event_type,
                title=episode.title,
                description=episode.description,
                actions=json.dumps(episode.actions),
                outcome=episode.outcome.value,
                duration_seconds=episode.duration_seconds,
                timestamp=episode.timestamp,
                day_of_week=episode.day_of_week,
                time_of_day=episode.time_of_day,
                device=episode.device,
                context=episode.context,
                learned=episode.learned,
                importance=episode.importance,
                linked_episode_ids=json.dumps(episode.linked_episode_ids),
            )
            session.add(row)
            await session.commit()
        return episode

    @staticmethod
    async def get_recent(limit: int = 20, device: str | None = None) -> list[Episode]:
        async with await get_session() as session:
            stmt = sa.select(EpisodeTable).order_by(EpisodeTable.timestamp.desc()).limit(limit)
            if device:
                stmt = stmt.where(EpisodeTable.device == device)
            result = await session.execute(stmt)
            return [_row_to_episode(r) for r in result.scalars().all()]

    @staticmethod
    async def search(query: str, limit: int = 10) -> list[Episode]:
        async with await get_session() as session:
            result = await session.execute(
                sa.select(EpisodeTable)
                .where(
                    sa.or_(
                        EpisodeTable.title.ilike(f"%{query}%"),
                        EpisodeTable.description.ilike(f"%{query}%"),
                    )
                )
                .order_by(EpisodeTable.timestamp.desc())
                .limit(limit)
            )
            return [_row_to_episode(r) for r in result.scalars().all()]


class ProcedureRepo:
    @staticmethod
    async def create(procedure: Procedure) -> Procedure:
        async with await get_session() as session:
            row = ProcedureTable(
                id=procedure.id,
                name=procedure.name,
                trigger_description=procedure.trigger_description,
                steps=json.dumps(procedure.steps),
                times_executed=procedure.times_executed,
                times_detected=procedure.times_detected,
                detection_threshold=procedure.detection_threshold,
                status=procedure.status.value,
                created_at=procedure.created_at,
                last_executed=procedure.last_executed,
                success_rate=procedure.success_rate,
                trigger_type=procedure.trigger_type.value,
                trigger_conditions=json.dumps(procedure.trigger_conditions),
                target_devices=json.dumps(procedure.target_devices),
            )
            session.add(row)
            await session.commit()
        return procedure

    @staticmethod
    async def get_active() -> list[Procedure]:
        async with await get_session() as session:
            result = await session.execute(
                sa.select(ProcedureTable).where(ProcedureTable.status == "active")
            )
            return [_row_to_procedure(r) for r in result.scalars().all()]

    @staticmethod
    async def update_status(procedure_id: str, status: ProcedureStatus) -> None:
        async with await get_session() as session:
            await session.execute(
                sa.update(ProcedureTable)
                .where(ProcedureTable.id == procedure_id)
                .values(status=status.value)
            )
            await session.commit()


# --- Row-to-model converters ---

def _row_to_knowledge(row: KnowledgeTable) -> Knowledge:
    return Knowledge(
        id=row.id,
        content=row.content,
        category=KnowledgeCategory(row.category),
        importance=row.importance,
        confidence=row.confidence,
        access_count=row.access_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_accessed=row.last_accessed,
        source_device=row.source_device,
        source_session=row.source_session,
        decay_score=row.decay_score,
        tags=json.loads(row.tags),
        previous_values=json.loads(row.previous_values),
    )


def _row_to_episode(row: EpisodeTable) -> Episode:
    return Episode(
        id=row.id,
        event_type=row.event_type,
        title=row.title,
        description=row.description,
        actions=json.loads(row.actions),
        outcome=EpisodeOutcome(row.outcome),
        duration_seconds=row.duration_seconds,
        timestamp=row.timestamp,
        day_of_week=row.day_of_week,
        time_of_day=row.time_of_day,
        device=row.device,
        context=row.context,
        learned=row.learned,
        importance=row.importance,
        linked_episode_ids=json.loads(row.linked_episode_ids),
    )


def _row_to_procedure(row: ProcedureTable) -> Procedure:
    return Procedure(
        id=row.id,
        name=row.name,
        trigger_description=row.trigger_description,
        steps=json.loads(row.steps),
        times_executed=row.times_executed,
        times_detected=row.times_detected,
        detection_threshold=row.detection_threshold,
        status=ProcedureStatus(row.status),
        created_at=row.created_at,
        last_executed=row.last_executed,
        success_rate=row.success_rate,
        trigger_type=TriggerType(row.trigger_type),
        trigger_conditions=json.loads(row.trigger_conditions),
        target_devices=json.loads(row.target_devices),
    )
