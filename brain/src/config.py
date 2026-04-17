"""Brain configuration loader. Reads TOML config files with dev overrides."""

from __future__ import annotations

import os
from pathlib import Path

import tomli
from pydantic import BaseModel

_BRAIN_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _BRAIN_ROOT / "config" / "config.toml"
_DEV_CONFIG = _BRAIN_ROOT / "config" / "config.dev.toml"


class GeneralConfig(BaseModel):
    name: str = "Jarvis"
    language: str = "en"
    debug: bool = False


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8400
    allowed_origins: list[str] = ["*"]
    jwt_secret_env: str = "JARVIS_JWT_SECRET"


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    fallback_provider: str = "openai"
    fallback_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1024


class BrainConfig(BaseModel):
    enabled: bool = True
    auto_extract: bool = True
    ask_before_storing: bool = False
    decay_enabled: bool = True
    decay_threshold_days: int = 30
    consolidation_interval_hours: int = 6
    max_context_memories: int = 10
    association_decay_days: int = 60
    procedure_detection_threshold: int = 3
    working_memory_capacity: int = 7


class DatabaseConfig(BaseModel):
    type: str = "sqlite"
    url_env: str = "DATABASE_URL"
    sqlite_path: str = "data/knowledge.db"


class RedisConfig(BaseModel):
    enabled: bool = False
    url_env: str = "REDIS_URL"


class Config(BaseModel):
    general: GeneralConfig = GeneralConfig()
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    brain: BrainConfig = BrainConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()

    @property
    def db_url(self) -> str:
        if self.database.type == "postgresql":
            url = os.environ.get(self.database.url_env, "")
            if not url:
                raise ValueError(f"Environment variable {self.database.url_env} not set")
            return url
        db_path = _BRAIN_ROOT / self.database.sqlite_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def redis_url(self) -> str | None:
        if not self.redis.enabled:
            return None
        return os.environ.get(self.redis.url_env)

    @property
    def jwt_secret(self) -> str:
        secret = os.environ.get(self.server.jwt_secret_env, "")
        if not secret and not self.general.debug:
            raise ValueError(f"Environment variable {self.server.jwt_secret_env} not set")
        return secret or "dev-secret-not-for-production"


def load_config(path: Path | None = None) -> Config:
    """Load config from TOML file. Merges dev overrides if present."""
    base: dict = {}

    if _DEFAULT_CONFIG.exists():
        with open(_DEFAULT_CONFIG, "rb") as f:
            base = tomli.load(f)

    if path and path.exists():
        with open(path, "rb") as f:
            overrides = tomli.load(f)
        _deep_merge(base, overrides)
    elif _DEV_CONFIG.exists():
        with open(_DEV_CONFIG, "rb") as f:
            overrides = tomli.load(f)
        _deep_merge(base, overrides)

    return Config(**base)


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
