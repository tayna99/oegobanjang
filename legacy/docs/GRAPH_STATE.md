# Graph State

## 1. 목적

Graph State는 LangGraph 워크플로우에서 모든 node가 공유하는 상태 객체다.

외고반장의 State는 사용자 요청, 감지된 intent, 실행 계획, Agent 결과, RAG 근거, 승인 상태, Evidence Log 후보 이벤트를 포함한다.

---

## 2. ForeignHiringState

```json
{
  "request_id": "string",
  "user_id": "string",
  "company_id": "string",
  "worker_id": "string",
  "candidate_id": "string",
  "user_message": "string",

  "detected_intents": [],
  "plan": {
    "steps": [],
    "required_agents": [],
    "requires_approval": false
  },

  "company_context": {},
  "worker_context": {},
  "candidate_context": {},
  "context_blockers": [],
  "context_loaded": false,

  "agent_results": [],
  "tool_results": [],
  "rag_contexts": [],
  "risk_flags": [],

  "approval": {
    "required": false,
    "status": "NOT_REQUIRED",
    "reason": ""
  },

  "evidence_events": [],
  "final_response": ""
}
```

---

## 3. 필드 설명

| 필드 | 설명 |
|---|---|
| request_id | 사용자 요청 단위 ID |
| user_id | 요청자 ID |
| company_id | 사업장 ID |
| worker_id | 근로자 ID. 없으면 근로자 context를 로드하지 않는다. |
| candidate_id | 후보자 ID. 없으면 후보자 context를 로드하지 않는다. |
| user_message | 사용자 자연어 요청 |
| detected_intents | Intent Router가 감지한 업무 의도 |
| plan | Planner가 만든 실행 계획 |
| company_context | State Loader가 정규화한 사업장 context |
| worker_context | State Loader가 정규화한 근로자 context |
| candidate_context | State Loader가 정규화한 후보자 context |
| context_blockers | State Loader가 표현한 누락 context 목록 |
| context_loaded | 요청된 context가 blocker 없이 로드됐는지 여부 |
| agent_results | Agent 실행 결과 |
| tool_results | Tool 실행 결과 |
| rag_contexts | RAG 검색 결과와 citation |
| risk_flags | 리스크 플래그 |
| approval | 승인 필요 여부와 상태 |
| evidence_events | Evidence Log 후보 이벤트 |
| final_response | 최종 응답 |

---

## 4. 상태 변경 원칙

- node는 자기 책임 필드만 수정한다.
- State Loader는 `company_context`, `worker_context`, `candidate_context`, `context_blockers`, `context_loaded`만 책임진다.
- 모든 Tool 실행 결과는 `tool_results`에 append한다.
- 모든 RAG 검색 결과는 `rag_contexts`에 append한다.
- 모든 위험 판단은 `risk_flags`에 append한다.
- 외부 실행 전 `approval.required=true`로 전환한다.
- 모든 주요 판단은 `evidence_events`에 append한다.

---

## 5. State Loader 계약

State Loader는 Planner 이후, Executor 이전에 실행된다.

역할은 판단이 아니라 context 정리다.

```txt
company_id / worker_id / candidate_id
→ company_context / worker_context / candidate_context
→ context_blockers / context_loaded
```

### 입력 ID

```json
{
  "company_id": "company_123",
  "worker_id": "worker_456",
  "candidate_id": "candidate_789"
}
```

`worker_id`, `candidate_id`는 선택값이다.

`company_id`가 비어 있고 worker 또는 candidate row에 `company_id`가 있으면 State Loader가 `company_id`를 정규화할 수 있다.

### Context Blocker

요청된 context를 찾지 못하면 예외를 던지지 않고 blocker로 표현한다.

```json
{
  "type": "missing_worker",
  "message": "근로자 정보를 찾을 수 없습니다.",
  "severity": "MEDIUM",
  "id": "worker_456"
}
```

현재 blocker type:

```txt
missing_company
missing_worker
missing_candidate
```

State Loader는 `risk_level`을 확정하지 않는다. Aggregator/Risk Classifier는 `context_blockers`를 읽어 `risk_flags` 또는 `risk_reasons`로 반영할 수 있다.

### 민감정보 처리

State Loader context에는 Agent 실행에 필요한 최소 필드만 둔다. Evidence Log 성격의 필드에는 원문 민감정보를 남기지 않는다.

현재 마스킹 또는 제거 대상:

```txt
phone → [전화번호]
mobile → [전화번호]
passport_number → [여권번호]
alien_registration_number → [외국인등록번호]
registration_number → [외국인등록번호]
address → [주소]
worker_reply → 제거
translated_ko → 제거
ocr_text → 제거
document_body → 제거
message_body → 제거
```

B/C 팀원 handoff:

- Aggregator는 `company_context`, `worker_context`, `candidate_context`, `context_blockers`를 읽을 수 있다.
- Risk Classifier는 blocker를 운영상 검토 신호로만 다룬다.
- Handoff Package는 raw context를 그대로 사용하지 않고 마스킹된 요약만 사용한다.
- Evidence Log에는 context 원문이 아니라 요약, source_id, risk_flags, 승인 상태만 저장한다.

---

## 6. 지원 Intent

```txt
HIRING
VISA_CHECK
DOCUMENT_CHECK
CONTACT
BRIEFING
UNSUPPORTED_VALUE_JUDGMENT
UNSUPPORTED_LEGAL_JUDGMENT
UNSUPPORTED_AUTO_SUBMISSION
```

---

## 7. Approval Status

```txt
NOT_REQUIRED
PENDING
APPROVED
REJECTED
```
