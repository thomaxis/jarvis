"""Shared data models for device agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SEARCH = "search"
    MEDIA_CONTROL = "media_control"
    VOLUME = "volume"
    TYPE_TEXT = "type_text"
    SCREENSHOT = "screenshot"
    SYSTEM_POWER = "system_power"
    FILE_OP = "file_op"
    OPEN_URL = "open_url"
    TERMINAL = "terminal"
    CLIPBOARD = "clipboard"
    NOTIFICATION = "notification"


@dataclass
class ActionRequest:
    action_id: str
    type: str
    target: str = ""
    device: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class ActionResult:
    action_id: str
    status: str  # "success" or "failure"
    details: str = ""
