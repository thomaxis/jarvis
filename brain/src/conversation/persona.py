"""Jarvis personality rules and tone logic."""

from __future__ import annotations

from typing import Any


# Words and phrases Jarvis never uses
BANNED_PHRASES = [
    "certainly",
    "of course",
    "I'd be happy to",
    "I'll be glad to",
    "sure thing",
    "absolutely",
    "great question",
    "furthermore",
    "additionally",
    "moreover",
    "leverage",
    "utilize",
    "streamline",
    "cutting-edge",
    "delve",
    "comprehensive",
    "innovative",
]


def apply_persona_rules(response: str, personality: dict[str, Any]) -> str:
    """Clean up LLM response to match Jarvis persona."""
    # Strip banned phrases
    for phrase in BANNED_PHRASES:
        response = response.replace(phrase, "")
        response = response.replace(phrase.capitalize(), "")

    # Clean up double spaces from removals
    while "  " in response:
        response = response.replace("  ", " ")

    # Trim verbosity if personality says concise
    verbosity = personality.get("verbosity", "concise")
    if verbosity == "concise":
        sentences = response.split(". ")
        if len(sentences) > 4:
            response = ". ".join(sentences[:4]) + "."

    return response.strip()


def get_greeting(time_of_day: str, personality: dict[str, Any]) -> str | None:
    """Context-aware greeting based on time and personality."""
    humor = personality.get("humor", True)

    greetings = {
        "morning": "Morning." if not humor else "Morning. Coffee first?",
        "afternoon": "Hey.",
        "evening": "Evening." if not humor else "Evening. Still at it?",
        "night": "Still up?" if humor else "Hey.",
    }
    return greetings.get(time_of_day)
