from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


def normalize_database_url(database_url: str) -> str:
    """Resolve relative SQLite URLs from the backend directory.

    `sqlite:///./data/oegobanjang.sqlite3` must point to the same file whether
    commands run from the repository root or from `backend/`.
    """

    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url

    path_value = database_url.removeprefix(sqlite_prefix)
    if path_value == ":memory:":
        return database_url

    db_path = Path(path_value).expanduser()
    if not db_path.is_absolute():
        db_path = BACKEND_DIR / db_path

    return f"{sqlite_prefix}{db_path.resolve().as_posix()}"


class Settings(BaseSettings):
    """
    외고반장 backend 공통 설정.

    실제 값은 루트 .env 또는 환경변수에서 읽는다.
    .env는 Git에 올리지 않고, .env.example만 공유한다.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "외고반장"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite:///./data/oegobanjang.sqlite3"

    @property
    def normalized_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_name: str = "oegobanjang_policy_docs"
    chroma_persist_directory: str = "data-pipeline/index/chroma/workforce"
    chroma_workforce_official_collection: str = "workforce_official"
    chroma_workforce_templates_collection: str = "workforce_templates"

    # LLM Keys
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    langchain_runtime_enabled: bool = True

    # Security
    jwt_secret: str = "change-this-local-secret"
    jwt_algorithm: str = "HS256"

    # CORS
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_local(self) -> bool:
        return self.app_env.lower() in {"local", "dev", "development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
