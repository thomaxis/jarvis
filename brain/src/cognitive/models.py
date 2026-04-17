"""Core data models for the cognitive architecture."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# --- Enums ---

class KnowledgeCategory(str, Enum):
    PREFERENCE = "preference"
    HABIT = "habit"
    PERSONAL = "personal"
    CORRECTION = "correction"
    STYLE = "style"
    DEVICE_SPECIFIC = "device_specific"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EpisodeOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ProcedureStatus(str, Enum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    DISABLED = "disabled"


class TriggerType(str, Enum):
    VERBAL = "verbal"
    TIME_BASED = "time_based"
    CONTEXT_BASED = "context_based"
    DEVICE_EVENT = "device_event"
    MANUAL = "manual"


# --- Core Data Models ---

@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    device_id: str
    timestamp: datetime = field(default_factory=_now)


@dataclass
class Goal:
    id: str = field(default_factory=_new_id)
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=_now)


@dataclass
class Action:
    id: str = field(default_factory=_new_id)
    type: str = ""
    target: str = ""
    device: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class PendingTask:
    id: str = field(default_factory=_new_id)
    description: str = ""
    trigger_device: str = ""
    trigger_condition: str = ""
    actions: list[Action] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)


@dataclass
class DeviceContext:
    device_id: str
    context_window: list[Message] = field(default_factory=list)
    current_topic: str = ""
    unresolved: list[str] = field(default_factory=list)
    pending_actions: list[Action] = field(default_factory=list)
    last_activity: datetime = field(default_factory=_now)


@dataclass
class Knowledge:
    id: str = field(default_factory=_new_id)
    content: str = ""
    category: KnowledgeCategory = KnowledgeCategory.PERSONAL
    importance: float = 0.5
    confidence: float = 0.8
    access_count: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    last_accessed: datetime = field(default_factory=_now)
    source_device: str = ""
    source_session: str = ""
    decay_score: float = 1.0
    tags: list[str] = field(default_factory=list)
    previous_values: list[str] = field(default_factory=list)


@dataclass
class Episode:
    id: str = field(default_factory=_new_id)
    event_type: str = ""
    title: str = ""
    description: str = ""
    actions: list[dict] = field(default_factory=list)
    outcome: EpisodeOutcome = EpisodeOutcome.SUCCESS
    duration_seconds: int = 0
    timestamp: datetime = field(default_factory=_now)
    day_of_week: str = ""
    time_of_day: str = ""
    device: str = ""
    context: str = ""
    learned: str = ""
    importance: float = 0.5
    linked_episode_ids: list[str] = field(default_factory=list)


@dataclass
class Procedure:
    id: str = field(default_factory=_new_id)
    name: str = ""
    trigger_description: str = ""
    steps: list[dict] = field(default_factory=list)
    times_executed: int = 0
    times_detected: int = 0
    detection_threshold: int = 3
    status: ProcedureStatus = ProcedureStatus.SUGGESTED
    created_at: datetime = field(default_factory=_now)
    last_executed: datetime | None = None
    success_rate: float = 1.0
    trigger_type: TriggerType = TriggerType.VERBAL
    trigger_conditions: dict = field(default_factory=dict)
    target_devices: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str = field(default_factory=_new_id)
    parent_id: str | None = None
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    target_device: str | None = None
    actions: list[Action] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    completed_at: datetime | None = None
    result: str | None = None
