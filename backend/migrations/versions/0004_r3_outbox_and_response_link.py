"""R3 stage ② — outbox(발송 대기열) 테이블 + thread_messages 응답 링크 컬럼

MESSAGING_CHANNELS.md §2(발신 파이프라인)·§3(수신 파이프라인). `next_actions.action_type=
'send_message'` 승인 후 manager의 "실행 확인"이 정확히 1개의 outbox 행을 만들고
(ChannelAdapter가 그 행을 처리한다), 발신 메시지(thread_messages.direction='system')에
심어둔 만료형 토큰(`response_token`)으로 근로자가 응답 링크 페이지에서 회신한다.

0001은 동결 스냅샷, 0002/0003은 R2.5~R2.4가 점유 — 이 리비전이 그 이후 변경분이다.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UPGRADE_SQL = """
ALTER TABLE thread_messages ADD COLUMN response_token text;
ALTER TABLE thread_messages ADD COLUMN response_token_expires_at timestamptz;
ALTER TABLE thread_messages ADD CONSTRAINT thread_messages_response_token_key UNIQUE (response_token);
ALTER TABLE thread_messages ADD CONSTRAINT thread_messages_response_token_check
  CHECK (response_token IS NULL OR response_token_expires_at IS NOT NULL);
CREATE INDEX ix_thread_messages_response_token ON thread_messages (response_token)
  WHERE response_token IS NOT NULL;

CREATE TABLE outbox (
  id                    text PRIMARY KEY,
  company_id            text NOT NULL REFERENCES companies(id),
  case_id               text NOT NULL,
  action_id             text NOT NULL,
  approval_id           text NOT NULL,
  thread_id             text,
  channel               text NOT NULL CHECK (channel IN ('sms','alimtalk','zalo')),
  event_type            text NOT NULL DEFAULT 'dispatch' CHECK (event_type IN ('dispatch','reminder','resend')),
  dedupe_key            text NOT NULL,
  body                  text NOT NULL,
  lang                  text,
  recipient_ref         text,
  status                text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','sent','delivered','failed')),
  external_id           text,
  attempt_count         integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  fallback_from_id      text,
  scheduled_for         timestamptz,
  sent_at               timestamptz,
  failed_reason         text,
  requested_by_user_id  text NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  UNIQUE (company_id, dedupe_key),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, case_id, action_id) REFERENCES next_actions(company_id, case_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id),
  FOREIGN KEY (company_id, thread_id) REFERENCES threads(company_id, id),
  FOREIGN KEY (company_id, requested_by_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, fallback_from_id) REFERENCES outbox(company_id, id),
  CHECK (status <> 'sent' OR sent_at IS NOT NULL),
  CHECK (status NOT IN ('sent','delivered') OR external_id IS NOT NULL)
);
CREATE INDEX ix_outbox_company_status ON outbox (company_id, status);
CREATE INDEX ix_outbox_case ON outbox (case_id);

CREATE FUNCTION trg_outbox_requires_approved_approval() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM approvals a
    WHERE a.company_id = NEW.company_id AND a.id = NEW.approval_id AND a.status = 'approved'
  ) THEN
    RAISE EXCEPTION 'outbox item requires an approved approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER outbox_requires_approved_approval
  BEFORE INSERT ON outbox
  FOR EACH ROW EXECUTE FUNCTION trg_outbox_requires_approved_approval();

CREATE FUNCTION trg_outbox_immutable_core() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.company_id <> OLD.company_id OR NEW.case_id <> OLD.case_id OR NEW.action_id <> OLD.action_id
     OR NEW.approval_id <> OLD.approval_id OR NEW.dedupe_key <> OLD.dedupe_key
     OR NEW.channel <> OLD.channel OR NEW.body <> OLD.body THEN
    RAISE EXCEPTION 'outbox core fields are immutable after creation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER outbox_immutable_core
  BEFORE UPDATE OF company_id, case_id, action_id, approval_id, dedupe_key, channel, body ON outbox
  FOR EACH ROW EXECUTE FUNCTION trg_outbox_immutable_core();

CREATE FUNCTION trg_outbox_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'outbox deletion is not allowed';
END;
$$;
CREATE TRIGGER outbox_no_delete BEFORE DELETE ON outbox
  FOR EACH ROW EXECUTE FUNCTION trg_outbox_no_delete();
"""

_DOWNGRADE_SQL = """
DROP TABLE outbox;

DROP INDEX ix_thread_messages_response_token;
ALTER TABLE thread_messages DROP CONSTRAINT thread_messages_response_token_check;
ALTER TABLE thread_messages DROP CONSTRAINT thread_messages_response_token_key;
ALTER TABLE thread_messages DROP COLUMN response_token_expires_at;
ALTER TABLE thread_messages DROP COLUMN response_token;
"""


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(_UPGRADE_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(_DOWNGRADE_SQL)
