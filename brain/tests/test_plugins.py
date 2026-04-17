"""Tests for the plugin system."""

from __future__ import annotations

import pytest
from typing import Any

from plugins.base import JarvisPlugin, PluginManager


class TestPlugin(JarvisPlugin):
    @property
    def name(self) -> str:
        return "test_plugin"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Test plugin"

    async def initialize(self, brain: Any) -> bool:
        return True

    def get_actions(self) -> dict[str, Any]:
        return {"test_action": lambda: (True, "test")}

    def get_intents(self) -> list[tuple[str, str]]:
        return [(r"\btest\b", "test_action")]


@pytest.mark.asyncio
async def test_load_plugin() -> None:
    pm = PluginManager()
    plugin = TestPlugin()
    success = await pm.load(plugin, brain=None)
    assert success
    assert pm.get_plugin("test_plugin") is not None


@pytest.mark.asyncio
async def test_duplicate_plugin() -> None:
    pm = PluginManager()
    plugin = TestPlugin()
    await pm.load(plugin, brain=None)
    success = await pm.load(plugin, brain=None)
    assert not success  # Duplicate rejected


@pytest.mark.asyncio
async def test_list_plugins() -> None:
    pm = PluginManager()
    await pm.load(TestPlugin(), brain=None)
    plugins = pm.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "test_plugin"


@pytest.mark.asyncio
async def test_get_all_actions() -> None:
    pm = PluginManager()
    await pm.load(TestPlugin(), brain=None)
    actions = pm.get_all_actions()
    assert "test_action" in actions


@pytest.mark.asyncio
async def test_unload_plugin() -> None:
    pm = PluginManager()
    await pm.load(TestPlugin(), brain=None)
    success = await pm.unload("test_plugin")
    assert success
    assert pm.get_plugin("test_plugin") is None


@pytest.mark.asyncio
async def test_shutdown_all() -> None:
    pm = PluginManager()
    await pm.load(TestPlugin(), brain=None)
    await pm.shutdown_all()
    assert len(pm.list_plugins()) == 0
