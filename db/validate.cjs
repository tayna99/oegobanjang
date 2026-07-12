// db/schema.sql + seed_demo.sql 실행 검증 — docs/DB_SCHEMA.md §5 가드레일이 스키마에서
// 실제로 강제되는지 확인한다. 실행: node --experimental-sqlite db/validate.cjs
// (Node 23.4+는 플래그 불필요. DB 파일을 새로 만들므로 기존 탐색 데이터는 사라진다.)
const { DatabaseSync } = require('node:sqlite');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const DB_PATH = path.join(DIR, 'oegobanjang_design.sqlite3');

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('PASS  ' + name); }
  else { fail++; console.log('FAIL  ' + name + (extra ? ' — ' + extra : '')); }
}
function expectThrow(name, fn, msgPart) {
  try { fn(); fail++; console.log('FAIL  ' + name + ' — 에러가 나야 하는데 통과됨'); }
  catch (e) {
    const m = String(e.message || e);
    if (!msgPart || m.includes(msgPart)) { pass++; console.log('PASS  ' + name); }
    else { fail++; console.log('FAIL  ' + name + ' — 다른 에러: ' + m); }
  }
}

try { fs.unlinkSync(DB_PATH); } catch {}
const db = new DatabaseSync(DB_PATH);

// 1. 스키마 실행
db.exec(fs.readFileSync(path.join(DIR, 'schema.sql'), 'utf8'));
ok('schema.sql 전체 실행', true);

// 2. 시드 실행
db.exec(fs.readFileSync(path.join(DIR, 'seed_demo.sql'), 'utf8'));
ok('seed_demo.sql 전체 실행', true);

// 3. 무결성
const fkViolations = db.prepare('PRAGMA foreign_key_check').all();
ok('foreign_key_check 위반 0건', fkViolations.length === 0, JSON.stringify(fkViolations));
const integ = db.prepare('PRAGMA integrity_check').all();
ok('integrity_check ok', integ.length === 1 && integ[0].integrity_check === 'ok');

// 4. 테이블 32개 + 뷰 4개 (docs/DB_SCHEMA.md §4·§6)
const tables = db.prepare("SELECT count(*) n FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").get();
ok('테이블 32개', tables.n === 32, 'actual=' + tables.n);
const views = db.prepare("SELECT count(*) n FROM sqlite_master WHERE type='view'").get();
ok('뷰 4개', views.n === 4, 'actual=' + views.n);

// 5. 시드 카운트
const counts = {};
for (const t of ['companies','users','memberships','workers','citations','worker_documents','cases','next_actions','approvals','case_citations','evidence_events','runs','run_steps','drafts','draft_variants','threads','thread_messages','interpretations','status_update_proposals','handoff_packages','package_exports','briefings','briefing_items','document_requirements']) {
  counts[t] = db.prepare('SELECT count(*) n FROM ' + t).get().n;
}
console.log('  seed counts: ' + JSON.stringify(counts));
ok('케이스 6건', counts.cases === 6);
ok('근로자 6명', counts.workers === 6);
ok('근거 9건', counts.citations === 9);
ok('판단 기록 10건', counts.evidence_events === 10);

// 6. append-only 트리거 (§5.2)
expectThrow('evidence UPDATE 차단', () => db.exec("UPDATE evidence_events SET summary='x' WHERE id='ev_4783'"), 'append-only');
expectThrow('evidence DELETE 차단', () => db.exec("DELETE FROM evidence_events WHERE id='ev_4783'"), 'append-only');

// 7. MVP 발송 차단 CHECK (§5.4)
expectThrow('drafts.sent_at CHECK', () => db.exec("UPDATE drafts SET sent_at='2026-07-11T00:00:00Z' WHERE id='drf_nguyen'"));
expectThrow('handoff.transferred_at CHECK', () => db.exec("UPDATE handoff_packages SET transferred_at='2026-07-11T00:00:00Z' WHERE id='hp_batbayar'"));
expectThrow('package_exports 외부전송 CHECK', () => db.exec("UPDATE package_exports SET external_delivery_performed=1 WHERE id='px_batbayar_0031'"));

// 8. 승인 가드레일: 액션당 pending 1건 + idempotency 유니크 (§4.3)
// pending 승인(apv_nguyen)의 idempotency_key는 NULL이다(decide() 전이라 아직 없음) —
// 아래는 시드 값에 기대지 않는 자기완결형 검증(2026-07-12 정정).
expectThrow('중복 pending 승인 차단', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_dup','cmp_greenfood','cs_nguyen','act_nguyen_approve','pending','idem-x','user','2026-07-10T00:00:00Z')"));
db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at, decided_at) VALUES ('apv_idem_a','cmp_greenfood','cs_tran','act_tran_confirm','approved','idem-selfcontained-1','user','2026-07-10T00:00:00Z','2026-07-10T00:05:00Z')");
expectThrow('idempotency_key 중복 차단(자기완결형)', () => db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_idem_b','cmp_greenfood','cs_rahmat','act_rahmat_confirm','pending','idem-selfcontained-1','user','2026-07-10T00:00:00Z')"));
db.exec(
  "INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key, requested_by_actor, requested_at) VALUES ('apv_null_a','cmp_greenfood','cs_oyunaa','act_oyunaa_confirm','pending', NULL, 'user','2026-07-10T00:00:00Z')");
ok('idempotency_key NULL은 서로 충돌하지 않음(3번째 NULL도 삽입 허용)', true);

// 9. 케이스 재사용 규칙 — 열린 케이스 중복 방지 (§4.3)
expectThrow('열린 케이스 중복 생성 차단', () => db.exec(
  "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES ('cs_dup','cmp_greenfood','case_099','wrk_nguyen','visa_expiry','중복','HIGH','draft','2026-08-09')"));
db.exec("INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES ('cs_dup_ok','cmp_greenfood','case_098','wrk_nguyen','visa_expiry','과거 완료본','HIGH','completed','2026-08-09')");
ok('종결 상태 중복은 허용(부분 유니크)', true);
db.exec("DELETE FROM cases WHERE id='cs_dup_ok'");

// 10. enum CHECK
expectThrow('잘못된 case state 차단', () => db.exec("UPDATE cases SET state='shipped' WHERE id='cs_nguyen'"));
expectThrow('잘못된 evidence type 차단', () => db.exec(
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary) VALUES ('ev_bad','cmp_greenfood',9999,'oops','2026-07-10T00:00:00Z','system','x')"));
expectThrow('agent_notes 금지 카테고리 차단', () => db.exec(
  "INSERT INTO agent_notes (id, company_id, subject_type, subject_id, category, note) VALUES ('an_bad','cmp_greenfood','worker','wrk_nguyen','diligence_score','성실도 높음')"));

// 11. returned 상태 수용 (§5.1)
db.exec("UPDATE cases SET state='returned' WHERE id='cs_nguyen'");
db.exec("UPDATE cases SET state='approval_pending' WHERE id='cs_nguyen'");
ok('returned 상태 수용', db.prepare("SELECT state FROM cases WHERE id='cs_nguyen'").get().state === 'approval_pending');

// 12. 파생 뷰 (§6)
const der = db.prepare("SELECT * FROM v_case_derived WHERE case_id='cs_nguyen'").get();
ok('v_case_derived: nguyen 누락 서류 2건', der.missing_doc_count === 2, JSON.stringify(der));
ok('v_case_derived: nguyen 사용 가능 근거 3건', der.usable_citation_count === 3, JSON.stringify(der));
db.exec("INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES ('cit_f01','F','internal','합성 데모 근거','내부','2026-07-10T00:00:00Z')");
db.exec("INSERT INTO case_citations (case_id, citation_id, added_by_actor) VALUES ('cs_nguyen','cit_f01','user')");
const der2 = db.prepare("SELECT usable_citation_count FROM v_case_derived WHERE case_id='cs_nguyen'").get();
ok('F등급은 usable 근거에서 제외', der2.usable_citation_count === 3, 'actual=' + der2.usable_citation_count);
const usable = db.prepare("SELECT count(*) n FROM v_usable_citations WHERE id='cit_f01'").get();
ok('v_usable_citations에 F등급 없음', usable.n === 0);
const links = db.prepare("SELECT linked_case_count FROM v_citation_link_counts WHERE citation_id='cit_004'").get();
ok('v_citation_link_counts: cit_004 연계 2건(siti·tran)', links.linked_case_count === 2, JSON.stringify(links));
const pipe = db.prepare("SELECT stage, case_count FROM v_pipeline_counts WHERE company_id='cmp_greenfood' ORDER BY stage").all();
console.log('  pipeline: ' + JSON.stringify(pipe));
ok('파이프라인 집계 산출', pipe.length >= 3);
// 검증용 F등급 데이터 원복 — 탐색 시 혼동 방지
db.exec("DELETE FROM case_citations WHERE citation_id='cit_f01'");
db.exec("DELETE FROM citations WHERE id='cit_f01'");

// 13. event_no 회사 내 유니크 (§9)
expectThrow('event_no 회사 내 중복 차단', () => db.exec(
  "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary) VALUES ('ev_dup','cmp_greenfood',4789,'risk_flagged','2026-07-10T00:00:00Z','system','x')"));

db.close();
console.log('');
console.log('결과: PASS ' + pass + ' / FAIL ' + fail);
process.exit(fail === 0 ? 0 : 1);
