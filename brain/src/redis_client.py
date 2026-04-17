"""Redis client with in-memory dict fallback for local dev."""

from __future__ import annotations

import json
from typing import Any

from brain.src.logger import get_logger

log = get_logger("redis")

_client: Any = None
_is_real_redis: bool = False


class InMemoryRedis:
    """Dict-based Redis substitute for local dev. Supports the subset we use."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._hashes: dict[str, dict[str, str]] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._store.pop(k, None)
            self._hashes.pop(k, None)

    async def exists(self, key: str) -> bool:
        return key in self._store or key in self._hashes

    async def hset(self, name: str, key: str, value: str) -> None:
        if name not in self._hashes:
            self._hashes[name] = {}
        self._hashes[name][key] = value

    async def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    async def hgetall(self, name: str) -> dict[str, str]:
        return dict(self._hashes.get(name, {}))

    async def hdel(self, name: str, *keys: str) -> None:
        if name in self._hashes:
            for k in keys:
                self._hashes[name].pop(k, None)

    async def lpush(self, key: str, *values: str) -> None:
        if key not in self._store:
            self._store[key] = []
        for v in values:
            self._store[key].insert(0, v)

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        lst = self._store.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start : stop + 1]

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        lst = self._store.get(key, [])
        if stop == -1:
            self._store[key] = lst[start:]
        else:
            self._store[key] = lst[start : stop + 1]

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


async def init_redis(url: str | None) -> None:
    """Initialize Redis connection. Falls back to in-memory if URL is None."""
    global _client, _is_real_redis

    if url:
        try:
            import redis.asyncio as aioredis
            _client = aioredis.from_url(url, decode_responses=True)
            await _client.ping()
            _is_real_redis = True
            log.info("redis_connected", url=url.split("@")[-1] if "@" in url else url)
            return
        except Exception as e:
            log.warning("redis_connection_failed", error=str(e), fallback="in_memory")

    _client = InMemoryRedis()
    _is_real_redis = False
    log.info("redis_using_fallback", type="in_memory")


def get_redis() -> Any:
    if _client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _client


def is_real_redis() -> bool:
    return _is_real_redis


async def close_redis() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None
