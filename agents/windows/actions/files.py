"""Windows file operations: open, search, list, create."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger("jarvis.actions.files")


def open_file(path: str) -> tuple[bool, str]:
    """Open a file with its default application."""
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"File not found: {path}"
    try:
        os.startfile(str(p))
        return True, f"Opened {p.name}"
    except Exception as e:
        return False, f"Failed to open {path}: {e}"


def open_folder(path: str) -> tuple[bool, str]:
    """Open a folder in File Explorer."""
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"Folder not found: {path}"
    try:
        subprocess.Popen(["explorer", str(p)])
        return True, f"Opened folder {p.name}"
    except Exception as e:
        return False, f"Failed to open folder: {e}"


def search_files(query: str, directory: str = "~", max_results: int = 20) -> list[str]:
    """Search for files by name pattern."""
    root = Path(directory).expanduser()
    results = []
    try:
        for p in root.rglob(f"*{query}*"):
            results.append(str(p))
            if len(results) >= max_results:
                break
    except PermissionError:
        pass
    return results


def list_directory(path: str = ".") -> list[dict]:
    """List contents of a directory."""
    p = Path(path).expanduser()
    if not p.exists():
        return []
    entries = []
    try:
        for item in sorted(p.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
    except PermissionError:
        pass
    return entries


def create_file(path: str, content: str = "") -> tuple[bool, str]:
    """Create a new file with optional content."""
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return True, f"Created {p.name}"
    except Exception as e:
        return False, f"Failed to create file: {e}"
