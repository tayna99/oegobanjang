from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DATABASE_URL 등 런타임 설정. README의 `.env` 관례를 따른다(docker-compose 등은 미결 — README §2)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/oegobanjang.sqlite3"
    environment: str = "local"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
