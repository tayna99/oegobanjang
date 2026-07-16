from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_db_engine(database_url: str | None = None) -> Engine:
    """엔진 생성. PostgreSQL은 FK를 항상 강제하므로 SQLite 시절의 PRAGMA 리스너가 필요 없다.

    lock_timeout: 승인 결정은 `SELECT ... FOR UPDATE`로 대상 행을 잠근다(app/services/approvals.py).
    경합 시 무한 대기 대신 짧게 실패하도록 세션 lock_timeout을 건다(F1 동시성).
    """
    settings = get_settings()
    url = database_url or settings.database_url
    return create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args={"options": "-c lock_timeout=5000"},
    )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
