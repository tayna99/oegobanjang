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
  "user_message": "베트남 E-9 근로자 3명 추가 채용 준비해줘. Nguyen 체류만료도 확인해줘."
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

다국어 Contact Agent 요청도 이 endpoint를 사용한다.

처리 흐름:

```txt
POST /api/v1/agent/run
→ intent_router_node
→ contact_input_extractor_node
→ planner_node
→ executor_node
→ MultilingualContactAgent
→ evidence_logger_node
→ final_response_node
```

요청은 자연어 `user_request`와 선택적인 `input_payload`를 받는다.

자연어 `user_request`만으로도 `CONTACT` intent와 일부 `input_payload`가 추출될 수 있다.
단, `input_payload`에 명시된 값이 있으면 자연어 추출값보다 우선한다.

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
  "intent": "CONTACT",
  "task_type": "message_draft",
  "plan": {},
  "agent_results": {},
  "approval": {
    "required": true,
    "status": "PENDING",
    "reason": "다국어 메시지 발송 또는 상태 업데이트 확정 전 담당자 승인이 필요합니다."
  },
  "evidence_events": [],
  "risk_flags": [],
  "final_response": "다국어 메시지 초안을 생성했습니다..."
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
- `input_payload.persist_result=true`일 때만 메시지 초안, 승인, Evidence Log 후보, 상태 업데이트 후보를 SQLite 운영 DB에 저장한다.
- 자연어 extractor는 `worker_name`을 추출할 수 있지만, DB 저장에는 `worker_id`가 필요하다.
- `persist_result=true` 요청에서는 `input_payload.worker_id`를 명시해야 한다.
- `worker_name` 기반 `worker_id` lookup은 workers 테이블/조회 기능이 생긴 뒤 후속 작업으로 구현한다.
- DB 저장 시에도 메시지는 초안 상태이며 `approval_required=true`, `approval.status=PENDING`을 유지한다.

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
POST /api/v1/approvals/{approval_id}/approve
POST /api/v1/approvals/{approval_id}/reject
```

승인 필요한 작업은 Agent가 직접 실행하지 않고 approval pending 상태로 넘긴다.

---

## 7. Evidence API

```txt
GET /api/v1/evidence?request_id={request_id}
```

요청 단위 Evidence Log를 조회한다.
