"""테스트는 create_all()을 쓰지 않는다.

Alembic 마이그레이션이 유일한 스키마 생성 경로라는 설계 원칙(docs/DB_SCHEMA.md §0-7,
레거시 결함 §12-1 "런타임 ALTER TABLE·산재한 create_all()")을 테스트에서도 지킨다.
매 테스트마다 임시 SQLite 파일에 `alembic upgrade head`를 서브프로세스로 실제 실행해
DB를 만든다 — 순환 FK(cases.prepared_run_id ↔ runs.id)가 Base.metadata.create_all()의
위상정렬에서 실패하는 것도 이 방식으로 피한다(backend/README.md 참조).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db_url() -> str:
    """pytest 내장 `tmp_path`를 쓰지 않는다 — 이 대신 순수 `tempfile`로 직접 격리한다.

    이유: 이 개발 머신의 `%TEMP%/pytest-of-<user>/`가 이전 세션에서 생긴 권한 문제로
    `os.scandir` 자체가 거부되는 상태였다(우리 코드와 무관한 환경 결함, 조사 완료 — 삭제는
    다른 세션에 영향을 줄 수 있는 공용 시스템 폴더라 건드리지 않는다). `tmp_path`는 내부적으로
    그 디렉터리를 스캔하므로 어떤 테스트에서든 실패한다. `tempfile.mkdtemp()`는 pytest의
    번호매김 디렉터리 관리를 거치지 않고 `%TEMP%` 바로 아래에 격리 폴더를 만들어 이 문제를
    완전히 피해간다 — 다른 환경(CI 등)에서도 동일하게 안전하게 동작한다.
    """
    tmp_dir = tempfile.mkdtemp(prefix="oegobanjang-backend-test-")
    try:
        yield f"sqlite:///{Path(tmp_dir, 'test.sqlite3').as_posix()}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def migrated_engine(db_url: str) -> Engine:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade head 실패:\n{result.stdout}\n{result.stderr}"

    engine = create_engine(db_url)

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    engine.dispose()
