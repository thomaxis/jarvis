"""Per-device permission checks."""

from __future__ import annotations

from typing import Any

from brain.src.logger import get_logger

log = get_logger("permissions")

# Default permissions by platform
PLATFORM_PERMISSIONS: dict[str, set[str]] = {
    "windows": {"os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice"},
    "macos": {"os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice"},
    "linux": {"os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice"},
    "ios": {"voice", "notifications", "reminders"},
    "android": {"voice", "notifications", "reminders"},
}

# Actions that require specific permissions
ACTION_PERMISSIONS: dict[str, str] = {
    "open_app": "apps",
    "close_app": "apps",
    "open_url": "browser",
    "search": "browser",
    "file_op": "files",
    "terminal": "terminal",
    "clipboard": "clipboard",
    "volume": "system",
    "system_power": "system",
    "screenshot": "os_control",
    "type_text": "os_control",
    "notification": "notifications",
}


def check_permission(
    action_type: str,
    agent_payload: dict[str, Any],
) -> bool:
    """Check if an agent has permission to execute an action."""
    platform = agent_payload.get("platform", "unknown")
    capabilities = set(agent_payload.get("capabilities", []))

    required = ACTION_PERMISSIONS.get(action_type)
    if not required:
        return True  # Unknown actions default to allowed

    platform_perms = PLATFORM_PERMISSIONS.get(platform, set())
    allowed = platform_perms | capabilities

    if required not in allowed:
        log.warning(
            "permission_denied",
            action=action_type,
            required=required,
            platform=platform,
            device=agent_payload.get("sub", "unknown"),
        )
        return False

    return True
