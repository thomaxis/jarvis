"""Linux system control: volume, brightness, lock, power."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("jarvis.linux.system")


def set_volume(level: int | str) -> tuple[bool, str]:
    try:
        if isinstance(level, str):
            if level == "mute":
                subprocess.run(["amixer", "set", "Master", "mute"], capture_output=True, timeout=5)
                return True, "Muted"
            elif level == "up":
                subprocess.run(["amixer", "set", "Master", "5%+"], capture_output=True, timeout=5)
                return True, "Volume up"
            elif level == "down":
                subprocess.run(["amixer", "set", "Master", "5%-"], capture_output=True, timeout=5)
                return True, "Volume down"
            level = int(level)

        level = max(0, min(100, int(level)))
        subprocess.run(["amixer", "set", "Master", f"{level}%"], capture_output=True, timeout=5)
        return True, f"Volume set to {level}%"
    except Exception as e:
        return False, f"Volume control failed: {e}"


def lock_screen() -> tuple[bool, str]:
    try:
        # Try multiple lock commands
        for cmd in [["loginctl", "lock-session"], ["xdg-screensaver", "lock"], ["gnome-screensaver-command", "-l"]]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5, check=True)
                return True, "Screen locked"
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        return False, "No screen locker found"
    except Exception as e:
        return False, f"Lock failed: {e}"


def shutdown(force: bool = False) -> tuple[bool, str]:
    try:
        subprocess.run(["systemctl", "poweroff"], capture_output=True, timeout=5)
        return True, "Shutting down"
    except Exception as e:
        return False, f"Shutdown failed: {e}"


def restart(force: bool = False) -> tuple[bool, str]:
    try:
        subprocess.run(["systemctl", "reboot"], capture_output=True, timeout=5)
        return True, "Restarting"
    except Exception as e:
        return False, f"Restart failed: {e}"


def suspend() -> tuple[bool, str]:
    try:
        subprocess.run(["systemctl", "suspend"], capture_output=True, timeout=5)
        return True, "Suspended"
    except Exception as e:
        return False, f"Suspend failed: {e}"
