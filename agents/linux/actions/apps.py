"""Linux app management using xdg-open and process control."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.linux.apps")

APP_MAP: dict[str, str] = {
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "chromium": "chromium-browser",
    "firefox": "firefox",
    "terminal": "x-terminal-emulator",
    "files": "nautilus",
    "file manager": "nautilus",
    "vs code": "code",
    "visual studio code": "code",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "steam": "steam",
    "gimp": "gimp",
    "vlc": "vlc",
    "calculator": "gnome-calculator",
    "settings": "gnome-control-center",
    "text editor": "gedit",
}


def open_app(name: str) -> tuple[bool, str]:
    name_lower = name.lower().strip()
    executable = APP_MAP.get(name_lower, name_lower)
    try:
        subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Opened {name}"
    except FileNotFoundError:
        # Try xdg-open as fallback
        try:
            subprocess.Popen(["xdg-open", executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Opened {name}"
        except Exception:
            return False, f"App not found: {name}"
    except Exception as e:
        return False, f"Failed to open {name}: {e}"


def close_app(name: str) -> tuple[bool, str]:
    name_lower = name.lower().strip()
    executable = APP_MAP.get(name_lower, name_lower)
    try:
        subprocess.run(["pkill", "-f", executable], capture_output=True, timeout=5)
        return True, f"Closed {name}"
    except Exception as e:
        return False, f"Failed to close {name}: {e}"


def list_running_apps() -> list[str]:
    try:
        result = subprocess.run(
            ["wmctrl", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        titles = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split(None, 3)
            if len(parts) >= 4:
                titles.append(parts[3])
        return titles
    except Exception:
        return []
