"""R3 message-integrity hardening for response links and external dispatch.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-21
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE thread_messages ADD COLUMN case_id text;
        ALTER TABLE thread_messages ADD COLUMN response_token_consumed_at timestamptz;
        ALTER TABLE thread_messages
          ADD CONSTRAINT thread_messages_case_fk
          FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id);
        ALTER TABLE thread_messages
          ADD CONSTRAINT thread_messages_response_token_consumed_check
          CHECK (response_token_consumed_at IS NULL OR response_token IS NOT NULL);

        CREATE FUNCTION trg_thread_messages_response_token_consumed_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.response_token_consumed_at IS DISTINCT FROM OLD.response_token_consumed_at THEN
            IF OLD.response_token_consumed_at IS NOT NULL
               OR NEW.response_token_consumed_at IS NULL
               OR OLD.response_token IS NULL THEN
              RAISE EXCEPTION 'response token consumption is immutable';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$;
        CREATE TRIGGER thread_messages_response_token_consumed_guard
          BEFORE UPDATE OF response_token_consumed_at ON thread_messages
          FOR EACH ROW EXECUTE FUNCTION trg_thread_messages_response_token_consumed_guard();

        ALTER TABLE outbox ADD COLUMN dispatch_started_at timestamptz;
        ALTER TABLE outbox DROP CONSTRAINT outbox_status_check;
        ALTER TABLE outbox
          ADD CONSTRAINT outbox_status_check
          CHECK (status IN ('queued','dispatching','sent','delivered','failed'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER thread_messages_response_token_consumed_guard ON thread_messages;
        DROP FUNCTION trg_thread_messages_response_token_consumed_guard();
        ALTER TABLE thread_messages DROP CONSTRAINT thread_messages_response_token_consumed_check;
        ALTER TABLE thread_messages DROP CONSTRAINT thread_messages_case_fk;
        ALTER TABLE thread_messages DROP COLUMN response_token_consumed_at;
        ALTER TABLE thread_messages DROP COLUMN case_id;

        ALTER TABLE outbox DROP CONSTRAINT outbox_status_check;
        ALTER TABLE outbox
          ADD CONSTRAINT outbox_status_check
          CHECK (status IN ('queued','sent','delivered','failed'));
        ALTER TABLE outbox DROP COLUMN dispatch_started_at;
        """
    )
