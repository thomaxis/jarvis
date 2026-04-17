"""Tests for Layer 7: Personality Memory."""

from __future__ import annotations

from brain.src.cognitive.personality import PersonalityMemory


def test_default_profile() -> None:
    pm = PersonalityMemory()
    assert pm.get("tone_preference") == "direct"
    assert pm.get("verbosity") == "concise"


def test_update() -> None:
    pm = PersonalityMemory()
    pm.update("tone_preference", "formal")
    assert pm.get("tone_preference") == "formal"


def test_add_correction() -> None:
    pm = PersonalityMemory()
    pm.add_correction("stop saying certainly")
    history = pm.profile.get("corrections_history", [])
    assert len(history) == 1
    assert history[0]["what"] == "stop saying certainly"


def test_device_style() -> None:
    pm = PersonalityMemory()
    assert "concise" in pm.get_device_style("phone-android")
    assert pm.get_device_style("windows-main") == "normal length, user has full attention"


def test_time_style() -> None:
    pm = PersonalityMemory()
    assert "efficiency" in pm.get_time_style("morning")
    assert pm.get_time_style("nonexistent") == ""
