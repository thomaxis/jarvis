"""Layer 7: Personality Memory -- user interaction style and preferences."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.src.logger import get_logger

log = get_logger("personality")

DEFAULT_PROFILE: dict[str, Any] = {
    "tone_preference": "direct",
    "verbosity": "concise",
    "humor": True,
    "formality": "casual",
    "preferred_response_length": "short",
    "frustration_indicators": ["repeating commands", "saying 'just do it'"],
    "interaction_patterns": {
        "morning": "brief, wants efficiency",
        "evening": "more relaxed, open to chat",
        "when_debugging": "facts only, no filler",
    },
    "corrections_history": [],
    "per_device_style": {
        "phone": "extra concise, user is usually on the go",
        "desktop": "normal length, user has full attention",
    },
}


class PersonalityMemory:
    """Tracks how the user prefers to interact. Persisted to JSON on disk."""

    def __init__(self, profile_path: Path | None = None) -> None:
        self._path = profile_path
        self._profile: dict[str, Any] = dict(DEFAULT_PROFILE)
        if profile_path and profile_path.exists():
            with open(profile_path) as f:
                self._profile = json.load(f)
            log.info("personality_loaded", path=str(profile_path))

    @property
    def profile(self) -> dict[str, Any]:
        return dict(self._profile)

    def get(self, key: str, default: Any = None) -> Any:
        return self._profile.get(key, default)

    def update(self, key: str, value: Any) -> None:
        self._profile[key] = value

    def add_correction(self, correction: str) -> None:
        from datetime import datetime
        history = self._profile.get("corrections_history", [])
        history.append({"what": correction, "when": datetime.utcnow().isoformat()})
        self._profile["corrections_history"] = history
        log.info("personality_correction", correction=correction)

    def get_device_style(self, device_id: str) -> str:
        styles = self._profile.get("per_device_style", {})
        if "phone" in device_id or "mobile" in device_id or "ios" in device_id or "android" in device_id:
            return styles.get("phone", "concise")
        return styles.get("desktop", "normal")

    def get_time_style(self, time_of_day: str) -> str:
        patterns = self._profile.get("interaction_patterns", {})
        return patterns.get(time_of_day, "")

    def save(self) -> None:
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._profile, f, indent=2)
            log.info("personality_saved", path=str(self._path))
