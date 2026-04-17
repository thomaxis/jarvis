"""Terminal/shell command execution."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.actions.terminal")

# Commands that are NEVER allowed
BLOCKED_COMMANDS = {
    "rm -rf /", "del /f /s /q C:\\", "format", "mkfs",
    "shutdown", "restart",  # Use system.py for these
}


def run_command(command: str, shell: str = "powershell", timeout: int = 30) -> tuple[bool, str]:
    """Execute a shell command and return the output."""
    # Safety check
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return False, f"Blocked dangerous command: {command}"

    try:
        if shell == "powershell":
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
            )
        else:
            result = subprocess.run(
                ["cmd", "/c", command],
                capture_output=True, text=True, timeout=timeout,
            )

        output = result.stdout.strip() or result.stderr.strip()
        success = result.returncode == 0
        return success, output[:2000]  # Cap output length
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, f"Command failed: {e}"
