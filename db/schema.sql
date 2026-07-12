-- ============================================================================
-- 외고반장 서비스 DB — 실행 가능 DDL (SQLite)
-- 정본 문서: docs/DB_SCHEMA.md (2026-07-12) — 이 파일은 그 문서 §4를 그대로 내린 것.
-- 스키마를 바꾸려면 문서와 이 파일을 같은 PR에서 함께 고친다.
--
-- 사용법: db/README.md 참조 (DBeaver에서 새 SQLite DB에 이 스크립트 실행).
-- 주의: FK 강제는 연결 옵션 — 실행 세션마다 PRAGMA foreign_keys=ON 필요.
--
-- 표기 규약
--  * id           : UUIDv7 문자열(앱 발급). 데모 시드는 가독성을 위해 슬러그 사용
--  * TIMESTAMPTZ  : ISO8601 UTC 문자열 저장(SQLite), PG 전환 시 timestamptz
--  * BOOLEAN      : 0/1 + CHECK
--  * JSON         : TEXT + json_valid CHECK (PG 전환 시 JSONB)
--  * 파생값(dDay·완성도·KPI)은 컬럼이 없다 — 문서 §6, 말미 뷰 참조
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 4.1 테넌트·계정
-- ---------------------------------------------------------------------------

CREATE TABLE companies (
  id                 TEXT PRIMARY KEY,
  name               TEXT NOT NULL,
  business_number    TEXT,
  industry           TEXT,
  region             TEXT,
  worker_count_band  TEXT NOT NULL DEFAULT '5_20'
                     CHECK (worker_count_band IN ('lt5','5_20','20_50','gt50')),
  timezone           TEXT NOT NULL DEFAULT 'Asia/Seoul',
  briefing_time      TEXT NOT NULL DEFAULT '08:30',
  approval_policy    TEXT NOT NULL DEFAULT 'owner_only'
                     CHECK (approval_policy IN ('owner_only','manager_allowed')),
  autonomy_level     TEXT NOT NULL DEFAULT 'L2' CHECK (autonomy_level IN ('L1','L2','L3')),
  onboarding_step    TEXT NOT NULL DEFAULT 'O1'
                     CHECK (onboarding_step IN ('O1','O2','O3','O4','O5','done')),
  onboarding_path    TEXT CHECK (onboarding_path IN ('ocr','manual','csv','agency')),
  case_seq           INTEGER NOT NULL DEFAULT 0,  -- case_code 발급 카운터(§9)
  evidence_seq       INTEGER NOT NULL DEFAULT 0,  -- 판단 기록 번호(#NNNN) 발급 카운터(§9)
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
  id                    TEXT PRIMARY KEY,
  phone                 TEXT NOT NULL UNIQUE,      -- 로그인 식별자(O1). PII — 표시 시 마스킹
  name                  TEXT NOT NULL,             -- evidence actor 표시에 사용
  email                 TEXT,
  pin_hash              TEXT,                      -- 승인 본인확인 PIN(7단계 §4) — 해시만
  biometric_registered  BOOLEAN NOT NULL DEFAULT 0 CHECK (biometric_registered IN (0,1)),
  terms_agreed_at       TIMESTAMPTZ NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE memberships (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  user_id            TEXT REFERENCES users(id),   -- 초대 수락 전 NULL
  role               TEXT NOT NULL CHECK (role IN ('owner','manager','viewer','expert')),
  status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('invited','active','removed')),
  invite_phone       TEXT,
  invite_token       TEXT UNIQUE,
  invite_expires_at  TIMESTAMPTZ,                 -- 초대 링크 만료 7일(3단계 §6)
  invited_by         TEXT REFERENCES users(id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, user_id)
);
CREATE INDEX ix_memberships_company ON memberships (company_id, role);

-- 승인 위임(7단계 §3.1) — P3
CREATE TABLE delegations (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  delegator_user_id  TEXT NOT NULL REFERENCES users(id),
  delegate_user_id   TEXT NOT NULL REFERENCES users(id),
  scope              TEXT NOT NULL DEFAULT 'approval' CHECK (scope IN ('approval')),
  starts_at          TIMESTAMPTZ NOT NULL,
  ends_at            TIMESTAMPTZ NOT NULL,
  revoked_at         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_delegations_company ON delegations (company_id, ends_at);

-- ---------------------------------------------------------------------------
-- 4.2 근로자·서류
-- ---------------------------------------------------------------------------

CREATE TABLE workers (
  id                     TEXT PRIMARY KEY,
  company_id             TEXT NOT NULL REFERENCES companies(id),
  display_name           TEXT NOT NULL,            -- "Nguyen Van A"
  nationality            TEXT NOT NULL,            -- 무채색 운영 정보로만(차별 금지)
  team                   TEXT,                     -- "제조1팀"
  visa_type              TEXT NOT NULL DEFAULT 'E-9',
  stay_expires_at        DATE NOT NULL,            -- 체류만료일 — D-day 계산의 필수 재료
  contract_ends_at       DATE,                     -- 있으면 충돌 감지 활성
  contact_channel        TEXT,
  preferred_language     TEXT CHECK (preferred_language IN ('ko','vi','id','en')),
  registration_no_masked TEXT,                     -- '900101-*******' — 원문 컬럼은 존재하지 않음(§7)
  source                 TEXT NOT NULL DEFAULT 'manual'
                         CHECK (source IN ('manual','ocr','csv','agency')),
  status                 TEXT NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active','inactive','left')),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_workers_company ON workers (company_id, status);
CREATE INDEX ix_workers_stay_expiry ON workers (company_id, stay_expires_at);

-- 근거 라이브러리(중앙 스토어) — company_id NULL = 전역 공식 근거
CREATE TABLE citations (
  id                  TEXT PRIMARY KEY,            -- 'cit_001' 표시 코드 = PK(전역 시퀀스)
  company_id          TEXT REFERENCES companies(id),
  grade               TEXT NOT NULL CHECK (grade IN ('A','B','C','E','F')),
  status              TEXT NOT NULL CHECK (status IN ('official','review_needed','stale','internal')),
  title               TEXT NOT NULL,
  source              TEXT NOT NULL,
  source_url          TEXT,
  effective_date      DATE,
  ingest_at           TIMESTAMPTZ NOT NULL,
  chroma_collection   TEXT,                        -- Chroma 청크 포인터(메타데이터 미러링만)
  chroma_document_id  TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_citations_status ON citations (status, grade);

-- 필수 서류 정의(전역 참조 — company_id 없음)
CREATE TABLE document_requirements (
  id           TEXT PRIMARY KEY,
  case_type    TEXT NOT NULL,
  visa_type    TEXT NOT NULL,
  required_doc TEXT NOT NULL,
  required     BOOLEAN NOT NULL DEFAULT 1 CHECK (required IN (0,1)),
  citation_id  TEXT REFERENCES citations(id),      -- "왜 필요한지" 근거
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (case_type, visa_type, required_doc)
);

CREATE TABLE worker_documents (
  id           TEXT PRIMARY KEY,
  company_id   TEXT NOT NULL REFERENCES companies(id),
  worker_id    TEXT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
  doc_type     TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'missing'
               CHECK (status IN ('missing','requested','received','expiring','company_check','pending')),
  due_date     DATE,
  expires_at   DATE,
  file_ref     TEXT,                               -- 암호화 저장소 키(경로 원문 아님)
  submitted_at TIMESTAMPTZ,
  reviewed_at  TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (worker_id, doc_type)
);
CREATE INDEX ix_worker_documents_company ON worker_documents (company_id, status);

-- O4-A 촬영 원본 포인터 — P3
CREATE TABLE worker_intake_files (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  worker_id          TEXT REFERENCES workers(id) ON DELETE CASCADE,
  storage_key        TEXT NOT NULL,                -- 암호화 스토리지 키(이미지·OCR 원문은 DB 밖)
  ocr_fields_masked  JSON CHECK (ocr_fields_masked IS NULL OR json_valid(ocr_fields_masked)),
  status             TEXT NOT NULL DEFAULT 'uploaded'
                     CHECK (status IN ('uploaded','ocr_done','confirmed','failed')),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_worker_intake_files_company ON worker_intake_files (company_id, status);

-- ---------------------------------------------------------------------------
-- 4.3 케이스 코어
-- ---------------------------------------------------------------------------

CREATE TABLE cases (
  id                  TEXT PRIMARY KEY,
  company_id          TEXT NOT NULL REFERENCES companies(id),
  case_code           TEXT NOT NULL,               -- "case_002" 회사별 발급(§9)
  worker_id           TEXT REFERENCES workers(id) ON DELETE SET NULL,
  case_type           TEXT NOT NULL CHECK (case_type IN
                        ('visa_expiry','missing_document','contract_visa_conflict',
                         'reporting_deadline','quota_review','hiring','onboarding','other')),
  title               TEXT NOT NULL,               -- 업무 단위 명칭(근로자명 미포함)
  summary             TEXT,                        -- 케이스 시트 요약 1문장(마스킹 적용)
  severity            TEXT NOT NULL CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
  state               TEXT NOT NULL DEFAULT 'draft' CHECK (state IN
                        ('draft','risk_review','approval_pending','returned',
                         'human_approved','completed','blocked')),
  agent_stage         TEXT CHECK (agent_stage IN
                        ('detected','collecting','drafted','awaiting_approval','executed')),
  due_date            DATE,                        -- D-day 앵커. dDay는 저장하지 않음(§6)
  assignee_user_id    TEXT REFERENCES users(id),
  approval_required   BOOLEAN NOT NULL DEFAULT 0 CHECK (approval_required IN (0,1)),
  prepared_by         TEXT NOT NULL DEFAULT 'rule' CHECK (prepared_by IN ('agent','rule')),
  prepared_run_id     TEXT REFERENCES runs(id),    -- 순환 FK(runs.case_id↔) — SQLite는 지연 해석
  parent_case_id      TEXT REFERENCES cases(id),   -- 런 체이닝(9단계 P0-2)
  guard_note          TEXT,                        -- high risk 경고문(Rule Engine 산출)
  checked_items       JSON CHECK (checked_items IS NULL OR json_valid(checked_items)),
  next_wake_at        TIMESTAMPTZ,
  next_wake_condition TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, case_code)
);
CREATE INDEX ix_cases_company_state ON cases (company_id, state);
CREATE INDEX ix_cases_company_severity_due ON cases (company_id, severity, due_date);
-- 케이스 재사용 규칙(레거시 PRD §15 승계): 열린 케이스 중복 생성 방지
CREATE UNIQUE INDEX ux_cases_reuse ON cases (company_id, worker_id, case_type, due_date)
  WHERE state IN ('draft','risk_review','approval_pending','returned');

-- 에이전트 런(툴콜링 루프 1회)
CREATE TABLE runs (
  id                  TEXT PRIMARY KEY,
  company_id          TEXT NOT NULL REFERENCES companies(id),
  case_id             TEXT REFERENCES cases(id),   -- 커맨드 런 초기엔 NULL 가능
  started_by          TEXT NOT NULL CHECK (started_by IN ('user','event')),
  trigger_event       TEXT,                        -- "D-30 진입" 등
  started_by_user_id  TEXT REFERENCES users(id),
  agent_name          TEXT NOT NULL,
  autonomy            TEXT NOT NULL DEFAULT 'medium' CHECK (autonomy IN ('low','medium','high')),
  status              TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                        ('queued','running','waiting_question','waiting_approval',
                         'completed','failed','cancelled')),
  goal_text           TEXT,                        -- 사용자 명령(저장 전 PII 스크럽)
  question            JSON CHECK (question IS NULL OR json_valid(question)),
  result_summary      TEXT,
  anchor_event_no     INTEGER,                     -- "런 1건 = 판단 기록 # 1건"(§9)
  parent_run_id       TEXT REFERENCES runs(id),
  priority_hint       TEXT,
  started_at          TIMESTAMPTZ,
  ended_at            TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_runs_company ON runs (company_id, status);
CREATE INDEX ix_runs_case ON runs (case_id);

CREATE TABLE run_steps (
  id           TEXT PRIMARY KEY,
  run_id       TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  seq          INTEGER NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('thinking','tool_call','guardrail','handoff','replan')),
  label        TEXT NOT NULL,
  detail       TEXT,                               -- 마스킹된 상세
  tool_name    TEXT,
  tool_status  TEXT CHECK (tool_status IN ('running','done','failed','blocked')),
  handoff_from TEXT,
  handoff_to   TEXT,
  payload_hash TEXT,                               -- 입출력 해시(원문 미저장)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (run_id, seq)
);

CREATE TABLE next_actions (
  id                TEXT PRIMARY KEY,
  company_id        TEXT NOT NULL REFERENCES companies(id),
  case_id           TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  kind              TEXT NOT NULL CHECK (kind IN ('approve','draft','detail','thread','package','confirm')),
  action_type       TEXT NOT NULL CHECK (action_type IN
                      ('request_document','create_handoff','send_message','confirm_status',
                       'export_package','complete_case','other')),
  label             TEXT NOT NULL,
  state             TEXT NOT NULL DEFAULT 'ready' CHECK (state IN ('ready','locked','scheduled','waiting')),
  requires_approval BOOLEAN NOT NULL DEFAULT 0 CHECK (requires_approval IN (0,1)),
  slot              TEXT CHECK (slot IN ('primary','secondary')),
  scheduled_at      TIMESTAMPTZ,                   -- state='scheduled' 도래 시각 — N13 소스
  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_next_actions_case ON next_actions (case_id);
CREATE INDEX ix_next_actions_company ON next_actions (company_id, state);
CREATE UNIQUE INDEX ux_next_actions_slot ON next_actions (case_id, slot) WHERE slot IS NOT NULL;

-- 승인 — 외부 발송의 유일한 관문. 다형 참조 없음(항상 케이스 액션 대상)
CREATE TABLE approvals (
  id                    TEXT PRIMARY KEY,
  company_id            TEXT NOT NULL REFERENCES companies(id),
  case_id               TEXT NOT NULL REFERENCES cases(id),
  action_id             TEXT NOT NULL REFERENCES next_actions(id),
  status                TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','rejected','cancelled')),
  -- 중복 승인 차단(GOTCHAS §2). nullable: requestApproval() 시점엔 아직 결정 키가 없다
  -- (decide() 호출 시에만 채워짐) — NULL끼리는 UNIQUE 충돌하지 않아 pending 승인이
  -- 여러 건이어도 안전하다(2026-07-12, API 구현 중 발견·정정, docs/DB_SCHEMA.md §4.3).
  idempotency_key       TEXT UNIQUE,
  requested_by_actor    TEXT NOT NULL CHECK (requested_by_actor IN ('agent','rule','user')),
  requested_by_user_id  TEXT REFERENCES users(id),
  decided_by_user_id    TEXT REFERENCES users(id),
  on_behalf_of_user_id  TEXT REFERENCES users(id), -- 대리 승인 시 위임자(7단계 §5)
  identity_method       TEXT CHECK (identity_method IN ('pin','biometric')),
  checklist             JSON CHECK (checklist IS NULL OR json_valid(checklist)), -- M2.6 §2c 4항목
  reason                TEXT,                      -- 반려 사유(서비스 계층 PII 패턴 차단)
  requested_at          TIMESTAMPTZ NOT NULL,
  decided_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_approvals_company_status ON approvals (company_id, status);
CREATE INDEX ix_approvals_case ON approvals (case_id);
-- 액션당 살아있는 승인 요청은 1건. 일괄 승인 테이블·컬럼은 만들지 않는다(GOTCHAS §3)
CREATE UNIQUE INDEX ux_approvals_one_pending ON approvals (action_id) WHERE status = 'pending';

-- 케이스↔근거 연결
CREATE TABLE case_citations (
  case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  citation_id     TEXT NOT NULL REFERENCES citations(id),
  added_by_actor  TEXT NOT NULL CHECK (added_by_actor IN ('agent','rule','user')),
  added_by_run_id TEXT REFERENCES runs(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (case_id, citation_id)
);
CREATE INDEX ix_case_citations_citation ON case_citations (citation_id);

-- ---------------------------------------------------------------------------
-- 4.5 판단 기록 — append-only (수정·삭제는 트리거가 차단)
-- ---------------------------------------------------------------------------

CREATE TABLE evidence_events (
  id              TEXT PRIMARY KEY,
  company_id      TEXT NOT NULL REFERENCES companies(id),
  event_no        INTEGER NOT NULL,                -- 회사별 단조 증가 — 표시 "#4789"(§9)
  type            TEXT NOT NULL CHECK (type IN
                    -- 코어(src/types.ts EvidenceType과 동일)
                    ('intent_classified','plan_created','tool_executed','rag_retrieved',
                     'risk_flagged','approval_requested','approval_decided','review_started',
                     'checklist_completed','exported','final_response_generated',
                     -- 확장(스펙 요구 — 화면이 붙는 마일스톤에 프론트 타입에도 추가)
                     'briefing_emitted','notification_sent','worker_reply_received',
                     'worker_reply_summarized','status_update_confirmed','handoff_generated',
                     'package_link_issued','package_link_viewed','delegation_granted',
                     'delegation_revoked','role_granted','role_changed','member_invited',
                     'member_removed','approval_escalated','autonomy_changed','worker_deleted')),
  at              TIMESTAMPTZ NOT NULL,            -- 발생 시각(주입 가능 — 테스트 결정성)
  case_id         TEXT REFERENCES cases(id),
  action_id       TEXT REFERENCES next_actions(id),
  approval_id     TEXT REFERENCES approvals(id),
  run_id          TEXT REFERENCES runs(id),
  actor_type      TEXT NOT NULL CHECK (actor_type IN ('system','user','agent','approver')),
  actor_user_id   TEXT REFERENCES users(id),
  actor_display   TEXT,                            -- "김담당 (본인 확인 완료)" — 마스킹된 표시 문자열
  summary         TEXT NOT NULL,                   -- PII 마스킹된 한 줄 요약만. 원문 전문 금지
  input_hash      TEXT,                            -- 'sha256:…' (프론트 hash = input_hash)
  output_hash     TEXT,
  hash_algorithm  TEXT NOT NULL DEFAULT 'sha256',
  trace_id        TEXT,
  request_id      TEXT,
  payload_ref     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, event_no)
);
CREATE INDEX ix_evidence_company_at ON evidence_events (company_id, at);
CREATE INDEX ix_evidence_case ON evidence_events (case_id);
CREATE INDEX ix_evidence_request ON evidence_events (request_id);

-- append-only 강제(문서 §5.2) — PG 전환 시 동일 트리거 + UPDATE/DELETE 권한 회수
CREATE TRIGGER evidence_events_no_update BEFORE UPDATE ON evidence_events
BEGIN SELECT RAISE(ABORT, 'evidence_events is append-only'); END;
CREATE TRIGGER evidence_events_no_delete BEFORE DELETE ON evidence_events
BEGIN SELECT RAISE(ABORT, 'evidence_events is append-only'); END;

-- ---------------------------------------------------------------------------
-- 4.7 초안·소통
-- ---------------------------------------------------------------------------

-- 컨택 스레드(근로자 단위 — 탭별 §3.1)
CREATE TABLE threads (
  id              TEXT PRIMARY KEY,
  company_id      TEXT NOT NULL REFERENCES companies(id),
  worker_id       TEXT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
  channel         TEXT NOT NULL,
  last_message_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, worker_id)                   -- MVP: 근로자당 1스레드
);

-- 메시지 초안(M3)
CREATE TABLE drafts (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  case_id            TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  thread_id          TEXT REFERENCES threads(id),
  created_by_run_id  TEXT REFERENCES runs(id),
  channel            TEXT NOT NULL,
  purpose            TEXT NOT NULL,
  status             TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                       ('draft','revision_requested','pending_approval','approved','rejected','superseded')),
  approval_id        TEXT REFERENCES approvals(id),
  compliance_checks  JSON CHECK (compliance_checks IS NULL OR json_valid(compliance_checks)),
  expected_scenarios JSON CHECK (expected_scenarios IS NULL OR json_valid(expected_scenarios)),
  sent_at            TIMESTAMPTZ CHECK (sent_at IS NULL),  -- MVP 발송 차단(§0-4) — 어댑터 마일스톤에서 해제
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_drafts_case ON drafts (case_id, status);

CREATE TABLE draft_variants (
  id         TEXT PRIMARY KEY,
  draft_id   TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
  lang       TEXT NOT NULL CHECK (lang IN ('ko','vi','id','en')),
  text       TEXT NOT NULL,                        -- 전문 저장 — §7 접근 규칙, evidence 복사 금지
  is_revised BOOLEAN NOT NULL DEFAULT 0 CHECK (is_revised IN (0,1)),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_draft_variants_draft ON draft_variants (draft_id);

CREATE TABLE thread_messages (
  id            TEXT PRIMARY KEY,
  thread_id     TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
  company_id    TEXT NOT NULL REFERENCES companies(id),
  direction     TEXT NOT NULL CHECK (direction IN ('outbound','inbound','system')),
  draft_id      TEXT REFERENCES drafts(id),
  lang          TEXT,
  body_original TEXT,                              -- 원문 전문(PII) — 스레드 상세 전용(§7)
  body_ko       TEXT,
  received_at   TIMESTAMPTZ,
  sent_at       TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_thread_messages_thread ON thread_messages (thread_id, created_at);

-- 응답 해석(M6) — 제안은 언제나 비확정(isFinal=false는 성격 자체라 컬럼 없음)
CREATE TABLE interpretations (
  id                   TEXT PRIMARY KEY,
  company_id           TEXT NOT NULL REFERENCES companies(id),
  thread_message_id    TEXT NOT NULL REFERENCES thread_messages(id),
  case_id              TEXT REFERENCES cases(id),
  summary_ko           TEXT NOT NULL,              -- 한국어 요약(마스킹)
  confidence           TEXT NOT NULL CHECK (confidence IN ('high','low')),
  status               TEXT NOT NULL DEFAULT 'proposed'
                       CHECK (status IN ('proposed','confirmed','discarded')),
  confirmed_by_user_id TEXT REFERENCES users(id),
  confirmed_at         TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_interpretations_company ON interpretations (company_id, status);

CREATE TABLE status_update_proposals (
  id                TEXT PRIMARY KEY,
  interpretation_id TEXT NOT NULL REFERENCES interpretations(id) ON DELETE CASCADE,
  target_type       TEXT NOT NULL,                 -- 예: worker_document
  target_key        TEXT NOT NULL,                 -- 예: "여권 사본"
  from_value        TEXT NOT NULL,
  to_value          TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed','confirmed','rejected')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_sup_interpretation ON status_update_proposals (interpretation_id);

-- ---------------------------------------------------------------------------
-- 4.8 행정사 패키지
-- ---------------------------------------------------------------------------

CREATE TABLE handoff_packages (
  id             TEXT PRIMARY KEY,
  company_id     TEXT NOT NULL REFERENCES companies(id),
  case_id        TEXT NOT NULL REFERENCES cases(id),
  package_type   TEXT NOT NULL CHECK (package_type IN ('expert_review','pre_entry')),
  masked_payload JSON NOT NULL CHECK (json_valid(masked_payload)),  -- allowlist 필드만(§7)
  included_items JSON CHECK (included_items IS NULL OR json_valid(included_items)),
  status         TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                   ('draft','pending_approval','approved','rejected','exported')),
  approval_id    TEXT REFERENCES approvals(id),
  transferred_at TIMESTAMPTZ CHECK (transferred_at IS NULL), -- MVP 전달 차단(§0-4)
  created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_handoff_packages_company ON handoff_packages (company_id, status);
CREATE INDEX ix_handoff_packages_case ON handoff_packages (case_id);

CREATE TABLE package_exports (
  id                          TEXT PRIMARY KEY,
  package_id                  TEXT NOT NULL REFERENCES handoff_packages(id) ON DELETE CASCADE,
  company_id                  TEXT NOT NULL REFERENCES companies(id),
  format                      TEXT NOT NULL CHECK (format IN ('pdf','link','email_draft')),
  content_hash                TEXT NOT NULL,       -- 산출물 해시만(원문 없음)
  exported_by_user_id         TEXT NOT NULL REFERENCES users(id),
  external_delivery_performed BOOLEAN NOT NULL DEFAULT 0
                              CHECK (external_delivery_performed = 0), -- MVP 외부 전송 없음
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_package_exports_package ON package_exports (package_id);

CREATE TABLE package_links (
  id                 TEXT PRIMARY KEY,
  package_id         TEXT NOT NULL REFERENCES handoff_packages(id) ON DELETE CASCADE,
  token_hash         TEXT NOT NULL UNIQUE,         -- 링크 토큰은 해시로 저장
  expires_at         TIMESTAMPTZ NOT NULL,         -- 기본 7일(7단계 §4)
  issued_by_user_id  TEXT NOT NULL REFERENCES users(id),
  revoked_at         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 4.9 브리핑
-- ---------------------------------------------------------------------------

CREATE TABLE briefings (
  id                   TEXT PRIMARY KEY,
  company_id           TEXT NOT NULL REFERENCES companies(id),
  briefing_date        DATE NOT NULL,              -- 회사 timezone 기준
  generated_at         TIMESTAMPTZ NOT NULL,
  source_snapshot_hash TEXT NOT NULL,              -- non-PII 운영 필드만으로 계산(§4.9)
  rerun_count          INTEGER NOT NULL DEFAULT 0,
  last_refreshed_at    TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, briefing_date)               -- 같은 날 재실행은 갱신
);

CREATE TABLE briefing_items (
  id          TEXT PRIMARY KEY,
  briefing_id TEXT NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  case_id     TEXT NOT NULL REFERENCES cases(id),
  rank        INTEGER NOT NULL,                    -- 발행 시점 정렬 스냅샷(hero=1)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (briefing_id, case_id)
);

-- ---------------------------------------------------------------------------
-- 4.10 알림 — P3 (N05b는 개별 푸시 금지라 타입 자체가 없다)
-- ---------------------------------------------------------------------------

CREATE TABLE notifications (
  id                TEXT PRIMARY KEY,
  company_id        TEXT NOT NULL REFERENCES companies(id),
  recipient_user_id TEXT NOT NULL REFERENCES users(id),
  type              TEXT NOT NULL CHECK (type IN
                      ('N01','N02','N03','N04','N05','N06','N07',
                       'N10','N11','N12','N13','N14','N20','N21','N22')),
  priority          TEXT NOT NULL CHECK (priority IN ('P1','P2','P3')),
  title             TEXT NOT NULL,                 -- 마스킹 적용(2단계 §5.3)
  body              TEXT NOT NULL,
  deeplink_path     TEXT NOT NULL,                 -- 'case/{id}/approve' — 딥링크 계약과 1:1
  notification_key  TEXT UNIQUE,                   -- 알림톡 nk 파라미터
  dedupe_key        TEXT NOT NULL,                 -- '{case}:{type}:{threshold}' idempotency
  channel           TEXT NOT NULL CHECK (channel IN ('push','alimtalk','email')),
  status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                      ('queued','held','sent','delivered','failed','suppressed')),
  scheduled_for     TIMESTAMPTZ,
  sent_at           TIMESTAMPTZ,
  delivered_at      TIMESTAMPTZ,
  case_id           TEXT REFERENCES cases(id),
  run_id            TEXT REFERENCES runs(id),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, dedupe_key)
);
CREATE INDEX ix_notifications_recipient ON notifications (recipient_user_id, status);

-- ---------------------------------------------------------------------------
-- 4.11 온보딩·수집 — P3
-- ---------------------------------------------------------------------------

CREATE TABLE csv_imports (
  id                  TEXT PRIMARY KEY,
  company_id          TEXT NOT NULL REFERENCES companies(id),
  uploaded_by_user_id TEXT NOT NULL REFERENCES users(id),
  filename            TEXT NOT NULL,               -- 원본 파일은 스캔 후 폐기 — 결과만 보존
  row_count           INTEGER NOT NULL DEFAULT 0,
  ok_count            INTEGER NOT NULL DEFAULT 0,
  error_count         INTEGER NOT NULL DEFAULT 0,
  error_rows          JSON CHECK (error_rows IS NULL OR json_valid(error_rows)),
  status              TEXT NOT NULL DEFAULT 'validating'
                      CHECK (status IN ('validating','failed','applied')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_csv_imports_company ON csv_imports (company_id);

-- ---------------------------------------------------------------------------
-- 4.12 에이전틱 확장 — P3
-- ---------------------------------------------------------------------------

CREATE TABLE autonomy_grants (
  id                   TEXT PRIMARY KEY,
  company_id           TEXT NOT NULL REFERENCES companies(id),
  case_type            TEXT NOT NULL,
  level                TEXT NOT NULL CHECK (level IN ('L1','L2','L3')),
  consented_by_user_id TEXT NOT NULL REFERENCES users(id), -- owner 명시 동의 필수
  consented_at         TIMESTAMPTZ NOT NULL,
  revoked_at           TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, case_type)
);

-- 에이전트 운영 메모(P2-7) — 사용자 열람·삭제 가능(append-only 원칙의 명시적 예외)
CREATE TABLE agent_notes (
  id           TEXT PRIMARY KEY,
  company_id   TEXT NOT NULL REFERENCES companies(id),
  subject_type TEXT NOT NULL CHECK (subject_type IN ('worker','company','expert')),
  subject_id   TEXT,
  -- 카테고리 화이트리스트 — 성실도·성격·이탈 추정 계열은 스키마 차원 금지(GOTCHAS §1)
  category     TEXT NOT NULL CHECK (category IN
                 ('response_pattern','deadline_practice','format_preference','channel_preference')),
  note         TEXT NOT NULL,                      -- 관찰 사실만
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_agent_notes_subject ON agent_notes (company_id, subject_type, subject_id);

-- 집계 스냅샷(파생 캐시 — 재계산 가능, 정본 아님)
CREATE TABLE stat_snapshots (
  id            TEXT PRIMARY KEY,
  company_id    TEXT NOT NULL REFERENCES companies(id),
  snapshot_date DATE NOT NULL,
  counts        JSON NOT NULL CHECK (json_valid(counts)),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, snapshot_date)
);

-- ---------------------------------------------------------------------------
-- 파생값 뷰(문서 §6) — "저장하지 않는다"의 실행 형태. 필요 시 셀렉터/뷰만 추가
-- ---------------------------------------------------------------------------

-- 사용 가능 근거(F등급 제외) — 승인 게이트 판정은 반드시 이 뷰(또는 동일 필터)를 거친다
CREATE VIEW v_usable_citations AS
SELECT * FROM citations WHERE grade <> 'F';

-- 근거별 연계 케이스 수(linkedCaseCount)
CREATE VIEW v_citation_link_counts AS
SELECT c.id AS citation_id, COUNT(cc.case_id) AS linked_case_count
FROM citations c LEFT JOIN case_citations cc ON cc.citation_id = c.id
GROUP BY c.id;

-- 케이스 파생값: dDay(조회 시점 기준) · 누락 서류 수 · 사용 가능 근거 수
CREATE VIEW v_case_derived AS
SELECT
  cs.id AS case_id,
  cs.company_id,
  CAST(julianday(cs.due_date) - julianday(date('now')) AS INTEGER) AS d_day,
  (SELECT COUNT(*) FROM worker_documents wd
    WHERE wd.worker_id = cs.worker_id AND wd.status = 'missing') AS missing_doc_count,
  (SELECT COUNT(*) FROM case_citations cc JOIN citations c2
    ON c2.id = cc.citation_id AND c2.grade <> 'F'
    WHERE cc.case_id = cs.id) AS usable_citation_count
FROM cases cs;

-- 파이프라인 5단 집계 — src/lib/caseStage.ts 파생 규칙과 동일(agent_stage 우선)
CREATE VIEW v_pipeline_counts AS
SELECT
  company_id,
  COALESCE(agent_stage,
    CASE
      WHEN state IN ('completed','human_approved') THEN 'executed'
      WHEN state IN ('approval_pending','returned','blocked') THEN 'awaiting_approval'
      ELSE 'collecting'
    END) AS stage,
  COUNT(*) AS case_count
FROM cases
GROUP BY company_id, stage;
