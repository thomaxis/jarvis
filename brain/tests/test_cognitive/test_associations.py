"""Tests for Layer 4: Associative Memory."""

from __future__ import annotations

from brain.src.cognitive.associations import AssociativeMemory


def test_add_and_get_related() -> None:
    am = AssociativeMemory()
    am.add_node("Chrome", "app")
    am.add_node("browsing", "topic")
    am.add_association("Chrome", "browsing", context="web")

    related = am.get_related("Chrome")
    assert len(related) == 1
    assert related[0]["name"] == "browsing"
    assert related[0]["weight"] > 0


def test_strengthen_association() -> None:
    am = AssociativeMemory()
    am.add_node("VS Code", "app")
    am.add_node("coding", "topic")

    am.add_association("VS Code", "coding")
    am.add_association("VS Code", "coding")
    am.add_association("VS Code", "coding")

    related = am.get_related("VS Code")
    assert related[0]["co_occurrences"] == 3
    assert related[0]["weight"] > 0.3


def test_spreading_activation() -> None:
    am = AssociativeMemory()
    am.add_node("design", "topic")
    am.add_node("Photoshop", "app")
    am.add_node("Figma", "app")
    am.add_node("portfolio", "project")

    am.add_association("design", "Photoshop")
    am.add_association("design", "Figma")
    am.add_association("Photoshop", "portfolio")

    activated = am.activate(["design"], depth=2)
    names = [a["name"] for a in activated]
    assert "Photoshop" in names
    assert "Figma" in names


def test_auto_create_nodes() -> None:
    am = AssociativeMemory()
    am.add_association("new_concept_a", "new_concept_b")

    related = am.get_related("new_concept_a")
    assert len(related) == 1
    assert related[0]["name"] == "new_concept_b"


def test_stats() -> None:
    am = AssociativeMemory()
    am.add_node("A", "topic")
    am.add_node("B", "topic")
    am.add_association("A", "B")

    stats = am.get_stats()
    assert stats["nodes"] == 2
    assert stats["edges"] == 1


def test_get_related_empty() -> None:
    am = AssociativeMemory()
    related = am.get_related("nonexistent")
    assert related == []
