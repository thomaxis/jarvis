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
async def test_input_endpoint(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/input",
        json={"device_id": "test-device", "text": "Hello Jarvis"},
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
