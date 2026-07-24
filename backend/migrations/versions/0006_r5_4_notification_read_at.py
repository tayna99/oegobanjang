"""R5.4 알림 인앱 읽음 처리 — notifications.read_at 컬럼 추가

인앱 알림 센터가 "이 알림을 읽었는가"를 추적하는 컬럼이다. §13-7 "MVP는 발신 확인 없음"
계약(db/validate.py "notification sent status is blocked"/"no delivery timestamp columns")과는
무관하다 — sent_at/delivered_at 같은 외부 발신 확인이 아니라, 인증된 수신자 본인이 인앱에서
열람했는지만 기록한다(GET /api/v1/notifications로 조회 + POST .../read로 갱신, 둘 다 세션
인증 필요 — evidence_events처럼 위조 불가능한 서버 트랜잭션 안에서만 값이 바뀐다).

파일명 번호 주의: 이 작업을 시작한 시점 저장소에는 0001~0003만 있었다. 병렬로 진행 중이던
0004(R3 outbox)·0005(R5.1 화이트라벨)도 착수 시점엔 각자 down_revision=0003이었다 — 병합
시 실제 체인 순서(0003→0004→0005→0006)로 재배치했다(backend/README.md 마이그레이션 절 참조).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE notifications ADD COLUMN read_at timestamptz;")


def downgrade() -> None:
    op.execute("ALTER TABLE notifications DROP COLUMN read_at;")
