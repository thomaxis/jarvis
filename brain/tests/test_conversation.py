"""Tests for the Conversation Engine."""

from __future__ import annotations

from brain.src.conversation.intent import Intent, detect_intent, extract_entities
from brain.src.conversation.persona import apply_persona_rules, get_greeting
from brain.src.conversation.prompt_builder import build_system_prompt


def test_detect_action_open() -> None:
    intent = detect_intent("Open Chrome")
    assert intent.type == "action"
    assert intent.entities["action"] == "open_app"
    assert "chrome" in intent.entities.get("target", "").lower()


def test_detect_action_close() -> None:
    intent = detect_intent("Close Spotify")
    assert intent.type == "action"
    assert intent.entities["action"] == "close_app"


def test_detect_volume() -> None:
    intent = detect_intent("Volume up")
    assert intent.type == "action"
    assert intent.entities["action"] == "volume"


def test_detect_question() -> None:
    intent = detect_intent("What time is the meeting?")
    assert intent.type == "question"


def test_detect_memory_store() -> None:
    intent = detect_intent("Remember that I prefer dark mode")
    assert intent.type == "memory_query"
    assert intent.entities["operation"] == "store"


def test_detect_memory_query() -> None:
    intent = detect_intent("What do you know about me?")
    assert intent.type == "memory_query"


def test_detect_routine_trigger() -> None:
    intent = detect_intent("Do my morning routine")
    assert intent.type == "command"
    assert intent.entities["command"] == "routine_trigger"


def test_detect_conversation() -> None:
    intent = detect_intent("I had a great day today")
    assert intent.type == "conversation"


def test_extract_app_entity() -> None:
    entities = extract_entities("Open Chrome and VS Code")
    assert "app" in entities


def test_extract_url_entity() -> None:
    entities = extract_entities("Go to https://github.com/test")
    assert entities["url"] == "https://github.com/test"


def test_extract_time_entity() -> None:
    entities = extract_entities("Set a reminder for 3:30 pm")
    assert "time" in entities


def test_persona_strips_banned() -> None:
    text = "Certainly, I'd be happy to help you with that."
    cleaned = apply_persona_rules(text, {"verbosity": "concise"})
    assert "certainly" not in cleaned.lower()
    assert "I'd be happy to" not in cleaned


def test_persona_trims_verbose() -> None:
    text = "First. Second. Third. Fourth. Fifth. Sixth."
    cleaned = apply_persona_rules(text, {"verbosity": "concise"})
    assert cleaned.count(".") <= 5  # Max 4 sentences + trailing


def test_greeting() -> None:
    g = get_greeting("morning", {"humor": True})
    assert g is not None
    assert "morning" in g.lower() or "coffee" in g.lower()


def test_build_prompt_basic() -> None:
    context = {
        "device_id": "windows-main",
        "input": "Open Chrome",
        "current_topic": "browsing",
        "unresolved": [],
        "active_goals": [],
        "cross_device_tasks": [],
        "recent_messages": [{"role": "user", "content": "Open Chrome"}],
        "corrections": [],
        "relevant_knowledge": [{"content": "User prefers Chrome", "category": "preference", "confidence": 0.9}],
        "semantic_matches": [],
        "associations": [],
        "recent_episodes": [],
        "matched_routine": None,
        "personality": {"tone": "direct", "verbosity": "concise", "device_style": "normal"},
    }
    prompt = build_system_prompt(context)
    assert "Jarvis" in prompt
    assert "windows-main" in prompt
    assert "User prefers Chrome" in prompt
    assert "browsing" in prompt
