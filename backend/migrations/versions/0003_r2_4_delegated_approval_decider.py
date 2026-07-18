"""R2.4 승인 결정자 정책에 위임(delegation) OR-arm 추가

`trg_approvals_decider_role`이 지금까지는 owner 또는 (manager_allowed+manager+LOW)만 허용했다 —
owner의 유효한 위임(`delegations`, scope='approval', 미철회, 결정 시각이 유효기간 내)을 받은
대리 결정자도 허용하도록 함수 본문을 교체하고, 트리거 감시 컬럼에 `on_behalf_of_user_id`를 추가한다.
0001은 동결 스냅샷, 0002는 R2.5/R2.6이 점유 — 이 리비전이 db/schema.sql의 그 이후 변경분이다.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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
      )
  ) AND NOT (
    NEW.on_behalf_of_user_id IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM delegations d
      JOIN memberships md ON md.company_id = d.company_id AND md.user_id = d.delegator_user_id
      WHERE d.company_id = NEW.company_id
        AND d.delegator_user_id = NEW.on_behalf_of_user_id
        AND d.delegate_user_id = NEW.decided_by_user_id
        AND d.scope = 'approval'
        AND d.revoked_at IS NULL
        AND d.starts_at <= COALESCE(NEW.decided_at, now())
        AND COALESCE(NEW.decided_at, now()) < d.ends_at
        AND md.status = 'active' AND md.role = 'owner'
    )
  ) THEN
    RAISE EXCEPTION 'approval decider is not allowed by company policy';
  END IF;
  RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        _NEW_FUNCTION
        + """
        DROP TRIGGER approvals_decider_role ON approvals;
        CREATE TRIGGER approvals_decider_role
          BEFORE INSERT OR UPDATE OF company_id, case_id, decided_by_user_id, on_behalf_of_user_id ON approvals
          FOR EACH ROW EXECUTE FUNCTION trg_approvals_decider_role();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        _OLD_FUNCTION
        + """
        DROP TRIGGER approvals_decider_role ON approvals;
        CREATE TRIGGER approvals_decider_role
          BEFORE INSERT OR UPDATE OF company_id, case_id, decided_by_user_id ON approvals
          FOR EACH ROW EXECUTE FUNCTION trg_approvals_decider_role();
        """
    )
