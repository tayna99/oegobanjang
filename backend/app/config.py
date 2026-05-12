from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


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


def normalize_backend_path(path_value: str) -> str:
    """Resolve backend-relative file paths consistently from any cwd."""

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path.resolve().as_posix()


def normalize_project_path(path_value: str) -> str:
    """Resolve project-root-relative paths consistently from any cwd."""

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve().as_posix()


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

    # Daily Briefing Scheduler
    daily_briefing_scheduler_enabled: bool = False
    daily_briefing_scheduler_run_on_startup: bool = False
    daily_briefing_scheduler_interval_seconds: int = 86400
    daily_briefing_scheduler_timezone: str = "Asia/Seoul"
    daily_briefing_scheduler_company_ids: str = ""
    daily_briefing_allow_seed_source_fallback: bool = True
    daily_briefing_citation_official_fetch_enabled: bool = False
    daily_briefing_official_fetch_timeout_seconds: int = 20
    daily_briefing_official_fetch_max_bytes: int = 5_000_000
    daily_briefing_rag_refresh_chunks_path: str = "data-pipeline/processed/chunks/daily_briefing_official_chunks.jsonl"
    daily_briefing_rag_refresh_chroma_records_path: str = "data-pipeline/processed/chunks/daily_briefing_official_chroma_records.jsonl"
    daily_briefing_rag_refresh_chroma_persist_dir: str = "data-pipeline/index/chroma/daily_briefing_official"
    daily_briefing_rag_refresh_chroma_collection: str = "daily_briefing_official"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_name: str = "oegobanjang_policy_docs"
    chroma_persist_directory: str = Field(
        default="data-pipeline/index/chroma/workforce",
        validation_alias=AliasChoices(
            "CHROMA_WORKFORCE_PERSIST_DIRECTORY",
            "CHROMA_PERSIST_DIRECTORY",
        ),
    )
    chroma_workforce_official_collection: str = "workforce_official"
    chroma_workforce_templates_collection: str = "workforce_templates"

    @property
    def normalized_chroma_persist_directory(self) -> str:
        return normalize_project_path(self.chroma_persist_directory)

    # LLM Keys
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    openai_model: str = "gpt-4.1-nano"
    langchain_runtime_enabled: bool = True
    langchain_checkpoint_enabled: bool = True
    langchain_checkpoint_path: str = "data/langchain_checkpoints.sqlite3"
    langchain_checkpoint_namespace: str = "workbridge_langchain_v1"

    @property
    def normalized_langchain_checkpoint_path(self) -> str:
        return normalize_backend_path(self.langchain_checkpoint_path)
    agent_chat_openai_smoke_enabled: bool = False
    agent_chat_openai_model: str = "gpt-4o-mini"

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

    @property
    def daily_briefing_scheduler_company_id_list(self) -> list[str] | None:
        company_ids = [
            company_id.strip()
            for company_id in self.daily_briefing_scheduler_company_ids.split(",")
            if company_id.strip()
        ]
        return company_ids or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
