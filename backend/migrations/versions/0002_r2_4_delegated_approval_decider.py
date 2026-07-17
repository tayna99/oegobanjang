"""R2.4 — trg_approvals_decider_role에 위임(delegation) 경로 추가.

db/schema.sql의 trg_approvals_decider_role()에 세 번째 OR절을 추가한다: 검증된 활성 위임
(scope='approval', 기간 내, 미해지)이 있으면 owner_only 정책이어도 대리 승인자를 허용한다
(§13-10, backend/app/services/approvals.py의 delegation 검증과 짝을 이루는 DB 최종 방어선).

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

_NEW_FUNCTION = """
CREATE OR REPLACE FUNCTION trg_approvals_decider_role() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1
    FROM memberships m
    JOIN companies c ON c.id = m.company_id
    JOIN cases cs ON cs.company_id = NEW.company_id AND cs.id = NEW.case_id
    WHERE m.company_id = NEW.company_id
      AND m.user_id = NEW.decided_by_user_id
      AND m.status = 'active'
      AND (
        m.role = 'owner'
        OR (c.approval_policy = 'manager_allowed' AND m.role = 'manager' AND cs.severity = 'LOW')
        OR (
          NEW.on_behalf_of_user_id IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM delegations d
            WHERE d.company_id = NEW.company_id
              AND d.delegator_user_id = NEW.on_behalf_of_user_id
              AND d.delegate_user_id = NEW.decided_by_user_id
              AND d.scope = 'approval'
              AND d.revoked_at IS NULL
              AND d.starts_at <= now()
              AND d.ends_at >= now()
          )
        )
      )
  ) THEN
    RAISE EXCEPTION 'approval decider is not allowed by company policy';
  END IF;
  RETURN NEW;
END;
$$;
"""

_OLD_FUNCTION = """
CREATE OR REPLACE FUNCTION trg_approvals_decider_role() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1
    FROM memberships m
    JOIN companies c ON c.id = m.company_id
    JOIN cases cs ON cs.company_id = NEW.company_id AND cs.id = NEW.case_id
    WHERE m.company_id = NEW.company_id
      AND m.user_id = NEW.decided_by_user_id
      AND m.status = 'active'
      AND (
        m.role = 'owner'
        OR (c.approval_policy = 'manager_allowed' AND m.role = 'manager' AND cs.severity = 'LOW')
      )
  ) THEN
    RAISE EXCEPTION 'approval decider is not allowed by company policy';
  END IF;
  RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(_NEW_FUNCTION)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(_OLD_FUNCTION)
