"""Plugin interface for extending Jarvis with custom integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class JarvisPlugin(ABC):
    """Base class for all Jarvis plugins.

    Plugins can:
    - Register custom actions that agents can execute
    - Hook into the brain's event pipeline
    - Add new commands to the intent system
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        ...

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    async def initialize(self, brain: Any) -> bool:
        """Called when the plugin is loaded. Return True if successful."""
        ...

    async def shutdown(self) -> None:
        """Called when the brain shuts down."""
        pass

    def get_actions(self) -> dict[str, Any]:
        """Return a dict of action_name -> handler_function for this plugin."""
        return {}

    def get_intents(self) -> list[tuple[str, str]]:
        """Return list of (regex_pattern, action_type) for intent detection."""
        return []


class PluginManager:
    """Loads and manages plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, JarvisPlugin] = {}

    async def load(self, plugin: JarvisPlugin, brain: Any) -> bool:
        """Load and initialize a plugin."""
        if plugin.name in self._plugins:
            return False

        success = await plugin.initialize(brain)
        if success:
            self._plugins[plugin.name] = plugin
        return success

    async def unload(self, name: str) -> bool:
        plugin = self._plugins.pop(name, None)
        if plugin:
            await plugin.shutdown()
            return True
        return False

    def get_plugin(self, name: str) -> JarvisPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [
            {"name": p.name, "version": p.version, "description": p.description}
            for p in self._plugins.values()
        ]

    def get_all_actions(self) -> dict[str, Any]:
        """Collect actions from all loaded plugins."""
        actions = {}
        for plugin in self._plugins.values():
            actions.update(plugin.get_actions())
        return actions

    async def shutdown_all(self) -> None:
        for plugin in self._plugins.values():
            await plugin.shutdown()
        self._plugins.clear()
