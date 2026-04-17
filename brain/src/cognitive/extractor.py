"""LLM-powered fact extraction from conversations."""

from __future__ import annotations

import json
from typing import Any

from brain.src.logger import get_logger

log = get_logger("extractor")

EXTRACTION_PROMPT = """Extract factual information about the user from this conversation snippet. Return a JSON array of facts.

Each fact should have:
- "content": the fact as a clear statement
- "category": one of "preference", "habit", "personal", "correction", "style", "device_specific"
- "confidence": 0.0 to 1.0 (how certain this is a real fact, not a guess)

Rules:
- Only extract NEW information. Don't restate what was already known.
- Only extract facts about the USER, not general knowledge.
- Corrections ("actually use X not Y") are high-confidence facts.
- Preferences stated directly ("I prefer X") are high-confidence.
- Inferred habits ("user tends to X") are lower confidence (0.5-0.7).
- If no facts are extractable, return an empty array: []

Conversation:
{conversation}

Previously known facts (do NOT re-extract these):
{known_facts}

Return ONLY the JSON array, no other text."""


def build_extraction_prompt(messages: list[dict], known_facts: list[str]) -> str:
    """Build the extraction prompt from conversation messages."""
    conversation = "\n".join(
        f"{'User' if m.get('role') == 'user' else 'Jarvis'}: {m.get('content', '')}"
        for m in messages
    )
    known = "\n".join(f"- {f}" for f in known_facts) if known_facts else "None"
    return EXTRACTION_PROMPT.format(conversation=conversation, known_facts=known)


def parse_extracted_facts(raw_response: str) -> list[dict[str, Any]]:
    """Parse the LLM's extraction response into structured facts."""
    raw = raw_response.strip()

    # Handle markdown code blocks
    if raw.startswith("```"):
        lines = raw.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                json_lines.append(line)
        raw = "\n".join(json_lines)

    try:
        facts = json.loads(raw)
        if not isinstance(facts, list):
            return []

        valid_categories = {"preference", "habit", "personal", "correction", "style", "device_specific"}
        validated = []
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            if "content" not in fact:
                continue
            category = fact.get("category", "personal")
            if category not in valid_categories:
                category = "personal"
            confidence = fact.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            confidence = max(0.0, min(1.0, float(confidence)))

            validated.append({
                "content": str(fact["content"]),
                "category": category,
                "confidence": confidence,
            })

        return validated
    except json.JSONDecodeError:
        log.warning("extraction_parse_failed", raw=raw[:200])
        return []


async def extract_facts_from_session(
    messages: list[dict],
    known_facts: list[str],
    llm_call: Any,
) -> list[dict[str, Any]]:
    """Extract facts from a conversation session using the LLM.

    Args:
        messages: List of {"role": str, "content": str} dicts
        known_facts: List of already-known fact strings to avoid re-extraction
        llm_call: Async callable that takes (system_prompt, user_text) and returns str
    """
    if not messages:
        return []

    prompt = build_extraction_prompt(messages, known_facts)

    try:
        raw = await llm_call("You are a fact extraction system. Return only valid JSON.", prompt)
        facts = parse_extracted_facts(raw)
        log.info("facts_extracted", count=len(facts))
        return facts
    except Exception as e:
        log.error("extraction_failed", error=str(e))
        return []
