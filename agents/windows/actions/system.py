"""Windows system control: volume, brightness, lock, shutdown."""

from __future__ import annotations

import ctypes
import logging
import subprocess

log = logging.getLogger("jarvis.actions.system")


def set_volume(level: int | str) -> tuple[bool, str]:
    """Set system volume. Accepts 0-100 or 'mute'/'unmute'."""
    try:
        if isinstance(level, str):
            if level == "mute":
                subprocess.run(
                    ["powershell", "-Command",
                     "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                    capture_output=True, timeout=5,
                )
                return True, "Muted"
            elif level == "up":
                for _ in range(5):
                    subprocess.run(
                        ["powershell", "-Command",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"],
                        capture_output=True, timeout=5,
                    )
                return True, "Volume up"
            elif level == "down":
                for _ in range(5):
                    subprocess.run(
                        ["powershell", "-Command",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"],
                        capture_output=True, timeout=5,
                    )
                return True, "Volume down"
            level = int(level)

        level = max(0, min(100, int(level)))
        subprocess.run(
            ["powershell", "-Command",
             f"Set-AudioDevice -PlaybackVolume {level}"],
            capture_output=True, timeout=5,
        )
        return True, f"Volume set to {level}%"
    except Exception as e:
        return False, f"Volume control failed: {e}"


def lock_screen() -> tuple[bool, str]:
    """Lock the workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return True, "Screen locked"
    except Exception as e:
        return False, f"Lock failed: {e}"


def shutdown(force: bool = False) -> tuple[bool, str]:
    """Shutdown the computer."""
    try:
        cmd = ["shutdown", "/s", "/t", "5"]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, capture_output=True)
        return True, "Shutting down in 5 seconds"
    except Exception as e:
        return False, f"Shutdown failed: {e}"


def restart(force: bool = False) -> tuple[bool, str]:
    """Restart the computer."""
    try:
        cmd = ["shutdown", "/r", "/t", "5"]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, capture_output=True)
        return True, "Restarting in 5 seconds"
    except Exception as e:
        return False, f"Restart failed: {e}"


def sleep_screen() -> tuple[bool, str]:
    """Put display to sleep."""
    try:
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return True, "Display sleeping"
    except Exception as e:
        return False, f"Sleep failed: {e}"


def get_battery_status() -> dict:
    """Get battery info (laptops only)."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-WmiObject Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus | ConvertTo-Json)"],
            capture_output=True, text=True, timeout=5,
        )
        import json
        return json.loads(result.stdout) if result.stdout.strip() else {"status": "no_battery"}
    except Exception:
        return {"status": "unavailable"}
