"""Windows app management: open, close, switch applications."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.actions.apps")

# Common app names to executable mappings
APP_MAP: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd": "cmd",
    "terminal": "wt",
    "windows terminal": "wt",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "vs code": "code",
    "visual studio code": "code",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "steam": "steam",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
}


def open_app(name: str) -> tuple[bool, str]:
    """Open an application by name."""
    name_lower = name.lower().strip()
    executable = APP_MAP.get(name_lower, name_lower)

    try:
        if executable.startswith("ms-"):
            # Windows URI scheme
            subprocess.Popen(["start", executable], shell=True)
        else:
            subprocess.Popen(["start", "", executable], shell=True)
        log.info("Opened: %s", name)
        return True, f"Opened {name}"
    except Exception as e:
        log.error("Failed to open %s: %s", name, e)
        return False, f"Failed to open {name}: {e}"


def close_app(name: str) -> tuple[bool, str]:
    """Close an application by name."""
    name_lower = name.lower().strip()
    executable = APP_MAP.get(name_lower, name_lower)

    # Map to process names
    process_map = {
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "msedge": "msedge.exe",
        "code": "Code.exe",
        "spotify": "Spotify.exe",
        "discord": "Discord.exe",
        "slack": "slack.exe",
        "notepad": "notepad.exe",
    }
    process_name = process_map.get(executable, f"{executable}.exe")

    try:
        subprocess.run(["taskkill", "/IM", process_name, "/F"], capture_output=True, check=True)
        log.info("Closed: %s", name)
        return True, f"Closed {name}"
    except subprocess.CalledProcessError:
        return False, f"{name} is not running"
    except Exception as e:
        return False, f"Failed to close {name}: {e}"


def list_running_apps() -> list[str]:
    """List currently running window titles."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -ExpandProperty MainWindowTitle"],
            capture_output=True, text=True, timeout=5,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception:
        return []
