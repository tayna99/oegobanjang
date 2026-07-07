from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

try:
    from app.config import get_settings
except ModuleNotFoundError:
    from backend.app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    path_value = database_url.removeprefix("sqlite:///")
    if path_value == ":memory:":
        return

    Path(path_value).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _async_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


def create_db_engine(database_url: str | None = None) -> Engine:
    url = database_url or getattr(settings, "normalized_database_url", settings.database_url)
    _ensure_sqlite_parent(url)
    return create_engine(
        url,
        connect_args=_connect_args(url),
        future=True,
    )


sync_engine = create_db_engine()
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)

async_engine = create_async_engine(
    _async_database_url(getattr(settings, "normalized_database_url", settings.database_url)),
    echo=settings.is_local,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


def get_sync_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
