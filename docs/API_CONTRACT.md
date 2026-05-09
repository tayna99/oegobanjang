# API Contract

## 1. 목적

이 문서는 frontend와 backend 사이의 API 계약을 정의한다.

---

## 2. 공통 응답 형식

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

에러 예시:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청값이 올바르지 않습니다."
  }
}
```

---

## 3. Health API

```txt
GET /api/v1/health
```

응답:

```json
{
  "status": "ok"
}
```

---

## 4. Agent 실행 API

```txt
POST /api/v1/agent/run
```

요청:

```json
{
  "request_id": "req_001",
  "user_id": "user_001",
  "company_id": "company_001",
  "user_message": "베트남 E-9 근로자 3명 추가 채용 준비해줘. Nguyen 체류만료도 확인해줘.",
  "persist_result": false
}
```

응답:

```json
{
  "request_id": "req_001",
  "detected_intents": ["HIRING", "VISA_CHECK"],
  "plan": {
    "steps": [],
    "required_agents": [],
    "requires_approval": true
  },
  "agent_results": [],
  "approval": {
    "required": true,
    "status": "PENDING",
    "reason": "외부 발송 또는 전문가 전달 전 담당자 승인이 필요합니다."
  },
  "evidence_events": [],
  "final_response": "요청을 분석하고 실행 계획 초안을 생성했습니다."
}
```

---

## Agent Runtime API

### POST /api/v1/agent/run

`/api/v1/agent/run`은 Agent Runtime의 공통 실행 endpoint다.

다국어 Contact Agent 요청도 이 endpoint를 사용한다. `user_message`와 `user_request`는
모두 LangChain v1 runtime의 `AgentRuntimeInput.user_message`로 정규화된다.

처리 흐름:

```txt
POST /api/v1/agent/run
→ langchain_v1 request normalizer
→ create_agent(response_format=WorkBridgeAgentResponse)
→ tools + middleware
→ structured_response
→ AgentRunResponse compatibility adapter
```

요청은 자연어 `user_request`와 선택적인 `input_payload`를 받는다.

자연어 `user_request`는 더 이상 legacy contact bypass로 전달되지 않는다.
LangChain v1 runtime이 structured response를 만들고, API는 공통 `AgentRunResponse`
shape으로 변환한다. 기존 다국어 contact 세부 런타임은 service-level 경로와 테스트에서 유지한다.

`/api/v1/agent/run`은 LangChain runtime state를 process-local store와
`agent_runtime_state_snapshots` DB table에 저장한다. DB snapshot은 PII-redacted JSON만 저장하며,
`/api/v1/agent/state/{request_id}`는 메모리 state가 없을 때 DB snapshot으로 fallback한다.

요청 기본 형태:

```json
{
  "user_request": "Nguyen한테 베트남어로 5월 10일 10시에 교육장에서 안전교육 있다고 안내 메시지 만들어줘",
  "input_payload": {}
}
```

응답 주요 형태:

```json
{
  "request_id": "request-id-string",
  "final_response": "LangChain v1 structured response summary...",
  "detected_intents": ["CONTACT"],
  "risk_flags": [],
  "approval_required": true,
  "approval_status": "PENDING",
  "handoff": {
    "available": false
  },
  "evidence_event_count": 4,
  "rag_context_count": 0
}
```

### Multilingual Contact Agent

다국어 Contact Agent는 다국어 메시지 초안 생성, 공식 자료 RAG 검색, 근로자 답변 요약, 상태 업데이트 후보 생성을 담당한다.

안전 원칙:

- 메시지는 자동 발송하지 않는다.
- 항상 `approval_required=true`를 유지한다.
- 발송 전 담당자 승인이 필요하다.
- 상태 업데이트는 candidate만 생성한다.
- `worker_reply` 원문은 `evidence_events`에 저장하지 않는다.
- 법적 판단, 비자 가능 여부 확정, 노무 자문은 하지 않는다.

DB 저장 opt-in 정책:

- 기본 실행은 Runtime response만 반환하고 DB에 저장하지 않는다.
- `input_payload.persist_result=false` 또는 필드가 없으면 응답만 반환하고 DB에 저장하지 않는다.
- `input_payload.persist_result=true`일 때만 성공 결과를 SQLite 운영 DB에 저장한다.
- 메시지 초안 생성 성공 결과는 `contact_messages`, `approvals`, `evidence_logs`를 생성한다.
- 근로자 답변 요약 성공 결과는 `status_update_candidates`, `approvals`, `evidence_logs`를 생성한다.
- 자연어 extractor는 `worker_name`을 추출할 수 있지만, DB 저장에는 `worker_id`가 필요하다.
- `persist_result=true` 요청에서는 `input_payload.worker_id`를 명시해야 한다.
- `persist_result=true` 요청에서는 `input_payload.company_id`도 명시해야 한다.
- `worker_id`가 없으면 Agent 응답은 유지하되 `persistence.saved=false`, `reason="worker_id is required for persistence"`를 반환한다.
- `company_id`가 없으면 Agent 응답은 유지하되 `persistence.saved=false`, `reason="company_id is required for persistence"`를 반환한다.
- `worker_name` 기반 `worker_id` lookup은 workers 테이블/조회 기능이 생긴 뒤 후속 작업으로 구현한다.
- DB 저장 시에도 메시지는 초안 상태이며 `approval_required=true`, `approval.status=PENDING`을 유지한다.

Handoff response 정책:

- 모든 `/api/v1/agent/run` 응답은 top-level `handoff` 필드를 포함한다.
- `handoff.available=false`이면 handoff draft가 생성되지 않은 상태다.
- `handoff.available=true`여도 자동 전달된 것이 아니다.
- `approval_status=PENDING`이면 담당자 승인 전 외부 전송 금지 상태다.
- API response에는 전체 handoff draft 본문을 노출하지 않는다.
- `worker_id`, `worker_reply` 원문, `translated_ko` 전문, 근로자-facing message body 전문, 개인정보 원문은 포함하지 않는다.
- LangChain v1 `user_message` 경로는 top-level `persist_result=true`일 때 handoff draft를 저장한다.
- `user_request` 경로는 legacy bypass가 아니라 LangChain v1 request normalizer로 흡수된다.

Handoff draft 없음:

```json
{
  "handoff": {
    "available": false
  }
}
```

Handoff draft 있음:

```json
{
  "handoff": {
    "available": true,
    "package_type": "expert_handoff_draft",
    "approval_required": true,
    "approval_status": "PENDING",
    "not_for_legal_judgment": true,
    "handoff_ready": false,
    "handoff_blockers": [],
    "raw_worker_reply_included": false,
    "full_translation_included": false,
    "message_body_included": false
  }
}
```

Handoff draft 저장 성공:

```json
{
  "handoff": {
    "available": true,
    "draft_id": "draft-id-string",
    "approval_id": "approval-id-string",
    "package_type": "expert_handoff_draft",
    "approval_required": true,
    "approval_status": "PENDING",
    "not_for_legal_judgment": true,
    "handoff_ready": false,
    "handoff_blockers": [],
    "raw_worker_reply_included": false,
    "full_translation_included": false,
    "message_body_included": false
  }
}
```

### GET /api/v1/handoff-package-drafts/{draft_id}

저장된 전문가 검토용 handoff package draft를 안전한 detail view로 조회한다.

조회 API는 read-only이며, 전문가 전달, 외부 export, 메시지 발송, 정부 제출, 상태 확정을 실행하지 않는다.

MVP/demo 단계에서는 회사 접근 scope 확인을 위해 `X-Company-Id` header가 필요하다.
운영 전에는 인증 토큰 기반 `company_id`/role 검증으로 교체해야 한다.

```http
GET /api/v1/handoff-package-drafts/{draft_id}
X-Company-Id: company-demo-001
```

접근 제어:

- `X-Company-Id`가 없으면 `403 Forbidden`
- draft의 `company_id`와 `X-Company-Id`가 다르면 `403 Forbidden`
- `draft_id` 자체가 없으면 `404 Not Found`
- `403`/`404` 응답에는 worker 정보, package 요약, 개인정보를 포함하지 않는다.

응답 예시:

```json
{
  "id": "draft-id-string",
  "package_type": "expert_handoff_draft",
  "status": "PENDING_APPROVAL",
  "approval_required": true,
  "approval_id": "approval-id-string",
  "approval_status": "PENDING",
  "transferred_at": null,
  "not_for_legal_judgment": true,
  "handoff_ready": false,
  "handoff_blockers": [],
  "case_summary": {
    "summary": "체류만료가 임박하여 서류 누락 여부 확인이 필요합니다.",
    "risk_level": "HIGH"
  },
  "worker_summary": {
    "masked_worker_id": "worker_***",
    "visa_type": "E-9",
    "stay_expires_at": "2026-06-01",
    "contract_ends_at": "2026-05-25"
  },
  "document_summary": {
    "missing_documents": ["passport_copy"]
  },
  "contact_summary": {
    "raw_worker_reply_included": false,
    "full_translation_included": false,
    "message_body_included": false
  },
  "evidence": {
    "citation_ids": ["gov24_stay_extension"],
    "evidence_log_ids": [],
    "not_for_legal_judgment": true
  },
  "created_at": "2026-05-06T12:00:00+00:00",
  "updated_at": "2026-05-06T12:00:00+00:00"
}
```

반환 정책:

- 전체 `package_json` 원문은 반환하지 않는다.
- `case_summary`와 `document_summary`는 저장 시 allowlist sanitize된 값만 반환한다.
- 조회 직전 금지 marker와 개인정보 패턴을 재검사한다.
- `worker_id` 원문, `worker_name`, `nationality`, `worker_reply` 원문, `translated_ko` 전문, 근로자-facing message body 전문, 여권번호, 외국인등록번호, 전화번호 전체, 주소 전체, OCR/문서 원문은 반환하지 않는다.
- 안전하지 않은 저장 데이터가 감지되면 detail을 반환하지 않고 오류로 막는다.

### POST /api/v1/handoff-package-drafts/{draft_id}/approve

전문가 검토용 handoff package draft를 담당자가 승인 처리한다.
이 API는 review decision만 저장하며, 전문가 자동 전달, 외부 export, 정부 제출, 메시지 발송을 실행하지 않는다.

요청:

```http
POST /api/v1/handoff-package-drafts/{draft_id}/approve
X-Company-Id: company-demo-001
```

```json
{
  "reviewed_by": "manager-demo",
  "reason": "검토 완료"
}
```

응답:

```json
{
  "draft_id": "draft-id-string",
  "approval_id": "approval-id-string",
  "status": "APPROVED",
  "approval_status": "APPROVED",
  "transferred_at": null
}
```

상태 전이:

```txt
handoff_package_drafts.status: PENDING_APPROVAL → APPROVED
approvals.status: PENDING → APPROVED
transferred_at: null 유지
```

### POST /api/v1/handoff-package-drafts/{draft_id}/reject

전문가 검토용 handoff package draft를 담당자가 반려 처리한다.
이 API도 review decision만 저장하며 외부 작업을 실행하지 않는다.

요청:

```http
POST /api/v1/handoff-package-drafts/{draft_id}/reject
X-Company-Id: company-demo-001
```

```json
{
  "reviewed_by": "manager-demo",
  "reason": "보완 필요"
}
```

응답:

```json
{
  "draft_id": "draft-id-string",
  "approval_id": "approval-id-string",
  "status": "REJECTED",
  "approval_status": "REJECTED",
  "transferred_at": null
}
```

상태 전이:

```txt
handoff_package_drafts.status: PENDING_APPROVAL → REJECTED
approvals.status: PENDING → REJECTED
transferred_at: null 유지
```

approve/reject 에러 정책:

- `X-Company-Id`가 없으면 `403 Forbidden`
- draft의 `company_id`와 `X-Company-Id`가 다르면 `403 Forbidden`
- `draft_id` 자체가 없으면 `404 Not Found`
- 이미 승인/반려된 draft를 다시 처리하면 `409 Conflict`
- `403`/`404`/`409` 응답에는 worker 정보, package 요약, 개인정보를 포함하지 않는다.
- 응답에는 전체 `package_json`, `worker_id` 원문, worker reply 원문, `translated_ko` 전문, message body 전문, 개인정보 원문을 포함하지 않는다.

예시:

```json
{
  "user_request": "베트남 근로자에게 안전교육 안내 메시지 작성해줘",
  "input_payload": {
    "worker_id": "worker_001",
    "language_code": "vi",
    "message_purpose": "safety_training_notice",
    "training_date": "2026-05-10",
    "training_time": "10:00",
    "location": "교육장",
    "persist_result": true
  }
}
```

`persist_result=true` 응답의 `persistence` 예시:

```json
{
  "enabled": true,
  "saved": true,
  "contact_message_id": "contact-message-id-string",
  "approval_id": "approval-id-string",
  "evidence_log_ids": ["evidence-log-id-string"]
}
```

#### 요청 예시 A: 자연어 vi 안전교육 메시지

요청:

```json
{
  "user_request": "Nguyen한테 베트남어로 5월 10일 10시에 교육장에서 안전교육 있다고 안내 메시지 만들어줘",
  "input_payload": {}
}
```

기대 동작:

```txt
intent=CONTACT
task_type=message_draft
language_code=vi
message_purpose=safety_training_notice
worker_name=Nguyen
training_date=5월 10일
training_time=10시
location=교육장
approval_required=true
approval.status=PENDING
```

응답에 포함되는 주요 필드:

```txt
korean_text
translated_text
citations
evidence_events
risk_flags
final_response
```

#### 요청 예시 B: 자연어 id 안전교육 메시지

요청:

```json
{
  "user_request": "Budi에게 인도네시아어로 안전교육 안내 메시지 작성해줘",
  "input_payload": {}
}
```

기대 동작:

```txt
intent=CONTACT
task_type=message_draft
language_code=id
message_purpose=safety_training_notice
approval_required=true
approval.status=PENDING
```

#### 요청 예시 C: 상담센터 안내

요청:

```json
{
  "user_request": "베트남 근로자에게 상담센터 연락처 안내해줘",
  "input_payload": {}
}
```

기대 동작:

```txt
intent=CONTACT
task_type=message_draft
language_code=vi
message_purpose=counseling_center_guide
center_name=외국인력상담센터
counseling_center_phone=1577-0071
approval_required=true
approval.status=PENDING
```

`citations`에는 EPS 또는 HRDK 상담센터 근거가 포함될 수 있다.

이 안내는 법적 확답이 아니라 공식 상담 채널 안내용이다.

#### 요청 예시 D: worker reply summary

요청:

```json
{
  "user_request": "이 베트남어 답변 요약하고 서류 상태 후보 만들어줘: Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi.",
  "input_payload": {}
}
```

기대 동작:

```txt
intent=CONTACT
task_type=worker_reply_summary
language_code=vi
message_purpose=document_reply
summary_ko 있음
status_update_candidates 있음
manager_review_required=true
approval_required=true
approval.status=PENDING
```

`worker_reply` 원문은 요청 처리에는 사용될 수 있지만, `evidence_events`에는 저장하지 않는다.

#### LLM 번역 opt-in

기본값은 rule-based/template 기반 번역 및 요약이다.

`use_llm_translation=true`는 현재 `worker_reply_summary`에만 적용된다.
`message_draft`는 계속 `message_templates.csv` 기반 번역문을 사용하며, LLM 자유번역을 시도하지 않는다.

요청 예시:

```json
{
  "user_request": "이 베트남어 답변 요약하고 서류 상태 후보 만들어줘: Tôi có hộ chiếu.",
  "input_payload": {
    "task_type": "worker_reply_summary",
    "worker_id": "worker_001",
    "language_code": "vi",
    "worker_reply": "Tôi có hộ chiếu.",
    "use_llm_translation": true
  }
}
```

동작:

```txt
use_llm_translation=true
→ LLMTranslationProvider 사용
→ OPENAI_API_KEY가 없거나 LLM 호출이 실패하면 rule-based fallback 사용
→ LLM 결과도 담당자 검토 필요
→ approval_required=true 유지
→ manager_review_required=true 유지
```

응답의 `agent_results.multilingual_contact_agent.translation_provider`에는 아래 값이 포함될 수 있다.

```txt
rule_based
llm
rule_based_fallback
mock
```

`worker_reply` 원문과 `translated_ko` 전문은 `evidence_events` 또는 DB `evidence_logs`에 저장하지 않는다.

#### 요청 예시 E: 자동 발송 금지

요청:

```json
{
  "user_request": "Nguyen에게 베트남어로 바로 발송해줘",
  "input_payload": {}
}
```

기대 동작:

```txt
메시지 초안은 생성될 수 있음
실제 발송은 하지 않음
approval_required=true
approval.status=PENDING
risk_flags에 APPROVAL_REQUIRED_FOR_SEND 포함
```

금지되는 출력:

```txt
auto_sent
sent=true
status_finalized
status_updated
government_submission
legal_judgment
visa_approved
```

#### input_payload 우선순위

입력값 우선순위:

```txt
1. input_payload 명시값
2. 자연어 extractor 추출값
3. 안전한 기본값
```

예시:

```json
{
  "user_request": "Nguyen한테 베트남어로 안내해줘",
  "input_payload": {
    "language_code": "id"
  }
}
```

기대:

```txt
language_code=id 유지
자연어의 베트남어가 id를 덮어쓰지 않음
```

#### 응답 필드 설명

| field | description |
|---|---|
| `intent` | Runtime이 감지한 intent. 다국어 Contact Agent 요청은 `CONTACT` |
| `task_type` | 실행 작업 유형. `message_draft` 또는 `worker_reply_summary` |
| `agent_results` | Agent 실행 결과. 메시지 초안, 요약, 후보 상태, citations 포함 |
| `approval_required` | Agent 결과 내부 승인 필요 여부. 다국어 메시지/상태 후보는 `true` |
| `approval` | Runtime 승인 상태. 발송 또는 상태 확정 전 `PENDING` |
| `citations` | 공식 RAG 근거 후보. title, publisher, source_id, raw_path 등 포함 |
| `evidence_events` | Evidence Log 후보 이벤트. 실제 DB 저장 전 후보 상태 |
| `risk_flags` | 안전상 주의가 필요한 플래그 |
| `final_response` | 사용자에게 보여줄 최종 응답 문구 |
| `handoff` | 전문가 전달용 초안 생성 여부와 승인 상태를 나타내는 안전 summary. 전체 draft 본문은 포함하지 않음 |

#### 실패 케이스

| case | expected risk flag / status |
|---|---|
| 없는 `message_purpose` | `TEMPLATE_NOT_FOUND` |
| 필수 placeholder 누락 | `MISSING_REQUIRED_FIELD` |
| 지원하지 않는 `language_code` | `UNSUPPORTED_LANGUAGE` 또는 validation error |
| 지원하지 않는 intent/task_type | `FAILED` 또는 validation error |

---

## 5. 주요 API 목록

```txt
/api/v1/auth
/api/v1/companies
/api/v1/workers
/api/v1/hiring
/api/v1/visas
/api/v1/documents
/api/v1/contacts
/api/v1/approvals
/api/v1/evidence
/api/v1/agent
```

---

## 6. 승인 API

```txt
GET /api/v1/approvals/{approval_id}
POST /api/v1/approvals/{approval_id}/approve
POST /api/v1/approvals/{approval_id}/reject
```

승인 필요한 작업은 Agent가 직접 실행하지 않고 approval pending 상태로 넘긴다.

공용 approval API는 MVP/demo 단계에서 `X-Company-Id` header를 필수로 사용한다.
운영 전에는 인증 토큰 기반 company membership/role 검증으로 교체해야 한다.

```http
GET /api/v1/approvals/{approval_id}
X-Company-Id: company-demo-001
```

조회 응답:

```json
{
  "approval_id": "approval-id-string",
  "target_type": "contact_message",
  "target_id": "target-id-string",
  "approval_status": "PENDING",
  "target_status": "PENDING_APPROVAL",
  "approval_required": true,
  "reviewed_by": null,
  "reviewed_at": null,
  "reason": null
}
```

승인/반려 요청:

```json
{
  "reviewed_by": "manager-demo",
  "reason": "검토 완료"
}
```

승인/반려 응답:

```json
{
  "approval_id": "approval-id-string",
  "target_type": "handoff_package_draft",
  "target_id": "target-id-string",
  "approval_status": "APPROVED",
  "target_status": "APPROVED",
  "approval_required": true,
  "reviewed_by": "manager-demo",
  "reviewed_at": "2026-05-08T12:00:00+00:00",
  "reason": "검토 완료"
}
```

접근/충돌 정책:

- `X-Company-Id`가 없으면 `403 Forbidden`
- `approval_id` 자체가 없으면 `404 Not Found`
- target row의 `company_id`와 `X-Company-Id`가 다르면 `403 Forbidden`
- approval row는 있지만 target row가 없으면 `409 Conflict`
- 지원하지 않는 `target_type`이면 `409 Conflict`
- approval 또는 target이 이미 승인/반려 등 PENDING 계열이 아니면 `409 Conflict`
- 에러 응답에는 worker 정보, 메시지 본문, package 요약, 개인정보를 포함하지 않는다.

현재 승인 처리 서비스 규칙:

```txt
contact_message approval 승인
→ approvals.status=APPROVED
→ contact_messages.status=APPROVED
→ 실제 발송은 아직 하지 않음

contact_message approval 반려
→ approvals.status=REJECTED
→ contact_messages.status=REJECTED
→ 실제 발송은 하지 않음

status_update_candidate approval 승인
→ approvals.status=APPROVED
→ status_update_candidates.status=APPROVED
→ 실제 worker_documents 반영은 아직 하지 않음

status_update_candidate approval 반려
→ approvals.status=REJECTED
→ status_update_candidates.status=REJECTED
→ 실제 worker_documents 반영은 하지 않음

handoff_package_draft approval 승인
→ approvals.status=APPROVED
→ handoff_package_drafts.status=APPROVED
→ 실제 전문가 전달, external export, 정부 제출은 하지 않음
→ transferred_at=null 유지

handoff_package_draft approval 반려
→ approvals.status=REJECTED
→ handoff_package_drafts.status=REJECTED
→ 실제 전문가 전달, external export, 정부 제출은 하지 않음
→ transferred_at=null 유지

agent_runtime_state_snapshot approval 승인
→ approvals.status=APPROVED
→ agent_runtime_state_snapshots.approval_json.status=APPROVED
→ structured_response.approval.status=APPROVED
→ actual resume, 메시지 발송, 전문가 전달, 정부 제출은 하지 않음

agent_runtime_state_snapshot approval 반려
→ approvals.status=REJECTED
→ agent_runtime_state_snapshots.approval_json.status=REJECTED
→ structured_response.approval.status=REJECTED
→ actual resume, 메시지 발송, 전문가 전달, 정부 제출은 하지 않음
```

승인/반려는 `PENDING` approval에만 가능하다.
공용 approval API는 review decision만 저장하며 실제 메시지 발송, worker_documents 반영, 전문가 전달, external export, 정부 제출을 실행하지 않는다.
응답에는 메시지 전문, worker reply 원문, `translated_ko` 전문, `package_json` 전문, `worker_id` 원문, 여권번호, 외국인등록번호, 전화번호 전체, 주소 전체를 포함하지 않는다.

---

## 7. Evidence API

```txt
GET /api/v1/evidence?request_id={request_id}
X-Company-Id: company-demo-001
```

요청 단위 Evidence Log를 조회한다.
MVP/demo 단계에서는 `X-Company-Id` header를 필수로 사용해 회사 범위를 제한한다.
header가 없으면 `403 Forbidden`을 반환한다.

응답:

```json
{
  "request_id": "request-id-string",
  "count": 2,
  "items": [
    {
      "id": "evidence-log-id-string",
      "event_type": "rag_retrieved",
      "agent_name": "langchain_v1",
      "tool_name": "retrieve_workforce_materials",
      "summary": "RAG 근거 문서가 검색되었습니다.",
      "source_ids": ["eps_employer_process"],
      "approval_required": false,
      "risk_flags": [],
      "request_id": "request-id-string",
      "company_id": "company-demo-001",
      "approval_id": null,
      "created_at": "2026-05-09T12:00:00+00:00"
    }
  ]
}
```

Evidence API 응답에는 `worker_id`, `contact_message_id`, `status_update_candidate_id`,
메시지 전문, worker reply 원문, handoff package 전문을 포함하지 않는다.
저장된 로그에 전화번호, 여권번호 등 PII가 실수로 포함되어 있어도 응답 단계에서 다시 redaction한다.
