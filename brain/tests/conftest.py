"""Shared test fixtures: test DB, mock Redis, FastAPI test client."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from brain.src.db.database import Base, close_db, init_db
from brain.src.redis_client import close_redis, init_redis


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Initialize test SQLite DB and in-memory Redis."""
    await init_db("sqlite+aiosqlite:///:memory:")
    await init_redis(None)  # In-memory fallback
    yield
    await close_db()
    await close_redis()


@pytest_asyncio.fixture
async def client(setup_db) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client."""
    from brain.src.api.server import create_app

    app = create_app()

    # Manually trigger lifespan-like setup (DB already initialized via setup_db)
    from brain.src.cognitive.manager import BrainManager
    app.state.brain = BrainManager()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
