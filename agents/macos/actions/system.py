"""macOS system control: volume, brightness, lock, sleep."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.macos.system")


def set_volume(level: int | str) -> tuple[bool, str]:
    try:
        if isinstance(level, str):
            if level == "mute":
                subprocess.run(["osascript", "-e", "set volume output muted true"], capture_output=True, timeout=5)
                return True, "Muted"
            elif level == "up":
                subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"], capture_output=True, timeout=5)
                return True, "Volume up"
            elif level == "down":
                subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"], capture_output=True, timeout=5)
                return True, "Volume down"
            level = int(level)

        level = max(0, min(100, int(level)))
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"], capture_output=True, timeout=5)
        return True, f"Volume set to {level}%"
    except Exception as e:
        return False, f"Volume control failed: {e}"


def lock_screen() -> tuple[bool, str]:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'],
            capture_output=True, timeout=5,
        )
        return True, "Screen locked"
    except Exception as e:
        return False, f"Lock failed: {e}"


def sleep_display() -> tuple[bool, str]:
    try:
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True, timeout=5)
        return True, "Display sleeping"
    except Exception as e:
        return False, f"Sleep failed: {e}"


def shutdown(force: bool = False) -> tuple[bool, str]:
    try:
        cmd = ["osascript", "-e", 'tell application "System Events" to shut down']
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True, "Shutting down"
    except Exception as e:
        return False, f"Shutdown failed: {e}"


def restart(force: bool = False) -> tuple[bool, str]:
    try:
        cmd = ["osascript", "-e", 'tell application "System Events" to restart']
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True, "Restarting"
    except Exception as e:
        return False, f"Restart failed: {e}"


def get_battery_status() -> dict:
    try:
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5)
        return {"raw": result.stdout.strip()}
    except Exception:
        return {"status": "unavailable"}
