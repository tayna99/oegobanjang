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
  invited_by         TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  UNIQUE (company_id, user_id),
  FOREIGN KEY (company_id, invited_by) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_memberships_company ON memberships (company_id, role);

-- 승인 위임(7단계 §3.1) — P3
CREATE TABLE delegations (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  delegator_user_id  TEXT NOT NULL,
  delegate_user_id   TEXT NOT NULL,
  scope              TEXT NOT NULL DEFAULT 'approval' CHECK (scope IN ('approval')),
  starts_at          TIMESTAMPTZ NOT NULL,
  ends_at            TIMESTAMPTZ NOT NULL,
  revoked_at         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, delegator_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, delegate_user_id) REFERENCES memberships(company_id, user_id)
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
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id)
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
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (company_id IS NOT NULL OR status <> 'internal')
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
  worker_id    TEXT NOT NULL,
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
  UNIQUE (worker_id, doc_type),
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_worker_documents_company ON worker_documents (company_id, status);

-- O4-A 촬영 원본 포인터 — P3
CREATE TABLE worker_intake_files (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  worker_id          TEXT,
  storage_key        TEXT NOT NULL,                -- 암호화 스토리지 키(이미지·OCR 원문은 DB 밖)
  ocr_fields_masked  JSON CHECK (ocr_fields_masked IS NULL OR json_valid(ocr_fields_masked)),
  status             TEXT NOT NULL DEFAULT 'uploaded'
                     CHECK (status IN ('uploaded','ocr_done','confirmed','failed')),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_worker_intake_files_company ON worker_intake_files (company_id, status);

-- ---------------------------------------------------------------------------
-- 4.3 케이스 코어
-- ---------------------------------------------------------------------------

CREATE TABLE cases (
  id                  TEXT PRIMARY KEY,
  company_id          TEXT NOT NULL REFERENCES companies(id),
  case_code           TEXT NOT NULL,               -- "case_002" 회사별 발급(§9)
  worker_id           TEXT,
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
  assignee_user_id    TEXT,
  approval_required   BOOLEAN NOT NULL DEFAULT 0 CHECK (approval_required IN (0,1)),
  prepared_by         TEXT NOT NULL DEFAULT 'rule' CHECK (prepared_by IN ('agent','rule')),
  prepared_run_id     TEXT,                        -- 순환 FK(runs.case_id↔)
  parent_case_id      TEXT,                        -- 런 체이닝(9단계 P0-2)
  guard_note          TEXT,                        -- high risk 경고문(Rule Engine 산출)
  checked_items       JSON CHECK (checked_items IS NULL OR json_valid(checked_items)),
  next_wake_at        TIMESTAMPTZ,
  next_wake_condition TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  UNIQUE (company_id, case_code),
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id),
  FOREIGN KEY (company_id, assignee_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, prepared_run_id) REFERENCES runs(company_id, id),
  FOREIGN KEY (company_id, parent_case_id) REFERENCES cases(company_id, id)
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
  case_id             TEXT,                        -- 커맨드 런 초기엔 NULL 가능
  started_by          TEXT NOT NULL CHECK (started_by IN ('user','event')),
  trigger_event       TEXT,                        -- "D-30 진입" 등
  started_by_user_id  TEXT,
  agent_name          TEXT NOT NULL,
  autonomy            TEXT NOT NULL DEFAULT 'medium' CHECK (autonomy IN ('low','medium','high')),
  status              TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                        ('queued','running','waiting_question','waiting_approval',
                         'completed','failed','cancelled')),
  goal_text           TEXT,                        -- 사용자 명령(저장 전 PII 스크럽)
  question            JSON CHECK (question IS NULL OR json_valid(question)),
  result_summary      TEXT,
  anchor_event_no     INTEGER,                     -- "런 1건 = 판단 기록 # 1건"(§9)
  parent_run_id       TEXT,
  priority_hint       TEXT,
  started_at          TIMESTAMPTZ,
  ended_at            TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, started_by_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, parent_run_id) REFERENCES runs(company_id, id)
);
CREATE INDEX ix_runs_company ON runs (company_id, status);
CREATE INDEX ix_runs_case ON runs (case_id);

CREATE TABLE run_steps (
  id           TEXT PRIMARY KEY,
  company_id   TEXT NOT NULL REFERENCES companies(id),
  run_id       TEXT NOT NULL,
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
  UNIQUE (company_id, run_id, seq),
  FOREIGN KEY (company_id, run_id) REFERENCES runs(company_id, id) ON DELETE CASCADE
);

CREATE TABLE next_actions (
  id                TEXT PRIMARY KEY,
  company_id        TEXT NOT NULL REFERENCES companies(id),
  case_id           TEXT NOT NULL,
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
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    action_type NOT IN ('send_message','create_handoff','export_package','complete_case')
    OR requires_approval = 1
  ),
  UNIQUE (company_id, id),
  UNIQUE (company_id, case_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_next_actions_case ON next_actions (case_id);
CREATE INDEX ix_next_actions_company ON next_actions (company_id, state);
CREATE UNIQUE INDEX ux_next_actions_slot ON next_actions (case_id, slot) WHERE slot IS NOT NULL;

-- 승인 — 외부 발송의 유일한 관문. 다형 참조 없음(항상 케이스 액션 대상)
CREATE TABLE approvals (
  id                    TEXT PRIMARY KEY,
  company_id            TEXT NOT NULL REFERENCES companies(id),
  case_id               TEXT NOT NULL,
  action_id             TEXT NOT NULL,
  status                TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','rejected')),
  -- 결정 멱등 키는 decide() 시점에만 채운다. pending 승인에서는 NULL을 허용하며,
  -- NULL끼리는 UNIQUE 충돌하지 않는다.
  idempotency_key       TEXT UNIQUE,               -- 중복 승인 차단(GOTCHAS §2)
  requested_by_actor    TEXT NOT NULL CHECK (requested_by_actor IN ('agent','rule','user')),
  requested_by_user_id  TEXT,
  decided_by_user_id    TEXT,
  on_behalf_of_user_id  TEXT, -- 대리 승인 시 위임자(7단계 §5)
  identity_method       TEXT CHECK (identity_method IN ('pin','biometric')),
  checklist             JSON CHECK (checklist IS NULL OR json_valid(checklist)), -- M2.6 §2c 4항목
  reason                TEXT,                      -- 반려 사유(서비스 계층 PII 패턴 차단)
  requested_at          TIMESTAMPTZ NOT NULL,
  decided_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (status = 'pending'
      AND decided_by_user_id IS NULL
      AND on_behalf_of_user_id IS NULL
      AND identity_method IS NULL
      AND reason IS NULL
      AND decided_at IS NULL)
    OR
    (status = 'approved'
      AND decided_by_user_id IS NOT NULL
      AND identity_method IS NOT NULL
      AND decided_at IS NOT NULL)
    OR
    (status = 'rejected'
      AND decided_by_user_id IS NOT NULL
      AND identity_method IS NOT NULL
      AND decided_at IS NOT NULL
      AND reason IS NOT NULL
      AND length(trim(reason)) > 0)
  ),
  UNIQUE (company_id, id),
  UNIQUE (company_id, case_id, id),
  FOREIGN KEY (company_id, case_id, action_id)
    REFERENCES next_actions(company_id, case_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, requested_by_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, decided_by_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, on_behalf_of_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_approvals_company_status ON approvals (company_id, status);
CREATE INDEX ix_approvals_case ON approvals (case_id);
-- 액션당 살아있는 승인 요청은 1건. 일괄 승인 테이블·컬럼은 만들지 않는다(GOTCHAS §3)
CREATE UNIQUE INDEX ux_approvals_one_pending ON approvals (action_id) WHERE status = 'pending';

-- 케이스↔근거 연결
CREATE TABLE case_citations (
  company_id      TEXT NOT NULL REFERENCES companies(id),
  case_id         TEXT NOT NULL,
  citation_id     TEXT NOT NULL REFERENCES citations(id),
  added_by_actor  TEXT NOT NULL CHECK (added_by_actor IN ('agent','rule','user')),
  added_by_run_id TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (company_id, case_id, citation_id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, added_by_run_id) REFERENCES runs(company_id, id)
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
                      'briefing_emitted','worker_reply_received',
                      'worker_reply_summarized','status_update_confirmed','handoff_generated',
                      'delegation_granted',
                     'delegation_revoked','role_granted','role_changed','member_invited',
                     'member_removed','approval_escalated','autonomy_changed','worker_deleted')),
  at              TIMESTAMPTZ NOT NULL,            -- 발생 시각(주입 가능 — 테스트 결정성)
  case_id         TEXT,
  action_id       TEXT,
  approval_id     TEXT,
  run_id          TEXT,
  actor_type      TEXT NOT NULL CHECK (actor_type IN ('system','user','agent','approver')),
  actor_user_id   TEXT,
  actor_display   TEXT,                            -- "김담당 (본인 확인 완료)" — 마스킹된 표시 문자열
  summary         TEXT NOT NULL,                   -- PII 마스킹된 한 줄 요약만. 원문 전문 금지
  input_hash      TEXT,                            -- 'sha256:…' (프론트 hash = input_hash)
  output_hash     TEXT,
  hash_algorithm  TEXT NOT NULL DEFAULT 'sha256',
  trace_id        TEXT,
  request_id      TEXT,
  payload_ref     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, event_no),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, case_id, action_id) REFERENCES next_actions(company_id, case_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id),
  FOREIGN KEY (company_id, run_id) REFERENCES runs(company_id, id),
  FOREIGN KEY (company_id, actor_user_id) REFERENCES memberships(company_id, user_id)
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
  worker_id       TEXT NOT NULL,
  channel         TEXT NOT NULL,
  last_message_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  UNIQUE (company_id, worker_id),                  -- MVP: 근로자당 1스레드
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);

-- 메시지 초안(M3)
CREATE TABLE drafts (
  id                 TEXT PRIMARY KEY,
  company_id         TEXT NOT NULL REFERENCES companies(id),
  case_id            TEXT NOT NULL,
  thread_id          TEXT,
  created_by_run_id  TEXT,
  channel            TEXT NOT NULL,
  purpose            TEXT NOT NULL,
  status             TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                       ('draft','revision_requested','pending_approval','approved','rejected','superseded')),
  approval_id        TEXT,
  compliance_checks  JSON CHECK (compliance_checks IS NULL OR json_valid(compliance_checks)),
  expected_scenarios JSON CHECK (expected_scenarios IS NULL OR json_valid(expected_scenarios)),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, thread_id) REFERENCES threads(company_id, id),
  FOREIGN KEY (company_id, created_by_run_id) REFERENCES runs(company_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id)
);
CREATE INDEX ix_drafts_case ON drafts (case_id, status);

CREATE TABLE draft_variants (
  id         TEXT PRIMARY KEY,
  company_id TEXT NOT NULL REFERENCES companies(id),
  draft_id   TEXT NOT NULL,
  lang       TEXT NOT NULL CHECK (lang IN ('ko','vi','id','en')),
  text       TEXT NOT NULL,                        -- 전문 저장 — §7 접근 규칙, evidence 복사 금지
  is_revised BOOLEAN NOT NULL DEFAULT 0 CHECK (is_revised IN (0,1)),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, draft_id) REFERENCES drafts(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_draft_variants_draft ON draft_variants (draft_id);

CREATE TABLE thread_messages (
  id            TEXT PRIMARY KEY,
  thread_id     TEXT NOT NULL,
  company_id    TEXT NOT NULL REFERENCES companies(id),
  direction     TEXT NOT NULL CHECK (direction IN ('inbound','system')),
  draft_id      TEXT,
  lang          TEXT,
  body_original TEXT,                              -- 원문 전문(PII) — 스레드 상세 전용(§7)
  body_ko       TEXT,
  received_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, thread_id) REFERENCES threads(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, draft_id) REFERENCES drafts(company_id, id)
);
CREATE INDEX ix_thread_messages_thread ON thread_messages (thread_id, created_at);

-- 응답 해석(M6) — 제안은 언제나 비확정(isFinal=false는 성격 자체라 컬럼 없음)
CREATE TABLE interpretations (
  id                   TEXT PRIMARY KEY,
  company_id           TEXT NOT NULL REFERENCES companies(id),
  thread_message_id    TEXT NOT NULL,
  case_id              TEXT,
  summary_ko           TEXT NOT NULL,              -- 한국어 요약(마스킹)
  confidence           TEXT NOT NULL CHECK (confidence IN ('high','low')),
  status               TEXT NOT NULL DEFAULT 'proposed'
                       CHECK (status IN ('proposed','confirmed','discarded')),
  confirmed_by_user_id TEXT,
  confirmed_at         TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, thread_message_id) REFERENCES thread_messages(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, confirmed_by_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_interpretations_company ON interpretations (company_id, status);

CREATE TABLE status_update_proposals (
  id                TEXT PRIMARY KEY,
  company_id        TEXT NOT NULL REFERENCES companies(id),
  interpretation_id TEXT NOT NULL,
  target_type       TEXT NOT NULL,                 -- 예: worker_document
  target_key        TEXT NOT NULL,                 -- 예: "여권 사본"
  from_value        TEXT NOT NULL,
  to_value          TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed','confirmed','rejected')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, interpretation_id) REFERENCES interpretations(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_sup_interpretation ON status_update_proposals (interpretation_id);

-- ---------------------------------------------------------------------------
-- 4.8 행정사 패키지
-- ---------------------------------------------------------------------------

CREATE TABLE handoff_packages (
  id             TEXT PRIMARY KEY,
  company_id     TEXT NOT NULL REFERENCES companies(id),
  case_id        TEXT NOT NULL,
  package_type   TEXT NOT NULL CHECK (package_type IN ('expert_review','pre_entry')),
  masked_payload JSON NOT NULL CHECK (json_valid(masked_payload)),  -- allowlist 필드만(§7)
  included_items JSON CHECK (included_items IS NULL OR json_valid(included_items)),
  status         TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                   ('draft','pending_approval','approved','rejected','exported')),
  approval_id    TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id)
);
CREATE INDEX ix_handoff_packages_company ON handoff_packages (company_id, status);
CREATE INDEX ix_handoff_packages_case ON handoff_packages (case_id);

CREATE TABLE package_exports (
  id                          TEXT PRIMARY KEY,
  package_id                  TEXT NOT NULL,
  company_id                  TEXT NOT NULL REFERENCES companies(id),
  format                      TEXT NOT NULL CHECK (format = 'pdf'), -- MVP: 내부 PDF 산출물만
  content_hash                TEXT NOT NULL,       -- 산출물 해시만(원문 없음)
  exported_by_user_id         TEXT NOT NULL,
  external_delivery_performed BOOLEAN NOT NULL DEFAULT 0
                              CHECK (external_delivery_performed = 0), -- MVP 외부 전송 없음
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, package_id) REFERENCES handoff_packages(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, exported_by_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_package_exports_package ON package_exports (package_id);

-- MVP에는 외부 전달 링크를 만들지 않는다. delivery adapter 마일스톤에서 별도 migration으로 도입한다.

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
  UNIQUE (company_id, id),
  UNIQUE (company_id, briefing_date)               -- 같은 날 재실행은 갱신
);

CREATE TABLE briefing_items (
  id          TEXT PRIMARY KEY,
  company_id  TEXT NOT NULL REFERENCES companies(id),
  briefing_id TEXT NOT NULL,
  case_id     TEXT NOT NULL,
  rank        INTEGER NOT NULL,                    -- 발행 시점 정렬 스냅샷(hero=1)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, briefing_id, case_id),
  FOREIGN KEY (company_id, briefing_id) REFERENCES briefings(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id)
);

-- ---------------------------------------------------------------------------
-- 4.10 알림 — P3 (N05b는 개별 푸시 금지라 타입 자체가 없다)
-- ---------------------------------------------------------------------------

CREATE TABLE notifications (
  id                TEXT PRIMARY KEY,
  company_id        TEXT NOT NULL REFERENCES companies(id),
  recipient_user_id TEXT NOT NULL,
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
                      ('queued','held','suppressed')),
  scheduled_for     TIMESTAMPTZ,
  case_id           TEXT,
  run_id            TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, dedupe_key),
  FOREIGN KEY (company_id, recipient_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, run_id) REFERENCES runs(company_id, id)
);
CREATE INDEX ix_notifications_recipient ON notifications (recipient_user_id, status);

-- ---------------------------------------------------------------------------
-- 4.11 온보딩·수집 — P3
-- ---------------------------------------------------------------------------

CREATE TABLE csv_imports (
  id                  TEXT PRIMARY KEY,
  company_id          TEXT NOT NULL REFERENCES companies(id),
  uploaded_by_user_id TEXT NOT NULL,
  filename            TEXT NOT NULL,               -- 원본 파일은 스캔 후 폐기 — 결과만 보존
  row_count           INTEGER NOT NULL DEFAULT 0,
  ok_count            INTEGER NOT NULL DEFAULT 0,
  error_count         INTEGER NOT NULL DEFAULT 0,
  error_rows          JSON CHECK (error_rows IS NULL OR json_valid(error_rows)),
  status              TEXT NOT NULL DEFAULT 'validating'
                      CHECK (status IN ('validating','failed','applied')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id, uploaded_by_user_id) REFERENCES memberships(company_id, user_id)
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
  consented_by_user_id TEXT NOT NULL, -- owner 명시 동의 필수
  consented_at         TIMESTAMPTZ NOT NULL,
  revoked_at           TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (company_id, case_type),
  FOREIGN KEY (company_id, consented_by_user_id) REFERENCES memberships(company_id, user_id)
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
-- DB guardrails that require predicates beyond a foreign key.
-- ---------------------------------------------------------------------------

CREATE TRIGGER document_requirements_citation_must_be_global_insert
BEFORE INSERT ON document_requirements
WHEN NEW.citation_id IS NOT NULL
 AND EXISTS (SELECT 1 FROM citations WHERE id = NEW.citation_id AND company_id IS NOT NULL)
BEGIN SELECT RAISE(ABORT, 'document requirement citation must be global'); END;

CREATE TRIGGER evidence_context_must_match_case_insert
BEFORE INSERT ON evidence_events
WHEN (NEW.action_id IS NOT NULL AND (
       NEW.case_id IS NULL
       OR NOT EXISTS (
         SELECT 1 FROM next_actions
         WHERE company_id = NEW.company_id AND case_id = NEW.case_id AND id = NEW.action_id
       )
     ))
 OR (NEW.approval_id IS NOT NULL AND (
       NEW.case_id IS NULL OR NEW.action_id IS NULL
       OR NOT EXISTS (
         SELECT 1 FROM approvals
         WHERE company_id = NEW.company_id AND case_id = NEW.case_id
           AND action_id = NEW.action_id AND id = NEW.approval_id
       )
     ))
BEGIN SELECT RAISE(ABORT, 'evidence action and approval must match its case'); END;

CREATE TRIGGER memberships_inviter_active_insert
BEFORE INSERT ON memberships
WHEN NEW.invited_by IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.invited_by AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'membership inviter must be an active member'); END;

CREATE TRIGGER memberships_inviter_active_update
BEFORE UPDATE OF company_id, invited_by ON memberships
WHEN NEW.invited_by IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.invited_by AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'membership inviter must be an active member'); END;

CREATE TRIGGER delegations_members_active_insert
BEFORE INSERT ON delegations
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.delegator_user_id
    AND status = 'active' AND role = 'owner'
) OR NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.delegate_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'delegation members must be active and delegator an owner'); END;

CREATE TRIGGER delegations_members_active_update
BEFORE UPDATE OF company_id, delegator_user_id, delegate_user_id ON delegations
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.delegator_user_id
    AND status = 'active' AND role = 'owner'
) OR NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.delegate_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'delegation members must be active and delegator an owner'); END;

CREATE TRIGGER cases_assignee_active_insert
BEFORE INSERT ON cases
WHEN NEW.assignee_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.assignee_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'case assignee must be an active member'); END;

CREATE TRIGGER cases_assignee_active_update
BEFORE UPDATE OF company_id, assignee_user_id ON cases
WHEN NEW.assignee_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.assignee_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'case assignee must be an active member'); END;

CREATE TRIGGER runs_starter_active_insert
BEFORE INSERT ON runs
WHEN NEW.started_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.started_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'run starter must be an active member'); END;

CREATE TRIGGER runs_starter_active_update
BEFORE UPDATE OF company_id, started_by_user_id ON runs
WHEN NEW.started_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.started_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'run starter must be an active member'); END;

CREATE TRIGGER approvals_members_active_insert
BEFORE INSERT ON approvals
WHEN (NEW.requested_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.requested_by_user_id AND status = 'active'
)) OR (NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.decided_by_user_id AND status = 'active'
)) OR (NEW.on_behalf_of_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.on_behalf_of_user_id AND status = 'active'
))
BEGIN SELECT RAISE(ABORT, 'approval users must be active members'); END;

CREATE TRIGGER approvals_members_active_update
BEFORE UPDATE OF company_id, requested_by_user_id, decided_by_user_id, on_behalf_of_user_id ON approvals
WHEN (NEW.requested_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.requested_by_user_id AND status = 'active'
)) OR (NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.decided_by_user_id AND status = 'active'
)) OR (NEW.on_behalf_of_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.on_behalf_of_user_id AND status = 'active'
))
BEGIN SELECT RAISE(ABORT, 'approval users must be active members'); END;

CREATE TRIGGER approvals_decider_role_insert
BEFORE INSERT ON approvals
WHEN NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1
  FROM memberships m
  JOIN companies c ON c.id = m.company_id
  JOIN cases cs ON cs.company_id = NEW.company_id AND cs.id = NEW.case_id
  WHERE m.company_id = NEW.company_id
    AND m.user_id = NEW.decided_by_user_id
    AND m.status = 'active'
    AND (
      m.role = 'owner'
      OR (c.approval_policy = 'manager_allowed' AND m.role = 'manager'
          AND cs.severity = 'LOW')
    )
)
BEGIN SELECT RAISE(ABORT, 'approval decider is not allowed by company policy'); END;

CREATE TRIGGER approvals_decider_role_update
BEFORE UPDATE OF company_id, case_id, decided_by_user_id ON approvals
WHEN NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1
  FROM memberships m
  JOIN companies c ON c.id = m.company_id
  JOIN cases cs ON cs.company_id = NEW.company_id AND cs.id = NEW.case_id
  WHERE m.company_id = NEW.company_id
    AND m.user_id = NEW.decided_by_user_id
    AND m.status = 'active'
    AND (
      m.role = 'owner'
      OR (c.approval_policy = 'manager_allowed' AND m.role = 'manager'
          AND cs.severity = 'LOW')
    )
)
BEGIN SELECT RAISE(ABORT, 'approval decider is not allowed by company policy'); END;

CREATE TRIGGER evidence_actor_active_insert
BEFORE INSERT ON evidence_events
WHEN NEW.actor_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.actor_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'evidence actor must be an active member'); END;

CREATE TRIGGER interpretations_confirmer_active_insert
BEFORE INSERT ON interpretations
WHEN NEW.confirmed_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.confirmed_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'interpretation confirmer must be an active member'); END;

CREATE TRIGGER interpretations_confirmer_active_update
BEFORE UPDATE OF company_id, confirmed_by_user_id ON interpretations
WHEN NEW.confirmed_by_user_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.confirmed_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'interpretation confirmer must be an active member'); END;

CREATE TRIGGER package_exports_exporter_active_insert
BEFORE INSERT ON package_exports
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.exported_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'package exporter must be an active member'); END;

CREATE TRIGGER package_exports_exporter_active_update
BEFORE UPDATE OF company_id, exported_by_user_id ON package_exports
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.exported_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'package exporter must be an active member'); END;

CREATE TRIGGER notifications_recipient_active_insert
BEFORE INSERT ON notifications
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.recipient_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'notification recipient must be an active member'); END;

CREATE TRIGGER notifications_recipient_active_update
BEFORE UPDATE OF company_id, recipient_user_id ON notifications
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.recipient_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'notification recipient must be an active member'); END;

CREATE TRIGGER csv_imports_uploader_active_insert
BEFORE INSERT ON csv_imports
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.uploaded_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'csv uploader must be an active member'); END;

CREATE TRIGGER csv_imports_uploader_active_update
BEFORE UPDATE OF company_id, uploaded_by_user_id ON csv_imports
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.uploaded_by_user_id AND status = 'active'
)
BEGIN SELECT RAISE(ABORT, 'csv uploader must be an active member'); END;

CREATE TRIGGER autonomy_grants_owner_active_insert
BEFORE INSERT ON autonomy_grants
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.consented_by_user_id
    AND status = 'active' AND role = 'owner'
)
BEGIN SELECT RAISE(ABORT, 'autonomy consent requires an active owner'); END;

CREATE TRIGGER autonomy_grants_owner_active_update
BEFORE UPDATE OF company_id, consented_by_user_id ON autonomy_grants
WHEN NOT EXISTS (
  SELECT 1 FROM memberships
  WHERE company_id = NEW.company_id AND user_id = NEW.consented_by_user_id
    AND status = 'active' AND role = 'owner'
)
BEGIN SELECT RAISE(ABORT, 'autonomy consent requires an active owner'); END;

CREATE TRIGGER document_requirements_citation_must_be_global_update
BEFORE UPDATE OF citation_id ON document_requirements
WHEN NEW.citation_id IS NOT NULL
 AND EXISTS (SELECT 1 FROM citations WHERE id = NEW.citation_id AND company_id IS NOT NULL)
BEGIN SELECT RAISE(ABORT, 'document requirement citation must be global'); END;

CREATE TRIGGER citations_company_scope_immutable
BEFORE UPDATE OF company_id ON citations
WHEN NEW.company_id IS NOT OLD.company_id
BEGIN SELECT RAISE(ABORT, 'citation company scope is immutable'); END;

CREATE TRIGGER case_citations_scope_insert
BEFORE INSERT ON case_citations
WHEN NOT EXISTS (
  SELECT 1 FROM citations
  WHERE id = NEW.citation_id
    AND (company_id IS NULL OR company_id = NEW.company_id)
)
BEGIN SELECT RAISE(ABORT, 'citation must be global or belong to the same company'); END;

CREATE TRIGGER case_citations_scope_update
BEFORE UPDATE OF company_id, citation_id ON case_citations
WHEN NOT EXISTS (
  SELECT 1 FROM citations
  WHERE id = NEW.citation_id
    AND (company_id IS NULL OR company_id = NEW.company_id)
)
BEGIN SELECT RAISE(ABORT, 'citation must be global or belong to the same company'); END;

CREATE TRIGGER workers_clear_case_worker_before_delete
BEFORE DELETE ON workers
BEGIN
  UPDATE cases
  SET worker_id = NULL
  WHERE company_id = OLD.company_id AND worker_id = OLD.id;
END;

-- A case cannot be created as if a human decision had already occurred.
CREATE TRIGGER cases_terminal_state_not_insertable
BEFORE INSERT ON cases
WHEN NEW.state IN ('human_approved', 'completed')
BEGIN SELECT RAISE(ABORT, 'case must begin before an approved action'); END;

CREATE TRIGGER cases_human_approval_transition
BEFORE UPDATE OF state ON cases
WHEN NEW.state = 'human_approved'
 AND OLD.state <> 'human_approved'
 AND (
   OLD.state <> 'approval_pending'
   OR NOT EXISTS (
     SELECT 1 FROM approvals
     WHERE company_id = NEW.company_id AND case_id = NEW.id AND status = 'approved'
   )
 )
BEGIN SELECT RAISE(ABORT, 'case human approval requires an approved case action'); END;

CREATE TRIGGER cases_completion_transition
BEFORE UPDATE OF state ON cases
WHEN NEW.state = 'completed'
 AND OLD.state <> 'completed'
 AND (
   OLD.state <> 'human_approved'
   OR NOT EXISTS (
     SELECT 1
     FROM approvals a
     JOIN next_actions n
       ON n.company_id = a.company_id AND n.case_id = a.case_id AND n.id = a.action_id
     WHERE a.company_id = NEW.company_id
       AND a.case_id = NEW.id
       AND a.status = 'approved'
       AND n.action_type = 'complete_case'
   )
)
BEGIN SELECT RAISE(ABORT, 'case completion requires an approved completion action'); END;

CREATE TRIGGER cases_terminal_state_immutable
BEFORE UPDATE OF state ON cases
WHEN OLD.state IN ('completed', 'blocked') AND NEW.state <> OLD.state
BEGIN SELECT RAISE(ABORT, 'terminal case state is immutable'); END;

CREATE TRIGGER cases_state_transition_whitelist
BEFORE UPDATE OF state ON cases
WHEN OLD.state NOT IN ('completed', 'blocked')
 AND NEW.state <> OLD.state
 AND NOT (
   (OLD.state = 'draft' AND NEW.state = 'risk_review')
   OR (OLD.state = 'risk_review' AND NEW.state IN ('approval_pending', 'blocked'))
   OR (OLD.state = 'approval_pending' AND NEW.state IN ('human_approved', 'returned', 'blocked'))
   OR (OLD.state = 'returned' AND NEW.state = 'approval_pending')
   OR (OLD.state = 'human_approved' AND NEW.state IN ('completed', 'blocked'))
 )
BEGIN SELECT RAISE(ABORT, 'case state transition is not allowed'); END;

CREATE TRIGGER approvals_require_approval_action_insert
BEFORE INSERT ON approvals
WHEN NOT EXISTS (
  SELECT 1 FROM next_actions
  WHERE company_id = NEW.company_id
    AND case_id = NEW.case_id
    AND id = NEW.action_id
    AND requires_approval = 1
)
BEGIN SELECT RAISE(ABORT, 'approval action must require approval'); END;

CREATE TRIGGER approvals_must_start_pending
BEFORE INSERT ON approvals
WHEN NEW.status <> 'pending'
BEGIN SELECT RAISE(ABORT, 'approval must start pending'); END;

CREATE TRIGGER approvals_target_immutable
BEFORE UPDATE OF company_id, case_id, action_id ON approvals
BEGIN SELECT RAISE(ABORT, 'approval target is immutable'); END;

CREATE TRIGGER approvals_require_approval_action_update
BEFORE UPDATE OF company_id, case_id, action_id ON approvals
WHEN NOT EXISTS (
  SELECT 1 FROM next_actions
  WHERE company_id = NEW.company_id
    AND case_id = NEW.case_id
    AND id = NEW.action_id
    AND requires_approval = 1
)
BEGIN SELECT RAISE(ABORT, 'approval action must require approval'); END;

CREATE TRIGGER approvals_terminal_immutable
BEFORE UPDATE ON approvals
WHEN OLD.status <> 'pending'
BEGIN SELECT RAISE(ABORT, 'terminal approval is immutable'); END;

-- 취소/삭제로 승인 이력을 없애지 않는다. pending 취소도 별도 감사 정책이
-- 확정되기 전까지는 지원하지 않는다.
CREATE TRIGGER approvals_no_delete
BEFORE DELETE ON approvals
BEGIN SELECT RAISE(ABORT, 'approval deletion is not allowed'); END;

CREATE TRIGGER approvals_pending_transition_only
BEFORE UPDATE OF status ON approvals
WHEN OLD.status = 'pending' AND NEW.status NOT IN ('approved','rejected')
BEGIN SELECT RAISE(ABORT, 'approval must transition from pending to a decision'); END;

CREATE TRIGGER approvals_sync_linked_drafts
AFTER UPDATE OF status ON approvals
WHEN OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected')
BEGIN
  UPDATE drafts
  SET status = NEW.status
  WHERE company_id = NEW.company_id
    AND case_id = NEW.case_id
    AND approval_id = NEW.id
    AND status = 'pending_approval';
END;

CREATE TRIGGER approvals_sync_linked_handoff_packages
AFTER UPDATE OF status ON approvals
WHEN OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected')
BEGIN
  UPDATE handoff_packages
  SET status = NEW.status
  WHERE company_id = NEW.company_id
    AND case_id = NEW.case_id
    AND approval_id = NEW.id
    AND status = 'pending_approval';
END;

CREATE TRIGGER next_actions_contract_immutable_after_approval
BEFORE UPDATE OF company_id, case_id, action_type, requires_approval ON next_actions
WHEN EXISTS (
  SELECT 1 FROM approvals
  WHERE company_id = OLD.company_id AND case_id = OLD.case_id AND action_id = OLD.id
)
BEGIN SELECT RAISE(ABORT, 'approved action contract is immutable'); END;

CREATE TRIGGER drafts_locked_payload_update
BEFORE UPDATE OF case_id, thread_id, created_by_run_id, channel, purpose,
                 compliance_checks, expected_scenarios ON drafts
WHEN OLD.status NOT IN ('draft', 'revision_requested')
BEGIN SELECT RAISE(ABORT, 'draft content is locked while approval is active or decided'); END;

CREATE TRIGGER draft_variants_editable_parent_insert
BEFORE INSERT ON draft_variants
WHEN NOT EXISTS (
  SELECT 1 FROM drafts
  WHERE company_id = NEW.company_id AND id = NEW.draft_id
    AND status IN ('draft', 'revision_requested')
)
BEGIN SELECT RAISE(ABORT, 'draft variants require an editable draft'); END;

CREATE TRIGGER draft_variants_editable_parent_update
BEFORE UPDATE ON draft_variants
WHEN NOT EXISTS (
  SELECT 1 FROM drafts
  WHERE company_id = OLD.company_id AND id = OLD.draft_id
    AND status IN ('draft', 'revision_requested')
) OR NOT EXISTS (
  SELECT 1 FROM drafts
  WHERE company_id = NEW.company_id AND id = NEW.draft_id
    AND status IN ('draft', 'revision_requested')
)
BEGIN SELECT RAISE(ABORT, 'draft variants require an editable draft'); END;

CREATE TRIGGER draft_variants_editable_parent_delete
BEFORE DELETE ON draft_variants
WHEN NOT EXISTS (
  SELECT 1 FROM drafts
  WHERE company_id = OLD.company_id AND id = OLD.draft_id
    AND status IN ('draft', 'revision_requested')
)
BEGIN SELECT RAISE(ABORT, 'draft variants require an editable draft'); END;

CREATE TRIGGER drafts_approval_state_insert
BEFORE INSERT ON drafts
WHEN NOT (
  (NEW.status IN ('draft','revision_requested','superseded') AND NEW.approval_id IS NULL)
  OR
  (NEW.status = 'pending_approval' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'pending' AND n.action_type = 'send_message'
  ))
)
BEGIN SELECT RAISE(ABORT, 'draft must start editable or pending approval'); END;

CREATE TRIGGER drafts_approval_state_update
BEFORE UPDATE OF company_id, case_id, status, approval_id ON drafts
WHEN NOT (
  (NEW.status IN ('draft','revision_requested','superseded') AND NEW.approval_id IS NULL)
  OR
  (NEW.status = 'pending_approval' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'pending' AND n.action_type = 'send_message'
  ))
  OR
  (NEW.status = 'approved' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'approved' AND n.action_type = 'send_message'
  ))
  OR
  (NEW.status = 'rejected' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'rejected' AND n.action_type = 'send_message'
  ))
)
BEGIN SELECT RAISE(ABORT, 'draft status requires a matching message approval'); END;

-- 승인에 한 번 연결된 초안은 요청 대상을 바꾸거나 승인 전 편집 상태로 되돌릴 수
-- 없다. 결정 상태 변경은 부모 approval의 상태와 일치해야 하며, parent trigger가
-- pending_approval → approved|rejected를 동기화한다.
CREATE TRIGGER drafts_approval_link_immutable
BEFORE UPDATE OF approval_id ON drafts
WHEN OLD.approval_id IS NOT NULL
 AND NEW.approval_id IS NOT OLD.approval_id
BEGIN SELECT RAISE(ABORT, 'draft approval link is immutable'); END;

CREATE TRIGGER drafts_approval_transition_guard
BEFORE UPDATE OF status ON drafts
WHEN
  (OLD.status = 'pending_approval'
   AND NEW.status NOT IN ('pending_approval','approved','rejected'))
  OR
  (OLD.status IN ('approved','rejected') AND NEW.status <> OLD.status)
  OR
  (NEW.status IN ('approved','rejected')
   AND NEW.status <> OLD.status
   AND OLD.status <> 'pending_approval')
BEGIN SELECT RAISE(ABORT, 'draft approval state cannot be reopened or skipped'); END;

CREATE TRIGGER handoff_approval_state_insert
BEFORE INSERT ON handoff_packages
WHEN NOT (
  (NEW.status = 'draft' AND NEW.approval_id IS NULL)
  OR
  (NEW.status = 'pending_approval' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'pending' AND n.action_type = 'create_handoff'
  ))
)
BEGIN SELECT RAISE(ABORT, 'handoff package must start draft or pending approval'); END;

CREATE TRIGGER handoff_approval_state_update
BEFORE UPDATE OF company_id, case_id, status, approval_id ON handoff_packages
WHEN NOT (
  (NEW.status = 'draft' AND NEW.approval_id IS NULL)
  OR
  (NEW.status = 'pending_approval' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'pending' AND n.action_type = 'create_handoff'
  ))
  OR
  (NEW.status IN ('approved','exported') AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'approved' AND n.action_type = 'create_handoff'
  ))
  OR
  (NEW.status = 'rejected' AND EXISTS (
    SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
      AND a.status = 'rejected' AND n.action_type = 'create_handoff'
  ))
)
BEGIN SELECT RAISE(ABORT, 'handoff status requires a matching handoff approval'); END;

-- package도 초안과 같은 방식으로 한 approval에 고정한다. approved 상태에서의
-- exported 전이만 내부 PDF 산출물 기록에 맞춰 허용하고, 그 밖의 재개·재결정은
-- 막는다.
CREATE TRIGGER handoff_packages_approval_link_immutable
BEFORE UPDATE OF approval_id ON handoff_packages
WHEN OLD.approval_id IS NOT NULL
 AND NEW.approval_id IS NOT OLD.approval_id
BEGIN SELECT RAISE(ABORT, 'handoff approval link is immutable'); END;

CREATE TRIGGER handoff_packages_approval_transition_guard
BEFORE UPDATE OF status ON handoff_packages
WHEN
  (OLD.status = 'pending_approval'
   AND NEW.status NOT IN ('pending_approval','approved','rejected'))
  OR
  (OLD.status = 'approved' AND NEW.status NOT IN ('approved','exported'))
  OR
  (OLD.status IN ('rejected','exported') AND NEW.status <> OLD.status)
  OR
  (NEW.status IN ('approved','rejected')
   AND NEW.status <> OLD.status
   AND OLD.status <> 'pending_approval')
  OR
  (NEW.status = 'exported'
   AND NEW.status <> OLD.status
   AND (
     OLD.status <> 'approved'
     OR NOT EXISTS (
       SELECT 1 FROM package_exports
       WHERE company_id = NEW.company_id AND package_id = NEW.id
     )
   ))
BEGIN SELECT RAISE(ABORT, 'handoff approval state cannot be reopened, skipped, or exported without a PDF'); END;

CREATE TRIGGER handoff_package_payload_locked_update
BEFORE UPDATE OF case_id, package_type, masked_payload, included_items ON handoff_packages
WHEN OLD.status <> 'draft'
BEGIN SELECT RAISE(ABORT, 'handoff package content is locked while approval is active or decided'); END;

CREATE TRIGGER package_exports_require_approved_package
BEFORE INSERT ON package_exports
WHEN NOT EXISTS (
  SELECT 1 FROM handoff_packages hp JOIN approvals a ON a.id = hp.approval_id
  WHERE hp.company_id = NEW.company_id AND hp.id = NEW.package_id
    AND hp.status IN ('approved','exported') AND a.status = 'approved'
)
BEGIN SELECT RAISE(ABORT, 'package export requires an approved handoff package'); END;

CREATE TRIGGER package_exports_require_approved_package_update
BEFORE UPDATE OF company_id, package_id ON package_exports
WHEN NOT EXISTS (
  SELECT 1 FROM handoff_packages hp JOIN approvals a ON a.id = hp.approval_id
  WHERE hp.company_id = NEW.company_id AND hp.id = NEW.package_id
    AND hp.status IN ('approved','exported') AND a.status = 'approved'
)
BEGIN SELECT RAISE(ABORT, 'package export requires an approved handoff package'); END;

-- 내부 PDF가 실제로 만들어질 때만 package 상태를 exported로 남긴다. 이 트리거
-- 밖에서 exported 상태만 먼저 기록하는 경로는 handoff state guard가 막는다.
CREATE TRIGGER package_exports_mark_package_exported
AFTER INSERT ON package_exports
BEGIN
  UPDATE handoff_packages
  SET status = 'exported'
  WHERE company_id = NEW.company_id
    AND id = NEW.package_id
    AND status = 'approved';
END;

CREATE TRIGGER agent_notes_subject_scope_insert
BEFORE INSERT ON agent_notes
WHEN (NEW.subject_type = 'worker' AND NOT EXISTS (
  SELECT 1 FROM workers WHERE id = NEW.subject_id AND company_id = NEW.company_id
)) OR (NEW.subject_type = 'company' AND (NEW.subject_id IS NULL OR NEW.subject_id <> NEW.company_id))
 OR (NEW.subject_type = 'expert' AND NOT EXISTS (
   SELECT 1 FROM memberships
   WHERE company_id = NEW.company_id AND user_id = NEW.subject_id
     AND role = 'expert' AND status = 'active'
 ))
BEGIN SELECT RAISE(ABORT, 'agent note subject must belong to the same company'); END;

CREATE TRIGGER agent_notes_subject_scope_update
BEFORE UPDATE OF company_id, subject_type, subject_id ON agent_notes
WHEN (NEW.subject_type = 'worker' AND NOT EXISTS (
  SELECT 1 FROM workers WHERE id = NEW.subject_id AND company_id = NEW.company_id
)) OR (NEW.subject_type = 'company' AND (NEW.subject_id IS NULL OR NEW.subject_id <> NEW.company_id))
 OR (NEW.subject_type = 'expert' AND NOT EXISTS (
   SELECT 1 FROM memberships
   WHERE company_id = NEW.company_id AND user_id = NEW.subject_id
     AND role = 'expert' AND status = 'active'
 ))
BEGIN SELECT RAISE(ABORT, 'agent note subject must belong to the same company'); END;

-- ---------------------------------------------------------------------------
-- 파생값 뷰(문서 §6) — "저장하지 않는다"의 실행 형태. 필요 시 셀렉터/뷰만 추가
-- ---------------------------------------------------------------------------

-- 사용 가능 근거(F등급 제외) — 승인 게이트 판정은 반드시 이 뷰(또는 동일 필터)를 거친다
CREATE VIEW v_global_usable_citations AS
SELECT * FROM citations WHERE company_id IS NULL AND status <> 'internal' AND grade <> 'F';

-- 근거별 연계 케이스 수(linkedCaseCount)
CREATE VIEW v_citation_link_counts AS
SELECT cc.company_id, cc.citation_id, COUNT(*) AS linked_case_count
FROM case_citations cc
GROUP BY cc.company_id, cc.citation_id;

-- 케이스 파생값: dDay(조회 시점 기준) · 누락 서류 수 · 사용 가능 근거 수
CREATE VIEW v_case_derived AS
SELECT
  cs.id AS case_id,
  cs.company_id,
  CAST(julianday(cs.due_date) - julianday(date('now')) AS INTEGER) AS d_day,
  (SELECT COUNT(*) FROM worker_documents wd
    WHERE wd.company_id = cs.company_id AND wd.worker_id = cs.worker_id AND wd.status = 'missing') AS missing_doc_count,
  (SELECT COUNT(*) FROM case_citations cc JOIN citations c2
    ON c2.id = cc.citation_id
      AND c2.grade <> 'F'
      AND (c2.company_id IS NULL OR c2.company_id = cs.company_id)
    WHERE cc.company_id = cs.company_id AND cc.case_id = cs.id) AS usable_citation_count
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
