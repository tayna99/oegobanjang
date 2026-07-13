-- ============================================================================
-- 외고반장 서비스 DB — 실행 가능 DDL (PostgreSQL 16+)
-- 정본 문서: docs/DB_SCHEMA.md — 이 파일은 그 문서 §4를 그대로 내린 것.
-- 스키마를 바꾸려면 문서와 이 파일을 같은 PR에서 함께 고친다.
--
-- 사용법: db/README.md 참조. 깨끗한 DB(또는 스키마)에 이 스크립트를 그대로 실행한다.
--   psql "$DATABASE_URL" -f db/schema.sql
-- FK는 PostgreSQL이 항상 강제한다(SQLite의 PRAGMA foreign_keys 같은 연결 스위치 불필요).
--
-- 표기 규약
--  * id           : text(앱이 UUIDv7 발급). 데모 시드는 가독성을 위해 슬러그 사용
--  * timestamptz  : PG 네이티브. 기본값 now()
--  * boolean      : PG 네이티브(true/false) — SQLite의 0/1+CHECK 관용은 쓰지 않는다
--  * jsonb        : PG 네이티브(입력 시 자동 검증) — SQLite의 json_valid CHECK 불필요
--  * 파생값(dDay·완성도·KPI)은 컬럼이 없다 — 문서 §6, 말미 뷰 참조
--  * DB 가드레일: 단순 FK/CHECK로 표현 못 하는 규칙은 트리거 함수로 강제(파일 하단)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.1 테넌트·계정
-- ---------------------------------------------------------------------------

CREATE TABLE companies (
  id                 text PRIMARY KEY,
  name               text NOT NULL,
  business_number    text,
  industry           text,
  region             text,
  worker_count_band  text NOT NULL DEFAULT '5_20'
                     CHECK (worker_count_band IN ('lt5','5_20','20_50','gt50')),
  timezone           text NOT NULL DEFAULT 'Asia/Seoul',
  briefing_time      text NOT NULL DEFAULT '08:30',
  approval_policy    text NOT NULL DEFAULT 'owner_only'
                     CHECK (approval_policy IN ('owner_only','manager_allowed')),
  autonomy_level     text NOT NULL DEFAULT 'L2' CHECK (autonomy_level IN ('L1','L2','L3')),
  onboarding_step    text NOT NULL DEFAULT 'O1'
                     CHECK (onboarding_step IN ('O1','O2','O3','O4','O5','done')),
  onboarding_path    text CHECK (onboarding_path IN ('ocr','manual','csv','agency')),
  case_seq           integer NOT NULL DEFAULT 0,  -- case_code 발급 카운터(§9)
  evidence_seq       integer NOT NULL DEFAULT 0,  -- 판단 기록 번호(#NNNN) 발급 카운터(§9)
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id                    text PRIMARY KEY,
  phone                 text NOT NULL UNIQUE,      -- 로그인 식별자(O1). PII — 표시 시 마스킹
  name                  text NOT NULL,             -- evidence actor 표시에 사용
  email                 text,
  pin_hash              text,                      -- 승인 본인확인 PIN(7단계 §4) — 해시만
  biometric_registered  boolean NOT NULL DEFAULT false,
  terms_agreed_at       timestamptz NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  id                 text PRIMARY KEY,
  company_id         text NOT NULL REFERENCES companies(id),
  user_id            text REFERENCES users(id),   -- 초대 수락 전 NULL
  role               text NOT NULL CHECK (role IN ('owner','manager','viewer','expert')),
  status             text NOT NULL DEFAULT 'active' CHECK (status IN ('invited','active','removed')),
  invite_phone       text,
  invite_token       text UNIQUE,
  invite_expires_at  timestamptz,                 -- 초대 링크 만료 7일(3단계 §6)
  invited_by         text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  UNIQUE (company_id, user_id),
  FOREIGN KEY (company_id, invited_by) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_memberships_company ON memberships (company_id, role);

-- 승인 위임(7단계 §3.1) — P3
CREATE TABLE delegations (
  id                 text PRIMARY KEY,
  company_id         text NOT NULL REFERENCES companies(id),
  delegator_user_id  text NOT NULL,
  delegate_user_id   text NOT NULL,
  scope              text NOT NULL DEFAULT 'approval' CHECK (scope IN ('approval')),
  starts_at          timestamptz NOT NULL,
  ends_at            timestamptz NOT NULL,
  revoked_at         timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, delegator_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, delegate_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_delegations_company ON delegations (company_id, ends_at);

-- ---------------------------------------------------------------------------
-- 4.2 근로자·서류
-- ---------------------------------------------------------------------------

CREATE TABLE workers (
  id                     text PRIMARY KEY,
  company_id             text NOT NULL REFERENCES companies(id),
  display_name           text NOT NULL,            -- "Nguyen Van A"
  nationality            text NOT NULL,            -- 무채색 운영 정보로만(차별 금지)
  team                   text,                     -- "제조1팀"
  visa_type              text NOT NULL DEFAULT 'E-9',
  stay_expires_at        date NOT NULL,            -- 체류만료일 — D-day 계산의 필수 재료
  contract_ends_at       date,                     -- 있으면 충돌 감지 활성
  contact_channel        text,
  preferred_language     text CHECK (preferred_language IN ('ko','vi','id','en')),
  registration_no_masked text,                     -- '900101-*******' — 원문 컬럼은 존재하지 않음(§7)
  source                 text NOT NULL DEFAULT 'manual'
                         CHECK (source IN ('manual','ocr','csv','agency')),
  status                 text NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active','inactive','left')),
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id)
);
CREATE INDEX ix_workers_company ON workers (company_id, status);
CREATE INDEX ix_workers_stay_expiry ON workers (company_id, stay_expires_at);

-- 근거 라이브러리(중앙 스토어) — company_id NULL = 전역 공식 근거
CREATE TABLE citations (
  id                  text PRIMARY KEY,            -- 'cit_001' 표시 코드 = PK(전역 시퀀스)
  company_id          text REFERENCES companies(id),
  grade               text NOT NULL CHECK (grade IN ('A','B','C','E','F')),
  status              text NOT NULL CHECK (status IN ('official','review_needed','stale','internal')),
  title               text NOT NULL,
  source              text NOT NULL,
  source_url          text,
  effective_date      date,
  ingest_at           timestamptz NOT NULL,
  chroma_collection   text,                        -- Chroma 청크 포인터(메타데이터 미러링만)
  chroma_document_id  text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CHECK (company_id IS NOT NULL OR status <> 'internal')
);
CREATE INDEX ix_citations_status ON citations (status, grade);

-- 필수 서류 정의(전역 참조 — company_id 없음)
CREATE TABLE document_requirements (
  id           text PRIMARY KEY,
  case_type    text NOT NULL,
  visa_type    text NOT NULL,
  required_doc text NOT NULL,
  required     boolean NOT NULL DEFAULT true,
  citation_id  text REFERENCES citations(id),      -- "왜 필요한지" 근거
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (case_type, visa_type, required_doc)
);

CREATE TABLE worker_documents (
  id           text PRIMARY KEY,
  company_id   text NOT NULL REFERENCES companies(id),
  worker_id    text NOT NULL,
  doc_type     text NOT NULL,
  status       text NOT NULL DEFAULT 'missing'
               CHECK (status IN ('missing','requested','received','expiring','company_check','pending')),
  due_date     date,
  expires_at   date,
  file_ref     text,                               -- 암호화 저장소 키(경로 원문 아님)
  submitted_at timestamptz,
  reviewed_at  timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (worker_id, doc_type),
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_worker_documents_company ON worker_documents (company_id, status);

-- O4-A 촬영 원본 포인터 — P3
CREATE TABLE worker_intake_files (
  id                 text PRIMARY KEY,
  company_id         text NOT NULL REFERENCES companies(id),
  worker_id          text,
  storage_key        text NOT NULL,                -- 암호화 스토리지 키(이미지·OCR 원문은 DB 밖)
  ocr_fields_masked  jsonb,
  status             text NOT NULL DEFAULT 'uploaded'
                     CHECK (status IN ('uploaded','ocr_done','confirmed','failed')),
  created_at         timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_worker_intake_files_company ON worker_intake_files (company_id, status);

-- ---------------------------------------------------------------------------
-- 4.3 케이스 코어
-- ---------------------------------------------------------------------------

CREATE TABLE cases (
  id                  text PRIMARY KEY,
  company_id          text NOT NULL REFERENCES companies(id),
  case_code           text NOT NULL,               -- "case_002" 회사별 발급(§9)
  worker_id           text,
  case_type           text NOT NULL CHECK (case_type IN
                        ('visa_expiry','missing_document','contract_visa_conflict',
                         'reporting_deadline','quota_review','hiring','onboarding','other')),
  title               text NOT NULL,               -- 업무 단위 명칭(근로자명 미포함)
  summary             text,                        -- 케이스 시트 요약 1문장(마스킹 적용)
  severity            text NOT NULL CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
  state               text NOT NULL DEFAULT 'draft' CHECK (state IN
                        ('draft','risk_review','approval_pending','returned',
                         'human_approved','completed','blocked')),
  agent_stage         text CHECK (agent_stage IN
                        ('detected','collecting','drafted','awaiting_approval','executed')),
  due_date            date,                        -- D-day 앵커. dDay는 저장하지 않음(§6)
  assignee_user_id    text,
  approval_required   boolean NOT NULL DEFAULT false,
  prepared_by         text NOT NULL DEFAULT 'rule' CHECK (prepared_by IN ('agent','rule')),
  prepared_run_id     text,                        -- 순환 FK(runs.case_id↔)
  parent_case_id      text,                        -- 런 체이닝(9단계 P0-2)
  guard_note          text,                        -- high risk 경고문(Rule Engine 산출)
  checked_items       jsonb,
  next_wake_at        timestamptz,
  next_wake_condition text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  UNIQUE (company_id, case_code),
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id),
  FOREIGN KEY (company_id, assignee_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, parent_case_id) REFERENCES cases(company_id, id)
  -- cases.prepared_run_id → runs FK는 runs 생성 후 ALTER로 추가(순환 참조, 아래)
);
CREATE INDEX ix_cases_company_state ON cases (company_id, state);
CREATE INDEX ix_cases_company_severity_due ON cases (company_id, severity, due_date);
-- 케이스 재사용 규칙(레거시 PRD §15 승계): 열린 케이스 중복 생성 방지
CREATE UNIQUE INDEX ux_cases_reuse ON cases (company_id, worker_id, case_type, due_date)
  WHERE state IN ('draft','risk_review','approval_pending','returned');

-- 에이전트 런(툴콜링 루프 1회)
CREATE TABLE runs (
  id                  text PRIMARY KEY,
  company_id          text NOT NULL REFERENCES companies(id),
  case_id             text,                        -- 커맨드 런 초기엔 NULL 가능
  started_by          text NOT NULL CHECK (started_by IN ('user','event')),
  trigger_event       text,                        -- "D-30 진입" 등
  started_by_user_id  text,
  agent_name          text NOT NULL,
  autonomy            text NOT NULL DEFAULT 'medium' CHECK (autonomy IN ('low','medium','high')),
  status              text NOT NULL DEFAULT 'queued' CHECK (status IN
                        ('queued','running','waiting_question','waiting_approval',
                         'completed','failed','cancelled')),
  goal_text           text,                        -- 사용자 명령(저장 전 PII 스크럽)
  question            jsonb,
  result_summary      text,
  anchor_event_no     integer,                     -- "런 1건 = 판단 기록 # 1건"(§9)
  parent_run_id       text,
  priority_hint       text,
  started_at          timestamptz,
  ended_at            timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (company_id, started_by_user_id) REFERENCES memberships(company_id, user_id),
  FOREIGN KEY (company_id, parent_run_id) REFERENCES runs(company_id, id)
);
CREATE INDEX ix_runs_company ON runs (company_id, status);
CREATE INDEX ix_runs_case ON runs (case_id);

-- 순환 FK 해소: cases.prepared_run_id → runs (runs 생성 후, 지연 제약)
ALTER TABLE cases
  ADD CONSTRAINT cases_prepared_run_fk
  FOREIGN KEY (company_id, prepared_run_id) REFERENCES runs(company_id, id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE run_steps (
  id           text PRIMARY KEY,
  company_id   text NOT NULL REFERENCES companies(id),
  run_id       text NOT NULL,
  seq          integer NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('thinking','tool_call','guardrail','handoff','replan')),
  label        text NOT NULL,
  detail       text,                               -- 마스킹된 상세
  tool_name    text,
  tool_status  text CHECK (tool_status IN ('running','done','failed','blocked')),
  handoff_from text,
  handoff_to   text,
  payload_hash text,                               -- 입출력 해시(원문 미저장)
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, run_id, seq),
  FOREIGN KEY (company_id, run_id) REFERENCES runs(company_id, id) ON DELETE CASCADE
);

CREATE TABLE next_actions (
  id                text PRIMARY KEY,
  company_id        text NOT NULL REFERENCES companies(id),
  case_id           text NOT NULL,
  kind              text NOT NULL CHECK (kind IN ('approve','draft','detail','thread','package','confirm')),
  action_type       text NOT NULL CHECK (action_type IN
                      ('request_document','create_handoff','send_message','confirm_status',
                       'export_package','complete_case','other')),
  label             text NOT NULL,
  state             text NOT NULL DEFAULT 'ready' CHECK (state IN ('ready','locked','scheduled','waiting')),
  requires_approval boolean NOT NULL DEFAULT false,
  slot              text CHECK (slot IN ('primary','secondary')),
  scheduled_at      timestamptz,                   -- state='scheduled' 도래 시각 — N13 소스
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CHECK (
    action_type NOT IN ('send_message','create_handoff','export_package','complete_case')
    OR requires_approval
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
  id                    text PRIMARY KEY,
  company_id            text NOT NULL REFERENCES companies(id),
  case_id               text NOT NULL,
  action_id             text NOT NULL,
  status                text NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','rejected')),
  -- 결정 멱등 키는 decide() 시점에만 채운다. pending 승인에서는 NULL을 허용하며,
  -- NULL끼리는 UNIQUE 충돌하지 않는다.
  idempotency_key       text UNIQUE,               -- 중복 승인 차단(GOTCHAS §2)
  requested_by_actor    text NOT NULL CHECK (requested_by_actor IN ('agent','rule','user')),
  requested_by_user_id  text,
  decided_by_user_id    text,
  on_behalf_of_user_id  text, -- 대리 승인 시 위임자(7단계 §5)
  identity_method       text CHECK (identity_method IN ('pin','biometric')),
  checklist             jsonb, -- M2.6 §2c 4항목
  reason                text,                      -- 반려 사유(서비스 계층 PII 패턴 차단)
  requested_at          timestamptz NOT NULL,
  decided_at            timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now(),
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
  company_id      text NOT NULL REFERENCES companies(id),
  case_id         text NOT NULL,
  citation_id     text NOT NULL REFERENCES citations(id),
  added_by_actor  text NOT NULL CHECK (added_by_actor IN ('agent','rule','user')),
  added_by_run_id text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (company_id, case_id, citation_id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, added_by_run_id) REFERENCES runs(company_id, id)
);
CREATE INDEX ix_case_citations_citation ON case_citations (citation_id);

-- ---------------------------------------------------------------------------
-- 4.5 판단 기록 — append-only (수정·삭제는 트리거가 차단)
-- ---------------------------------------------------------------------------

CREATE TABLE evidence_events (
  id              text PRIMARY KEY,
  company_id      text NOT NULL REFERENCES companies(id),
  event_no        integer NOT NULL,                -- 회사별 단조 증가 — 표시 "#4789"(§9)
  type            text NOT NULL CHECK (type IN
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
  at              timestamptz NOT NULL,            -- 발생 시각(주입 가능 — 테스트 결정성)
  case_id         text,
  action_id       text,
  approval_id     text,
  run_id          text,
  actor_type      text NOT NULL CHECK (actor_type IN ('system','user','agent','approver')),
  actor_user_id   text,
  actor_display   text,                            -- "김담당 (본인 확인 완료)" — 마스킹된 표시 문자열
  summary         text NOT NULL,                   -- PII 마스킹된 한 줄 요약만. 원문 전문 금지
  input_hash      text,                            -- 'sha256:…' (프론트 hash = input_hash)
  output_hash     text,
  hash_algorithm  text NOT NULL DEFAULT 'sha256',
  trace_id        text,
  request_id      text,
  payload_ref     text,
  created_at      timestamptz NOT NULL DEFAULT now(),
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

-- ---------------------------------------------------------------------------
-- 4.7 초안·소통
-- ---------------------------------------------------------------------------

-- 컨택 스레드(근로자 단위 — 탭별 §3.1)
CREATE TABLE threads (
  id              text PRIMARY KEY,
  company_id      text NOT NULL REFERENCES companies(id),
  worker_id       text NOT NULL,
  channel         text NOT NULL,
  last_message_at timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  UNIQUE (company_id, worker_id),                  -- MVP: 근로자당 1스레드
  FOREIGN KEY (company_id, worker_id) REFERENCES workers(company_id, id) ON DELETE CASCADE
);

-- 메시지 초안(M3)
CREATE TABLE drafts (
  id                 text PRIMARY KEY,
  company_id         text NOT NULL REFERENCES companies(id),
  case_id            text NOT NULL,
  thread_id          text,
  created_by_run_id  text,
  channel            text NOT NULL,
  purpose            text NOT NULL,
  status             text NOT NULL DEFAULT 'draft' CHECK (status IN
                       ('draft','revision_requested','pending_approval','approved','rejected','superseded')),
  approval_id        text,
  compliance_checks  jsonb,
  expected_scenarios jsonb,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, thread_id) REFERENCES threads(company_id, id),
  FOREIGN KEY (company_id, created_by_run_id) REFERENCES runs(company_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id)
);
CREATE INDEX ix_drafts_case ON drafts (case_id, status);

CREATE TABLE draft_variants (
  id         text PRIMARY KEY,
  company_id text NOT NULL REFERENCES companies(id),
  draft_id   text NOT NULL,
  lang       text NOT NULL CHECK (lang IN ('ko','vi','id','en')),
  text       text NOT NULL,                        -- 전문 저장 — §7 접근 규칙, evidence 복사 금지
  is_revised boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, draft_id) REFERENCES drafts(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_draft_variants_draft ON draft_variants (draft_id);

CREATE TABLE thread_messages (
  id            text PRIMARY KEY,
  thread_id     text NOT NULL,
  company_id    text NOT NULL REFERENCES companies(id),
  direction     text NOT NULL CHECK (direction IN ('inbound','system')),
  draft_id      text,
  lang          text,
  body_original text,                              -- 원문 전문(PII) — 스레드 상세 전용(§7)
  body_ko       text,
  received_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, thread_id) REFERENCES threads(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, draft_id) REFERENCES drafts(company_id, id)
);
CREATE INDEX ix_thread_messages_thread ON thread_messages (thread_id, created_at);

-- 응답 해석(M6) — 제안은 언제나 비확정(isFinal=false는 성격 자체라 컬럼 없음)
CREATE TABLE interpretations (
  id                   text PRIMARY KEY,
  company_id           text NOT NULL REFERENCES companies(id),
  thread_message_id    text NOT NULL,
  case_id              text,
  summary_ko           text NOT NULL,              -- 한국어 요약(마스킹)
  confidence           text NOT NULL CHECK (confidence IN ('high','low')),
  status               text NOT NULL DEFAULT 'proposed'
                       CHECK (status IN ('proposed','confirmed','discarded')),
  confirmed_by_user_id text,
  confirmed_at         timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, thread_message_id) REFERENCES thread_messages(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, confirmed_by_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_interpretations_company ON interpretations (company_id, status);

CREATE TABLE status_update_proposals (
  id                text PRIMARY KEY,
  company_id        text NOT NULL REFERENCES companies(id),
  interpretation_id text NOT NULL,
  target_type       text NOT NULL,                 -- 예: worker_document
  target_key        text NOT NULL,                 -- 예: "여권 사본"
  from_value        text NOT NULL,
  to_value          text NOT NULL,
  status            text NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed','confirmed','rejected')),
  created_at        timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, interpretation_id) REFERENCES interpretations(company_id, id) ON DELETE CASCADE
);
CREATE INDEX ix_sup_interpretation ON status_update_proposals (interpretation_id);

-- ---------------------------------------------------------------------------
-- 4.8 행정사 패키지
-- ---------------------------------------------------------------------------

CREATE TABLE handoff_packages (
  id             text PRIMARY KEY,
  company_id     text NOT NULL REFERENCES companies(id),
  case_id        text NOT NULL,
  package_type   text NOT NULL CHECK (package_type IN ('expert_review','pre_entry')),
  masked_payload jsonb NOT NULL,                   -- allowlist 필드만(§7)
  included_items jsonb,
  status         text NOT NULL DEFAULT 'draft' CHECK (status IN
                   ('draft','pending_approval','approved','rejected','exported')),
  approval_id    text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id),
  FOREIGN KEY (company_id, case_id, approval_id) REFERENCES approvals(company_id, case_id, id)
);
CREATE INDEX ix_handoff_packages_company ON handoff_packages (company_id, status);
CREATE INDEX ix_handoff_packages_case ON handoff_packages (case_id);

CREATE TABLE package_exports (
  id                          text PRIMARY KEY,
  package_id                  text NOT NULL,
  company_id                  text NOT NULL REFERENCES companies(id),
  format                      text NOT NULL CHECK (format = 'pdf'), -- MVP: 내부 PDF 산출물만
  content_hash                text NOT NULL,       -- 산출물 해시만(원문 없음)
  exported_by_user_id         text NOT NULL,
  external_delivery_performed boolean NOT NULL DEFAULT false
                              CHECK (external_delivery_performed = false), -- MVP 외부 전송 없음
  created_at                  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, package_id) REFERENCES handoff_packages(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, exported_by_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_package_exports_package ON package_exports (package_id);

-- MVP에는 외부 전달 링크를 만들지 않는다. delivery adapter 마일스톤에서 별도 migration으로 도입한다.

-- ---------------------------------------------------------------------------
-- 4.9 브리핑
-- ---------------------------------------------------------------------------

CREATE TABLE briefings (
  id                   text PRIMARY KEY,
  company_id           text NOT NULL REFERENCES companies(id),
  briefing_date        date NOT NULL,              -- 회사 timezone 기준
  generated_at         timestamptz NOT NULL,
  source_snapshot_hash text NOT NULL,              -- non-PII 운영 필드만으로 계산(§4.9)
  rerun_count          integer NOT NULL DEFAULT 0,
  last_refreshed_at    timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, id),
  UNIQUE (company_id, briefing_date)               -- 같은 날 재실행은 갱신
);

CREATE TABLE briefing_items (
  id          text PRIMARY KEY,
  company_id  text NOT NULL REFERENCES companies(id),
  briefing_id text NOT NULL,
  case_id     text NOT NULL,
  rank        integer NOT NULL,                    -- 발행 시점 정렬 스냅샷(hero=1)
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, briefing_id, case_id),
  FOREIGN KEY (company_id, briefing_id) REFERENCES briefings(company_id, id) ON DELETE CASCADE,
  FOREIGN KEY (company_id, case_id) REFERENCES cases(company_id, id)
);

-- ---------------------------------------------------------------------------
-- 4.10 알림 — P3 (N05b는 개별 푸시 금지라 타입 자체가 없다)
-- ---------------------------------------------------------------------------

CREATE TABLE notifications (
  id                text PRIMARY KEY,
  company_id        text NOT NULL REFERENCES companies(id),
  recipient_user_id text NOT NULL,
  type              text NOT NULL CHECK (type IN
                      ('N01','N02','N03','N04','N05','N06','N07',
                       'N10','N11','N12','N13','N14','N20','N21','N22')),
  priority          text NOT NULL CHECK (priority IN ('P1','P2','P3')),
  title             text NOT NULL,                 -- 마스킹 적용(2단계 §5.3)
  body              text NOT NULL,
  deeplink_path     text NOT NULL,                 -- 'case/{id}/approve' — 딥링크 계약과 1:1
  notification_key  text UNIQUE,                   -- 알림톡 nk 파라미터
  dedupe_key        text NOT NULL,                 -- '{case}:{type}:{threshold}' idempotency
  channel           text NOT NULL CHECK (channel IN ('push','alimtalk','email')),
  status            text NOT NULL DEFAULT 'queued' CHECK (status IN
                      ('queued','held','suppressed')),
  scheduled_for     timestamptz,
  case_id           text,
  run_id            text,
  created_at        timestamptz NOT NULL DEFAULT now(),
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
  id                  text PRIMARY KEY,
  company_id          text NOT NULL REFERENCES companies(id),
  uploaded_by_user_id text NOT NULL,
  filename            text NOT NULL,               -- 원본 파일은 스캔 후 폐기 — 결과만 보존
  row_count           integer NOT NULL DEFAULT 0,
  ok_count            integer NOT NULL DEFAULT 0,
  error_count         integer NOT NULL DEFAULT 0,
  error_rows          jsonb,
  status              text NOT NULL DEFAULT 'validating'
                      CHECK (status IN ('validating','failed','applied')),
  created_at          timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (company_id, uploaded_by_user_id) REFERENCES memberships(company_id, user_id)
);
CREATE INDEX ix_csv_imports_company ON csv_imports (company_id);

-- ---------------------------------------------------------------------------
-- 4.12 에이전틱 확장 — P3
-- ---------------------------------------------------------------------------

CREATE TABLE autonomy_grants (
  id                   text PRIMARY KEY,
  company_id           text NOT NULL REFERENCES companies(id),
  case_type            text NOT NULL,
  level                text NOT NULL CHECK (level IN ('L1','L2','L3')),
  consented_by_user_id text NOT NULL, -- owner 명시 동의 필수
  consented_at         timestamptz NOT NULL,
  revoked_at           timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, case_type),
  FOREIGN KEY (company_id, consented_by_user_id) REFERENCES memberships(company_id, user_id)
);

-- 에이전트 운영 메모(P2-7) — 사용자 열람·삭제 가능(append-only 원칙의 명시적 예외)
CREATE TABLE agent_notes (
  id           text PRIMARY KEY,
  company_id   text NOT NULL REFERENCES companies(id),
  subject_type text NOT NULL CHECK (subject_type IN ('worker','company','expert')),
  subject_id   text,
  -- 카테고리 화이트리스트 — 성실도·성격·이탈 추정 계열은 스키마 차원 금지(GOTCHAS §1)
  category     text NOT NULL CHECK (category IN
                 ('response_pattern','deadline_practice','format_preference','channel_preference')),
  note         text NOT NULL,                      -- 관찰 사실만
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_agent_notes_subject ON agent_notes (company_id, subject_type, subject_id);

-- 집계 스냅샷(파생 캐시 — 재계산 가능, 정본 아님)
CREATE TABLE stat_snapshots (
  id            text PRIMARY KEY,
  company_id    text NOT NULL REFERENCES companies(id),
  snapshot_date date NOT NULL,
  counts        jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, snapshot_date)
);

-- ===========================================================================
-- DB 가드레일 — 단순 FK/CHECK로 표현 못 하는 규칙을 트리거 함수로 강제한다.
-- PostgreSQL 트리거의 WHEN 절은 서브쿼리를 쓸 수 없으므로 조건 판정은 함수 본문에서 한다.
-- SQLite 원본의 INSERT/UPDATE 쌍은 NEW-only 로직이면 하나의 함수 + `INSERT OR UPDATE OF`
-- 트리거로 통합했다(메시지 문자열은 원본과 동일하게 유지 — 검증 스크립트가 substring 비교).
-- ===========================================================================

-- 판단 기록 append-only(문서 §5.2)
CREATE FUNCTION trg_evidence_events_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'evidence_events is append-only';
END;
$$;
CREATE TRIGGER evidence_events_no_update BEFORE UPDATE ON evidence_events
  FOR EACH ROW EXECUTE FUNCTION trg_evidence_events_immutable();
CREATE TRIGGER evidence_events_no_delete BEFORE DELETE ON evidence_events
  FOR EACH ROW EXECUTE FUNCTION trg_evidence_events_immutable();

-- document_requirements.citation_id 는 전역 근거(company_id IS NULL)만
CREATE FUNCTION trg_doc_req_citation_global() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.citation_id IS NOT NULL
     AND EXISTS (SELECT 1 FROM citations WHERE id = NEW.citation_id AND company_id IS NOT NULL) THEN
    RAISE EXCEPTION 'document requirement citation must be global';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER document_requirements_citation_global
  BEFORE INSERT OR UPDATE OF citation_id ON document_requirements
  FOR EACH ROW EXECUTE FUNCTION trg_doc_req_citation_global();

-- evidence 의 action/approval 참조는 같은 케이스 소속이어야 한다
CREATE FUNCTION trg_evidence_context_match() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.action_id IS NOT NULL AND (
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
      )) THEN
    RAISE EXCEPTION 'evidence action and approval must match its case';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER evidence_context_must_match_case
  BEFORE INSERT ON evidence_events
  FOR EACH ROW EXECUTE FUNCTION trg_evidence_context_match();

-- membership 초대자는 활성 멤버여야 한다
CREATE FUNCTION trg_memberships_inviter_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.invited_by IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.invited_by AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'membership inviter must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER memberships_inviter_active
  BEFORE INSERT OR UPDATE OF company_id, invited_by ON memberships
  FOR EACH ROW EXECUTE FUNCTION trg_memberships_inviter_active();

-- 위임 당사자: delegator=활성 owner, delegate=활성 멤버
CREATE FUNCTION trg_delegations_members_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.delegator_user_id
      AND status = 'active' AND role = 'owner'
  ) OR NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.delegate_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'delegation members must be active and delegator an owner';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER delegations_members_active
  BEFORE INSERT OR UPDATE OF company_id, delegator_user_id, delegate_user_id ON delegations
  FOR EACH ROW EXECUTE FUNCTION trg_delegations_members_active();

-- 케이스 담당자는 활성 멤버여야 한다
CREATE FUNCTION trg_cases_assignee_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.assignee_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.assignee_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'case assignee must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER cases_assignee_active
  BEFORE INSERT OR UPDATE OF company_id, assignee_user_id ON cases
  FOR EACH ROW EXECUTE FUNCTION trg_cases_assignee_active();

-- 런 시작자는 활성 멤버여야 한다
CREATE FUNCTION trg_runs_starter_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.started_by_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.started_by_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'run starter must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER runs_starter_active
  BEFORE INSERT OR UPDATE OF company_id, started_by_user_id ON runs
  FOR EACH ROW EXECUTE FUNCTION trg_runs_starter_active();

-- 승인 관련 사용자(요청/결정/대리)는 활성 멤버여야 한다
CREATE FUNCTION trg_approvals_members_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.requested_by_user_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.requested_by_user_id AND status = 'active'
     )) OR (NEW.decided_by_user_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.decided_by_user_id AND status = 'active'
     )) OR (NEW.on_behalf_of_user_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM memberships WHERE company_id = NEW.company_id AND user_id = NEW.on_behalf_of_user_id AND status = 'active'
     )) THEN
    RAISE EXCEPTION 'approval users must be active members';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER approvals_members_active
  BEFORE INSERT OR UPDATE OF company_id, requested_by_user_id, decided_by_user_id, on_behalf_of_user_id ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_members_active();

-- 승인 결정자 role 정책: owner, 또는 (manager_allowed 회사 + manager + 케이스 severity LOW)
CREATE FUNCTION trg_approvals_decider_role() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER approvals_decider_role
  BEFORE INSERT OR UPDATE OF company_id, case_id, decided_by_user_id ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_decider_role();

-- evidence actor(사람)는 활성 멤버여야 한다(append-only이라 INSERT만)
CREATE FUNCTION trg_evidence_actor_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.actor_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.actor_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'evidence actor must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER evidence_actor_active
  BEFORE INSERT ON evidence_events
  FOR EACH ROW EXECUTE FUNCTION trg_evidence_actor_active();

-- 응답 해석 확인자는 활성 멤버여야 한다
CREATE FUNCTION trg_interpretations_confirmer_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.confirmed_by_user_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.confirmed_by_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'interpretation confirmer must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER interpretations_confirmer_active
  BEFORE INSERT OR UPDATE OF company_id, confirmed_by_user_id ON interpretations
  FOR EACH ROW EXECUTE FUNCTION trg_interpretations_confirmer_active();

-- 패키지 내보낸 사람은 활성 멤버여야 한다
CREATE FUNCTION trg_package_exports_exporter_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.exported_by_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'package exporter must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER package_exports_exporter_active
  BEFORE INSERT OR UPDATE OF company_id, exported_by_user_id ON package_exports
  FOR EACH ROW EXECUTE FUNCTION trg_package_exports_exporter_active();

-- 알림 수신자는 활성 멤버여야 한다
CREATE FUNCTION trg_notifications_recipient_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.recipient_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'notification recipient must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER notifications_recipient_active
  BEFORE INSERT OR UPDATE OF company_id, recipient_user_id ON notifications
  FOR EACH ROW EXECUTE FUNCTION trg_notifications_recipient_active();

-- CSV 업로더는 활성 멤버여야 한다
CREATE FUNCTION trg_csv_imports_uploader_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.uploaded_by_user_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'csv uploader must be an active member';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER csv_imports_uploader_active
  BEFORE INSERT OR UPDATE OF company_id, uploaded_by_user_id ON csv_imports
  FOR EACH ROW EXECUTE FUNCTION trg_csv_imports_uploader_active();

-- 자율성 승급 동의자는 활성 owner여야 한다
CREATE FUNCTION trg_autonomy_grants_owner_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memberships
    WHERE company_id = NEW.company_id AND user_id = NEW.consented_by_user_id
      AND status = 'active' AND role = 'owner'
  ) THEN
    RAISE EXCEPTION 'autonomy consent requires an active owner';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER autonomy_grants_owner_active
  BEFORE INSERT OR UPDATE OF company_id, consented_by_user_id ON autonomy_grants
  FOR EACH ROW EXECUTE FUNCTION trg_autonomy_grants_owner_active();

-- 근거의 company 스코프는 불변
CREATE FUNCTION trg_citations_scope_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.company_id IS DISTINCT FROM OLD.company_id THEN
    RAISE EXCEPTION 'citation company scope is immutable';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER citations_company_scope_immutable
  BEFORE UPDATE OF company_id ON citations
  FOR EACH ROW EXECUTE FUNCTION trg_citations_scope_immutable();

-- case_citations 는 전역 근거이거나 같은 회사 근거여야 한다
CREATE FUNCTION trg_case_citations_scope() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM citations
    WHERE id = NEW.citation_id AND (company_id IS NULL OR company_id = NEW.company_id)
  ) THEN
    RAISE EXCEPTION 'citation must be global or belong to the same company';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER case_citations_scope
  BEFORE INSERT OR UPDATE OF company_id, citation_id ON case_citations
  FOR EACH ROW EXECUTE FUNCTION trg_case_citations_scope();

-- worker 삭제 시 참조 케이스의 worker_id를 NULL로(테넌트 키는 보존)
CREATE FUNCTION trg_workers_clear_case_worker() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  UPDATE cases SET worker_id = NULL
  WHERE company_id = OLD.company_id AND worker_id = OLD.id;
  RETURN OLD;
END;
$$;
CREATE TRIGGER workers_clear_case_worker_before_delete
  BEFORE DELETE ON workers
  FOR EACH ROW EXECUTE FUNCTION trg_workers_clear_case_worker();

-- 케이스는 사람 결정이 이미 일어난 상태로 생성될 수 없다
CREATE FUNCTION trg_cases_terminal_not_insertable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.state IN ('human_approved', 'completed') THEN
    RAISE EXCEPTION 'case must begin before an approved action';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER cases_terminal_state_not_insertable
  BEFORE INSERT ON cases
  FOR EACH ROW EXECUTE FUNCTION trg_cases_terminal_not_insertable();

-- 케이스 상태 전이 규칙(전이 화이트리스트 + 승인/완료 근거 + 종착 불변)
CREATE FUNCTION trg_cases_state_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.state = OLD.state THEN
    RETURN NEW;
  END IF;

  -- 종착 상태는 불변
  IF OLD.state IN ('completed', 'blocked') THEN
    RAISE EXCEPTION 'terminal case state is immutable';
  END IF;

  -- 전이 화이트리스트(docs/DB_SCHEMA.md §5.1, src/stores/caseStore.ts와 동일)
  IF NOT (
    (OLD.state = 'draft' AND NEW.state = 'risk_review')
    OR (OLD.state = 'risk_review' AND NEW.state IN ('approval_pending', 'blocked'))
    OR (OLD.state = 'approval_pending' AND NEW.state IN ('human_approved', 'returned', 'blocked'))
    OR (OLD.state = 'returned' AND NEW.state = 'approval_pending')
    OR (OLD.state = 'human_approved' AND NEW.state IN ('completed', 'blocked'))
  ) THEN
    RAISE EXCEPTION 'case state transition is not allowed';
  END IF;

  -- human_approved 는 승인된 케이스 액션이 있어야 한다
  IF NEW.state = 'human_approved' AND NOT EXISTS (
    SELECT 1 FROM approvals
    WHERE company_id = NEW.company_id AND case_id = NEW.id AND status = 'approved'
  ) THEN
    RAISE EXCEPTION 'case human approval requires an approved case action';
  END IF;

  -- completed 는 승인된 complete_case 액션이 있어야 한다
  IF NEW.state = 'completed' AND NOT EXISTS (
    SELECT 1
    FROM approvals a
    JOIN next_actions n ON n.company_id = a.company_id AND n.case_id = a.case_id AND n.id = a.action_id
    WHERE a.company_id = NEW.company_id AND a.case_id = NEW.id
      AND a.status = 'approved' AND n.action_type = 'complete_case'
  ) THEN
    RAISE EXCEPTION 'case completion requires an approved completion action';
  END IF;

  RETURN NEW;
END;
$$;
CREATE TRIGGER cases_state_transition
  BEFORE UPDATE OF state ON cases
  FOR EACH ROW EXECUTE FUNCTION trg_cases_state_transition();

-- 승인 대상 액션은 requires_approval=true 여야 한다
CREATE FUNCTION trg_approvals_require_approval_action() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM next_actions
    WHERE company_id = NEW.company_id AND case_id = NEW.case_id
      AND id = NEW.action_id AND requires_approval
  ) THEN
    RAISE EXCEPTION 'approval action must require approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER approvals_require_approval_action
  BEFORE INSERT OR UPDATE OF company_id, case_id, action_id ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_require_approval_action();

-- 승인은 pending 으로 시작해야 한다
CREATE FUNCTION trg_approvals_must_start_pending() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status <> 'pending' THEN
    RAISE EXCEPTION 'approval must start pending';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER approvals_must_start_pending
  BEFORE INSERT ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_must_start_pending();

-- 승인 대상(company/case/action)은 불변, 상태 전이는 pending→approved/rejected만
CREATE FUNCTION trg_approvals_update_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- 대상 불변
  IF NEW.company_id IS DISTINCT FROM OLD.company_id
     OR NEW.case_id IS DISTINCT FROM OLD.case_id
     OR NEW.action_id IS DISTINCT FROM OLD.action_id THEN
    RAISE EXCEPTION 'approval target is immutable';
  END IF;
  -- 종착 승인은 불변
  IF OLD.status <> 'pending' THEN
    RAISE EXCEPTION 'terminal approval is immutable';
  END IF;
  -- pending 은 approved/rejected 로만 전이
  IF NEW.status NOT IN ('approved', 'rejected') THEN
    RAISE EXCEPTION 'approval must transition from pending to a decision';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER approvals_update_guard
  BEFORE UPDATE ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_update_guard();

-- 종착 승인 삭제 금지
-- 취소/삭제로 승인 이력을 없애지 않는다. pending 취소도 별도 감사 정책이 확정되기 전까지 미지원.
CREATE FUNCTION trg_approvals_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'approval deletion is not allowed';
END;
$$;
CREATE TRIGGER approvals_no_delete
  BEFORE DELETE ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_no_delete();

-- 승인 결정 시 연결된 draft 상태 동기화(pending_approval → 결정값)
CREATE FUNCTION trg_approvals_sync_drafts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected') THEN
    UPDATE drafts
    SET status = NEW.status
    WHERE company_id = NEW.company_id AND case_id = NEW.case_id
      AND approval_id = NEW.id AND status = 'pending_approval';
  END IF;
  RETURN NULL;
END;
$$;
CREATE TRIGGER approvals_sync_linked_drafts
  AFTER UPDATE OF status ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_sync_drafts();

-- 승인 결정 시 연결된 handoff_package 상태 동기화
CREATE FUNCTION trg_approvals_sync_handoff() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected') THEN
    UPDATE handoff_packages
    SET status = NEW.status
    WHERE company_id = NEW.company_id AND case_id = NEW.case_id
      AND approval_id = NEW.id AND status = 'pending_approval';
  END IF;
  RETURN NULL;
END;
$$;
CREATE TRIGGER approvals_sync_linked_handoff_packages
  AFTER UPDATE OF status ON approvals
  FOR EACH ROW EXECUTE FUNCTION trg_approvals_sync_handoff();

-- 승인이 걸린 액션의 계약(유형·승인요구)은 불변
CREATE FUNCTION trg_next_actions_contract_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM approvals
    WHERE company_id = OLD.company_id AND case_id = OLD.case_id AND action_id = OLD.id
  ) THEN
    RAISE EXCEPTION 'approved action contract is immutable';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER next_actions_contract_immutable_after_approval
  BEFORE UPDATE OF company_id, case_id, action_type, requires_approval ON next_actions
  FOR EACH ROW EXECUTE FUNCTION trg_next_actions_contract_immutable();

-- 초안 본문은 draft/revision_requested 상태에서만 수정 가능
CREATE FUNCTION trg_drafts_locked_payload() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status NOT IN ('draft', 'revision_requested') THEN
    RAISE EXCEPTION 'draft content is locked while approval is active or decided';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER drafts_locked_payload_update
  BEFORE UPDATE OF case_id, thread_id, created_by_run_id, channel, purpose,
                   compliance_checks, expected_scenarios ON drafts
  FOR EACH ROW EXECUTE FUNCTION trg_drafts_locked_payload();

-- draft_variants 는 편집 가능한 초안(draft/revision_requested)에만 붙는다
CREATE FUNCTION trg_draft_variants_editable_parent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  rec record;
BEGIN
  rec := CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
  IF NOT EXISTS (
    SELECT 1 FROM drafts
    WHERE company_id = rec.company_id AND id = rec.draft_id
      AND status IN ('draft', 'revision_requested')
  ) THEN
    RAISE EXCEPTION 'draft variants require an editable draft';
  END IF;
  -- UPDATE는 OLD 부모도 편집 가능해야 함(부모 이동/교체 방지)
  IF TG_OP = 'UPDATE' AND NOT EXISTS (
    SELECT 1 FROM drafts
    WHERE company_id = OLD.company_id AND id = OLD.draft_id
      AND status IN ('draft', 'revision_requested')
  ) THEN
    RAISE EXCEPTION 'draft variants require an editable draft';
  END IF;
  RETURN rec;
END;
$$;
CREATE TRIGGER draft_variants_editable_parent
  BEFORE INSERT OR UPDATE OR DELETE ON draft_variants
  FOR EACH ROW EXECUTE FUNCTION trg_draft_variants_editable_parent();

-- 초안은 편집 가능(draft/revision_requested/superseded, approval 없음) 또는 pending_approval(대응
-- pending send_message 승인 존재)로만 생성된다. approved/rejected는 직접 INSERT할 수 없고 승인
-- 동기화(approvals_sync_linked_drafts)를 통해서만 도달한다.
CREATE FUNCTION trg_drafts_approval_state_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT (
    (NEW.status IN ('draft','revision_requested','superseded') AND NEW.approval_id IS NULL)
    OR (NEW.status = 'pending_approval' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'pending' AND n.action_type = 'send_message'
    ))
  ) THEN
    RAISE EXCEPTION 'draft must start editable or pending approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER drafts_approval_state_insert
  BEFORE INSERT ON drafts
  FOR EACH ROW EXECUTE FUNCTION trg_drafts_approval_state_insert();

-- 초안 상태 UPDATE는 대응하는 send_message 승인 상태와 정합해야 한다
CREATE FUNCTION trg_drafts_approval_state_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT (
    (NEW.status IN ('draft','revision_requested','superseded') AND NEW.approval_id IS NULL)
    OR (NEW.status = 'pending_approval' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'pending' AND n.action_type = 'send_message'
    ))
    OR (NEW.status = 'approved' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'approved' AND n.action_type = 'send_message'
    ))
    OR (NEW.status = 'rejected' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'rejected' AND n.action_type = 'send_message'
    ))
  ) THEN
    RAISE EXCEPTION 'draft status requires a matching message approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER drafts_approval_state_update
  BEFORE UPDATE OF company_id, case_id, status, approval_id ON drafts
  FOR EACH ROW EXECUTE FUNCTION trg_drafts_approval_state_update();

-- 승인에 한 번 연결된 초안은 요청 대상을 바꾸거나 승인 전 편집 상태로 되돌릴 수 없다.
CREATE FUNCTION trg_drafts_approval_link_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.approval_id IS NOT NULL AND NEW.approval_id IS DISTINCT FROM OLD.approval_id THEN
    RAISE EXCEPTION 'draft approval link is immutable';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER drafts_approval_link_immutable
  BEFORE UPDATE OF approval_id ON drafts
  FOR EACH ROW EXECUTE FUNCTION trg_drafts_approval_link_immutable();

-- 트리거 이름 주의: PostgreSQL은 같은 테이블의 BEFORE 트리거를 **이름 알파벳순**으로 발화한다
-- (SQLite는 생성순). link_immutable·reopen_guard(전이 가드)가 catch-all인 state_update보다 먼저
-- 발화해야 해당 위반에 맞는 메시지가 표면화되므로, 가드 트리거 이름을 state_update보다 앞서도록
-- 지었다(link < reopen < state).
CREATE FUNCTION trg_drafts_approval_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (OLD.status = 'pending_approval' AND NEW.status NOT IN ('pending_approval','approved','rejected'))
     OR (OLD.status IN ('approved','rejected') AND NEW.status <> OLD.status)
     OR (NEW.status IN ('approved','rejected') AND NEW.status <> OLD.status AND OLD.status <> 'pending_approval') THEN
    RAISE EXCEPTION 'draft approval state cannot be reopened or skipped';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER drafts_approval_reopen_guard
  BEFORE UPDATE OF status ON drafts
  FOR EACH ROW EXECUTE FUNCTION trg_drafts_approval_transition_guard();

-- 행정사 패키지는 draft(approval 없음) 또는 pending_approval(대응 pending create_handoff 승인)로만
-- 생성된다. approved/exported/rejected는 승인 동기화·export 기록을 통해서만 도달한다.
CREATE FUNCTION trg_handoff_approval_state_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT (
    (NEW.status = 'draft' AND NEW.approval_id IS NULL)
    OR (NEW.status = 'pending_approval' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'pending' AND n.action_type = 'create_handoff'
    ))
  ) THEN
    RAISE EXCEPTION 'handoff package must start draft or pending approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER handoff_approval_state_insert
  BEFORE INSERT ON handoff_packages
  FOR EACH ROW EXECUTE FUNCTION trg_handoff_approval_state_insert();

-- 행정사 패키지 상태 UPDATE는 대응하는 create_handoff 승인 상태와 정합해야 한다
CREATE FUNCTION trg_handoff_approval_state_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT (
    (NEW.status = 'draft' AND NEW.approval_id IS NULL)
    OR (NEW.status = 'pending_approval' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'pending' AND n.action_type = 'create_handoff'
    ))
    OR (NEW.status IN ('approved','exported') AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'approved' AND n.action_type = 'create_handoff'
    ))
    OR (NEW.status = 'rejected' AND EXISTS (
      SELECT 1 FROM approvals a JOIN next_actions n ON n.id = a.action_id
      WHERE a.company_id = NEW.company_id AND a.case_id = NEW.case_id AND a.id = NEW.approval_id
        AND a.status = 'rejected' AND n.action_type = 'create_handoff'
    ))
  ) THEN
    RAISE EXCEPTION 'handoff status requires a matching handoff approval';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER handoff_approval_state_update
  BEFORE UPDATE OF company_id, case_id, status, approval_id ON handoff_packages
  FOR EACH ROW EXECUTE FUNCTION trg_handoff_approval_state_update();

-- package도 초안과 같은 방식으로 한 approval에 고정한다.
CREATE FUNCTION trg_handoff_approval_link_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.approval_id IS NOT NULL AND NEW.approval_id IS DISTINCT FROM OLD.approval_id THEN
    RAISE EXCEPTION 'handoff approval link is immutable';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER handoff_approval_link_immutable
  BEFORE UPDATE OF approval_id ON handoff_packages
  FOR EACH ROW EXECUTE FUNCTION trg_handoff_approval_link_immutable();

-- approved에서의 exported 전이만, 그것도 내부 PDF 산출물(package_exports) 기록이 있을 때만 허용한다.
CREATE FUNCTION trg_handoff_approval_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (OLD.status = 'pending_approval' AND NEW.status NOT IN ('pending_approval','approved','rejected'))
     OR (OLD.status = 'approved' AND NEW.status NOT IN ('approved','exported'))
     OR (OLD.status IN ('rejected','exported') AND NEW.status <> OLD.status)
     OR (NEW.status IN ('approved','rejected') AND NEW.status <> OLD.status AND OLD.status <> 'pending_approval')
     OR (NEW.status = 'exported' AND NEW.status <> OLD.status AND (
           OLD.status <> 'approved'
           OR NOT EXISTS (
             SELECT 1 FROM package_exports
             WHERE company_id = NEW.company_id AND package_id = NEW.id
           )
         )) THEN
    RAISE EXCEPTION 'handoff approval state cannot be reopened, skipped, or exported without a PDF';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER handoff_approval_reopen_guard
  BEFORE UPDATE OF status ON handoff_packages
  FOR EACH ROW EXECUTE FUNCTION trg_handoff_approval_transition_guard();

-- 행정사 패키지 본문은 draft 상태에서만 수정 가능
CREATE FUNCTION trg_handoff_payload_locked() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status <> 'draft' THEN
    RAISE EXCEPTION 'handoff package content is locked while approval is active or decided';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER handoff_package_payload_locked_update
  BEFORE UPDATE OF case_id, package_type, masked_payload, included_items ON handoff_packages
  FOR EACH ROW EXECUTE FUNCTION trg_handoff_payload_locked();

-- 패키지 export 는 승인된 handoff_package 에만 가능
CREATE FUNCTION trg_package_exports_require_approved() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM handoff_packages hp JOIN approvals a ON a.id = hp.approval_id
    WHERE hp.company_id = NEW.company_id AND hp.id = NEW.package_id
      AND hp.status IN ('approved','exported') AND a.status = 'approved'
  ) THEN
    RAISE EXCEPTION 'package export requires an approved handoff package';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER package_exports_require_approved_package
  BEFORE INSERT OR UPDATE OF company_id, package_id ON package_exports
  FOR EACH ROW EXECUTE FUNCTION trg_package_exports_require_approved();

-- 내부 PDF가 실제로 만들어질 때만 package 상태를 exported로 남긴다(이 트리거 밖에서 exported만
-- 먼저 기록하는 경로는 handoff transition guard가 막는다).
CREATE FUNCTION trg_package_exports_mark_exported() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  UPDATE handoff_packages
  SET status = 'exported'
  WHERE company_id = NEW.company_id AND id = NEW.package_id AND status = 'approved';
  RETURN NULL;
END;
$$;
CREATE TRIGGER package_exports_mark_package_exported
  AFTER INSERT ON package_exports
  FOR EACH ROW EXECUTE FUNCTION trg_package_exports_mark_exported();

-- agent_notes.subject 는 같은 회사 소속이어야 한다(worker/company/expert)
CREATE FUNCTION trg_agent_notes_subject_scope() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.subject_type = 'worker' AND NOT EXISTS (
        SELECT 1 FROM workers WHERE id = NEW.subject_id AND company_id = NEW.company_id
     ))
     OR (NEW.subject_type = 'company' AND (NEW.subject_id IS NULL OR NEW.subject_id <> NEW.company_id))
     OR (NEW.subject_type = 'expert' AND NOT EXISTS (
        SELECT 1 FROM memberships
        WHERE company_id = NEW.company_id AND user_id = NEW.subject_id
          AND role = 'expert' AND status = 'active'
     )) THEN
    RAISE EXCEPTION 'agent note subject must belong to the same company';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER agent_notes_subject_scope
  BEFORE INSERT OR UPDATE OF company_id, subject_type, subject_id ON agent_notes
  FOR EACH ROW EXECUTE FUNCTION trg_agent_notes_subject_scope();

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
  (cs.due_date - CURRENT_DATE) AS d_day,
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
