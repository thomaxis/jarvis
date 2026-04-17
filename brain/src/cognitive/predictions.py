"""Predictive suggestions -- time-based procedural triggers and proactive alerts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from brain.src.cognitive.procedural import ProceduralMemory
from brain.src.cognitive.models import TriggerType
from brain.src.logger import get_logger

log = get_logger("predictions")


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


class PredictionEngine:
    """Generates proactive suggestions based on time, patterns, and context."""

    def __init__(self, procedural: ProceduralMemory) -> None:
        self._procedural = procedural

    async def get_suggestions(self, device_id: str, now: datetime | None = None) -> list[dict[str, Any]]:
        """Get contextual suggestions based on current time and patterns."""
        now = now or datetime.utcnow()
        suggestions: list[dict[str, Any]] = []

        # Check time-based routine triggers
        time_suggestions = await self._check_time_triggers(now)
        suggestions.extend(time_suggestions)

        return suggestions

    async def _check_time_triggers(self, now: datetime) -> list[dict]:
        """Check if any active routines have time-based triggers that match now."""
        routines = await self._procedural.get_active_routines()
        matches = []

        day = now.strftime("%A").lower()
        hour = now.hour
        tod = _time_of_day(hour)

        for routine in routines:
            if routine.trigger_type != TriggerType.TIME_BASED:
                continue

            conditions = routine.trigger_conditions
            trigger_day = conditions.get("day", "").lower()
            trigger_hour = conditions.get("hour")
            trigger_time_of_day = conditions.get("time_of_day", "")

            day_match = not trigger_day or trigger_day == day or trigger_day == "daily"
            hour_match = trigger_hour is None or int(trigger_hour) == hour
            tod_match = not trigger_time_of_day or trigger_time_of_day == tod

            if day_match and hour_match and tod_match:
                matches.append({
                    "type": "routine_trigger",
                    "routine_name": routine.name,
                    "routine_id": routine.id,
                    "steps": routine.steps,
                    "message": f"It's {tod}. Want me to run '{routine.name}'?",
                })

        return matches

    def get_time_greeting(self, now: datetime | None = None) -> str:
        """Context-aware greeting based on current time."""
        now = now or datetime.utcnow()
        tod = _time_of_day(now.hour)
        day = now.strftime("%A")

        greetings = {
            "morning": f"Morning. It's {day}.",
            "afternoon": "Hey.",
            "evening": "Evening.",
            "night": "Still up?",
        }
        return greetings.get(tod, "Hey.")
