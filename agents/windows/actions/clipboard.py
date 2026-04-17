"""Clipboard read/write operations."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.actions.clipboard")


def read_clipboard() -> tuple[bool, str]:
    """Read text from the clipboard."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        content = result.stdout.strip()
        return True, content
    except Exception as e:
        return False, f"Clipboard read failed: {e}"


def write_clipboard(text: str) -> tuple[bool, str]:
    """Write text to the clipboard."""
    try:
        subprocess.run(
            ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
            capture_output=True, timeout=5,
        )
        return True, "Copied to clipboard"
    except Exception as e:
        return False, f"Clipboard write failed: {e}"
