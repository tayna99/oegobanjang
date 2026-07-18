"""R2.5 evidence type CHECK 정합 + R2.6 handoff_packages 링크 만료·토큰 컬럼

0001은 동결 스냅샷(모듈 docstring 참조)이라 더 이상 손대지 않는다 — 이 리비전이
db/schema.sql의 그 이후 변경분(§4.5 evidence_events.type CHECK 확장, §4.8
handoff_packages.link_token/link_issued_at/link_expires_at 추가)을 ALTER로 표현한다.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 원본(0001) CHECK — pg_get_constraintdef로 대조 확인한 문자열 그대로.
_ORIGINAL_TYPE_CHECK = """
  ('intent_classified','plan_created','tool_executed','rag_retrieved',
   'risk_flagged','approval_requested','approval_decided','review_started',
   'checklist_completed','exported','final_response_generated',
   'briefing_emitted','worker_reply_received',
   'worker_reply_summarized','status_update_confirmed','handoff_generated',
   'delegation_granted',
   'delegation_revoked','role_granted','role_changed','member_invited',
   'member_removed','approval_escalated','autonomy_changed','worker_deleted')
"""

# R2.5 — 프론트(src/types.ts EvidenceType)가 이미 발행 중이었으나 DB CHECK엔 없던 7종 추가.
_NEW_TYPE_CHECK = """
  ('intent_classified','plan_created','tool_executed','rag_retrieved',
   'risk_flagged','approval_requested','approval_decided','approval_rejected',
   'review_started','checklist_completed','exported','final_response_generated',
   'briefing_emitted','worker_reply_received',
   'worker_reply_summarized','status_update_confirmed','handoff_generated',
   'delegation_granted',
   'delegation_revoked','role_granted','role_changed','member_invited',
   'member_removed','approval_escalated','autonomy_changed','worker_deleted',
   'interpretation_confirmed','package_link_issued','package_link_viewed',
   'dispatch_executed','delivery_confirmed','package_reply')
"""


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        f"""
        ALTER TABLE evidence_events DROP CONSTRAINT evidence_events_type_check;
        ALTER TABLE evidence_events ADD CONSTRAINT evidence_events_type_check
          CHECK (type IN {_NEW_TYPE_CHECK});

        ALTER TABLE handoff_packages ADD COLUMN link_token text;
        ALTER TABLE handoff_packages ADD COLUMN link_issued_at timestamptz;
        ALTER TABLE handoff_packages ADD COLUMN link_expires_at timestamptz;
        ALTER TABLE handoff_packages ADD CONSTRAINT handoff_packages_link_token_key UNIQUE (link_token);
        ALTER TABLE handoff_packages ADD CONSTRAINT handoff_packages_link_check
          CHECK (link_expires_at IS NULL OR (link_issued_at IS NOT NULL AND link_token IS NOT NULL));
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        f"""
        ALTER TABLE handoff_packages DROP CONSTRAINT handoff_packages_link_check;
        ALTER TABLE handoff_packages DROP CONSTRAINT handoff_packages_link_token_key;
        ALTER TABLE handoff_packages DROP COLUMN link_expires_at;
        ALTER TABLE handoff_packages DROP COLUMN link_issued_at;
        ALTER TABLE handoff_packages DROP COLUMN link_token;

        ALTER TABLE evidence_events DROP CONSTRAINT evidence_events_type_check;
        ALTER TABLE evidence_events ADD CONSTRAINT evidence_events_type_check
          CHECK (type IN {_ORIGINAL_TYPE_CHECK});
        """
    )
