"""Tests for Layer 2: Short-Term Memory."""

from __future__ import annotations

import pytest
import pytest_asyncio

from brain.src.cognitive.models import Message
from brain.src.cognitive.short_term import ShortTermMemory


@pytest_asyncio.fixture
async def stm(setup_db) -> ShortTermMemory:
    return ShortTermMemory()


@pytest.mark.asyncio
async def test_add_and_get_messages(stm: ShortTermMemory) -> None:
    msg = Message(role="user", content="test message", device_id="stm-device")
    await stm.add_message("stm-device", msg)

    messages = await stm.get_messages("stm-device")
    assert len(messages) >= 1
    assert messages[-1].content == "test message"


@pytest.mark.asyncio
async def test_message_buffer_limit(stm: ShortTermMemory) -> None:
    for i in range(30):
        msg = Message(role="user", content=f"msg {i}", device_id="buf-device")
        await stm.add_message("buf-device", msg)

    messages = await stm.get_messages("buf-device")
    assert len(messages) <= 20  # BUFFER_SIZE


@pytest.mark.asyncio
async def test_corrections(stm: ShortTermMemory) -> None:
    await stm.add_correction("Use Firefox instead of Chrome", "test-device")

    corrections = await stm.get_corrections()
    assert len(corrections) >= 1
    assert corrections[0]["correction"] == "Use Firefox instead of Chrome"


@pytest.mark.asyncio
async def test_device_registration(stm: ShortTermMemory) -> None:
    await stm.register_device("windows-main")
    await stm.register_device("phone-android")

    devices = await stm.get_active_devices()
    assert "windows-main" in devices
    assert "phone-android" in devices

    await stm.unregister_device("phone-android")
    devices = await stm.get_active_devices()
    assert "phone-android" not in devices


@pytest.mark.asyncio
async def test_recent_commands(stm: ShortTermMemory) -> None:
    await stm.add_command("open chrome", "test-device")
    await stm.add_command("play music", "test-device")

    commands = await stm.get_recent_commands()
    assert len(commands) >= 2


@pytest.mark.asyncio
async def test_clear_device(stm: ShortTermMemory) -> None:
    msg = Message(role="user", content="to be cleared", device_id="clear-stm")
    await stm.add_message("clear-stm", msg)

    await stm.clear_device("clear-stm")
    messages = await stm.get_messages("clear-stm")
    assert len(messages) == 0
