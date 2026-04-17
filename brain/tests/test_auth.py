"""Tests for JWT auth and agent registration."""

from __future__ import annotations

import pytest

from brain.src.api.auth.jwt import create_agent_token, extract_token, verify_agent_token
from brain.src.api.auth.permissions import check_permission

TEST_SECRET = "test-secret-key-for-testing"


def test_create_and_verify_token() -> None:
    token = create_agent_token("windows-main", "windows", TEST_SECRET, capabilities=["apps", "files"])
    assert token

    payload = verify_agent_token(token, TEST_SECRET)
    assert payload is not None
    assert payload["sub"] == "windows-main"
    assert payload["platform"] == "windows"
    assert "apps" in payload["capabilities"]


def test_invalid_token() -> None:
    payload = verify_agent_token("garbage.token.here", TEST_SECRET)
    assert payload is None


def test_wrong_secret() -> None:
    token = create_agent_token("test-device", "windows", TEST_SECRET)
    payload = verify_agent_token(token, "wrong-secret")
    assert payload is None


def test_extract_bearer_token() -> None:
    assert extract_token("Bearer abc123") == "abc123"
    assert extract_token("abc123") is None
    assert extract_token("") is None
    assert extract_token("Bearer ") == ""


def test_permissions_desktop() -> None:
    payload = {"sub": "windows-main", "platform": "windows", "capabilities": []}
    assert check_permission("open_app", payload) is True
    assert check_permission("terminal", payload) is True
    assert check_permission("screenshot", payload) is True


def test_permissions_mobile() -> None:
    payload = {"sub": "phone-ios", "platform": "ios", "capabilities": []}
    assert check_permission("notification", payload) is True
    assert check_permission("terminal", payload) is False
    assert check_permission("file_op", payload) is False


def test_permissions_custom_capability() -> None:
    payload = {"sub": "phone-ios", "platform": "ios", "capabilities": ["terminal"]}
    assert check_permission("terminal", payload) is True


@pytest.mark.asyncio
async def test_agent_register_endpoint(client) -> None:
    resp = await client.post("/api/v1/agent/register", json={
        "device_id": "test-agent",
        "platform": "windows",
        "capabilities": ["apps"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["device_id"] == "test-agent"


@pytest.mark.asyncio
async def test_agent_status_endpoint(client) -> None:
    resp = await client.get("/api/v1/agent/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "online_devices" in data
