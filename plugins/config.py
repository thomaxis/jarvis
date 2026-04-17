"""Plugin configuration persistence. Stores API keys and settings per plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.src.logger import get_logger

log = get_logger("plugin_config")

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "brain" / "data" / "plugins"


def get_plugin_config(plugin_name: str) -> dict[str, Any]:
    """Load saved config for a plugin."""
    path = _CONFIG_DIR / f"{plugin_name}.json"
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_plugin_config(plugin_name: str, config: dict[str, Any]) -> None:
    """Save config for a plugin."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = _CONFIG_DIR / f"{plugin_name}.json"
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    log.info("plugin_config_saved", plugin=plugin_name)


def delete_plugin_config(plugin_name: str) -> None:
    path = _CONFIG_DIR / f"{plugin_name}.json"
    if path.exists():
        path.unlink()


def is_plugin_configured(plugin_name: str) -> bool:
    config = get_plugin_config(plugin_name)
    return bool(config.get("configured"))
