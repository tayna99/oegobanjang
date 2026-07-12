// SQLite design DDL guardrail verification.
// Run: node db/validate.cjs
const { DatabaseSync } = require('node:sqlite');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const DB_PATH = path.join(DIR, 'oegobanjang_design.sqlite3');

let pass = 0;
let fail = 0;

function ok(name, condition, extra) {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${name}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${name}${extra ? ` — ${extra}` : ''}`);
  }
}

function expectThrow(name, fn, messagePart) {
  try {
    fn();
    fail += 1;
    console.log(`FAIL  ${name} — expected an error`);
  } catch (error) {
    const message = String(error.message || error);
    if (!messagePart || message.includes(messagePart)) {
      pass += 1;
      console.log(`PASS  ${name}`);
    } else {
      fail += 1;
      console.log(`FAIL  ${name} — unexpected error: ${message}`);
    }
  }
}

function scalar(sql) {
  return db.prepare(sql).get();
}

try { fs.unlinkSync(DB_PATH); } catch {}
const db = new DatabaseSync(DB_PATH);

db.exec(fs.readFileSync(path.join(DIR, 'schema.sql'), 'utf8'));
ok('schema.sql executes', true);
ok('foreign_keys is enabled for this connection', scalar('PRAGMA foreign_keys').foreign_keys === 1);

db.exec(fs.readFileSync(path.join(DIR, 'seed_demo.sql'), 'utf8'));
ok('seed_demo.sql executes', true);

const fkViolations = db.prepare('PRAGMA foreign_key_check').all();
ok('foreign_key_check has no violations', fkViolations.length === 0, JSON.stringify(fkViolations));
const integrity = db.prepare('PRAGMA integrity_check').all();
ok('integrity_check is ok', integrity.length === 1 && integrity[0].integrity_check === 'ok');

const tables = scalar("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'");
ok('31 tables after removing package_links', tables.n === 31, `actual=${tables.n}`);
const views = scalar("SELECT count(*) AS n FROM sqlite_master WHERE type='view'");
ok('4 views', views.n === 4, `actual=${views.n}`);
ok('package_links is absent', scalar("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND name='package_links'").n === 0);

const counts = {};
for (const table of [
  'companies', 'users', 'memberships', 'workers', 'citations', 'worker_documents',
  'cases', 'next_actions', 'approvals', 'case_citations', 'evidence_events', 'runs',
  'run_steps', 'drafts', 'draft_variants', 'threads', 'thread_messages',
  'interpretations', 'status_update_proposals', 'handoff_packages', 'package_exports',
  'briefings', 'briefing_items', 'document_requirements',
]) {
  counts[table] = scalar(`SELECT count(*) AS n FROM ${table}`).n;
}
console.log(`  seed counts: ${JSON.stringify(counts)}`);
ok('seed has 6 cases', counts.cases === 6);
ok('seed has 6 workers', counts.workers === 6);
ok('seed has 9 citations', counts.citations === 9);
ok('seed has 10 evidence events', counts.evidence_events === 10);

// Immutable evidence remains enforced.
expectThrow('evidence UPDATE is blocked', () => db.exec("UPDATE evidence_events SET summary='x' WHERE id='ev_4783'"), 'append-only');
expectThrow('evidence DELETE is blocked', () => db.exec("DELETE FROM evidence_events WHERE id='ev_4783'"), 'append-only');

// Seed a second tenant and its valid graph for isolation attacks.
db.exec(`
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
    ('act_other_message', 'cmp_other', 'cs_other', 'approve', 'send_message', 'Approve message', 'ready', 1),
    ('act_other_handoff', 'cmp_other', 'cs_other', 'approve', 'create_handoff', 'Approve handoff', 'ready', 1),
    ('act_other_detail', 'cmp_other', 'cs_other', 'detail', 'other', 'Detail', 'ready', 0);
  INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES
    ('apv_other_message', 'cmp_other', 'cs_other', 'act_other_message', 'pending', 'idem-other-message', 'rule', '2026-07-10T00:00:00Z'),
    ('apv_other_handoff', 'cmp_other', 'cs_other', 'act_other_handoff', 'pending', 'idem-other-handoff', 'rule', '2026-07-10T00:00:00Z');
  INSERT INTO threads (id, company_id, worker_id, channel) VALUES
    ('th_other', 'cmp_other', 'wrk_other', 'zalo');
  INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES
    ('tm_other_inbound', 'cmp_other', 'th_other', 'inbound');
  INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash) VALUES
    ('brf_other', 'cmp_other', '2026-07-10', '2026-07-10T00:00:00Z', 'sha256:other');
`);
ok('second tenant setup succeeds', true);

// Pending approvals may omit a decision idempotency key; a concrete key is still unique.
expectThrow('duplicate pending approval is blocked', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_dup','cmp_greenfood','cs_nguyen','act_nguyen_approve','pending','idem-x','user','2026-07-10T00:00:00Z')"));
db.exec(`
  INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
    ('act_other_idem_a', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Idempotency A', 'ready', 1),
    ('act_other_idem_b', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Idempotency B', 'ready', 1),
    ('act_other_null_a', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Null key A', 'ready', 1),
    ('act_other_null_b', 'cmp_other', 'cs_other', 'approve', 'confirm_status', 'Null key B', 'ready', 1);
  INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES
    ('apv_idem_a', 'cmp_other', 'cs_other', 'act_other_idem_a', 'pending', 'idem-selfcontained-1', 'user', '2026-07-10T00:00:00Z'),
    ('apv_null_a', 'cmp_other', 'cs_other', 'act_other_null_a', 'pending', NULL, 'user', '2026-07-10T00:00:00Z'),
    ('apv_null_b', 'cmp_other', 'cs_other', 'act_other_null_b', 'pending', NULL, 'user', '2026-07-10T00:00:00Z');
`);
expectThrow('idempotency key is unique when present', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_idem_b','cmp_other','cs_other','act_other_idem_b','pending','idem-selfcontained-1','user','2026-07-10T00:00:00Z')"));
ok('pending approvals may share a NULL idempotency key', true);

// Valid same-company child rows give every direct relation an UPDATE target.
db.exec(`
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
`);
ok('same-company direct tenant relations are allowed', true);

// Every direct tenant relation must reject another company's parent record.
expectThrow('worker document rejects foreign worker', () => db.exec(
  "INSERT INTO worker_documents (id, company_id, worker_id, doc_type) VALUES ('wd_cross','cmp_other','wrk_nguyen','passport')"));
expectThrow('worker intake rejects foreign worker', () => db.exec(
  "INSERT INTO worker_intake_files (id, company_id, worker_id, storage_key) VALUES ('wif_cross','cmp_other','wrk_nguyen','uploads/cross.png')"));
expectThrow('case rejects foreign worker', () => db.exec(
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_cross_worker','cmp_other','case_002','wrk_nguyen','other','Cross','LOW','draft')"));
expectThrow('case rejects foreign prepared run', () => db.exec(
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, prepared_run_id) VALUES ('cs_cross_run','cmp_other','case_003','wrk_other','other','Cross run','LOW','draft','run_4788')"));
expectThrow('run rejects foreign case', () => db.exec(
  "INSERT INTO runs (id, company_id, case_id, started_by, agent_name, status) VALUES ('run_cross','cmp_other','cs_nguyen','event','Agent','queued')"));
expectThrow('run step rejects foreign run', () => db.exec(
  "INSERT INTO run_steps (id, company_id, run_id, seq, kind, label) VALUES ('st_cross','cmp_other','run_4788',2,'thinking','Cross step')"));
expectThrow('action rejects foreign case', () => db.exec(
  "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_cross','cmp_other','cs_nguyen','detail','other','Cross','ready',0)"));
expectThrow('approval rejects action from another case', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_case_cross','cmp_greenfood','cs_nguyen','act_batbayar_handoff','pending','idem-case-cross','rule','2026-07-10T00:00:00Z')"));
expectThrow('approval rejects foreign action', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_tenant_cross','cmp_other','cs_other','act_nguyen_approve','pending','idem-tenant-cross','rule','2026-07-10T00:00:00Z')"));
expectThrow('thread rejects foreign worker', () => db.exec(
  "INSERT INTO threads (id, company_id, worker_id, channel) VALUES ('th_cross','cmp_other','wrk_nguyen','zalo')"));
expectThrow('draft rejects foreign case', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status) VALUES ('drf_cross','cmp_other','cs_nguyen','zalo','Cross','draft')"));
expectThrow('draft rejects foreign thread', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, thread_id, channel, purpose, status) VALUES ('drf_cross_thread','cmp_other','cs_other','th_tran','zalo','Cross','draft')"));
expectThrow('draft rejects foreign source run', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, created_by_run_id, channel, purpose, status) VALUES ('drf_cross_run','cmp_other','cs_other','run_4788','zalo','Cross','draft')"));
expectThrow('draft variant rejects foreign draft', () => db.exec(
  "INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES ('dv_cross','cmp_other','drf_nguyen','ko','x')"));
expectThrow('thread message rejects foreign thread', () => db.exec(
  "INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES ('tm_cross','cmp_other','th_tran','inbound')"));
expectThrow('interpretation rejects foreign case', () => db.exec(
  "INSERT INTO interpretations (id, company_id, thread_message_id, case_id, summary_ko, confidence) VALUES ('int_cross','cmp_other','tm_other_inbound','cs_nguyen','x','low')"));
expectThrow('status proposal rejects foreign interpretation', () => db.exec(
  "INSERT INTO status_update_proposals (id, company_id, interpretation_id, target_type, target_key, from_value, to_value) VALUES ('sup_cross','cmp_other','int_tran','worker_document','passport','missing','received')"));
expectThrow('handoff rejects foreign case', () => db.exec(
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status) VALUES ('hp_cross','cmp_other','cs_nguyen','expert_review','{}','draft')"));
expectThrow('briefing item rejects foreign case', () => db.exec(
  "INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank) VALUES ('bi_cross','cmp_other','brf_other','cs_nguyen',1)"));
expectThrow('notification rejects foreign case', () => db.exec(
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, case_id) VALUES ('nt_cross','cmp_other','usr_other','N01','P1','x','x','/','cross','push','cs_nguyen')"));
expectThrow('worker document update rejects foreign worker', () => db.exec(
  "UPDATE worker_documents SET worker_id='wrk_nguyen' WHERE id='wd_other_valid'"));
expectThrow('worker intake update rejects foreign worker', () => db.exec(
  "UPDATE worker_intake_files SET worker_id='wrk_nguyen' WHERE id='wif_other_valid'"));
expectThrow('case update rejects foreign worker', () => db.exec(
  "UPDATE cases SET worker_id='wrk_nguyen' WHERE id='cs_other'"));
expectThrow('case update rejects foreign assignee', () => db.exec(
  "UPDATE cases SET assignee_user_id='usr_kim' WHERE id='cs_other'"));
expectThrow('run update rejects foreign case', () => db.exec(
  "UPDATE runs SET case_id='cs_nguyen' WHERE id='run_other'"));
expectThrow('run update rejects foreign starter', () => db.exec(
  "UPDATE runs SET started_by_user_id='usr_kim' WHERE id='run_other'"));
expectThrow('run step update rejects foreign run', () => db.exec(
  "UPDATE run_steps SET run_id='run_4788' WHERE id='st_other_valid'"));
expectThrow('action update rejects foreign case', () => db.exec(
  "UPDATE next_actions SET case_id='cs_nguyen' WHERE id='act_other_detail'"));
expectThrow('thread update rejects foreign worker', () => db.exec(
  "UPDATE threads SET worker_id='wrk_nguyen' WHERE id='th_other'"));
expectThrow('draft update rejects foreign case', () => db.exec(
  "UPDATE drafts SET case_id='cs_nguyen' WHERE id='drf_other_update'"));
expectThrow('draft variant update rejects another company parent', () => db.exec(
  "UPDATE draft_variants SET company_id='cmp_greenfood' WHERE id='dv_other_update'"));
expectThrow('thread message update rejects foreign thread', () => db.exec(
  "UPDATE thread_messages SET thread_id='th_tran' WHERE id='tm_other_inbound'"));
expectThrow('interpretation update rejects foreign message', () => db.exec(
  "UPDATE interpretations SET thread_message_id='tm_tran_reply' WHERE id='int_other_valid'"));
expectThrow('status proposal update rejects foreign interpretation', () => db.exec(
  "UPDATE status_update_proposals SET interpretation_id='int_tran' WHERE id='sup_other_valid'"));
expectThrow('handoff update rejects foreign case', () => db.exec(
  "UPDATE handoff_packages SET case_id='cs_nguyen' WHERE id='hp_other_update'"));
expectThrow('briefing item update rejects foreign case', () => db.exec(
  "UPDATE briefing_items SET case_id='cs_nguyen' WHERE id='bi_other_valid'"));
expectThrow('notification update rejects foreign case', () => db.exec(
  "UPDATE notifications SET case_id='cs_nguyen' WHERE id='nt_other_valid'"));
expectThrow('csv import update rejects foreign uploader', () => db.exec(
  "UPDATE csv_imports SET uploaded_by_user_id='usr_kim' WHERE id='csv_other_valid'"));
expectThrow('autonomy grant update rejects foreign owner', () => db.exec(
  "UPDATE autonomy_grants SET consented_by_user_id='usr_kim' WHERE id='ag_other_valid'"));
expectThrow('delegation update rejects foreign delegate', () => db.exec(
  "UPDATE delegations SET delegate_user_id='usr_kim' WHERE id='del_other_valid'"));
expectThrow('membership update rejects foreign inviter', () => db.exec(
  "UPDATE memberships SET invited_by='usr_kim' WHERE id='mbr_other_valid_invite'"));
expectThrow('tenant table rejects user without membership', () => db.exec(
  "INSERT INTO csv_imports (id, company_id, uploaded_by_user_id, filename) VALUES ('csv_orphan','cmp_other','usr_orphan','x.csv')"));
expectThrow('tenant table rejects inactive membership user', () => db.exec(
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel) VALUES ('nt_invited','cmp_other','usr_invited','N01','P1','x','x','/','invited','push')"), 'active member');
expectThrow('case rejects an assignee without membership', () => db.exec(
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, assignee_user_id) VALUES ('cs_bad_assignee','cmp_other','case_002','wrk_other','other','Bad assignee','LOW','draft','usr_orphan')"));
expectThrow('run rejects a starter without membership', () => db.exec(
  "INSERT INTO runs (id, company_id, case_id, started_by, started_by_user_id, agent_name, status) VALUES ('run_bad_starter','cmp_other','cs_other','user','usr_orphan','Agent','queued')"));
expectThrow('membership rejects an inviter without membership', () => db.exec(
  "INSERT INTO memberships (id, company_id, role, status, invited_by) VALUES ('mbr_bad_inviter','cmp_other','viewer','invited','usr_orphan')"));
expectThrow('delegation requires an active owner', () => db.exec(
  "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, starts_at, ends_at) VALUES ('del_bad_role','cmp_other','usr_other_manager','usr_other','2026-07-10T00:00:00Z','2026-07-11T00:00:00Z')"), 'delegation members');
expectThrow('interpretation rejects an inactive confirmer', () => db.exec(
  "INSERT INTO interpretations (id, company_id, thread_message_id, summary_ko, confidence, status, confirmed_by_user_id) VALUES ('int_bad_confirmer','cmp_other','tm_other_inbound','x','low','confirmed','usr_invited')"), 'active member');
expectThrow('autonomy consent requires an active owner', () => db.exec(
  "INSERT INTO autonomy_grants (id, company_id, case_type, level, consented_by_user_id, consented_at) VALUES ('ag_bad_owner','cmp_other','other','L2','usr_other_manager','2026-07-10T00:00:00Z')"), 'active owner');
db.exec("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_expert_ok','cmp_other','expert','usr_other_expert','format_preference','Uses structured checklists')");
ok('agent note accepts an active same-company expert', true);
expectThrow('agent note rejects an expert from another company', () => db.exec(
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_expert_cross','cmp_other','expert','usr_kim','format_preference','x')"), 'same company');
db.exec("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_worker_ok','cmp_other','worker','wrk_other','response_pattern','Uses concise replies')");
db.exec("INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_company_ok','cmp_other','company','cmp_other','format_preference','Uses internal checklists')");
expectThrow('agent note rejects a worker from another company', () => db.exec(
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_worker_cross','cmp_other','worker','wrk_nguyen','response_pattern','x')"), 'same company');
expectThrow('agent note rejects another company subject', () => db.exec(
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('note_company_cross','cmp_other','company','cmp_greenfood','format_preference','x')"), 'same company');
expectThrow('agent note update rejects a worker from another company', () => db.exec(
  "UPDATE agent_notes SET subject_id='wrk_nguyen' WHERE id='note_worker_ok'"), 'same company');
expectThrow('case cannot begin in a human-approved state', () => db.exec(
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_bad_terminal','cmp_other','case_003','wrk_other','other','Bad terminal','LOW','human_approved')"), 'must begin');

// Citation scope: global and own-company citations are valid; foreign internal citations are not.
db.exec("INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) VALUES ('cit_other_internal','cmp_other','A','internal','Other internal','other','2026-07-10T00:00:00Z')");
db.exec("INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES ('cit_global_ok','A','official','Global','official','2026-07-10T00:00:00Z')");
expectThrow('global citations cannot be internal evidence', () => db.exec(
  "INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES ('cit_global_internal','A','internal','Bad global','x','2026-07-10T00:00:00Z')"));
db.exec("INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) VALUES ('cit_company_scoped','cmp_other','A','official','Scoped local','x','2026-07-10T00:00:00Z')");
ok('company-specific citations stay out of the global view', scalar("SELECT count(*) AS n FROM v_global_usable_citations WHERE id='cit_company_scoped'").n === 0);
db.exec("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_other','cs_other','cit_other_internal','user')");
db.exec("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_other','cs_other','cit_global_ok','user')");
db.exec("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_greenfood','cs_nguyen','cit_global_ok','user')");
ok('same-company and global citations are allowed', true);
expectThrow('case rejects foreign internal citation', () => db.exec(
  "INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp_greenfood','cs_nguyen','cit_other_internal','user')"), 'same company');
expectThrow('case citation update rejects a foreign case', () => db.exec(
  "UPDATE case_citations SET case_id='cs_nguyen' WHERE company_id='cmp_other' AND case_id='cs_other' AND citation_id='cit_other_internal'"));
expectThrow('global document requirement rejects internal citation', () => db.exec(
  "INSERT INTO document_requirements (id, case_type, visa_type, required_doc, citation_id) VALUES ('req_private','other','E-9','private','cit_other_internal')"), 'must be global');
db.exec("INSERT INTO document_requirements (id, case_type, visa_type, required_doc, citation_id) VALUES ('req_global_update','other','E-9','global-only','cit_global_ok')");
expectThrow('global document requirement cannot be updated to an internal citation', () => db.exec(
  "UPDATE document_requirements SET citation_id='cit_other_internal' WHERE id='req_global_update'"), 'must be global');
expectThrow('a global citation cannot be re-scoped to a company', () => db.exec(
  "UPDATE citations SET company_id='cmp_greenfood' WHERE id='cit_global_ok'"), 'scope is immutable');
expectThrow('an internal citation cannot be promoted to global', () => db.exec(
  "UPDATE citations SET company_id=NULL WHERE id='cit_other_internal'"), 'scope is immutable');
ok('unscoped usable citation view is absent', scalar("SELECT count(*) AS n FROM sqlite_master WHERE type='view' AND name='v_usable_citations'").n === 0);
ok('global usable citation view hides internal citations', scalar('SELECT count(*) AS n FROM v_global_usable_citations WHERE company_id IS NOT NULL').n === 0);
ok('citation links are company scoped', scalar("SELECT linked_case_count FROM v_citation_link_counts WHERE company_id='cmp_other' AND citation_id='cit_other_internal'").linked_case_count === 1);
const globalCitationCounts = db.prepare("SELECT company_id, linked_case_count FROM v_citation_link_counts WHERE citation_id='cit_global_ok' ORDER BY company_id").all();
ok('shared global citation counts are separated by company', globalCitationCounts.length === 2 && globalCitationCounts.every((row) => row.linked_case_count === 1), JSON.stringify(globalCitationCounts));

// MVP delivery cannot be represented as a completed outbound action.
expectThrow('notification sent status is blocked', () => db.exec(
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_sent','cmp_other','usr_other','N01','P1','x','x','/','sent','push','sent')"));
expectThrow('notification delivered status is blocked', () => db.exec(
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_delivered','cmp_other','usr_other','N01','P1','x','x','/','delivered','push','delivered')"));
expectThrow('notification failed status is blocked', () => db.exec(
  "INSERT INTO notifications (id, company_id, recipient_user_id, type, priority, title, body, deeplink_path, dedupe_key, channel, status) VALUES ('nt_failed','cmp_other','usr_other','N01','P1','x','x','/','failed','push','failed')"));
expectThrow('outbound thread message is blocked', () => db.exec(
  "INSERT INTO thread_messages (id, company_id, thread_id, direction) VALUES ('tm_outbound','cmp_other','th_other','outbound')"));
expectThrow('notification_sent evidence type is blocked', () => db.exec(
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary) VALUES ('ev_notification_sent','cmp_other',1,'notification_sent','2026-07-10T00:00:00Z','system','x')"));
ok('thread_messages has no sent_at column', !db.prepare("PRAGMA table_info(thread_messages)").all().some((column) => column.name === 'sent_at'));
ok('notifications has no delivery timestamp columns', !db.prepare("PRAGMA table_info(notifications)").all().some((column) => column.name === 'sent_at' || column.name === 'delivered_at'));
expectThrow('evidence rejects an action and approval from another case', () => db.exec(
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, case_id, action_id, approval_id, actor_type, summary) VALUES ('ev_bad_context','cmp_greenfood',9999,'approval_requested','2026-07-10T00:00:00Z','cs_nguyen','act_batbayar_handoff','apv_batbayar_export','system','x')"), 'must match its case');

// Approval state is explicit, scoped, and single-transition.
expectThrow('approval must start pending', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, decided_by_user_id, identity_method, requested_at, decided_at) VALUES ('apv_direct_terminal','cmp_other','cs_other','act_other_message','approved','idem-direct-terminal','rule','usr_other','pin','2026-07-10T00:00:00Z','2026-07-10T00:05:00Z')"), 'must start pending');
expectThrow('pending approval cannot carry decision metadata', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, decided_by_user_id, identity_method, requested_at, decided_at) VALUES ('apv_pending_metadata','cmp_other','cs_other','act_other_message','pending','idem-pending-metadata','rule','usr_other','pin','2026-07-10T00:00:00Z','2026-07-10T00:05:00Z')"));
expectThrow('approval cannot target non-approval action', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_detail','cmp_other','cs_other','act_other_detail','pending','idem-detail','rule','2026-07-10T00:00:00Z')"), 'must require approval');
expectThrow('required action cannot disable approval', () => db.exec(
  "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_bad_required','cmp_other','cs_other','approve','send_message','Bad','ready',0)"));
for (const actionType of ['create_handoff', 'export_package', 'complete_case']) {
  expectThrow(`${actionType} action cannot disable approval`, () => db.exec(
    `INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_bad_${actionType}','cmp_other','cs_other','approve','${actionType}','Bad','ready',0)`));
}
expectThrow('required action cannot be changed to bypass approval', () => db.exec(
  "UPDATE next_actions SET action_type='send_message' WHERE id='act_other_detail'"));
db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_owner_only','cmp_other','cs_other','approve','confirm_status','Approve','ready',1)");
db.exec("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_owner_only','cmp_other','cs_other','act_other_owner_only','pending','idem-manager-owner-only','rule','2026-07-10T00:00:00Z')");
expectThrow('approval decider must satisfy the owner-only policy', () => db.exec(
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_manager_owner_only'"), 'not allowed by company policy');
db.exec("UPDATE companies SET approval_policy='manager_allowed' WHERE id='cmp_other'");
db.exec("INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES ('cs_other_medium','cmp_other','case_004','wrk_other','other','Medium case','MEDIUM','draft')");
db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_medium','cmp_other','cs_other_medium','approve','send_message','Approve','ready',1)");
db.exec("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_manager_medium','cmp_other','cs_other_medium','act_other_medium','pending','idem-manager-medium','rule','2026-07-10T00:00:00Z')");
expectThrow('manager cannot approve a medium-risk case', () => db.exec(
  "UPDATE approvals SET status='approved', decided_by_user_id='usr_other_manager', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_manager_medium'"), 'not allowed by company policy');
db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_reject','cmp_other','cs_other','approve','confirm_status','Reject','ready',1)");
db.exec("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_reject','cmp_other','cs_other','act_other_reject','pending','idem-other-reject','rule','2026-07-10T00:00:00Z')");
expectThrow('rejected approval requires a reason', () => db.exec(
  "UPDATE approvals SET status='rejected', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_other_reject'"));
expectThrow('pending approval cannot become approved without identity', () => db.exec(
  "UPDATE approvals SET status='approved' WHERE id='apv_other_handoff'"));
expectThrow('an approval action contract cannot change after a request exists', () => db.exec(
  "UPDATE next_actions SET action_type='other' WHERE id='act_other_handoff'"), 'action contract is immutable');
db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_nguyen_retarget','cmp_greenfood','cs_nguyen','approve','create_handoff','Retarget','ready',1)");
expectThrow('linked approval cannot be retargeted to a different required action', () => db.exec(
  "UPDATE approvals SET action_id='act_nguyen_retarget' WHERE id='apv_nguyen'"), 'approval target is immutable');
expectThrow('case rejects a transition outside its state machine', () => db.exec(
  "UPDATE cases SET state='risk_review' WHERE id='cs_nguyen'"), 'state transition is not allowed');
db.exec("UPDATE cases SET state='risk_review' WHERE id='cs_other'");
db.exec("UPDATE cases SET state='approval_pending' WHERE id='cs_other'");
expectThrow('case cannot become human-approved while approval is pending', () => db.exec(
  "UPDATE cases SET state='human_approved' WHERE id='cs_other'"), 'requires an approved case action');
expectThrow('blocked case state cannot be reopened', () => db.exec(
  "UPDATE cases SET state='risk_review' WHERE id='cs_batbayar'"), 'terminal case state');
db.exec("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:05:00Z' WHERE id='apv_other_message'");
ok('pending approval can become approved with identity', scalar("SELECT status FROM approvals WHERE id='apv_other_message'").status === 'approved');
expectThrow('terminal approval cannot be re-decided', () => db.exec(
  "UPDATE approvals SET status='rejected', reason='later' WHERE id='apv_other_message'"), 'terminal approval');
expectThrow('terminal approval cannot be deleted', () => db.exec(
  "DELETE FROM approvals WHERE id='apv_other_message'"), 'terminal approval');
db.exec("UPDATE cases SET state='human_approved' WHERE id='cs_other'");
ok('case becomes human-approved only after its approved action', scalar("SELECT state FROM cases WHERE id='cs_other'").state === 'human_approved');
expectThrow('draft rejects an approval from another company', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_foreign_approval','cmp_other','cs_other','zalo','x','pending_approval','apv_nguyen')"));
expectThrow('draft rejects an approval from another case', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other_case_approval','cmp_other','cs_other_medium','zalo','x','pending_approval','apv_other_message')"));
expectThrow('draft update rejects an approval from another company', () => db.exec(
  "UPDATE drafts SET status='pending_approval', approval_id='apv_nguyen' WHERE id='drf_other_update'"));
expectThrow('handoff rejects an approval from another company', () => db.exec(
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_foreign_approval','cmp_other','cs_other','expert_review','{}','pending_approval','apv_nguyen')"));
expectThrow('handoff rejects an approval from another case', () => db.exec(
  "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_other_case_approval','cmp_other','cs_other_medium','expert_review','{}','pending_approval','apv_other_handoff')"));
expectThrow('handoff update rejects an approval from another company', () => db.exec(
  "UPDATE handoff_packages SET status='pending_approval', approval_id='apv_nguyen' WHERE id='hp_other_update'"));
expectThrow('draft needs a matching message approval state', () => db.exec(
  "INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_bad','cmp_other','cs_other','zalo','x','pending_approval','apv_other_handoff')"), 'matching message approval');
db.exec("INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other','cmp_other','cs_other','zalo','x','approved','apv_other_message')");
ok('draft accepts its approved message approval', true);
expectThrow('pending draft content cannot change before a new revision', () => db.exec(
  "UPDATE drafts SET purpose='changed' WHERE id='drf_nguyen'"), 'draft content is locked');
expectThrow('pending draft variants cannot change before a new revision', () => db.exec(
  "UPDATE draft_variants SET text='changed' WHERE id='dv_nguyen_ko'"), 'editable draft');
db.exec("UPDATE approvals SET status='approved', decided_by_user_id='usr_owner', identity_method='pin', decided_at='2026-07-10T00:08:00Z' WHERE id='apv_nguyen'");
ok('approved approval automatically updates its linked draft', scalar("SELECT status FROM drafts WHERE id='drf_nguyen'").status === 'approved');
expectThrow('approved draft cannot receive a new variant', () => db.exec(
  "INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES ('dv_other_late','cmp_other','drf_other','ko','changed')"), 'editable draft');
db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_reject_message','cmp_other','cs_other','approve','send_message','Reject message','ready',1)");
db.exec("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_reject_message','cmp_other','cs_other','act_other_reject_message','pending','idem-other-reject-message','rule','2026-07-10T00:00:00Z')");
db.exec("INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, approval_id) VALUES ('drf_other_reject','cmp_other','cs_other','zalo','x','pending_approval','apv_other_reject_message')");
db.exec("UPDATE approvals SET status='rejected', decided_by_user_id='usr_other', identity_method='pin', reason='Needs revision', decided_at='2026-07-10T00:08:00Z' WHERE id='apv_other_reject_message'");
ok('rejected approval automatically updates its linked draft', scalar("SELECT status FROM drafts WHERE id='drf_other_reject'").status === 'rejected');
db.exec("INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status, approval_id) VALUES ('hp_other','cmp_other','cs_other','expert_review','{}','pending_approval','apv_other_handoff')");
expectThrow('package export needs an approved handoff', () => db.exec(
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_pending','hp_other','cmp_other','pdf','sha256:x','usr_other')"), 'approved handoff');
expectThrow('pending handoff package content cannot change', () => db.exec(
  "UPDATE handoff_packages SET included_items='[]' WHERE id='hp_other'"), 'handoff package content is locked');
db.exec("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:06:00Z' WHERE id='apv_other_handoff'");
ok('approved approval automatically updates its linked handoff package', scalar("SELECT status FROM handoff_packages WHERE id='hp_other'").status === 'approved');
expectThrow('approved handoff package content cannot change', () => db.exec(
  "UPDATE handoff_packages SET package_type='pre_entry' WHERE id='hp_other'"), 'handoff package content is locked');
db.exec("INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, status) VALUES ('hp_other_draft','cmp_other','cs_other','expert_review','{}','draft')");
expectThrow('package export rejects an inactive exporter', () => db.exec(
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_inactive','hp_other','cmp_other','pdf','sha256:x','usr_invited')"), 'active member');
db.exec("INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_other','hp_other','cmp_other','pdf','sha256:other','usr_other')");
ok('approved handoff package accepts an internal PDF export', true);
expectThrow('package export rejects non-PDF formats', () => db.exec(
  "INSERT INTO package_exports (id, package_id, company_id, format, content_hash, exported_by_user_id) VALUES ('px_link','hp_other','cmp_other','link','sha256:link','usr_other')"));
expectThrow('package export cannot be repointed to an unapproved package', () => db.exec(
  "UPDATE package_exports SET package_id='hp_other_draft' WHERE id='px_other'"), 'approved handoff');
expectThrow('package export update rejects a foreign company package', () => db.exec(
  "UPDATE package_exports SET package_id='hp_batbayar' WHERE id='px_other'"), 'approved handoff');
expectThrow('package export cannot claim external delivery', () => db.exec(
  "UPDATE package_exports SET external_delivery_performed=1 WHERE id='px_other'"));

db.exec("INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES ('act_other_complete','cmp_other','cs_other','approve','complete_case','Complete','ready',1)");
db.exec("INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_other_complete','cmp_other','cs_other','act_other_complete','pending','idem-other-complete','rule','2026-07-10T00:00:00Z')");
expectThrow('case completion requires an approved completion action', () => db.exec(
  "UPDATE cases SET state='completed' WHERE id='cs_other'"), 'requires an approved completion action');
db.exec("UPDATE approvals SET status='approved', decided_by_user_id='usr_other', identity_method='pin', decided_at='2026-07-10T00:07:00Z' WHERE id='apv_other_complete'");
db.exec("UPDATE cases SET state='completed' WHERE id='cs_other'");
ok('case completes after its approved completion action', scalar("SELECT state FROM cases WHERE id='cs_other'").state === 'completed');

// Deleting a worker retains the case's tenant and clears only its worker reference.
db.exec("DELETE FROM workers WHERE id='wrk_rahmat'");
const deletedWorkerCase = scalar("SELECT company_id, worker_id FROM cases WHERE id='cs_rahmat'");
ok('worker delete clears case worker_id only', deletedWorkerCase.company_id === 'cmp_greenfood' && deletedWorkerCase.worker_id === null);
db.exec("DELETE FROM workers WHERE id='wrk_tran'");
const deletedThreadWorkerCase = scalar("SELECT company_id, worker_id FROM cases WHERE id='cs_tran'");
ok('worker delete retains its case tenant after thread cascades', deletedThreadWorkerCase.company_id === 'cmp_greenfood' && deletedThreadWorkerCase.worker_id === null);
ok('worker delete cascades its thread message interpretation graph', scalar("SELECT count(*) AS n FROM interpretations WHERE id='int_tran'").n === 0 && scalar("SELECT count(*) AS n FROM status_update_proposals WHERE id='sup_tran_contract'").n === 0);

const finalFkViolations = db.prepare('PRAGMA foreign_key_check').all();
ok('final foreign_key_check has no violations', finalFkViolations.length === 0, JSON.stringify(finalFkViolations));

db.close();
console.log(`\nResult: PASS ${pass} / FAIL ${fail}`);
process.exit(fail === 0 ? 0 : 1);
