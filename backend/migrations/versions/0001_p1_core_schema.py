"""p1 core schema — PostgreSQL

이 리비전은 설계 정본 `db/schema.sql`을 **그대로 실행**한다. 트리거 함수 34종·복합 테넌트 FK·
파생 뷰는 SQLAlchemy 모델로 표현되지 않으므로, DDL 정본을 단일 파일(`db/schema.sql`)로 두고
마이그레이션은 그것을 적용만 한다. 이렇게 하면 설계 킷과 백엔드 스키마가 **구조적으로 동일**해져
드리프트(docs/DB_SCHEMA.md §12-5 F5)가 원천 차단된다.

주의(미배포 스캐폴드 규약): 지금은 `db/schema.sql`을 런타임에 읽는다. 최초 실배포 시점에는 이
리비전을 불변으로 동결해야 하므로 그 시점의 `db/schema.sql` 내용을 이 파일에 인라인 스냅샷으로
복사한다(그 이후의 스키마 변경은 0002+ ALTER 리비전으로만).

Revision ID: 0001
Revises:
Create Date: 2026-07-13
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# backend/migrations/versions/0001_...py → parents[3] = repo root
_SCHEMA_SQL = Path(__file__).resolve().parents[3] / "db" / "schema.sql"


def upgrade() -> None:
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")
    # exec_driver_sql: SQLAlchemy의 bind 파라미터 파싱을 우회해 원문 그대로 드라이버에 보낸다
    # (다중 문장 + $$ dollar-quoted 함수 본문을 안전하게 실행).
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
