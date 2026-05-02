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
| user_message | 사용자 자연어 요청 |
| detected_intents | Intent Router가 감지한 업무 의도 |
| plan | Planner가 만든 실행 계획 |
| company_context | 사업장 상태 |
| worker_context | 근로자 상태 |
| candidate_context | 후보자 상태 |
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
- 모든 Tool 실행 결과는 `tool_results`에 append한다.
- 모든 RAG 검색 결과는 `rag_contexts`에 append한다.
- 모든 위험 판단은 `risk_flags`에 append한다.
- 외부 실행 전 `approval.required=true`로 전환한다.
- 모든 주요 판단은 `evidence_events`에 append한다.

---

## 5. 지원 Intent

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

## 6. Approval Status

```txt
NOT_REQUIRED
PENDING
APPROVED
REJECTED
```