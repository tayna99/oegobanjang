# Decisions

이 문서는 외고반장 프로젝트의 주요 기술/제품 의사결정을 기록한다.

---

## Decision 001: 초기 구조는 backend 중심으로 간다

### Date

TBD

### Context

API 서버와 Agent 실행 서버를 분리하는 구조도 고려했다.  
하지만 초기 MVP 단계에서 서버를 여러 개 운영하면 로컬 개발, 환경변수 관리, 포트 관리, CI 관리가 복잡해질 수 있다.

### Decision

초기 구조는 FastAPI backend 중심으로 구성한다.

Agent Runtime은 아래 경로에서 관리한다.

```txt
backend/app/agent_runtime/
```

### Consequence

장점:

- 로컬 실행이 단순하다.
- API와 Agent 상태 관리가 쉽다.
- 승인과 Evidence Log 저장 흐름이 단순하다.
- 팀원들이 같은 서버 기준으로 개발할 수 있다.

단점:

- Agent 실행이 무거워지면 backend 부하가 커질 수 있다.
- 추후 독립 배포가 필요해지면 분리 작업이 필요하다.

---

## Decision 002: AI는 판정자가 아니라 케이스 처리 보조자다

### Date

TBD

### Context

비자, 체류, 고용변동, 노무 이슈는 법적 책임이 발생할 수 있다.

### Decision

AI는 비자 가능 여부를 확정하지 않는다.  
공식 근거와 현재 상태를 바탕으로 확인할 항목, 누락 서류, 다음 안전 행동, 전문가 검토 지점을 제안한다.

### Consequence

- Safety Guardrail이 필수다.
- Human Approval이 필수다.
- Evidence Log가 필수다.

---

## Decision 003: RAG와 DB/Rule Base를 분리한다

### Date

TBD

### Context

RAG는 공식 근거 검색에는 강하지만 현재 직원 상태 관리에는 적합하지 않다.

### Decision

- 법령·절차·서식·안전자료는 RAG에 넣는다.
- 직원 상태·후보 상태·서류 보유 여부·D-day 계산은 DB/Rule Base에서 처리한다.

### Consequence

- `document_requirements.csv`가 중요하다.
- RAG는 “왜 필요한지”를 설명하는 근거 역할을 한다.

---

## Decision 004: 다국어 Contact Agent 저장은 초안과 후보 상태로 제한한다

### Date

TBD

### Context

다국어 Contact Agent는 메시지 초안, 근로자 답변 요약, 상태 업데이트 후보, Evidence Log 후보 이벤트를 생성한다.

이 결과를 운영 DB에 저장해야 담당자 승인, 반려, 수정, 감사 추적이 가능하다.
다만 외국인 근로자 메시지와 답변에는 개인정보 또는 민감한 상황 설명이 포함될 수 있다.

### Decision

- 다국어 메시지 초안 전문은 `contact_messages.korean_text`, `contact_messages.translated_text`에 저장한다.
- 초안 생성 시 `contact_messages.status=PENDING_APPROVAL`, `approval_required=true`, `sent_at=null`로 관리한다.
- Evidence Log에는 메시지 전문과 `worker_reply` 원문을 저장하지 않는다.
- Evidence Log에는 원문 없는 요약, source_id 목록, risk_flags, 승인 필요 여부만 저장한다.
- 상태 업데이트는 `status_update_candidates`에 후보로만 저장한다.
- 실제 발송과 실제 상태 반영은 approval 이후 별도 단계에서만 가능하다.

### Consequence

장점:

- 담당자가 메시지 초안을 검토하고 승인/반려할 수 있다.
- 감사 로그에는 필요한 근거와 요약만 남아 개인정보 노출 위험이 줄어든다.
- 근로자 서류 상태가 AI 응답만으로 확정 변경되지 않는다.

주의:

- `contact_messages`는 메시지 전문을 저장하므로 접근 권한과 보관 정책이 필요하다.
- `evidence_logs.summary`에는 개인정보 원문을 넣지 않도록 service 계층에서 추가 검증이 필요하다.

---

## Decision 005: Handoff Package는 저장 가능한 초안이지만 자동 전달하지 않는다

### Date

2026-05-06

### Context

Aggregator 이후 고위험 케이스 또는 명시적 전문가 전달 케이스에서는 handoff package draft가 생성된다.
이 draft는 담당자가 나중에 조회하고 승인/반려할 수 있어야 하지만, 전문가에게 자동 전달되면 안 된다.

### Decision

- `handoff_package_drafts` 테이블에 전문가 검토용 초안을 저장한다.
- 저장은 LangGraph `user_message` 경로에서 top-level `persist_result=true`일 때만 수행한다.
- Contact Runtime `user_request` 경로는 기존처럼 `input_payload.persist_result`를 사용하며, 현재 handoff draft를 저장하지 않는다.
- `package_json`은 allowlist 기반 sanitize JSON만 저장한다.
- `worker_id`는 DB relation 필드로만 저장하고, `package_json`과 API response draft body에는 저장하지 않는다.
- `company_id`는 handoff draft 조회/승인 scope 검사용으로 저장한다.
- MVP/demo 단계의 조회 API는 `X-Company-Id` header와 draft의 `company_id`를 비교해 접근을 제한한다.
- `X-Company-Id`가 없거나 scope가 다르면 `403 Forbidden`으로 차단한다.
- 초안 생성 시 `approval_required=true`, `approval.status=PENDING`, `transferred_at=null`을 유지한다.
- approve/reject API는 review decision만 저장한다.
- 승인 시 `handoff_package_drafts.status=APPROVED`, `approvals.status=APPROVED`로 변경하지만 `transferred_at=null`을 유지한다.
- 반려 시 `handoff_package_drafts.status=REJECTED`, `approvals.status=REJECTED`로 변경하지만 `transferred_at=null`을 유지한다.
- 이미 승인/반려된 draft 재처리는 `409 Conflict`로 차단한다.
- 승인 후에도 실제 전문가 전달은 별도 실행 단계에서만 가능하다.

### Consequence

장점:

- handoff draft 생성 이력과 승인 이력을 추적할 수 있다.
- API response에는 safe summary만 노출하면서 DB에는 검토 가능한 초안을 보존할 수 있다.
- 전문가 전달과 초안 저장이 분리되어 자동 전달 사고를 줄인다.

주의:

- `package_json` sanitize allowlist를 계속 유지해야 한다.
- 향후 실제 전달 API를 만들 때도 별도 approval-required flow가 필요하다.
- 운영 전에는 `X-Company-Id` header 기반 MVP scope 검사를 인증 토큰 기반 company membership/role 검증으로 교체해야 한다.

---

## Decision 006: Agent output/audit 테이블은 company_id scope를 표준화한다

### Date

2026-05-07

### Context

`handoff_package_drafts`에는 `company_id` scope가 있지만, 기존 Contact Agent output과 Evidence Log에는 company scope가 없었다.
이미 persistence/API가 열린 테이블은 context table 구현보다 접근 제어 기준을 먼저 맞추는 것이 안전하다.

### Decision

- `contact_messages.company_id`를 추가한다.
- `status_update_candidates.company_id`를 추가한다.
- `evidence_logs.company_id`를 추가한다.
- `approvals.company_id`는 이번 단계에서 추가하지 않는다.
- 승인 scope는 `approvals.target_type`별 target row의 `company_id`를 resolver로 확인한다.
- Contact Runtime에서 `persist_result=true`로 DB 저장하려면 `worker_id`와 `company_id`가 모두 필요하다.
- `company_id`가 없으면 Agent 실행은 유지하고 `persistence.saved=false`, `reason="company_id is required for persistence"`를 반환한다.

### Consequence

장점:

- 잘못된 company scope로 저장되는 것을 막는다.
- 향후 contact/evidence/approval 조회 API에서 공통 scope 검사를 적용할 수 있다.
- `approvals`에는 중복 scope를 저장하지 않아 target row와 정합성이 어긋날 위험을 줄인다.

주의:

- 인증 시스템 전까지는 API request/header 기반 company scope를 임시로 사용한다.
- 기존 nullable row는 migration 호환을 위해 허용하지만, 신규 persistence 경로는 company_id를 요구한다.

---

## Decision 007: 공용 Approval API는 target resolver 기반 scope를 사용한다

### Date

2026-05-08

### Context

`contact_messages`, `status_update_candidates`, `handoff_package_drafts`는 모두 담당자 승인 대상이지만 화면과 workflow에 따라 approval을 `approval_id` 또는 target id로 조회할 수 있어야 한다.
`approvals`에는 `company_id`를 직접 저장하지 않기로 했기 때문에 공용 approval API는 target row의 `company_id`를 기준으로 접근 scope를 확인해야 한다.

### Decision

- 공용 approval API를 추가한다.
- 지원 endpoint:

```txt
GET /api/v1/approvals
GET /api/v1/approvals/{approval_id}
POST /api/v1/approvals/{approval_id}/approve
POST /api/v1/approvals/{approval_id}/reject
```

- 기존 handoff draft id 기반 API는 유지한다.
- MVP/demo 단계에서는 모든 공용 approval API 요청에 `X-Company-Id` header가 필요하다.
- `resolve_approval_target_company_id()`로 target row의 `company_id`를 확인한다.
- `GET /api/v1/approvals`는 프론트 승인 대기함 화면을 위한 safe summary 목록 API다.
- 목록 API에서 `status`를 생략하면 `PENDING`으로 처리한다.
- 목록 API 1차 지원 status는 `PENDING`, `APPROVED`, `REJECTED`다.
- 목록 API 1차 지원 target은 `contact_message`, `status_update_candidate`, `handoff_package_draft`다.
- 목록 API는 target resolver로 company scope를 확인하고 다른 회사 approval을 제외한다.
- `approval_id`가 없으면 `404 Not Found`로 처리한다.
- approval row는 있지만 target row가 없거나 target type이 미지원이거나 target 상태가 PENDING 계열이 아니면 `409 Conflict`로 처리한다.
- company scope가 다르면 `403 Forbidden`으로 처리한다.
- approve/reject는 review decision만 저장한다.
- approve 이후에도 메시지 자동 발송, worker_documents 자동 반영, 전문가 자동 전달, external export, 정부 제출은 실행하지 않는다.
- `contact_messages.sent_at`과 `handoff_package_drafts.transferred_at`은 승인/반려 시에도 `null`을 유지한다.
- approve/reject 시 target별 Evidence Log summary 이벤트를 저장한다.

### Consequence

장점:

- 공용 approval 화면은 `approval_id` 하나로 여러 target을 처리할 수 있다.
- 승인 대기함 화면은 기본적으로 `PENDING` 목록만 조회하고, 완료/반려 항목은 명시 필터로 조회한다.
- `approvals.company_id` 중복 저장 없이 target table과 scope 정합성을 유지한다.
- 기존 handoff 화면의 draft id 기반 API를 깨지 않고 점진적으로 공용 API를 추가한다.

주의:

- target type이 늘어나면 resolver, 상태 전이, safe response, Evidence Log event_type을 함께 추가해야 한다.
- 공용 approval API 응답과 에러에는 메시지 전문, worker reply 원문, `translated_ko` 전문, `package_json`, `worker_id` 원문, 개인정보 원문을 포함하지 않아야 한다.

---

## Decision 008: DB 문서는 SQLite MVP 기준으로 implemented와 planned를 분리한다

### Date

2026-05-08

### Context

`docs/DB_SCHEMA.md`에는 실제 구현된 service DB 테이블과 향후 필요한 context table 설계가 함께 적혀 있었다.
2026-05-08 시점에는 실제 SQLAlchemy 모델과 Alembic migration이 존재하는 service DB가 `approvals`, `contact_messages`, `status_update_candidates`, `handoff_package_drafts`, `evidence_logs` 중심이었다.
2026-05-09 후속 구현으로 `agent_runtime_state_snapshots`, `users`, `companies`, `workers`, `candidates`, `document_requirements`, `worker_documents` 모델/migration을 추가했다.
runtime tool은 DB context repository를 우선 조회하고, CSV seed는 데모 fixture/fallback으로만 서비스 계층에 격리한다.

또한 현재 구현은 SQLite MVP 기준이므로 JSON 형태 값은 `Text(JSON string)`으로 저장한다.
운영 DB 전환은 후속 검토 대상이며, 현재 DB 문서의 중심 범위가 아니다.

### Decision

- 현재 DB 구현은 SQLite MVP 기준으로 유지한다.
- `docs/DB_SCHEMA.md`를 아래 구조로 정리한다.

```txt
Current SQLite MVP Schema
Planned Context Tables
```

- 실제 구현된 service DB/context DB와 planned context tables를 문서에서 명확히 분리한다.
- SQLite MVP에서는 `Text(JSON string)`, `String ID`, 로컬 개발/테스트 기준을 사용한다.
- 운영 DB 전환은 후속 검토로만 짧게 언급한다.
- context tables 중 `users`, `companies`, `workers`, `candidates`, `document_requirements`, `worker_documents`는 SQLite MVP 모델로 승격한다.
- legacy graph State Loader는 archive 영역으로 두고, production runtime tool은 DB-first context repository를 사용한다고 문서화한다.

### Consequence

장점:

- 현재 구현된 DB와 앞으로 설계할 DB를 혼동하지 않는다.
- MVP SQLite 구현 기준으로 다음 DB 작업 범위를 잡을 수 있다.
- Context table 구현 전에 State Loader 전환, company scope, worker/candidate lookup 정책을 먼저 설계할 수 있다.

주의:

- `docs/DB_SCHEMA.md`의 planned table은 실제 migration이 아니다.
- Context tables를 구현할 때는 Alembic migration, SQLAlchemy model, service/API, State Loader repository, tests를 함께 추가해야 한다.
- 운영 DB 전환을 결정하면 별도 migration 전략과 scope 정책을 다시 설계해야 한다.

---

## Decision 009: Approval 이후 실행은 outbox/checkpoint를 먼저 기록하고 외부 실행은 열지 않는다

### Date

2026-05-09

### Context

LangChain v1 runtime은 `approval_required=true`, `approval.status=PENDING`으로 안전하게 멈출 수 있다.
하지만 승인 이후 바로 메시지 발송, 행정사 전달, 정부 제출을 실행하면 제품/법무 리스크가 커진다.
따라서 approval resume/send를 열기 전에 승인된 실행 단위, outbox, checkpoint, idempotency key, Evidence Log를 먼저 둬야 한다.

### Decision

- `approval_actions`, `delivery_outbox`, `agent_checkpoints`, `runtime_metrics` 테이블을 추가한다.
- 승인 후 허용 action은 아래로 제한한다.

```txt
finalize_internal_draft
mark_handoff_package_ready
prepare_external_delivery
```

- 아래 action은 계속 차단한다.

```txt
auto_send_to_candidate
auto_send_to_sending_agency
auto_send_to_admin_scrivener
auto_submit_to_government_portal
```

- `prepare_external_delivery`는 outbox `PENDING`까지만 만들고 실제 발송하지 않는다.
- 승인된 outbox는 `/api/v1/agent/outbox/{request_id}/prepare`로
  `READY_FOR_INTERNAL_REVIEW` 상태까지만 전환할 수 있다.
  이때 `delivery_outbox_prepared` Evidence Log를 남기고, 메시지 발송/전문가 전달/정부 제출은 계속 실행하지 않는다.
- `agent_checkpoints`는 `request_id`, `approval_id`, `resume_token`, `allowed_actions`, `blocked_actions`, `status`, `idempotency_key`, `last_error`를 저장한다.
- `POST /api/v1/agent/resume/{request_id}`는 내부 action만 허용하고 외부 action은 `403`으로 차단한다.
- `runtime_metrics`는 model/tool/retrieval/approval 관측값만 저장하고 원문 PII는 저장하지 않는다.

### Consequence

장점:

- 승인 후에도 외부 발송/전달/제출이 자동 실행되지 않는다.
- 내부 상태 전환, outbox 준비, checkpoint 생성은 idempotency key로 중복을 줄일 수 있다.
- 나중에 진짜 resume/send를 열 때도 이미 durable record와 Evidence Log가 있다.

주의:

- durable agent checkpoint는 아직 LangChain/LangGraph 실행 재개용 checkpoint가 아니라 제품 상태 전이용 checkpoint다.
- 승인 이후 실제 발송, 행정사 전달, 정부 제출은 별도 mission에서 outbox worker, idempotency, audit, 권한 정책을 설계한 뒤에만 열 수 있다.
