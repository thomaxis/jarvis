"""Offline mode: local cache + command queuing for when brain is unreachable."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.offline")


class OfflineCache:
    """Caches top knowledge and queues commands when brain is offline."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or Path.home() / ".jarvis" / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._knowledge_file = self._cache_dir / "knowledge.json"
        self._queue_file = self._cache_dir / "command_queue.json"
        self._personality_file = self._cache_dir / "personality.json"

    def cache_knowledge(self, knowledge: list[dict]) -> None:
        """Cache top knowledge entries for offline access."""
        with open(self._knowledge_file, "w") as f:
            json.dump(knowledge, f, indent=2)
        log.info("Cached %d knowledge entries", len(knowledge))

    def get_cached_knowledge(self) -> list[dict]:
        if not self._knowledge_file.exists():
            return []
        try:
            with open(self._knowledge_file) as f:
                return json.load(f)
        except Exception:
            return []

    def cache_personality(self, profile: dict) -> None:
        with open(self._personality_file, "w") as f:
            json.dump(profile, f, indent=2)

    def get_cached_personality(self) -> dict:
        if not self._personality_file.exists():
            return {}
        try:
            with open(self._personality_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def queue_command(self, command: dict) -> None:
        """Queue a command for replay when back online."""
        queue = self._load_queue()
        command["queued_at"] = datetime.utcnow().isoformat()
        queue.append(command)
        self._save_queue(queue)
        log.info("Queued command: %s", command.get("text", "")[:60])

    def get_queued_commands(self) -> list[dict]:
        return self._load_queue()

    def flush_queue(self) -> list[dict]:
        """Get and clear all queued commands."""
        queue = self._load_queue()
        self._save_queue([])
        log.info("Flushed %d queued commands", len(queue))
        return queue

    def _load_queue(self) -> list[dict]:
        if not self._queue_file.exists():
            return []
        try:
            with open(self._queue_file) as f:
                return json.load(f)
        except Exception:
            return []

    def _save_queue(self, queue: list[dict]) -> None:
        with open(self._queue_file, "w") as f:
            json.dump(queue, f, indent=2)
