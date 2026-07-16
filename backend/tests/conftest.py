"""PostgreSQL 테스트 하니스.

- 세션 1회: 전용 테스트 DB(`ogb_test`)를 새로 만들고 `alembic upgrade head`(=db/schema.sql 적용)로
  스키마를 구축한다. create_all()은 쓰지 않는다 — Alembic이 유일한 스키마 생성 경로.
- 테스트별 격리: 커넥션에 외곽 트랜잭션을 걸고 세션은 `join_transaction_mode="create_savepoint"`로
  바인딩한다. 서비스 코드의 `db.commit()`이 SAVEPOINT 릴리스로 흡수되어, 테스트 종료 시 외곽
  트랜잭션 롤백으로 전량 원복된다(트리거·함수는 스키마에 상주하므로 재구축 없이 빠르다).

DB 레벨 가드레일(테넌트 격리·승인 상태머신 등 145건)은 `db/validate.py`가 담당한다 — 이 pytest는
서비스 계층(승인 decide API·동시성)을 검증한다.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parent.parent

_ADMIN_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
)
_TEST_DB = os.environ.get("TEST_DB_NAME", "ogb_test")


def _swap_db(url: str, dbname: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{dbname}"))


def _psycopg_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="session")
def session_engine():
    admin_dsn = _psycopg_dsn(_ADMIN_URL)
    # 관리 연결(autocommit)로 테스트 DB를 새로 만든다.
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{_TEST_DB}"')

    test_url = _swap_db(_ADMIN_URL, _TEST_DB)
    env = os.environ.copy()
    env["DATABASE_URL"] = test_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",  # alembic 출력의 UTF-8(한글·— 등)을 Windows cp949로 디코드하지 않도록
    )
    assert result.returncode == 0, f"alembic upgrade head 실패:\n{result.stdout}\n{result.stderr}"

    engine = create_engine(test_url, future=True)
    yield engine
    engine.dispose()
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB}" WITH (FORCE)')


@pytest.fixture()
def db(session_engine):
    """savepoint 격리된 세션. 서비스가 commit해도 외곽 트랜잭션 롤백으로 원복된다."""
    connection = session_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        if outer.is_active:
            outer.rollback()
        connection.close()
