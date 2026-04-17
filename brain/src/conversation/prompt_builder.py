"""Builds the system prompt with brain context for LLM calls."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT_TEMPLATE = """You are Jarvis, a personal AI assistant. You are sharp, direct, and slightly witty. Like a trusted colleague who knows the user well.

## Your personality
- Tone: {tone}
- Verbosity: {verbosity}
- Device style: {device_style}
- Never say "certainly", "of course", "I'd be happy to". Just do it.
- Adapt: serious when troubleshooting, casual when chatting, concise on mobile.

## Current context
- Device: {device_id}
- Current topic: {topic}
{goals_section}
{cross_tasks_section}
{unresolved_section}

## What you know about the user
{knowledge_section}

## Recent conversation
{recent_messages_section}

## Recent corrections (respect these)
{corrections_section}

## Related concepts
{associations_section}

## Past experiences
{episodes_section}

{routine_section}

{plugins_section}

## How to respond
Just respond naturally in plain text. Be yourself. Talk like a real assistant, not a robot.
Keep it short and direct. No filler.

When the user asks you to DO something on their computer (open an app, play music, search, etc.), put the action command on its own line at the very end of your response, prefixed with [ACTION]:
  [ACTION] open_app chrome
  [ACTION] spotify_play Bohemian Rhapsody
  [ACTION] volume up
  [ACTION] search best restaurants nearby
  [ACTION] spotify_pause
  [ACTION] spotify_next
  [ACTION] spotify_setup <client_id>

Only add [ACTION] lines when the user is clearly asking you to do something. Most responses are just conversation with no actions.

If you learn something new about the user worth remembering, put it on its own line at the end prefixed with [REMEMBER]:
  [REMEMBER] User's name is Thomas
  [REMEMBER] User prefers dark mode
  [REMEMBER] User is building a SaaS called LeadCrush

If a plugin is NOT configured and the user tries to use it, explain what they need to do to set it up. Ask for the info directly.
"""


def build_system_prompt(context: dict[str, Any]) -> str:
    personality = context.get("personality", {})

    goals = context.get("active_goals", [])
    goals_section = ""
    if goals:
        goals_section = "## Active goals\n" + "\n".join(f"- {g['description']}" for g in goals)

    cross_tasks = context.get("cross_device_tasks", [])
    cross_tasks_section = ""
    if cross_tasks:
        cross_tasks_section = "## Pending cross-device tasks\n" + "\n".join(
            f"- {t['description']} (trigger: {t.get('trigger_device', 'any')})" for t in cross_tasks
        )

    unresolved = context.get("unresolved", [])
    unresolved_section = ""
    if unresolved:
        unresolved_section = "## Unresolved questions\n" + "\n".join(f"- {q}" for q in unresolved)

    knowledge = context.get("relevant_knowledge", [])
    knowledge_section = "No stored knowledge relevant to this query."
    if knowledge:
        lines = []
        for k in knowledge:
            lines.append(f"- [{k.get('category', 'general')}] {k['content']} (confidence: {k.get('confidence', 0.5)})")
        knowledge_section = "\n".join(lines)

    recent = context.get("recent_messages", [])
    recent_section = "No recent messages."
    if recent:
        lines = [f"{'User' if m['role'] == 'user' else 'Jarvis'}: {m['content']}" for m in recent[-6:]]
        recent_section = "\n".join(lines)

    corrections = context.get("corrections", [])
    corrections_section = "None."
    if corrections:
        corrections_section = "\n".join(f"- {c.get('correction', c)}" for c in corrections[:3])

    associations = context.get("associations", [])
    associations_section = "None."
    if associations:
        lines = [f"- {a['name']} ({a.get('type', 'topic')}, relevance: {a.get('activation_score', 0)})" for a in associations[:5]]
        associations_section = "\n".join(lines)

    episodes = context.get("recent_episodes", [])
    episodes_section = "None."
    if episodes:
        lines = [f"- {e['title']} ({e.get('outcome', 'unknown')}, device: {e.get('device', 'unknown')})" for e in episodes[:3]]
        episodes_section = "\n".join(lines)

    routine = context.get("matched_routine")
    routine_section = ""
    if routine:
        steps_str = ", ".join(f"{s.get('action', '?')} {s.get('target', '')}" for s in routine.get("steps", []))
        routine_section = f"## Matched routine: {routine['name']}\nSteps: {steps_str}\nExecute this routine if appropriate."

    plugins = context.get("plugins", [])
    plugins_section = ""
    if plugins:
        lines = []
        for p in plugins:
            status = "ready" if p.get("configured") else "NOT CONFIGURED"
            actions_str = ", ".join(p.get("actions", []))
            lines.append(f"- {p['name']}: {status} | Actions: {actions_str}")
        plugins_section = "## Available plugins\n" + "\n".join(lines)

    return SYSTEM_PROMPT_TEMPLATE.format(
        tone=personality.get("tone", "direct"),
        verbosity=personality.get("verbosity", "concise"),
        device_style=personality.get("device_style", "normal"),
        device_id=context.get("device_id", "unknown"),
        topic=context.get("current_topic", "none"),
        goals_section=goals_section,
        cross_tasks_section=cross_tasks_section,
        unresolved_section=unresolved_section,
        knowledge_section=knowledge_section,
        recent_messages_section=recent_section,
        corrections_section=corrections_section,
        associations_section=associations_section,
        episodes_section=episodes_section,
        routine_section=routine_section,
        plugins_section=plugins_section,
    )
