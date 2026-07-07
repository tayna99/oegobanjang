# DB Schema

## Purpose

이 문서는 외고반장 service DB의 현재 구현 상태와 향후 계획을 분리해서 기록한다.

현재 구현은 SQLite MVP 기준이다.
운영 DB 전환은 후속 검토 대상이다.

```txt
Current Implementation: SQLite MVP
```

핵심 분리 원칙:

```txt
RAG 문서/embedding = Chroma
운영 상태 = SQLite service DB
Agent 초안/후보 = SQLite service DB
승인 상태 = approvals
감사 요약 = evidence_logs
민감정보 원문 = 저장 금지
승인 = review decision, 실행 아님
```

---

## Current SQLite MVP Schema

현재 실제 SQLAlchemy 모델과 Alembic migration이 존재하는 service DB 테이블은 아래 5개다.

```txt
approvals
contact_messages
status_update_candidates
handoff_package_drafts
evidence_logs
```

구현 파일:

```txt
backend/app/models/approval.py
backend/app/models/contact.py
backend/app/models/handoff.py
backend/app/models/evidence.py
```

Migration:

```txt
backend/migrations/versions/20260505_0001_contact_persistence_tables.py
backend/migrations/versions/20260506_0002_handoff_package_drafts.py
backend/migrations/versions/20260507_0003_handoff_company_scope.py
backend/migrations/versions/20260507_0004_company_scope_for_agent_outputs.py
```

SQLite MVP type policy:

| Logical type | Current SQLite MVP |
|---|---|
| ID | `String(36)` / `String(64)` |
| JSON list/object | `Text(JSON string)` |
| Company scope | nullable string column or resolver |
| Relation | selective FK, some string relation IDs |

### approvals

역할:

관리자 승인 상태를 저장한다. `approvals` 자체에는 `company_id`를 저장하지 않고, target row의 `company_id`로 company scope를 검사한다.

주요 컬럼:

| column | current type | note |
|---|---|---|
| `id` | `String(36)` | approval ID |
| `target_type` | `String(80)` | polymorphic target type |
| `target_id` | `String(36)` | target row ID |
| `status` | `String(40)` | review status |
| `requested_by` | `String(64) nullable` | 요청자 |
| `reviewed_by` | `String(64) nullable` | 검토자 |
| `created_at` | `DateTime` | 생성 시각 |
| `reviewed_at` | `DateTime nullable` | 검토 시각 |
| `reason` | `Text nullable` | 승인 필요 사유 또는 반려 사유 |

Scope/relations:

```txt
company_id: 없음
worker_id: 없음
approval_id: id 자체
FK: 없음. target_type/target_id resolver 사용
```

지원 target_type:

```txt
contact_message
status_update_candidate
handoff_package_draft
```

상태값:

```txt
PENDING
APPROVED
REJECTED
CANCELLED (planned/documented)
```

관련 service/API:

```txt
backend/app/services/approval_service.py
backend/app/services/contact_persistence_service.py
backend/app/services/handoff_persistence_service.py
GET /api/v1/approvals
backend/app/api/v1/approvals.py
backend/app/api/v1/handoff.py
```

목록 조회:

```txt
GET /api/v1/approvals
X-Company-Id: required
default status: PENDING
supported status: PENDING, APPROVED, REJECTED
supported list target_type: contact_message, status_update_candidate, handoff_package_draft
```

`approvals`에는 `company_id`가 없으므로 목록 조회도 target resolver로 company scope를 확인한다.
응답은 승인 대기함 목적의 safe summary만 포함한다.
`contact_messages.korean_text`, `contact_messages.translated_text`, `status_update_candidates.worker_id`, `handoff_package_drafts.package_json`, worker_id 원문, PII 원문은 목록 응답에 포함하지 않는다.

민감정보 저장 정책:

`reason`에는 민감정보 원문을 넣지 않는다. 공용 approval service는 명백한 여권번호, 외국인등록번호, 전화번호 패턴과 금지 marker를 차단한다.

승인은 실행이 아니다:

```txt
contact_message 승인 != 메시지 발송
status_update_candidate 승인 != worker_documents 반영
handoff_package_draft 승인 != 전문가 전달
```

### contact_messages

역할:

다국어 메시지 초안을 저장한다. 메시지 전문은 담당자 검토용 운영 데이터로 저장되지만, 실제 발송은 하지 않는다.

주요 컬럼:

| column | current type | note |
|---|---|---|
| `id` | `String(36)` | message draft ID |
| `company_id` | `String(64) nullable` | 접근 scope |
| `worker_id` | `String(64) nullable` | 내부 relation |
| `message_purpose` | `String(100)` | 메시지 목적 |
| `language_code` | `String(16)` | MVP는 vi/id 중심 |
| `korean_text` | `Text` | 한국어 초안 전문 |
| `translated_text` | `Text nullable` | 번역 초안 전문 |
| `status` | `String(40)` | draft/review 상태 |
| `approval_required` | `Boolean` | 발송 전 승인 필요 |
| `approval_id` | `String(36) FK approvals.id nullable` | 승인 ID |
| `citation_source_ids` | `Text(JSON string) nullable` | source_id 목록 |
| `risk_flags` | `Text(JSON string) nullable` | 안전 플래그 |
| `created_by` | `String(64) nullable` | 생성자 |
| `created_at` | `DateTime` | 생성 시각 |
| `updated_at` | `DateTime` | 수정 시각 |
| `sent_at` | `DateTime nullable` | 실제 발송 시각. 승인 시에도 null 유지 |

Scope/relations:

```txt
company_id: 있음
worker_id: 있음
approval_id: 있음
FK: approval_id -> approvals.id
```

상태값:

```txt
PENDING_APPROVAL
APPROVED
REJECTED
SENT (future execution step)
CANCELLED (planned/documented)
```

Text(JSON string) 컬럼:

```txt
citation_source_ids
risk_flags
```

관련 service/API:

```txt
backend/app/services/contact_persistence_service.py
backend/app/services/agent_service.py
backend/app/services/approval_service.py
POST /api/v1/agent/run
GET/POST /api/v1/approvals/{approval_id}
```

민감정보 저장 정책:

- `korean_text`, `translated_text`는 메시지 초안 전문이므로 접근 제어가 필요하다.
- Evidence Log에는 메시지 전문을 저장하지 않는다.
- approve 이후에도 `sent_at=null`을 유지하며 자동 발송하지 않는다.

### status_update_candidates

역할:

근로자 답변에서 추출한 상태 업데이트 후보를 저장한다. 실제 `worker_documents` 또는 worker 상태를 변경하지 않는다.

주요 컬럼:

| column | current type | note |
|---|---|---|
| `id` | `String(36)` | candidate ID |
| `company_id` | `String(64) nullable` | 접근 scope |
| `worker_id` | `String(64)` | 내부 relation |
| `target_type` | `String(80)` | 예: `worker_document` |
| `target_key` | `String(100)` | 예: `passport`, `photo` |
| `candidate_status` | `String(100)` | 후보 상태값 |
| `confidence` | `String(40) nullable` | confidence |
| `manager_review_required` | `Boolean` | 담당자 검토 필요 |
| `status` | `String(40)` | review/apply 상태 |
| `source_message_id` | `String(36) FK contact_messages.id nullable` | 관련 메시지 |
| `approval_id` | `String(36) FK approvals.id nullable` | 승인 ID |
| `created_at` | `DateTime` | 생성 시각 |
| `reviewed_at` | `DateTime nullable` | 검토 시각 |

Scope/relations:

```txt
company_id: 있음
worker_id: 있음
approval_id: 있음
FK: approval_id -> approvals.id
FK: source_message_id -> contact_messages.id
```

상태값:

```txt
PENDING_REVIEW
APPROVED
REJECTED
APPLIED (future apply step)
```

Text(JSON string) 컬럼:

```txt
없음
```

관련 service/API:

```txt
backend/app/services/contact_persistence_service.py
backend/app/services/agent_service.py
backend/app/services/approval_service.py
POST /api/v1/agent/run
GET/POST /api/v1/approvals/{approval_id}
```

민감정보 저장 정책:

- `worker_reply` 원문과 `translated_ko` 전문은 저장하지 않는다.
- 상태 후보는 담당자 검토 전까지 확정 상태가 아니다.
- approve 이후에도 `candidate_status`만 유지하고 실제 `worker_documents`를 반영하지 않는다.

### handoff_package_drafts

역할:

전문가 검토용 handoff package 초안을 저장한다. 실제 전문가 전달, external export, 정부 제출을 실행하지 않는다.

주요 컬럼:

| column | current type | note |
|---|---|---|
| `id` | `String(36)` | draft ID |
| `request_id` | `String(64) nullable` | Runtime request ID |
| `company_id` | `String(64) nullable` | 접근 scope |
| `package_type` | `String(80)` | `expert_handoff_draft` |
| `case_type` | `String(80) nullable` | case type |
| `worker_id` | `String(64) nullable` | 내부 relation. package_json/API detail에는 미노출 |
| `masked_worker_id` | `String(80)` | safe display ID |
| `risk_level` | `String(40) nullable` | risk level |
| `handoff_ready` | `Boolean` | 초안 준비 가능 여부 |
| `handoff_blockers` | `Text(JSON string) nullable` | blockers |
| `package_json` | `Text(JSON string)` | allowlist 기반 safe package |
| `approval_required` | `Boolean` | 승인 필요 |
| `approval_id` | `String(36) FK approvals.id nullable` | 승인 ID |
| `status` | `String(40)` | review 상태 |
| `created_by` | `String(64) nullable` | 생성자 |
| `created_at` | `DateTime` | 생성 시각 |
| `updated_at` | `DateTime` | 수정 시각 |
| `transferred_at` | `DateTime nullable` | 실제 전달 시각. 승인 시에도 null 유지 |

Scope/relations:

```txt
company_id: 있음
worker_id: 있음
approval_id: 있음
FK: approval_id -> approvals.id
```

상태값:

```txt
PENDING_APPROVAL
APPROVED
REJECTED
```

Text(JSON string) 컬럼:

```txt
handoff_blockers
package_json
```

관련 service/API:

```txt
backend/app/services/handoff_persistence_service.py
backend/app/services/approval_service.py
GET /api/v1/handoff-package-drafts/{draft_id}
POST /api/v1/handoff-package-drafts/{draft_id}/approve
POST /api/v1/handoff-package-drafts/{draft_id}/reject
GET/POST /api/v1/approvals/{approval_id}
```

민감정보 저장 정책:

`package_json`은 allowlist 기반으로만 저장한다.

저장 금지:

```txt
worker_id 원문
worker_name 원문
nationality
worker_reply 원문
translated_ko 전문
message body 전문
여권번호
외국인등록번호
전화번호 전체
주소 전체
문서/OCR 원문
법률·노무 판단 확정 문장
비자 가능 여부 확정 문장
```

approve 이후에도 `transferred_at=null`을 유지하며 전문가 자동 전달은 하지 않는다.

### evidence_logs

역할:

AI 판단, 초안 생성, 승인 요청/결정 등 주요 이벤트의 감사 요약을 저장한다.

주요 컬럼:

| column | current type | note |
|---|---|---|
| `id` | `String(36)` | log ID |
| `event_type` | `String(100)` | event type |
| `agent_name` | `String(100)` | agent/service name |
| `tool_name` | `String(100) nullable` | tool name |
| `summary` | `Text` | 원문 없는 요약 |
| `source_ids` | `Text(JSON string) nullable` | source_id 목록 |
| `approval_required` | `Boolean` | 승인 필요 여부 |
| `risk_flags` | `Text(JSON string) nullable` | 안전 플래그 |
| `request_id` | `String(64) nullable` | request ID |
| `company_id` | `String(64) nullable` | 접근 scope |
| `worker_id` | `String(64) nullable` | 내부 relation |
| `contact_message_id` | `String(36) FK contact_messages.id nullable` | 관련 메시지 |
| `status_update_candidate_id` | `String(36) FK status_update_candidates.id nullable` | 관련 상태 후보 |
| `approval_id` | `String(36) FK approvals.id nullable` | 관련 approval |
| `created_at` | `DateTime` | 생성 시각 |

Scope/relations:

```txt
company_id: 있음
worker_id: 있음
approval_id: 있음
FK: approval_id -> approvals.id
FK: contact_message_id -> contact_messages.id
FK: status_update_candidate_id -> status_update_candidates.id
handoff_package_draft_id: 없음
```

Text(JSON string) 컬럼:

```txt
source_ids
risk_flags
```

관련 service/API:

```txt
backend/app/services/contact_persistence_service.py
backend/app/services/handoff_persistence_service.py
backend/app/services/approval_service.py
```

`backend/app/api/v1/evidence.py`와 `backend/app/services/evidence_service.py`는 현재 비어 있다.

저장 금지:

```txt
worker_reply 원문
translated_ko 전문
message body 전문
package_json 전문
여권번호
외국인등록번호
전화번호 전체
주소 전체
문서/OCR 원문
```

현재 `handoff_package_draft_id` FK는 없다. Handoff audit은 `approval_id`와 `request_id` 중심으로 추적한다. Draft 중심 감사 조회가 중요해지는 시점에 전용 FK 추가를 검토한다.

---

## Company Scope Status

현재 구현 기준:

| table | company_id | scope policy |
|---|---:|---|
| `contact_messages` | 있음 | target row scope |
| `status_update_candidates` | 있음 | target row scope |
| `handoff_package_drafts` | 있음 | target row scope |
| `evidence_logs` | 있음 | audit query scope |
| `approvals` | 없음 | target resolver 기반 |

`approvals`에는 `company_id`를 직접 저장하지 않는다.
공용 approval API는 `resolve_approval_target_company_id(db, approval)`로 target row의 `company_id`를 확인한다.

MVP/demo 단계에서는 `X-Company-Id` header를 사용한다.
운영 전에는 인증 토큰 기반 company membership/role 검증으로 교체해야 한다.

---

## Approval Semantics

승인은 외부 실행이 아니라 review decision이다.

```txt
contact_message 승인
→ approvals.status=APPROVED
→ contact_messages.status=APPROVED
→ 메시지 자동 발송 없음
→ sent_at=null 유지

status_update_candidate 승인
→ approvals.status=APPROVED
→ status_update_candidates.status=APPROVED
→ worker_documents 자동 반영 없음
→ candidate_status 유지

handoff_package_draft 승인
→ approvals.status=APPROVED
→ handoff_package_drafts.status=APPROVED
→ 전문가 자동 전달 없음
→ external export 없음
→ 정부 제출 없음
→ transferred_at=null 유지
```

재처리/충돌:

```txt
approval 없음 → 404
approval 있음 + target row 없음 → 409
approval 있음 + target_type 미지원 → 409
approval.status != PENDING → 409
target 상태가 PENDING 계열이 아님 → 409
target company_id와 X-Company-Id 불일치 → 403
```

---

## Implemented Context Tables

아래 테이블은 2026-05-09 기준 실제 SQLAlchemy 모델과 Alembic migration이 있다.
runtime 판단은 DB context repository를 우선 사용한다.
seed CSV는 데모 fixture와 로컬 fallback 용도로만 서비스 계층에 격리한다.

```txt
users
companies
workers
candidates
document_requirements
worker_documents
```

아래 테이블은 approval resume/send를 바로 열지 않기 위한 안전한 중간층이다.
승인 후에도 실제 발송, 행정사 전달, 정부 제출은 실행하지 않고 내부 action/outbox/checkpoint/metrics만 기록한다.

```txt
approval_actions
delivery_outbox
agent_checkpoints
langchain_agent_checkpoints
runtime_metrics
```

구현 파일:

```txt
backend/app/models/company.py
backend/app/models/worker.py
backend/app/models/document.py
backend/app/models/user.py
backend/app/models/hiring.py
backend/app/models/runtime_execution.py
backend/app/services/context_data_service.py
backend/app/services/runtime_resume_service.py
backend/app/services/runtime_metrics_service.py
backend/app/services/langchain_checkpoint_service.py
backend/migrations/versions/20260509_0006_context_tables.py
backend/migrations/versions/20260509_0007_runtime_resume_outbox_metrics.py
backend/migrations/versions/20260509_0008_langchain_agent_checkpoints.py
```

아래 테이블은 계속 planned 상태다.

```txt
worker_sensitive_profiles
hiring_requests
visas
rag_sources
```

현재 빈 placeholder 또는 후속 설계 대상 파일은 존재할 수 있다.

```txt
backend/app/models/visa.py
```

State Loader 현황:

```txt
runtime tool은 DB context repository를 우선 읽는다.
기존 legacy graph State Loader는 archive/legacy 영역이며 production runtime 경로가 아니다.
seed CSV는 context_data_service 내부 fallback/fixture로만 사용한다.
```

Context table 역할:

| table | role |
|---|---|
| `users` | 관리자/담당자 계정과 role |
| `companies` | 사업장 master |
| `workers` | 외국인 근로자 master |
| `candidates` | 신규 채용 후보 준비 상태 |
| `document_requirements` | 케이스별 필수 서류 기준 |
| `worker_documents` | 근로자별 제출 서류 상태 |
| `approval_actions` | 승인 후 허용/차단 action 기록. 외부 실행 금지 action은 `BLOCKED` |
| `delivery_outbox` | 외부 전달 준비용 outbox. PENDING 상태만 만들고 실제 발송하지 않음 |
| `agent_checkpoints` | 승인 후 제한 resume을 위한 token/idempotency checkpoint |
| `langchain_agent_checkpoints` | LangGraph/LangChain execution checkpoint metadata. 실제 checkpoint payload는 별도 SQLite 파일에 저장 |
| `runtime_metrics` | model/tool/retrieval/approval runtime 관측값. 원문 PII 저장 금지 |
| `worker_sensitive_profiles` | planned: 여권번호, 외국인등록번호, 전화번호 등 암호화 민감정보 |
| `hiring_requests` | planned: 신규 인력 요청 |
| `visas` | planned: 체류/비자 상태 |
| `rag_sources` | planned: 필요 시 RAG source metadata. Vector/embedding 자체는 Chroma |

후속 구현 시 함께 결정할 것:

- company membership/role scope
- worker/candidate lookup 정책
- `worker_documents` apply flow
- 민감정보 암호화/마스킹 정책

---

## Operating DB Transition

운영 DB 전환은 후속 검토 대상이다.
현재 문서의 기준은 SQLite MVP이며, JSON 형태 값은 `Text(JSON string)`으로 저장한다.

Chroma는 service DB migration 대상이 아니다.
공식 문서, chunk, embedding, vector index는 SQLite service DB와 분리한다.

---

## Verification Notes

DB 관련 테스트는 현재 `Base.metadata.create_all()`로 SQLite in-memory DB를 구성한다.
Alembic migration과 SQLAlchemy model의 차이를 확인하려면 별도 migration smoke test가 필요하다.

현재 주요 테스트:

```txt
backend/tests/test_contact_persistence_service.py
backend/tests/test_handoff_persistence_service.py
backend/tests/test_handoff_api.py
backend/tests/test_approval_api.py
backend/tests/test_multilingual_contact_persistence_runtime.py
backend/tests/test_runtime_followup_operationalization.py
backend/tests/test_runtime_resume_outbox_metrics.py
```
