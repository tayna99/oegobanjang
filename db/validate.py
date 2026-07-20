"""PostgreSQL design DDL guardrail verification.

Run:  DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" \
        uv run --no-project --with "psycopg[binary]" python db/validate.py --reset
Env:  DATABASE_URL (default: local Docker PG on :55432)

db/schema.sql(정본) + db/seed_demo.sql을 대상 스키마에 로드한 뒤, 테넌트 격리·승인
상태머신·외부 실행 차단 등 181개 회귀를 검증한다. 이 파일은 db/validate.cjs(SQLite)의
PG 이식본이다 — 검증 이름·시맨틱은 1:1로 보존하고, SQLite 전용(PRAGMA·sqlite_master·
boolean 0/1)만 PG로 옮겼다.

psycopg는 autocommit으로 열어 각 문장을 독립 트랜잭션으로 실행한다(node:sqlite db.exec와
동일 시맨틱) — 실패 문장은 전량 롤백되고 커넥션은 계속 사용 가능하다.
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
).replace("postgresql+psycopg://", "postgresql://")

parser = argparse.ArgumentParser(description="Reset and validate the local PostgreSQL schema")
parser.add_argument(
    "--reset",
    action="store_true",
    help="drop and recreate the target public schema before validation (destructive)",
)
args = parser.parse_args()
if not args.reset:
    raise SystemExit(
        "Refusing to drop the database schema. Re-run with --reset against a disposable validation DB."
    )

passed = 0
failed = 0


def ok(name: str, condition: bool, extra: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}" + (f" — {extra}" if extra else ""))


def expect_throw(name: str, sql: str, message_part: str | None = None) -> None:
    global passed, failed
    try:
        conn.execute(sql)
    except Exception as error:  # noqa: BLE001
        message = str(error)
        if not message_part or message_part in message:
            passed += 1
            print(f"PASS  {name}")
        else:
            failed += 1
            print(f"FAIL  {name} — unexpected error: {message.splitlines()[0]}")
    else:
        failed += 1
        print(f"FAIL  {name} — expected an error")


def run(sql: str) -> None:
    conn.execute(sql)


def scalar(sql: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchone()


def rows(sql: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


conn = psycopg.connect(DATABASE_URL, autocommit=True)

# 대상 스키마를 매번 새로 만든다(재실행 가능).
conn.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")

run((DIR / "schema.sql").read_text(encoding="utf-8"))
ok("schema.sql executes", True)
# PostgreSQL은 FK를 항상 강제한다(SQLite의 연결 스위치가 없다).
ok("foreign key enforcement is active (PostgreSQL always enforces)", True)

run((DIR / "seed_demo.sql").read_text(encoding="utf-8"))
ok("seed_demo.sql executes", True)

# seed가 로드됐다는 것 자체가 FK/무결성 위반이 없다는 뜻(PG는 즉시 강제).
ok("foreign_key_check has no violations", True)
ok("integrity_check is ok", True)

n_tables = scalar(
    "SELECT count(*) AS n FROM information_schema.tables "
    "WHERE table_schema='public' AND table_type='BASE TABLE'"
)["n"]
ok(
    "40 tables (R5.1 expert whitelabel: expert_accounts/expert_office_members/expert_grants/"
    "expert_login_otps/expert_sessions/package_view_log/pii_field_policies added)",
    n_tables == 40,
    f"actual={n_tables}",
)
n_views = scalar("SELECT count(*) AS n FROM information_schema.views WHERE table_schema='public'")["n"]
ok("4 views", n_views == 4, f"actual={n_views}")
ok(
    "package_links is absent",
    scalar(
        "SELECT count(*) AS n FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='package_links'"
    )["n"]
    == 0,
)

counts = {}
for table in [
    "companies", "users", "memberships", "workers", "citations", "worker_documents",
    "cases", "next_actions", "approvals", "case_citations", "evidence_events", "runs",
    "run_steps", "drafts", "draft_variants", "threads", "thread_messages",
    "interpretations", "status_update_proposals", "handoff_packages", "package_exports",
    "briefings", "briefing_items", "document_requirements",
]:
    counts[table] = scalar(f"SELECT count(*) AS n FROM {table}")["n"]
print(f"  seed counts: {counts}")
ok("seed has 6 cases", counts["cases"] == 6)
ok("seed has 6 workers", counts["workers"] == 6)
ok("seed has 9 citations", counts["citations"] == 9)
ok("seed has 10 evidence events", counts["evidence_events"] == 10)
ok("seed PDF export marks its package exported",
   scalar("SELECT status FROM handoff_packages WHERE id='hp_batbayar'")["status"] == "exported")

# Immutable evidence remains enforced.
expect_throw("evidence UPDATE is blocked", "UPDATE evidence_events SET summary='x' WHERE id='ev_4783'", "append-only")
expect_throw("evidence DELETE is blocked", "DELETE FROM evidence_events WHERE id='ev_4783'", "append-only")

# login_otps / sessions (F1~F10 backend PR — 인증/세션).
run("""
  INSERT INTO login_otps (id, phone, code_hash, expires_at) VALUES
    ('otp_1', '010-1111-2222', 'hash-abc', now() + interval '5 minutes');
""")
ok("login_otps insert succeeds", True)
expect_throw("login_otps phone is immutable", "UPDATE login_otps SET phone='010-0000-0000' WHERE id='otp_1'", "immutable")
expect_throw("login_otps code_hash is immutable", "UPDATE login_otps SET code_hash='hash-xyz' WHERE id='otp_1'", "immutable")
expect_throw(
    "login_otps expires_at is immutable",
    "UPDATE login_otps SET expires_at = now() + interval '1 minute' WHERE id='otp_1'",
    "immutable",
)
expect_throw(
    "login_otps created_at is immutable", "UPDATE login_otps SET created_at = now() WHERE id='otp_1'", "immutable"
)
run("UPDATE login_otps SET attempt_count = attempt_count + 1 WHERE id='otp_1'")
ok("login_otps attempt_count remains mutable", scalar("SELECT attempt_count AS n FROM login_otps WHERE id='otp_1'")["n"] == 1)
expect_throw(
    "login_otps attempt_count rejects negative",
    "INSERT INTO login_otps (id, phone, code_hash, expires_at, attempt_count) "
    "VALUES ('otp_bad', '010-1111-3333', 'hash-bad', now() + interval '5 minutes', -1)",
)
run("UPDATE login_otps SET consumed_at = now() WHERE id='otp_1'")
ok("login_otps consumed_at settable once", True)
expect_throw("login_otps cannot be consumed twice", "UPDATE login_otps SET consumed_at = now() WHERE id='otp_1'", "already consumed")

run("""
  INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES
    ('sess_1', 'usr_kim', 'token-hash-abc', now() + interval '30 days');
""")
ok("sessions insert succeeds", True)
expect_throw(
    "sessions rejects unknown user_id",
    "INSERT INTO sessions (id, user_id, token_hash, expires_at) "
    "VALUES ('sess_bad', 'usr_does_not_exist', 'token-hash-zzz', now() + interval '30 days')",
)
expect_throw(
    "sessions token_hash is unique",
    "INSERT INTO sessions (id, user_id, token_hash, expires_at) "
    "VALUES ('sess_dup', 'usr_kim', 'token-hash-abc', now() + interval '30 days')",
)
expect_throw(
    "sessions rejects expires_at <= created_at",
    "INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at) "
    "VALUES ('sess_bad_ttl', 'usr_kim', 'token-hash-ttl', now(), now())",
)
expect_throw("sessions user_id is immutable", "UPDATE sessions SET user_id='usr_park' WHERE id='sess_1'", "immutable")
expect_throw("sessions token_hash is immutable", "UPDATE sessions SET token_hash='token-hash-changed' WHERE id='sess_1'", "immutable")
expect_throw(
    "sessions expires_at is immutable",
    "UPDATE sessions SET expires_at = now() + interval '1 day' WHERE id='sess_1'",
    "immutable",
)
run("UPDATE sessions SET revoked_at = now() WHERE id='sess_1'")
ok("sessions revoked_at settable once", True)
expect_throw("sessions cannot be revoked twice", "UPDATE sessions SET revoked_at = now() WHERE id='sess_1'", "already revoked")

# Seed a second tenant and its valid graph for isolation attacks.
run("""
  INSERT INTO companies (id, name) VALUES ('cmp_other', 'Other Factory');
  INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
    ('usr_other', '010-9000-0001', 'Other Owner', '2026-07-10T00:00:00Z'),
    ('usr_invited', '010-9000-0002', 'Invited User', '2026-07-10T00:00:00Z'),
    ('usr_orphan', '010-9000-0003', 'Orphan User', '2026-07-10T00:00:00Z'),
    ('usr_other_manager', '010-9000-0004', 'Other Manager', '2026-07-10T00:00:00Z'),
    ('usr_other_expert', '010-9000-0005', 'Other Expert', '2026-07-10T00:00:00Z');
  INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
    ('mbr_other_owner', 'cmp_other', 'usr_other', 'owner', 'active'),
    ('mbr_other_invited', 'cmp_other', 'usr_invited', 'viewer', 'invited'),
    ('mbr_other_manager', 'cmp_other', 'usr_other_manager', 'manager', 'active'),
    ('mbr_other_expert', 'cmp_other', 'usr_other_expert', 'expert', 'active');
  INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
    ('wrk_other', 'cmp_other', 'Other Worker', 'VN', '2026-12-31');
  INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES
    ('cs_other', 'cmp_other', 'case_001', 'wrk_other', 'other', 'Other case', 'LOW', 'draft');
  INSERT INTO runs (id, company_id, case_id, started_by, agent_name, status) VALUES
    ('run_other', 'cmp_other', 'cs_other', 'event', 'Other Agent', 'queued');
  INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
    ('act_other_message', 'cmp_other', 'cs_other', 'approve', 'send_message', 'Approve message', 'ready', true),
    ('act_other_handoff', 'cmp_other', 'cs_other', 'approve', 'create_handoff', 'Approve handoff', 'ready', true),
    ('act_other_detail', 'cmp_other', 'cs_other', 'detail', 'other', 'Detail', 'ready', false);
  INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES
    ('apv_other_message', 'cmp_other', 'cs_other', 'act_other_message', 'pending', 'idem-other-message', 'rule', '2026-07-10T00:00:00Z'),
    ('apv_other_handoff', 'cmp_other', 'cs_other', 'act_other_handoff', 'pending', 'idem-other-handoff', 'rule', '2026-07-10T00:00:00Z');
  INSERT INTO threads (id, company_id, worker_id, channel) VALUES
    ('th_other', 'cmp_other', 'wrk_other', 'zalo');
  INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES
    ('tm_other_inbound', 'cmp_other', 'th_other', 'inbound');
  INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash) VALUES
    ('brf_other', 'cmp_other', '2026-07-10', '2026-07-10T00:00:00Z', 'sha256:other');
""")
ok("second tenant setup succeeds", True)

# Pending approvals may omit a decision idempotency key; a concrete key is still unique.
expect_throw(
    "duplicate pending approval is blocked",
    "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_dup','cmp_greenfood','cs_nguyen','act_nguyen_approve','pending','idem-x','user','2026-07-10T00:00:00Z')",
)
run("""
  INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
    ('act_other_idem_a', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Idempotency A', 'ready', true),
    ('act_other_idem_b', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Idempotency B', 'ready', true),
    ('act_other_null_a', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Null key A', 'ready', true),
    ('act_other_null_b', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Null key B', 'ready', true);
  INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES
    ('apv_idem_a', 'cmp_other', 'cs_other', 'act_other_idem_a', 'pending', 'idem-selfcontained-1', 'user', '2026-07-10T00:00:00Z'),
    ('apv_null_a', 'cmp_other', 'cs_other', 'act_other_null_a', 'pending', NULL, 'user', '2026-07-10T00:00:00Z'),
    ('apv_null_b', 'cmp_other', 'cs_other', 'act_other_null_b', 'pending', NULL, 'user', '2026-07-10T00:00:00Z');
""")
expect_throw(
    "idempotency key is unique when present",
    "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_idem_b','cmp_other','cs_other','act_other_idem_b','pending','idem-selfcontained-1','user','2026-07-10T00:00:00Z')",
)
ok("pending approvals may share a NULL idempotency key",
   scalar("SELECT count(*) AS n FROM approvals WHERE id IN ('apv_null_a','apv_null_b') AND idempotency_key IS NULL")["n"] == 2)
expect_throw("pending approval cannot be deleted", "DELETE FROM approvals WHERE id='apv_idem_a'", "approval deletion")

# Valid same-company child rows give every direct relation an UPDATE target.
run("""
  INSERT INTO worker_documents (id, company_id, worker_id, doc_type) VALUES
    ('wd_other_valid', 'cmp_other', 'wrk_other', 'passport');
  INSERT INTO worker_intake_files (id, company_id, worker_id, storage_key) VALUES
    ('wif_other_valid', 'cmp_other', 'wrk_other', 'uploads/other.png');
  INSERT INTO run_steps (id, company_id, run_id, seq, kind, label) VALUES
    ('st_other_valid', 'cmp_other', 'run_other', 1, 'thinking', 'Other step');
  INSERT INTO drafts (id, company_id, case_id, channel, purpose, status) VALUES
    ('drf_other_update', 'cmp_other', 'cs_other', 'zalo', 'Update target', 'draft');
  INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES
    ('dv_other_update', 'cmp_other', 'drf_other_update', 'ko', 'same-company draft');
  INSERT INTO interpretations (id, company_id, thread_message_id, case_id, summary_ko, confidence) VALUES
    ('int_other_valid', 'cmp_other', 'tm_other_inbound', 'cs_other', 'same-company interpretation', 'low');
  INSERT INTO status_update_proposals (id, company_id, interpretation_id, target_type, target_key, from_value, to_value) VALUES
    ('sup_other_valid', 'cmp_other', 'int_other_valid', 'worker_document', 'passport', 'missing', 'received');
  INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status) VALUES
    ('hp_other_update', 'cmp_other', 'cs_other', 'expert_review', '{}', 'draft');
  INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank) VALUES
    ('bi_other_valid', 'cmp_other', 'brf_other', 'cs_other', 1);
  INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel) VALUES
    ('nt_other_valid', 'cmp_other', 'usr_other', 'N01', 'P1', 'x', 'x', '/', 'other-valid', 'push');
  INSERT INTO csv_imports (id, company_id, uploaded_by_user_id, filename) VALUES
    ('csv_other_valid', 'cmp_other', 'usr_other', 'other.csv');
  INSERT INTO autonomy_grants (id, company_id, case_type, level, consented_by_user_id, consented_at) VALUES
    ('ag_other_valid', 'cmp_other', 'other', 'L2', 'usr_other', '2026-07-10T00:00:00Z');
  INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, starts_at, ends_at) VALUES
    ('del_other_valid', 'cmp_other', 'usr_other', 'usr_other_manager', '2026-07-10T00:00:00Z', '2026-07-11T00:00:00Z');
  INSERT INTO memberships (id, company_id, role, status, invited_by) VALUES
    ('mbr_other_valid_invite', 'cmp_other', 'viewer', 'invited', 'usr_other');
""")
ok("same-company direct tenant relations are allowed", True)

# Every direct tenant relation must reject another company's parent record.
expect_throw("worker document rejects foreign worker",
  "INSERT INTO worker_documents (id, company_id, worker_id, doc_type) VALUES ('wd_cross','cmp_other','wrk_nguyen','passport')")
expect_throw("worker intake rejects foreign worker",
  "INSERT INTO worker_intake_files (id, company_id, worker_id, storage_key) VALUES ('wif_cross','cmp_other','wrk_nguyen','uploads/cross.png')")
expect_throw("case rejects foreign worker",
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_cross_worker','cmp_other','case_002','wrk_nguyen','other','Cross','LOW','draft')")
expect_throw("case rejects foreign prepared run",
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, prepared_run_id) VALUES ('cs_cross_run','cmp_other','case_003','wrk_other','other','Cross run','LOW','draft','run_4788')")
expect_throw("run rejects foreign case",
  "INSERT INTO runs (id, company_id, case_id, started_by, agent_name, status) VALUES ('run_cross','cmp_other','cs_nguyen','event','Agent','queued')")
expect_throw("run step rejects foreign run",
  "INSERT INTO run_steps (id, company_id, run_id, seq, kind, label) VALUES ('st_cross','cmp_other','run_4788',2,'thinking','Cross step')")
expect_throw("action rejects foreign case",
  "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_cross','cmp_other','cs_nguyen','detail','other','Cross','ready',false)")
expect_throw("approval rejects action from another case",
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_case_cross','cmp_greenfood','cs_nguyen','act_batbayar_handoff','pending','idem-case-cross','rule','2026-07-10T00:00:00Z')")
expect_throw("approval rejects foreign action",
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_tenant_cross','cmp_other','cs_other','act_nguyen_approve','pending','idem-tenant-cross','rule','2026-07-10T00:00:00Z')")
expect_throw("thread rejects foreign worker",
  "INSERT INTO threads (id, company_id, worker_id, channel) VALUES ('th_cross','cmp_other','wrk_nguyen','zalo')")
expect_throw("draft rejects foreign case",
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status) VALUES ('drf_cross','cmp_other','cs_nguyen','zalo','Cross','draft')")
expect_throw("draft rejects foreign thread",
  "INSERT INTO drafts (id, company_id, case_id, thread_id, channel, purpose, status) VALUES ('drf_cross_thread','cmp_other','cs_other','th_tran','zalo','Cross','draft')")
expect_throw("draft rejects foreign source run",
  "INSERT INTO drafts (id, company_id, case_id, created_by_run_id, channel, purpose, status) VALUES ('drf_cross_run','cmp_other','cs_other','run_4788','zalo','Cross','draft')")
expect_throw("draft variant rejects foreign draft",
  "INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES ('dv_cross','cmp_other','drf_nguyen','ko','x')")
expect_throw("thread message rejects foreign thread",
  "INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES ('tm_cross','cmp_other','th_tran','inbound')")
expect_throw("interpretation rejects foreign case",
  "INSERT INTO interpretations (id, company_id, thread_message_id, case_id, summary_ko, confidence) VALUES ('int_cross','cmp_other','tm_other_inbound','cs_nguyen','x','low')")
expect_throw("status proposal rejects foreign interpretation",
  "INSERT INTO status_update_proposals (id, company_id, interpretation_id, target_type, target_key, from_value, to_value) VALUES ('sup_cross','cmp_other','int_tran','worker_document','passport','missing','received')")
expect_throw("handoff rejects foreign case",
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status) VALUES ('hp_cross','cmp_other','cs_nguyen','expert_review','{}','draft')")
expect_throw("briefing item rejects foreign case",
  "INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank) VALUES ('bi_cross','cmp_other','brf_other','cs_nguyen',1)")
expect_throw("notification rejects foreign case",
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, case_id) VALUES ('nt_cross','cmp_other','usr_other','N01','P1','x','x','/','cross','push','cs_nguyen')")
expect_throw("worker document update rejects foreign worker",
  "UPDATE worker_documents SET worker_id='wrk_nguyen' WHERE id='wd_other_valid'")
expect_throw("worker intake update rejects foreign worker",
  "UPDATE worker_intake_files SET worker_id='wrk_nguyen' WHERE id='wif_other_valid'")
expect_throw("case update rejects foreign worker",
  "UPDATE cases SET worker_id='wrk_nguyen' WHERE id='cs_other'")
expect_throw("case update rejects foreign assignee",
  "UPDATE cases SET assignee_user_id='usr_kim' WHERE id='cs_other'")
expect_throw("run update rejects foreign case",
  "UPDATE runs SET case_id='cs_nguyen' WHERE id='run_other'")
expect_throw("run update rejects foreign starter",
  "UPDATE runs SET started_by_user_id='usr_kim' WHERE id='run_other'")
expect_throw("run step update rejects foreign run",
  "UPDATE run_steps SET run_id='run_4788' WHERE id='st_other_valid'")
expect_throw("action update rejects foreign case",
  "UPDATE next_actions SET case_id='cs_nguyen' WHERE id='act_other_detail'")
expect_throw("thread update rejects foreign worker",
  "UPDATE threads SET worker_id='wrk_nguyen' WHERE id='th_other'")
expect_throw("draft update rejects foreign case",
  "UPDATE drafts SET case_id='cs_nguyen' WHERE id='drf_other_update'")
expect_throw("draft variant update rejects another company parent",
  "UPDATE draft_variants SET company_id='cmp_greenfood' WHERE id='dv_other_update'")
expect_throw("thread message update rejects foreign thread",
  "UPDATE thread_messages SET thread_id='th_tran' WHERE id='tm_other_inbound'")
expect_throw("interpretation update rejects foreign message",
  "UPDATE interpretations SET thread_message_id='tm_tran_reply' WHERE id='int_other_valid'")
expect_throw("status proposal update rejects foreign interpretation",
  "UPDATE status_update_proposals SET interpretation_id='int_tran' WHERE id='sup_other_valid'")
expect_throw("handoff update rejects foreign case",
  "UPDATE handoff_packages SET case_id='cs_nguyen' WHERE id='hp_other_update'")
expect_throw("briefing item update rejects foreign case",
  "UPDATE briefing_items SET case_id='cs_nguyen' WHERE id='bi_other_valid'")
expect_throw("notification update rejects foreign case",
  "UPDATE notifications SET case_id='cs_nguyen' WHERE id='nt_other_valid'")
expect_throw("csv import update rejects foreign uploader",
  "UPDATE csv_imports SET uploaded_by_user_id='usr_kim' WHERE id='csv_other_valid'")
expect_throw("autonomy grant update rejects foreign owner",
  "UPDATE autonomy_grants SET consented_by_user_id='usr_kim' WHERE id='ag_other_valid'")
expect_throw("delegation update rejects foreign delegate",
  "UPDATE delegations SET delegate_user_id='usr_kim' WHERE id='del_other_valid'")
expect_throw("membership update rejects foreign inviter",
  "UPDATE memberships SET invited_by='usr_kim' WHERE id='mbr_other_valid_invite'")
expect_throw("tenant table rejects user without membership",
  "INSERT INTO csv_imports (id, company_id, uploaded_by_user_id, filename) VALUES ('csv_orphan','cmp_other','usr_orphan','x.csv')")
expect_throw("tenant table rejects inactive membership user",
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel) VALUES ('nt_invited','cmp_other','usr_invited','N01','P1','x','x','/','invited','push')", "active member")
expect_throw("case rejects an assignee without membership",
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, assignee_user_id) VALUES ('cs_bad_assignee','cmp_other','case_002','wrk_other','other','Bad assignee','LOW','draft','usr_orphan')")
expect_throw("run rejects a starter without membership",
  "INSERT INTO runs (id, company_id, case_id, started_by, started_by_user_id, agent_name, status) VALUES ('run_bad_starter','cmp_other','cs_other','user','usr_orphan','Agent','queued')")
expect_throw("membership rejects an inviter without membership",
  "INSERT INTO memberships (id, company_id, role, status, invited_by) VALUES ('mbr_bad_inviter','cmp_other','viewer','invited','usr_orphan')")
expect_throw("delegation requires an active owner",
  "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, starts_at, ends_at) VALUES ('del_bad_role','cmp_other','usr_other_manager','usr_other','2026-07-10T00:00:00Z','2026-07-11T00:00:00Z')", "delegation members")
expect_throw("interpretation rejects an inactive confirmer",
  "INSERT INTO interpretations (id, company_id, thread_message_id, summary_ko, confidence, status, confirmed_by_user_id) VALUES ('int_bad_confirmer','cmp_other','tm_other_inbound','x','low','confirmed','usr_invited')", "active member")
expect_throw("autonomy consent requires an active owner",
  "INSERT INTO autonomy_grants (id, company_id, case_type, level, consented_by_user_id, consented_at) VALUES ('ag_bad_owner','cmp_other','other','L2','usr_other_manager','2026-07-10T00:00:00Z')", "active owner")
run("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_expert_ok','cmp_other','expert','usr_other_expert','format_preference','Uses structured checklists')")
ok("agent note accepts an active same-company expert", True)
expect_throw("agent note rejects an expert from another company",
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_expert_cross','cmp_other','expert','usr_kim','format_preference','x')", "same company")
run("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_worker_ok','cmp_other','worker','wrk_other','response_pattern','Uses concise replies')")
run("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_company_ok','cmp_other','company','cmp_other','format_preference','Uses internal checklists')")
expect_throw("agent note rejects a worker from another company",
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_worker_cross','cmp_other','worker','wrk_nguyen','response_pattern','x')", "same company")
expect_throw("agent note rejects another company subject",
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_company_cross','cmp_other','company','cmp_greenfood','format_preference','x')", "same company")
expect_throw("agent note update rejects a worker from another company",
  "UPDATE agent_notes SET subject_id='wrk_nguyen' WHERE id='note_worker_ok'", "same company")
expect_throw("case cannot begin in a human-approved state",
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_bad_terminal','cmp_other','case_003','wrk_other','other','Bad terminal','LOW','human_approved')", "must begin")

# Citation scope: global and own-company citations are valid; foreign internal citations are not.
run("INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) VALUES ('cit_other_internal','cmp_other','A','internal','Other internal','other','2026-07-10T00:00:00Z')")
run("INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES ('cit_global_ok','A','official','Global','official','2026-07-10T00:00:00Z')")
expect_throw("global citations cannot be internal evidence",
  "INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES ('cit_global_internal','A','internal','Bad global','x','2026-07-10T00:00:00Z')")
run("INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) VALUES ('cit_company_scoped','cmp_other','A','official','Scoped local','x','2026-07-10T00:00:00Z')")
ok("company-specific citations stay out of the global view",
  scalar("SELECT count(*) AS n FROM v_global_usable_citations WHERE id='cit_company_scoped'")["n"] == 0)
run("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_other','cs_other','cit_other_internal','user')")
run("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_other','cs_other','cit_global_ok','user')")
run("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_greenfood','cs_nguyen','cit_global_ok','user')")
ok("same-company and global citations are allowed", True)
expect_throw("case rejects foreign internal citation",
  "INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_greenfood','cs_nguyen','cit_other_internal','user')", "same company")
expect_throw("case citation update rejects a foreign case",
  "UPDATE case_citations SET case_id='cs_nguyen' WHERE company_id='cmp_other' AND case_id='cs_other' AND citation_id='cit_other_internal'")
expect_throw("global document requirement rejects internal citation",
  "INSERT INTO document_requirements (id, case_type, visa_type, required_doc, citation_id) VALUES ('req_private','other','E-9','private','cit_other_internal')", "must be global")
run("INSERT INTO document_requirements (id, case_type, visa_type, required_doc, citation_id) VALUES ('req_global_update','other','E-9','global-only','cit_global_ok')")
expect_throw("global document requirement cannot be updated to an internal citation",
  "UPDATE document_requirements SET citation_id='cit_other_internal' WHERE id='req_global_update'", "must be global")
expect_throw("a global citation cannot be re-scoped to a company",
  "UPDATE citations SET company_id='cmp_greenfood' WHERE id='cit_global_ok'", "scope is immutable")
expect_throw("an internal citation cannot be promoted to global",
  "UPDATE citations SET company_id=NULL WHERE id='cit_other_internal'", "scope is immutable")
ok("unscoped usable citation view is absent",
  scalar("SELECT count(*) AS n FROM information_schema.views WHERE table_schema='public' AND table_name='v_usable_citations'")["n"] == 0)
ok("global usable citation view hides internal citations",
  scalar("SELECT count(*) AS n FROM v_global_usable_citations WHERE company_id IS NOT NULL")["n"] == 0)
ok("citation links are company scoped",
  scalar("SELECT linked_case_count FROM v_citation_link_counts WHERE company_id='cmp_other' AND citation_id='cit_other_internal'")["linked_case_count"] == 1)
global_citation_counts = rows("SELECT company_id, linked_case_count FROM v_citation_link_counts WHERE citation_id='cit_global_ok' ORDER BY company_id")
ok("shared global citation counts are separated by company",
  len(global_citation_counts) == 2 and all(r["linked_case_count"] == 1 for r in global_citation_counts),
  str(global_citation_counts))

# MVP delivery cannot be represented as a completed outbound action.
expect_throw("notification sent status is blocked",
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_sent','cmp_other','usr_other','N01','P1','x','x','/','sent','push','sent')")
expect_throw("notification delivered status is blocked",
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_delivered','cmp_other','usr_other','N01','P1','x','x','/','delivered','push','delivered')")
expect_throw("notification failed status is blocked",
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_failed','cmp_other','usr_other','N01','P1','x','x','/','failed','push','failed')")
expect_throw("outbound thread message is blocked",
  "INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES ('tm_outbound','cmp_other','th_other','outbound')")
expect_throw("notification_sent evidence type is blocked",
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary) VALUES ('ev_notification_sent','cmp_other',1,'notification_sent','2026-07-10T00:00:00Z','system','x')")
ok("thread_messages has no sent_at column",
  scalar("SELECT count(*) AS n FROM information_schema.columns WHERE table_schema='public' AND table_name='thread_messages' AND column_name='sent_at'")["n"] == 0)
ok("notifications has no delivery timestamp columns",
  scalar("SELECT count(*) AS n FROM information_schema.columns WHERE table_schema='public' AND table_name='notifications' AND column_name IN ('sent_at','delivered_at')")["n"] == 0)
expect_throw("evidence rejects an action and approval from another case",
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, case_id, action_id, approval_id, actor_type, summary) VALUES ('ev_bad_context','cmp_greenfood',9999,'approval_requested','2026-07-10T00:00:00Z','cs_nguyen','act_batbayar_handoff','apv_batbayar_export','system','x')", "must match its case")

# Approval state is explicit, scoped, and single-transition.
expect_throw("approval must start pending",
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, decided_by_user_id, identity_method, requested_at, decided_at) VALUES ('apv_direct_terminal','cmp_other','cs_other','act_other_message','approved','idem-direct-terminal','rule','usr_other','pin','2026-07-10T00:00:00Z','2026-07-10T00:05:00Z')", "must start pending")
expect_throw("pending approval cannot carry decision metadata",
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, decided_by_user_id, identity_method, requested_at, decided_at) VALUES ('apv_pending_metadata','cmp_other','cs_other','act_other_message','pending','idem-pending-metadata','rule','usr_other','pin','2026-07-10T00:00:00Z','2026-07-10T00:05:00Z')")
expect_throw("approval cannot target non-approval action",
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_detail','cmp_other','cs_other','act_other_detail','pending','idem-detail','rule','2026-07-10T00:00:00Z')", "must require approval")
expect_throw("required action cannot disable approval",
  "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_bad_required','cmp_other','cs_other','approve','send_message','Bad','ready',false)")
for action_type in ["create_handoff", "export_package", "complete_case"]:
    expect_throw(f"{action_type} action cannot disable approval",
      f"INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_bad_{action_type}','cmp_other','cs_other','approve','{action_type}','Bad','ready',false)")
expect_throw("required action cannot be changed to bypass approval",
  "UPDATE next_actions SET action_type='send_message' WHERE id='act_other_detail'")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_owner_only','cmp_other','cs_other','approve','confirm_status','Approve','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_owner_only','cmp_other','cs_other','act_other_owner_only','pending','idem-manager-owner-only','rule','2026-07-10T00:00:00Z')")
expect_throw("approval decider must satisfy the owner-only policy",
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_manager_owner_only'", "not allowed by company policy")

# R2.4 — delegated decider (del_other_valid: usr_other(owner) -> usr_other_manager, scope='approval',
# 2026-07-10T00:00:00Z ~ 2026-07-11T00:00:00Z). owner_only 정책 하에서도 유효한 위임 + on_behalf_of_user_id면 허용된다.
# 전용 케이스(cs_other_delegated)를 쓴다 — cs_other를 재사용하면 이 블록에서 승인된 액션이
# 뒤쪽 "case cannot become human-approved while approval is pending" 검증(같은 cs_other 대상)을
# 오염시킨다.
run("INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_other_delegated','cmp_other','case_005','wrk_other','other','Delegated case','LOW','draft')")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_delegated','cmp_other','cs_other_delegated','approve','confirm_status','Delegated Approve','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_delegated','cmp_other','cs_other_delegated','act_other_delegated','pending','idem-manager-delegated','rule','2026-07-10T00:00:00Z')")
run("UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', on_behalf_of_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T12:00:00Z' WHERE id='apv_manager_delegated'")
ok("delegated manager can approve on behalf of the owner under owner-only policy",
  scalar("SELECT status FROM approvals WHERE id='apv_manager_delegated'")["status"] == "approved")

run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_delegated_expired','cmp_other','cs_other_delegated','approve','confirm_status','Delegated Approve Expired','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_delegated_expired','cmp_other','cs_other_delegated','act_other_delegated_expired','pending','idem-manager-delegated-expired','rule','2026-07-10T00:00:00Z')")
expect_throw("delegated decider is rejected once the delegation window has expired",
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', on_behalf_of_user_id='usr_other', identity_method='pin', decided_at='2026-07-12T00:00:00Z' WHERE id='apv_manager_delegated_expired'",
  "not allowed by company policy")

run("UPDATE delegations SET revoked_at='2026-07-10T13:00:00Z' WHERE id='del_other_valid'")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_delegated_revoked','cmp_other','cs_other_delegated','approve','confirm_status','Delegated Approve Revoked','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_delegated_revoked','cmp_other','cs_other_delegated','act_other_delegated_revoked','pending','idem-manager-delegated-revoked','rule','2026-07-10T00:00:00Z')")
expect_throw("delegated decider is rejected once the delegation is revoked",
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', on_behalf_of_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T14:00:00Z' WHERE id='apv_manager_delegated_revoked'",
  "not allowed by company policy")

run("UPDATE companies SET approval_policy='manager_allowed' WHERE id='cmp_other'")
run("INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_other_medium','cmp_other','case_004','wrk_other','other','Medium case','MEDIUM','draft')")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_medium','cmp_other','cs_other_medium','approve','send_message','Approve','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_medium','cmp_other','cs_other_medium','act_other_medium','pending','idem-manager-medium','rule','2026-07-10T00:00:00Z')")
expect_throw("manager cannot approve a medium-risk case",
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_manager_medium'", "not allowed by company policy")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_reject','cmp_other','cs_other','approve','confirm_status','Reject','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_reject','cmp_other','cs_other','act_other_reject','pending','idem-other-reject','rule','2026-07-10T00:00:00Z')")
expect_throw("rejected approval requires a reason",
  "UPDATE approvals SET status='rejected', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_other_reject'")
expect_throw("pending approval cannot become approved without identity",
  "UPDATE approvals SET status='approved' WHERE id='apv_other_handoff'")
expect_throw("an approval action contract cannot change after a request exists",
  "UPDATE next_actions SET action_type='other' WHERE id='act_other_handoff'", "action contract is immutable")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_nguyen_retarget','cmp_greenfood','cs_nguyen','approve','create_handoff','Retarget','ready',true)")
expect_throw("linked approval cannot be retargeted to a different required action",
  "UPDATE approvals SET action_id='act_nguyen_retarget' WHERE id='apv_nguyen'", "approval target is immutable")
expect_throw("case rejects a transition outside its state machine",
  "UPDATE cases SET state='risk_review' WHERE id='cs_nguyen'", "state transition is not allowed")
run("UPDATE cases SET state='risk_review' WHERE id='cs_other'")
run("UPDATE cases SET state='approval_pending' WHERE id='cs_other'")
expect_throw("case cannot become human-approved while approval is pending",
  "UPDATE cases SET state='human_approved' WHERE id='cs_other'", "requires an approved case action")
expect_throw("blocked case state cannot be reopened",
  "UPDATE cases SET state='risk_review' WHERE id='cs_batbayar'", "terminal case state")
run("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_other_message'")
ok("pending approval can become approved with identity",
  scalar("SELECT status FROM approvals WHERE id='apv_other_message'")["status"] == "approved")
expect_throw("terminal approval cannot be re-decided",
  "UPDATE approvals SET status='rejected', reason='later' WHERE id='apv_other_message'", "terminal approval")
expect_throw("terminal approval cannot be deleted",
  "DELETE FROM approvals WHERE id='apv_other_message'", "approval deletion")
run("UPDATE cases SET state='human_approved' WHERE id='cs_other'")
ok("case becomes human-approved only after its approved action",
  scalar("SELECT state FROM cases WHERE id='cs_other'")["state"] == "human_approved")
run("UPDATE approvals SET status='approved', idempotency_key='idem-decision-once', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:01:00Z' WHERE id='apv_null_a'")
expect_throw("decision idempotency key cannot be reused",
  "UPDATE approvals SET status='approved', idempotency_key='idem-decision-once', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:01:00Z' WHERE id='apv_null_b'")
expect_throw("draft rejects an approval from another company",
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_foreign_approval','cmp_other','cs_other','zalo','x','pending_approval','apv_nguyen')")
expect_throw("draft rejects an approval from another case",
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other_case_approval','cmp_other','cs_other_medium','zalo','x','pending_approval','apv_other_message')")
expect_throw("draft update rejects an approval from another company",
  "UPDATE drafts SET status='pending_approval', approval_id='apv_nguyen' WHERE id='drf_other_update'")
expect_throw("handoff rejects an approval from another company",
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_foreign_approval','cmp_other','cs_other','expert_review','{}','pending_approval','apv_nguyen')")
expect_throw("handoff rejects an approval from another case",
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_other_case_approval','cmp_other','cs_other_medium','expert_review','{}','pending_approval','apv_other_handoff')")
expect_throw("handoff update rejects an approval from another company",
  "UPDATE handoff_packages SET status='pending_approval', approval_id='apv_nguyen' WHERE id='hp_other_update'")
expect_throw("draft needs a matching message approval state",
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_bad','cmp_other','cs_other','zalo','x','pending_approval','apv_other_handoff')", "draft must start editable")
expect_throw("draft cannot be inserted as an already approved artifact",
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_direct_terminal','cmp_other','cs_other','zalo','x','approved','apv_other_message')", "draft must start editable")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_draft_lifecycle','cmp_other','cs_other','approve','send_message','Approve lifecycle draft','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES ('apv_other_draft_lifecycle','cmp_other','cs_other','act_other_draft_lifecycle','pending','rule','2026-07-10T00:00:00Z')")
run("INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other','cmp_other','cs_other','zalo','x','pending_approval','apv_other_draft_lifecycle')")
run("UPDATE approvals SET status='approved', idempotency_key='idem-other-draft-lifecycle', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:04:00Z' WHERE id='apv_other_draft_lifecycle'")
ok("draft reaches approved only through approval synchronization",
  scalar("SELECT status FROM drafts WHERE id='drf_other'")["status"] == "approved")
expect_throw("pending draft cannot clear approval and return to draft",
  "UPDATE drafts SET status='draft', approval_id=NULL WHERE id='drf_nguyen'", "draft approval")
expect_throw("pending draft cannot replace its approval",
  "UPDATE drafts SET approval_id='apv_other_message' WHERE id='drf_nguyen'", "draft approval link")
expect_throw("pending draft content cannot change before a new revision",
  "UPDATE drafts SET purpose='changed' WHERE id='drf_nguyen'", "draft content is locked")
expect_throw("pending draft variants cannot change before a new revision",
  "UPDATE draft_variants SET text='changed' WHERE id='dv_nguyen_ko'", "editable draft")
run("UPDATE approvals SET status='approved', decided_by_user_id='usr_owner', identity_method='pin', decided_at='2026-07-10T00:08:00Z' WHERE id='apv_nguyen'")
ok("approved approval automatically updates its linked draft",
  scalar("SELECT status FROM drafts WHERE id='drf_nguyen'")["status"] == "approved")
expect_throw("approved draft cannot clear its approval",
  "UPDATE drafts SET approval_id=NULL WHERE id='drf_nguyen'", "draft approval link")
expect_throw("approved draft cannot return to draft",
  "UPDATE drafts SET status='draft' WHERE id='drf_nguyen'", "draft approval state")
expect_throw("approved draft content stays locked after rollback attempts",
  "UPDATE drafts SET purpose='changed after approval' WHERE id='drf_nguyen'", "draft content is locked")
expect_throw("approved draft cannot receive a new variant",
  "INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES ('dv_other_late','cmp_other','drf_other','ko','changed')", "editable draft")
run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_reject_message','cmp_other','cs_other','approve','send_message','Reject message','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_reject_message','cmp_other','cs_other','act_other_reject_message','pending','idem-other-reject-message','rule','2026-07-10T00:00:00Z')")
run("INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other_reject','cmp_other','cs_other','zalo','x','pending_approval','apv_other_reject_message')")
run("UPDATE approvals SET status='rejected', decided_by_user_id='usr_other', identity_method='pin', reason='Needs revision', decided_at='2026-07-10T00:08:00Z' WHERE id='apv_other_reject_message'")
ok("rejected approval automatically updates its linked draft",
  scalar("SELECT status FROM drafts WHERE id='drf_other_reject'")["status"] == "rejected")
run("INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_other','cmp_other','cs_other','expert_review','{}','pending_approval','apv_other_handoff')")
expect_throw("package export needs an approved handoff",
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_pending','hp_other','cmp_other','pdf','sha256:x','usr_other')", "approved handoff")
expect_throw("pending handoff cannot clear approval and return to draft",
  "UPDATE handoff_packages SET status='draft', approval_id=NULL WHERE id='hp_other'", "handoff approval")
expect_throw("pending handoff cannot replace its approval",
  "UPDATE handoff_packages SET approval_id='apv_other_message' WHERE id='hp_other'", "handoff approval link")
expect_throw("pending handoff package content cannot change",
  "UPDATE handoff_packages SET included_items='[]' WHERE id='hp_other'", "handoff package content is locked")
run("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:06:00Z' WHERE id='apv_other_handoff'")
ok("approved approval automatically updates its linked handoff package",
  scalar("SELECT status FROM handoff_packages WHERE id='hp_other'")["status"] == "approved")
expect_throw("handoff cannot be inserted as an already approved artifact",
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_direct_terminal','cmp_other','cs_other','expert_review','{}','approved','apv_other_handoff')", "handoff package must start")
expect_throw("approved handoff cannot clear its approval",
  "UPDATE handoff_packages SET approval_id=NULL WHERE id='hp_other'", "handoff approval link")
expect_throw("approved handoff cannot return to draft",
  "UPDATE handoff_packages SET status='draft' WHERE id='hp_other'", "handoff approval state")
expect_throw("approved handoff package content cannot change",
  "UPDATE handoff_packages SET package_type='pre_entry' WHERE id='hp_other'", "handoff package content is locked")
expect_throw("approved handoff cannot claim a PDF export without an export record",
  "UPDATE handoff_packages SET status='exported' WHERE id='hp_other'", "exported without a PDF")
run("INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status) VALUES ('hp_other_draft','cmp_other','cs_other','expert_review','{}','draft')")
expect_throw("package export rejects an inactive exporter",
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_inactive','hp_other','cmp_other','pdf','sha256:x','usr_invited')", "active member")
run("INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_other','hp_other','cmp_other','pdf','sha256:other','usr_other')")
ok("approved handoff package accepts an internal PDF export and becomes exported",
  scalar("SELECT status FROM handoff_packages WHERE id='hp_other'")["status"] == "exported")
expect_throw("package export rejects non-PDF formats",
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_link','hp_other','cmp_other','link','sha256:link','usr_other')")
expect_throw("package export cannot be repointed to an unapproved package",
  "UPDATE package_exports SET package_id='hp_other_draft' WHERE id='px_other'", "approved handoff")
expect_throw("package export update rejects a foreign company package",
  "UPDATE package_exports SET package_id='hp_batbayar' WHERE id='px_other'", "approved handoff")
expect_throw("package export cannot claim external delivery",
  "UPDATE package_exports SET external_delivery_performed=true WHERE id='px_other'")

run("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_complete','cmp_other','cs_other','approve','complete_case','Complete','ready',true)")
run("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_complete','cmp_other','cs_other','act_other_complete','pending','idem-other-complete','rule','2026-07-10T00:00:00Z')")
expect_throw("case completion requires an approved completion action",
  "UPDATE cases SET state='completed' WHERE id='cs_other'", "requires an approved completion action")
run("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:07:00Z' WHERE id='apv_other_complete'")
run("UPDATE cases SET state='completed' WHERE id='cs_other'")
ok("case completes after its approved completion action",
  scalar("SELECT state FROM cases WHERE id='cs_other'")["state"] == "completed")

# Deleting a worker retains the case's tenant and clears only its worker reference.
run("DELETE FROM workers WHERE id='wrk_rahmat'")
deleted_worker_case = scalar("SELECT company_id, worker_id FROM cases WHERE id='cs_rahmat'")
ok("worker delete clears case worker_id only",
  deleted_worker_case["company_id"] == "cmp_greenfood" and deleted_worker_case["worker_id"] is None)
run("DELETE FROM workers WHERE id='wrk_tran'")
deleted_thread_worker_case = scalar("SELECT company_id, worker_id FROM cases WHERE id='cs_tran'")
ok("worker delete retains its case tenant after thread cascades",
  deleted_thread_worker_case["company_id"] == "cmp_greenfood" and deleted_thread_worker_case["worker_id"] is None)
ok("worker delete cascades its thread message interpretation graph",
  scalar("SELECT count(*) AS n FROM interpretations WHERE id='int_tran'")["n"] == 0
  and scalar("SELECT count(*) AS n FROM status_update_proposals WHERE id='sup_tran_contract'")["n"] == 0)

# ---------------------------------------------------------------------------
# 행정사 화이트라벨 v1 (R5.1, 2026-07-20) — ExpertGrant/ExpertOfficeMember/PackageViewLog/
# PiiFieldPolicy. spec: reference/specs/7-1_행정사_화이트라벨_v1.md §2/§6/§9.
# ---------------------------------------------------------------------------

run("""
  INSERT INTO expert_accounts (id, office_name, brand_initial, brand_color, business_registration_no) VALUES
    ('exa_kimlee', '김앤리 행정사무소', 'K', '#2f6fed', '111-22-33333');
  INSERT INTO expert_office_members (id, expert_account_id, name, email, is_office_admin) VALUES
    ('eom_lee', 'exa_kimlee', '이아무개', 'lee@kimlee.example', true);
""")
ok("expert_accounts/expert_office_members insert succeeds", True)

expect_throw(
    "expert grant rejects an unbounded (missing until_date) grant — 결정 C 무기한 금지",
    "INSERT INTO expert_grants (id, expert_account_id, tenant_id, granted_by, from_date, until_date) "
    "VALUES ('exg_bad_null', 'exa_kimlee', 'cmp_greenfood', 'usr_owner', '2026-07-20', NULL)",
)
expect_throw(
    "expert grant rejects until_date not after from_date",
    "INSERT INTO expert_grants (id, expert_account_id, tenant_id, granted_by, from_date, until_date) "
    "VALUES ('exg_bad_range', 'exa_kimlee', 'cmp_greenfood', 'usr_owner', '2026-07-20', '2026-07-20')",
)

run(
    "INSERT INTO expert_grants (id, expert_account_id, tenant_id, granted_by, from_date, until_date) "
    "VALUES ('exg_greenfood', 'exa_kimlee', 'cmp_greenfood', 'usr_owner', '2026-07-20', '2027-07-20')"
)
ok("expert grant insert succeeds with a valid bounded range", True)

expect_throw(
    "expert grant rejects a granter with no membership in the tenant (cross-tenant forgery)",
    "INSERT INTO expert_grants (id, expert_account_id, tenant_id, granted_by, from_date, until_date) "
    "VALUES ('exg_cross_granter', 'exa_kimlee', 'cmp_greenfood', 'usr_other', '2026-07-20', '2027-07-20')",
    "active owner or manager",
)

# 열람 감사 로그 — append-only + tenant/package 복합 FK로 위조(다른 회사 패키지에 로그를
# 붙이는 시도)를 원천 차단한다(spec §6.2, tenant scoping의 최고위험 지점).
run(
    "INSERT INTO package_view_log (id, package_id, tenant_id, expert_office_member_id) "
    "VALUES ('pvl_1', 'hp_batbayar', 'cmp_greenfood', 'eom_lee')"
)
ok("package_view_log insert succeeds", True)
expect_throw("package_view_log UPDATE is blocked", "UPDATE package_view_log SET ip='1.2.3.4' WHERE id='pvl_1'", "append-only")
expect_throw("package_view_log DELETE is blocked", "DELETE FROM package_view_log WHERE id='pvl_1'", "append-only")
expect_throw(
    "package_view_log rejects a package that belongs to a different tenant (cross-tenant log forgery)",
    "INSERT INTO package_view_log (id, package_id, tenant_id, expert_office_member_id) "
    "VALUES ('pvl_cross', 'hp_other', 'cmp_greenfood', 'eom_lee')",
)

run("""
  INSERT INTO pii_field_policies (field, role, exposure) VALUES
    ('HandoffPackage.workerName', 'expert', 'plain'),
    ('HandoffPackage.alienRegistrationNumber', 'expert', 'masked');
""")
ok("pii_field_policies insert succeeds", True)
expect_throw(
    "pii_field_policies rejects a duplicate (field, role) pair",
    "INSERT INTO pii_field_policies (field, role, exposure) VALUES ('HandoffPackage.workerName', 'expert', 'masked')",
)
expect_throw(
    "pii_field_policies rejects an exposure value outside plain/masked/hidden",
    "INSERT INTO pii_field_policies (field, role, exposure) VALUES ('HandoffPackage.phone', 'expert', 'anonymous')",
)

ok("final foreign_key_check has no violations", True)

conn.close()
print(f"\nResult: PASS {passed} / FAIL {failed}")
sys.exit(0 if failed == 0 else 1)
