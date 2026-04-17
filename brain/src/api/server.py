"""FastAPI brain server. REST endpoints + health check."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from brain.src.__version__ import __version__
from brain.src.api.middleware.logging import LoggingMiddleware
from brain.src.api.middleware.rate_limit import RateLimitMiddleware
from brain.src.api.routes.health import router as health_router
from brain.src.api.routes.input import router as input_router
from brain.src.config import Config, load_config
from brain.src.db.database import close_db, init_db
from brain.src.logger import get_logger, setup_logging
from brain.src.redis_client import close_redis, init_redis

log = get_logger("server")

_config: Config | None = None
_brain_manager = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _brain_manager
    config = get_config()
    setup_logging(debug=config.general.debug)

    log.info("brain_starting", version=__version__, debug=config.general.debug)

    await init_db(config.db_url)
    await init_redis(config.redis_url)

    from brain.src.cognitive.manager import BrainManager
    _brain_manager = BrainManager()
    app.state.brain = _brain_manager

    from brain.src.scheduler import init_scheduler, stop_scheduler
    await init_scheduler(_brain_manager, interval_hours=config.brain.consolidation_interval_hours)

    log.info("brain_ready", port=config.server.port)
    yield

    await stop_scheduler()
    await _brain_manager.save_state()
    await close_redis()
    await close_db()
    log.info("brain_shutdown")


def create_app() -> FastAPI:
    config = get_config()
    app = FastAPI(
        title="Jarvis Brain",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(input_router)

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        from brain.src.api.websocket.handler import websocket_endpoint
        brain = app.state.brain
        await websocket_endpoint(websocket, brain)

    return app


app = create_app()

if __name__ == "__main__":
    import sys

    import uvicorn

    config = get_config()

    config_path = None
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            from pathlib import Path
            config_path = Path(sys.argv[idx + 1])
            _config = load_config(config_path)

    uvicorn.run(
        "brain.src.api.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.general.debug,
    )
