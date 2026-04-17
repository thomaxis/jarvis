"""Layer 2: Short-Term Memory -- recent events from the last 30 minutes across all devices."""

from __future__ import annotations

import json
from datetime import datetime

from brain.src.cognitive.models import Message
from brain.src.logger import get_logger
from brain.src.redis_client import get_redis

log = get_logger("short_term")

BUFFER_SIZE = 20  # Per device
CORRECTIONS_SIZE = 10

_KEY_PREFIX = "stm:"


def _messages_key(device_id: str) -> str:
    return f"{_KEY_PREFIX}messages:{device_id}"


def _corrections_key() -> str:
    return f"{_KEY_PREFIX}corrections"


def _active_devices_key() -> str:
    return f"{_KEY_PREFIX}active_devices"


def _commands_key() -> str:
    return f"{_KEY_PREFIX}recent_commands"


class ShortTermMemory:
    """Recent events buffer. Redis-backed with auto-pruning."""

    async def add_message(self, device_id: str, message: Message) -> None:
        redis = get_redis()
        key = _messages_key(device_id)
        data = json.dumps({
            "role": message.role,
            "content": message.content,
            "device_id": message.device_id,
            "timestamp": message.timestamp.isoformat(),
        })
        await redis.lpush(key, data)
        await redis.ltrim(key, 0, BUFFER_SIZE - 1)

    async def get_messages(self, device_id: str, limit: int = BUFFER_SIZE) -> list[Message]:
        redis = get_redis()
        raw_list = await redis.lrange(_messages_key(device_id), 0, limit - 1)
        messages = []
        for raw in raw_list:
            data = json.loads(raw)
            messages.append(Message(
                role=data["role"],
                content=data["content"],
                device_id=data["device_id"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
            ))
        return list(reversed(messages))  # Oldest first

    async def get_all_recent_messages(self, limit: int = 50) -> list[Message]:
        """Get recent messages across all known devices."""
        devices = await self.get_active_devices()
        all_messages: list[Message] = []
        for device_id in devices:
            msgs = await self.get_messages(device_id, limit=limit)
            all_messages.extend(msgs)
        all_messages.sort(key=lambda m: m.timestamp)
        return all_messages[-limit:]

    async def add_correction(self, correction: str, device_id: str) -> None:
        redis = get_redis()
        data = json.dumps({
            "correction": correction,
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        await redis.lpush(_corrections_key(), data)
        await redis.ltrim(_corrections_key(), 0, CORRECTIONS_SIZE - 1)
        log.info("correction_recorded", correction=correction, device=device_id)

    async def get_corrections(self) -> list[dict]:
        redis = get_redis()
        raw_list = await redis.lrange(_corrections_key(), 0, -1)
        return [json.loads(r) for r in raw_list]

    async def add_command(self, command: str, device_id: str) -> None:
        redis = get_redis()
        data = json.dumps({
            "command": command,
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        await redis.lpush(_commands_key(), data)
        await redis.ltrim(_commands_key(), 0, 49)

    async def get_recent_commands(self, limit: int = 20) -> list[dict]:
        redis = get_redis()
        raw_list = await redis.lrange(_commands_key(), 0, limit - 1)
        return [json.loads(r) for r in raw_list]

    async def register_device(self, device_id: str) -> None:
        redis = get_redis()
        await redis.hset(_active_devices_key(), device_id, datetime.utcnow().isoformat())
        log.info("device_registered", device=device_id)

    async def unregister_device(self, device_id: str) -> None:
        redis = get_redis()
        await redis.hdel(_active_devices_key(), device_id)
        log.info("device_unregistered", device=device_id)

    async def get_active_devices(self) -> list[str]:
        redis = get_redis()
        devices = await redis.hgetall(_active_devices_key())
        return list(devices.keys())

    async def clear_device(self, device_id: str) -> None:
        redis = get_redis()
        await redis.delete(_messages_key(device_id))
