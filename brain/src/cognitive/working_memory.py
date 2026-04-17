"""Layer 1: Working Memory -- the conscious mind. Redis-backed, per-device contexts."""

from __future__ import annotations

import json
from dataclasses import asdict

from brain.src.cognitive.models import Action, DeviceContext, Goal, Message, PendingTask
from brain.src.logger import get_logger
from brain.src.redis_client import get_redis

log = get_logger("working_memory")

CAPACITY = 7  # Max items per device context window
CONTEXT_WINDOW_SIZE = 5

_KEY_PREFIX = "wm:"
_GOALS_KEY = f"{_KEY_PREFIX}goals"
_CROSS_TASKS_KEY = f"{_KEY_PREFIX}cross_device_tasks"
_FOCUS_KEY = f"{_KEY_PREFIX}focus_entity"


def _device_key(device_id: str) -> str:
    return f"{_KEY_PREFIX}device:{device_id}"


class WorkingMemory:
    """Per-device working memory with global goals and cross-device tasks."""

    async def get_device_context(self, device_id: str) -> DeviceContext:
        redis = get_redis()
        data = await redis.hgetall(_device_key(device_id))
        if not data:
            return DeviceContext(device_id=device_id)

        messages_raw = json.loads(data.get("context_window", "[]"))
        messages = [
            Message(
                role=m["role"],
                content=m["content"],
                device_id=m["device_id"],
            )
            for m in messages_raw
        ]

        return DeviceContext(
            device_id=device_id,
            context_window=messages,
            current_topic=data.get("current_topic", ""),
            unresolved=json.loads(data.get("unresolved", "[]")),
            pending_actions=[],
        )

    async def update_device_context(self, ctx: DeviceContext) -> None:
        redis = get_redis()
        messages = [
            {"role": m.role, "content": m.content, "device_id": m.device_id}
            for m in ctx.context_window[-CONTEXT_WINDOW_SIZE:]
        ]
        key = _device_key(ctx.device_id)
        await redis.hset(key, "context_window", json.dumps(messages))
        await redis.hset(key, "current_topic", ctx.current_topic)
        await redis.hset(key, "unresolved", json.dumps(ctx.unresolved))
        log.debug("working_memory_updated", device=ctx.device_id, topic=ctx.current_topic)

    async def add_message(self, device_id: str, message: Message) -> None:
        ctx = await self.get_device_context(device_id)
        ctx.context_window.append(message)
        if len(ctx.context_window) > CONTEXT_WINDOW_SIZE:
            ctx.context_window = ctx.context_window[-CONTEXT_WINDOW_SIZE:]
        await self.update_device_context(ctx)

    async def set_topic(self, device_id: str, topic: str) -> None:
        redis = get_redis()
        await redis.hset(_device_key(device_id), "current_topic", topic)

    async def add_unresolved(self, device_id: str, question: str) -> None:
        ctx = await self.get_device_context(device_id)
        ctx.unresolved.append(question)
        if len(ctx.unresolved) > CAPACITY:
            ctx.unresolved = ctx.unresolved[-CAPACITY:]
        await self.update_device_context(ctx)

    async def resolve_question(self, device_id: str, question: str) -> None:
        ctx = await self.get_device_context(device_id)
        ctx.unresolved = [q for q in ctx.unresolved if q != question]
        await self.update_device_context(ctx)

    async def clear_device(self, device_id: str) -> None:
        redis = get_redis()
        await redis.delete(_device_key(device_id))
        log.info("working_memory_cleared", device=device_id)

    # --- Global state ---

    async def get_goals(self) -> list[Goal]:
        redis = get_redis()
        raw = await redis.get(_GOALS_KEY)
        if not raw:
            return []
        return [Goal(**g) for g in json.loads(raw)]

    async def set_goals(self, goals: list[Goal]) -> None:
        redis = get_redis()
        data = [{"id": g.id, "description": g.description, "status": g.status.value} for g in goals]
        await redis.set(_GOALS_KEY, json.dumps(data))

    async def add_goal(self, goal: Goal) -> None:
        goals = await self.get_goals()
        goals.append(goal)
        await self.set_goals(goals)

    async def get_focus_entity(self) -> str | None:
        redis = get_redis()
        return await redis.get(_FOCUS_KEY)

    async def set_focus_entity(self, entity: str | None) -> None:
        redis = get_redis()
        if entity:
            await redis.set(_FOCUS_KEY, entity)
        else:
            await redis.delete(_FOCUS_KEY)

    async def add_cross_device_task(self, task: PendingTask) -> None:
        redis = get_redis()
        raw = await redis.get(_CROSS_TASKS_KEY)
        tasks = json.loads(raw) if raw else []
        tasks.append({
            "id": task.id,
            "description": task.description,
            "trigger_device": task.trigger_device,
            "trigger_condition": task.trigger_condition,
        })
        await redis.set(_CROSS_TASKS_KEY, json.dumps(tasks))

    async def get_cross_device_tasks(self) -> list[dict]:
        redis = get_redis()
        raw = await redis.get(_CROSS_TASKS_KEY)
        return json.loads(raw) if raw else []
