"""Action safety checks. Confirmation required for destructive operations."""

from __future__ import annotations

import logging

log = logging.getLogger("jarvis.safety")

# Actions that require user confirmation before execution
DESTRUCTIVE_ACTIONS = {
    "system_power",   # shutdown, restart, sleep
    "file_delete",    # deleting files
    "terminal",       # arbitrary command execution
}

# Actions that are always safe
SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "open_url",
    "search",
    "volume",
    "screenshot",
    "clipboard",
    "notification",
    "type_text",
    "media_control",
}


def requires_confirmation(action_type: str, target: str = "") -> bool:
    """Check if an action requires user confirmation."""
    if action_type in SAFE_ACTIONS:
        return False
    if action_type in DESTRUCTIVE_ACTIONS:
        return True
    # Unknown actions require confirmation by default
    return True


async def request_confirmation(action_type: str, target: str) -> bool:
    """Request confirmation from the user. Returns True if approved.

    In text mode, prompts via stdin. In voice mode, speaks and listens.
    """
    prompt = f"Execute {action_type}"
    if target:
        prompt += f" on '{target}'"
    prompt += "? [y/N] "

    try:
        response = input(prompt).strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
