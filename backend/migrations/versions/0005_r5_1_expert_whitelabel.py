"""R5.1 행정사 화이트라벨 v1 — ExpertGrant/ExpertOfficeMember/PackageViewLog/PiiFieldPolicy

정본: reference/specs/7-1_행정사_화이트라벨_v1.md, docs/DB_SCHEMA.md §4.8-1.
v0(mock, M4.6)의 Tenant/ExpertAccount/ExpertMembership을 실서비스 계약으로 승격한다.
"tenant"는 별도 테이블이 아니라 companies 값 공간이다(spec §2.6) — tenant_id는 전부
companies(id)를 참조한다.

신규 테이블 7개: expert_accounts, expert_office_members, expert_grants,
expert_login_otps, expert_sessions, package_view_log, pii_field_policies.
handoff_packages에 expert_account_id(nullable, v0 하위호환) 컬럼 추가.
evidence_events.type CHECK에 expert_access_granted/expert_access_revoked 추가.

0001은 동결 스냅샷, 0002/0003이 그 이후 변경분 — 이 리비전이 db/schema.sql의 R5.1분(§4.8-1)이다.

Revision ID: 0005
Revises: 0003
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 0002가 이미 이 목록으로 CHECK를 교체했다(_NEW_TYPE_CHECK) — 이 리비전은 그 목록에 R5.1
# 이벤트 타입 2종만 더한다.
_PRE_R5_1_TYPE_CHECK = """
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

_R5_1_TYPE_CHECK = """
  ('intent_classified','plan_created','tool_executed','rag_retrieved',
   'risk_flagged','approval_requested','approval_decided','approval_rejected',
   'review_started','checklist_completed','exported','final_response_generated',
   'briefing_emitted','worker_reply_received',
   'worker_reply_summarized','status_update_confirmed','handoff_generated',
   'delegation_granted',
   'delegation_revoked','role_granted','role_changed','member_invited',
   'member_removed','approval_escalated','autonomy_changed','worker_deleted',
   'interpretation_confirmed','package_link_issued','package_link_viewed',
   'dispatch_executed','delivery_confirmed','package_reply',
   'expert_access_granted','expert_access_revoked')
"""

_UPGRADE_SQL = f"""
-- 행정사무소 — 브랜드·과금 경계(결정 B).
CREATE TABLE expert_accounts (
  id                       text PRIMARY KEY,
  office_name              text NOT NULL,
  brand_initial            text NOT NULL,
  brand_color              text NOT NULL,
  status                   text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
  business_registration_no text UNIQUE,
  created_at               timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE handoff_packages ADD COLUMN expert_account_id text;
ALTER TABLE handoff_packages
  ADD CONSTRAINT handoff_packages_expert_account_fk
  FOREIGN KEY (expert_account_id) REFERENCES expert_accounts(id);

CREATE TABLE expert_office_members (
  id                text PRIMARY KEY,
  expert_account_id text NOT NULL REFERENCES expert_accounts(id),
  name              text NOT NULL,
  email             text NOT NULL,
  status            text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
  is_office_admin   boolean NOT NULL DEFAULT false,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (expert_account_id, id),
  UNIQUE (expert_account_id, email)
);
CREATE INDEX ix_expert_office_members_account ON expert_office_members (expert_account_id, status);

CREATE TABLE expert_grants (
  id                    text PRIMARY KEY,
  status                text NOT NULL DEFAULT 'invited'
                        CHECK (status IN ('invited','company_authorized','active','expired','revoked')),
  expert_account_id     text NOT NULL REFERENCES expert_accounts(id),
  tenant_id             text NOT NULL REFERENCES companies(id),
  scope                 text NOT NULL DEFAULT 'package_review' CHECK (scope = 'package_review'),
  granted_by            text NOT NULL,
  basis                 text NOT NULL DEFAULT 'processing_agreement' CHECK (basis = 'processing_agreement'),
  from_date             date NOT NULL,
  until_date            date NOT NULL,
  review_interval_days  integer NOT NULL DEFAULT 365 CHECK (review_interval_days > 0),
  revoked_reason        text CHECK (revoked_reason IN ('expired','manual')),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CHECK (until_date > from_date),
  FOREIGN KEY (tenant_id, granted_by) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_expert_grants_tenant ON expert_grants (tenant_id, status);
CREATE INDEX ix_expert_grants_account ON expert_grants (expert_account_id, status);

CREATE TABLE expert_login_otps (
  id            text PRIMARY KEY,
  email         text NOT NULL,
  code_hash     text NOT NULL,
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  expires_at    timestamptz NOT NULL,
  consumed_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_expert_login_otps_email ON expert_login_otps (email, created_at DESC);

CREATE TABLE expert_sessions (
  id                       text PRIMARY KEY,
  expert_office_member_id  text NOT NULL REFERENCES expert_office_members(id),
  token_hash               text NOT NULL UNIQUE,
  created_at               timestamptz NOT NULL DEFAULT now(),
  expires_at               timestamptz NOT NULL,
  revoked_at               timestamptz,
  CHECK (expires_at > created_at)
);
CREATE INDEX ix_expert_sessions_member ON expert_sessions (expert_office_member_id);

CREATE TABLE package_view_log (
  id                       text PRIMARY KEY,
  package_id               text NOT NULL,
  tenant_id                text NOT NULL REFERENCES companies(id),
  expert_office_member_id  text NOT NULL REFERENCES expert_office_members(id),
  viewed_at                timestamptz NOT NULL DEFAULT now(),
  ip                       text,
  FOREIGN KEY (tenant_id, package_id) REFERENCES handoff_packages(company_id, id)
);
CREATE INDEX ix_package_view_log_package ON package_view_log (package_id, viewed_at);
CREATE INDEX ix_package_view_log_member ON package_view_log (expert_office_member_id, viewed_at);

CREATE TABLE pii_field_policies (
  field      text NOT NULL,
  role       text NOT NULL CHECK (role IN ('owner','manager','viewer','expert')),
  exposure   text NOT NULL CHECK (exposure IN ('plain','masked','hidden')),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (field, role)
);

-- spec §2.4 결정 A 채택값 — 전 환경 필수 시드. 이 리포지토리엔 아직 db/seed_reference.sql
-- 분리가 없어(사용 중인 브랜치 시점 기준) 마이그레이션 자체에 데이터 시드를 둔다.
INSERT INTO pii_field_policies (field, role, exposure) VALUES
  ('HandoffPackage.workerName', 'owner', 'plain'),
  ('HandoffPackage.workerName', 'manager', 'plain'),
  ('HandoffPackage.workerName', 'viewer', 'plain'),
  ('HandoffPackage.workerName', 'expert', 'plain'),
  ('HandoffPackage.nationality', 'owner', 'plain'),
  ('HandoffPackage.nationality', 'manager', 'plain'),
  ('HandoffPackage.nationality', 'viewer', 'plain'),
  ('HandoffPackage.nationality', 'expert', 'plain'),
  ('HandoffPackage.alienRegistrationNumber', 'owner', 'masked'),
  ('HandoffPackage.alienRegistrationNumber', 'manager', 'masked'),
  ('HandoffPackage.alienRegistrationNumber', 'viewer', 'masked'),
  ('HandoffPackage.alienRegistrationNumber', 'expert', 'masked'),
  ('HandoffPackage.passportNumber', 'owner', 'masked'),
  ('HandoffPackage.passportNumber', 'manager', 'masked'),
  ('HandoffPackage.passportNumber', 'viewer', 'masked'),
  ('HandoffPackage.passportNumber', 'expert', 'masked'),
  ('HandoffPackage.phone', 'owner', 'masked'),
  ('HandoffPackage.phone', 'manager', 'masked'),
  ('HandoffPackage.phone', 'viewer', 'masked'),
  ('HandoffPackage.phone', 'expert', 'masked');

-- 열람 감사 로그 append-only(evidence_events와 동일 원칙)
CREATE FUNCTION trg_package_view_log_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'package_view_log is append-only';
END;
$$;
CREATE TRIGGER package_view_log_no_update BEFORE UPDATE ON package_view_log
  FOR EACH ROW EXECUTE FUNCTION trg_package_view_log_immutable();
CREATE TRIGGER package_view_log_no_delete BEFORE DELETE ON package_view_log
  FOR EACH ROW EXECUTE FUNCTION trg_package_view_log_immutable();

CREATE FUNCTION trg_expert_login_otps_update_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.email IS DISTINCT FROM OLD.email
     OR NEW.code_hash IS DISTINCT FROM OLD.code_hash
     OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'expert login otp request is immutable';
  END IF;
  IF OLD.consumed_at IS NOT NULL AND NEW.consumed_at IS DISTINCT FROM OLD.consumed_at THEN
    RAISE EXCEPTION 'expert login otp is already consumed';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER expert_login_otps_update_guard
  BEFORE UPDATE ON expert_login_otps
  FOR EACH ROW EXECUTE FUNCTION trg_expert_login_otps_update_guard();

CREATE FUNCTION trg_expert_sessions_update_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.expert_office_member_id IS DISTINCT FROM OLD.expert_office_member_id
     OR NEW.token_hash IS DISTINCT FROM OLD.token_hash
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
     OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
    RAISE EXCEPTION 'expert session identity/expiry is immutable';
  END IF;
  IF OLD.revoked_at IS NOT NULL THEN
    RAISE EXCEPTION 'expert session is already revoked';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER expert_sessions_update_guard
  BEFORE UPDATE ON expert_sessions
  FOR EACH ROW EXECUTE FUNCTION trg_expert_sessions_update_guard();

CREATE FUNCTION trg_expert_grants_granter_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.tenant_id AND user_id = NEW.granted_by
      AND status = 'active' AND role IN ('owner','manager')
  ) THEN
    RAISE EXCEPTION 'expert grant granter must be an active owner or manager';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER expert_grants_granter_active
  BEFORE INSERT OR UPDATE OF tenant_id, granted_by ON expert_grants
  FOR EACH ROW EXECUTE FUNCTION trg_expert_grants_granter_active();

ALTER TABLE evidence_events DROP CONSTRAINT evidence_events_type_check;
ALTER TABLE evidence_events ADD CONSTRAINT evidence_events_type_check
  CHECK (type IN {_R5_1_TYPE_CHECK});
"""

_DOWNGRADE_SQL = f"""
ALTER TABLE evidence_events DROP CONSTRAINT evidence_events_type_check;
ALTER TABLE evidence_events ADD CONSTRAINT evidence_events_type_check
  CHECK (type IN {_PRE_R5_1_TYPE_CHECK});

DROP TRIGGER expert_grants_granter_active ON expert_grants;
DROP FUNCTION trg_expert_grants_granter_active();
DROP TRIGGER expert_sessions_update_guard ON expert_sessions;
DROP FUNCTION trg_expert_sessions_update_guard();
DROP TRIGGER expert_login_otps_update_guard ON expert_login_otps;
DROP FUNCTION trg_expert_login_otps_update_guard();
DROP TRIGGER package_view_log_no_delete ON package_view_log;
DROP TRIGGER package_view_log_no_update ON package_view_log;
DROP FUNCTION trg_package_view_log_immutable();

DROP TABLE pii_field_policies;
DROP TABLE package_view_log;
DROP TABLE expert_sessions;
DROP TABLE expert_login_otps;
DROP TABLE expert_grants;
DROP TABLE expert_office_members;
ALTER TABLE handoff_packages DROP CONSTRAINT handoff_packages_expert_account_fk;
ALTER TABLE handoff_packages DROP COLUMN expert_account_id;
DROP TABLE expert_accounts;
"""


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(_UPGRADE_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(_DOWNGRADE_SQL)
