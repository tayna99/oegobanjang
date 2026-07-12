from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


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


def create_db_engine(database_url: str | None = None) -> Engine:
    """엔진 생성 — SQLite는 매 연결마다 FK를 켜야 하므로 이벤트 리스너로 강제한다.

    (docs/DB_SCHEMA.md §2 "FK는 논리적 관계는 전부 실제 FK로 선언" — 선언만으로는
    SQLite가 강제하지 않는다. `PRAGMA foreign_keys=ON`을 연결마다 반드시 실행해야 한다.)
    """
    settings = get_settings()
    url = database_url or settings.database_url
    _ensure_sqlite_parent(url)
    engine = create_engine(url, connect_args=_connect_args(url), future=True)

    if url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
