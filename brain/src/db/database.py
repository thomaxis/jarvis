"""SQLAlchemy async engine factory. PostgreSQL for prod, SQLite for dev."""

from __future__ import annotations

import json
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from brain.src.logger import get_logger

log = get_logger("db")


class Base(DeclarativeBase):
    pass


class KnowledgeTable(Base):
    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    importance: Mapped[float] = mapped_column(sa.Float, default=0.5)
    confidence: Mapped[float] = mapped_column(sa.Float, default=0.8)
    access_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    source_device: Mapped[str] = mapped_column(sa.String(100), default="")
    source_session: Mapped[str] = mapped_column(sa.String(100), default="")
    decay_score: Mapped[float] = mapped_column(sa.Float, default=1.0)
    tags: Mapped[str] = mapped_column(sa.Text, default="[]")
    previous_values: Mapped[str] = mapped_column(sa.Text, default="[]")


class EpisodeTable(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    event_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    title: Mapped[str] = mapped_column(sa.Text, default="")
    description: Mapped[str] = mapped_column(sa.Text, default="")
    actions: Mapped[str] = mapped_column(sa.Text, default="[]")
    outcome: Mapped[str] = mapped_column(sa.String(20), default="success")
    duration_seconds: Mapped[int] = mapped_column(sa.Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    day_of_week: Mapped[str] = mapped_column(sa.String(20), default="")
    time_of_day: Mapped[str] = mapped_column(sa.String(20), default="")
    device: Mapped[str] = mapped_column(sa.String(100), default="")
    context: Mapped[str] = mapped_column(sa.Text, default="")
    learned: Mapped[str] = mapped_column(sa.Text, default="")
    importance: Mapped[float] = mapped_column(sa.Float, default=0.5)
    linked_episode_ids: Mapped[str] = mapped_column(sa.Text, default="[]")


class ProcedureTable(Base):
    __tablename__ = "procedures"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    trigger_description: Mapped[str] = mapped_column(sa.Text, default="")
    steps: Mapped[str] = mapped_column(sa.Text, nullable=False, default="[]")
    times_executed: Mapped[int] = mapped_column(sa.Integer, default=0)
    times_detected: Mapped[int] = mapped_column(sa.Integer, default=0)
    detection_threshold: Mapped[int] = mapped_column(sa.Integer, default=3)
    status: Mapped[str] = mapped_column(sa.String(20), default="suggested")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    last_executed: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    success_rate: Mapped[float] = mapped_column(sa.Float, default=1.0)
    trigger_type: Mapped[str] = mapped_column(sa.String(30), default="verbal")
    trigger_conditions: Mapped[str] = mapped_column(sa.Text, default="{}")
    target_devices: Mapped[str] = mapped_column(sa.Text, default="[]")


class ArchiveTable(Base):
    __tablename__ = "archive"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    original_table: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    original_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    data: Mapped[str] = mapped_column(sa.Text, nullable=False)
    archived_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    reason: Mapped[str] = mapped_column(sa.String(100), default="decay")


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(db_url: str) -> None:
    """Initialize the database engine and create tables."""
    global _engine, _session_factory

    connect_args = {}
    if "sqlite" in db_url:
        connect_args["check_same_thread"] = False

    _engine = create_async_engine(db_url, echo=False, connect_args=connect_args)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info("database_initialized", url=db_url.split("@")[-1] if "@" in db_url else db_url)


async def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory()


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
