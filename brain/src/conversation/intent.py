"""Intent detection and entity extraction from user input."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    type: str  # action, question, conversation, command, memory_query
    confidence: float = 0.5
    entities: dict[str, Any] = field(default_factory=dict)


# Action patterns: things the user wants Jarvis to DO
_ACTION_PATTERNS = [
    (r"\b(open|launch|start|run)\b\s+(.+)", "open_app"),
    (r"\b(close|quit|exit|kill)\b\s+(.+)", "close_app"),
    (r"\b(search|google|look up)\b\s+(.+)", "search"),
    (r"\b(play|pause|stop|next|previous)\b\s*(music|song|track)?", "media_control"),
    (r"\bvolume\s+(up|down|mute|\d+)", "volume"),
    (r"\b(set|create)\s+(reminder|alarm|timer)\b", "reminder"),
    (r"\b(type|write|input)\b\s+(.+)", "type_text"),
    (r"\b(screenshot|capture)\b", "screenshot"),
    (r"\b(lock|sleep|shutdown|restart)\b", "system_power"),
]

# Question patterns
_QUESTION_PATTERNS = [
    r"^(what|who|where|when|why|how|which|can you|do you|is there|are there)\b",
    r"\?$",
]

# Memory patterns
_MEMORY_PATTERNS = [
    (r"\b(remember|memorize|save|store)\b.*\b(that|this)\b", "store"),
    (r"\b(forget|delete|remove)\b.*\b(memory|fact|knowledge)\b", "delete"),
    (r"\bwhat do you (know|remember)\b", "query"),
    (r"\bshow.*memories\b", "query"),
]

# Command patterns (Jarvis-specific)
_COMMAND_PATTERNS = [
    (r"\bmorning\s*(routine|setup)\b", "routine_trigger"),
    (r"\bdo (the|my) usual\b", "routine_trigger"),
    (r"\brun\s+routine\b", "routine_trigger"),
    (r"\bstop remembering\b", "pause_memory"),
    (r"\breset brain\b", "reset"),
    (r"\bexport brain\b", "export"),
]


def detect_intent(text: str) -> Intent:
    """Detect the primary intent from user input."""
    text_lower = text.lower().strip()

    # Check command patterns first (highest priority)
    for pattern, cmd_type in _COMMAND_PATTERNS:
        if re.search(pattern, text_lower):
            return Intent(type="command", confidence=0.9, entities={"command": cmd_type})

    # Check memory patterns
    for pattern, mem_type in _MEMORY_PATTERNS:
        if re.search(pattern, text_lower):
            return Intent(type="memory_query", confidence=0.85, entities={"operation": mem_type})

    # Check action patterns
    for pattern, action_type in _ACTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            entities = {"action": action_type}
            if match.lastindex and match.lastindex >= 2:
                entities["target"] = match.group(2).strip()
            elif match.lastindex and match.lastindex >= 1:
                entities["target"] = match.group(1).strip()
            return Intent(type="action", confidence=0.8, entities=entities)

    # Check question patterns
    for pattern in _QUESTION_PATTERNS:
        if re.search(pattern, text_lower):
            return Intent(type="question", confidence=0.7, entities={})

    # Default to conversation
    return Intent(type="conversation", confidence=0.5, entities={})


def extract_entities(text: str) -> dict[str, str]:
    """Extract named entities from text. Simple regex-based extraction."""
    entities: dict[str, str] = {}

    # App names (common ones)
    app_pattern = r"\b(chrome|firefox|safari|edge|vs ?code|visual studio|slack|discord|spotify|steam|photoshop|figma|terminal|cmd|powershell)\b"
    match = re.search(app_pattern, text.lower())
    if match:
        entities["app"] = match.group(1)

    # File paths
    path_pattern = r"(?:[A-Z]:\\|~\/|\.\/|\/)[^\s]+"
    match = re.search(path_pattern, text)
    if match:
        entities["path"] = match.group(0)

    # URLs
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, text)
    if match:
        entities["url"] = match.group(0)

    # Time expressions
    time_pattern = r"\b(\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|in\s+\d+\s+(?:minutes?|hours?|seconds?))\b"
    match = re.search(time_pattern, text.lower())
    if match:
        entities["time"] = match.group(1)

    return entities
