from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "M4 — AI-генератор постів для Telegram"
    debug: bool = False
    database_url: str = f"sqlite:///{BASE_DIR / 'aibot.db'}"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session: str = "aibot_session"
    telegram_target_channel: str | None = None
    test_mode: bool = True
    auto_publish: bool = False
    request_timeout: int = Field(default=20, ge=1, le=120)
    default_language: str = "uk"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
