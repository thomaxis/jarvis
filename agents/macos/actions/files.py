"""macOS file operations."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger("jarvis.macos.files")


def open_file(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"File not found: {path}"
    try:
        subprocess.run(["open", str(p)], capture_output=True, check=True, timeout=10)
        return True, f"Opened {p.name}"
    except Exception as e:
        return False, f"Failed to open {path}: {e}"


def open_folder(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"Folder not found: {path}"
    try:
        subprocess.run(["open", str(p)], capture_output=True, check=True, timeout=10)
        return True, f"Opened folder {p.name}"
    except Exception as e:
        return False, f"Failed to open folder: {e}"


def search_files(query: str, directory: str = "~", max_results: int = 20) -> list[str]:
    root = Path(directory).expanduser()
    results = []
    try:
        result = subprocess.run(
            ["mdfind", "-onlyin", str(root), query],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                results.append(line.strip())
                if len(results) >= max_results:
                    break
    except Exception:
        pass
    return results
