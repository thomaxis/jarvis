"""macOS app management using osascript and subprocess."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.macos.apps")

APP_MAP: dict[str, str] = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "finder": "Finder",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "spotify": "Spotify",
    "discord": "Discord",
    "slack": "Slack",
    "notes": "Notes",
    "messages": "Messages",
    "mail": "Mail",
    "calendar": "Calendar",
    "xcode": "Xcode",
    "preview": "Preview",
    "photos": "Photos",
    "music": "Music",
}


def open_app(name: str) -> tuple[bool, str]:
    name_lower = name.lower().strip()
    app_name = APP_MAP.get(name_lower, name)
    try:
        subprocess.run(["open", "-a", app_name], capture_output=True, check=True, timeout=10)
        return True, f"Opened {app_name}"
    except subprocess.CalledProcessError:
        return False, f"Could not find app: {app_name}"
    except Exception as e:
        return False, f"Failed to open {app_name}: {e}"


def close_app(name: str) -> tuple[bool, str]:
    name_lower = name.lower().strip()
    app_name = APP_MAP.get(name_lower, name)
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{app_name}" to quit'],
            capture_output=True, check=True, timeout=10,
        )
        return True, f"Closed {app_name}"
    except subprocess.CalledProcessError:
        return False, f"{app_name} is not running"
    except Exception as e:
        return False, f"Failed to close {app_name}: {e}"


def list_running_apps() -> list[str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'],
            capture_output=True, text=True, timeout=5,
        )
        return [a.strip() for a in result.stdout.split(",") if a.strip()]
    except Exception:
        return []
