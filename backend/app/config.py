from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DATABASE_URL 등 런타임 설정. 서비스 DB는 PostgreSQL 16+로 확정(docs/DB_SCHEMA.md §1)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
    environment: str = "local"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
