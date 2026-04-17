"""Linux file operations."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger("jarvis.linux.files")


def open_file(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"File not found: {path}"
    try:
        subprocess.Popen(["xdg-open", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Opened {p.name}"
    except Exception as e:
        return False, f"Failed to open {path}: {e}"


def open_folder(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"Folder not found: {path}"
    try:
        subprocess.Popen(["xdg-open", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Opened folder {p.name}"
    except Exception as e:
        return False, f"Failed to open folder: {e}"


def search_files(query: str, directory: str = "~", max_results: int = 20) -> list[str]:
    root = Path(directory).expanduser()
    try:
        result = subprocess.run(
            ["find", str(root), "-maxdepth", "5", "-iname", f"*{query}*", "-type", "f"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        return lines[:max_results]
    except Exception:
        return []
