"""Tests for the FastAPI brain server."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_input_endpoint_chat(client: AsyncClient) -> None:
    """Test input with chat=True (default) -- returns LLM response."""
    resp = await client.post(
        "/api/v1/input",
        json={"device_id": "test-device", "text": "Hello Jarvis"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "response" in data


@pytest.mark.asyncio
async def test_input_endpoint_context_only(client: AsyncClient) -> None:
    """Test input with chat=False -- returns raw context."""
    resp = await client.post(
        "/api/v1/input",
        json={"device_id": "test-device", "text": "Hello Jarvis", "chat": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "context" in data
    assert data["context"]["input"] == "Hello Jarvis"


@pytest.mark.asyncio
async def test_response_endpoint(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/response",
        json={
            "device_id": "test-device",
            "response_text": "Hello! How can I help?",
            "facts": [{"content": "User greeted Jarvis", "category": "personal", "confidence": 0.6}],
            "topic": "greeting",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
