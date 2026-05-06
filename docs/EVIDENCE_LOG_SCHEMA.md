# Evidence Log Schema

## 1. 목적

Evidence Log는 AI가 왜 그렇게 판단했는지, 어떤 근거를 사용했는지, 누가 승인했는지를 추적하기 위한 기록이다.

외고반장은 법적 리스크와 행정 사고를 다루므로, 모든 중요한 판단은 설명 가능해야 한다.

---

## 2. 저장해야 하는 이벤트

- intent_classified
- plan_created
- tool_executed
- rag_retrieved
- message_draft_created
- risk_flagged
- approval_requested
- approval_completed
- worker_reply_summarized
- status_update_candidate_created
- final_response_generated

---

## 3. evidence_logs 테이블 초안

| column | type | description |
|---|---|---|
| id | UUID | 로그 ID |
| request_id | UUID | 사용자 요청 ID |
| company_id | UUID | 사업장 ID |
| worker_id | UUID nullable | 근로자 ID |
| agent_name | varchar | 실행 Agent |
| event_type | varchar | 이벤트 유형 |
| tool_name | varchar nullable | 실행 Tool |
| summary | text | 원문 없는 이벤트 요약 |
| source_ids | jsonb | 참조 source_id 목록 |
| approval_required | boolean | 승인 필요 여부 |
| risk_flags | jsonb | 안전 플래그 |
| contact_message_id | UUID nullable | 관련 메시지 초안 ID |
| status_update_candidate_id | UUID nullable | 관련 상태 후보 ID |
| approval_id | UUID nullable | 승인 ID |
| created_at | timestamp | 생성 시각 |

---

## 4. 민감정보 처리

Evidence Log에는 다음 원문을 저장하지 않는다.

- 외국인등록번호
- 여권번호
- 전화번호 전체
- 주소 전체
- 서류 파일 원문
- 메시지 전문
- worker_reply 원문
- 기타 개인정보 원문

저장 가능한 정보:

- 마스킹된 식별자
- 문서 보유 여부
- source_id
- 판단 요약
- 승인 상태
- 처리 시각
- candidate 상태 요약
- risk_flags

---

## 5. Multilingual Contact Agent 이벤트

다국어 Contact Agent는 아래 이벤트 후보를 생성할 수 있다.

```txt
rag_retrieved
message_draft_created
approval_requested
worker_reply_summarized
status_update_candidate_created
```

저장 가능:

- 요약
- source_id 목록
- approval_required
- risk_flags
- candidate 상태 요약

저장 금지:

- 메시지 전문
- worker_reply 원문
- 개인정보 원문

예시 요약:

```txt
message_draft_created → 베트남어 안전교육 안내 메시지 초안이 생성됨
worker_reply_summarized → 근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘
status_update_candidate_created → 사진 제출 예정 상태 후보가 생성됨
```

---

## 6. 예시

```json
{
  "event_type": "risk_flagged",
  "request_id": "req_001",
  "agent_name": "visa_document_agent",
  "step_name": "visa_risk_check",
  "summary": "체류만료 D-30 구간으로 관리자 확인이 필요합니다.",
  "citation_ids": ["gov24_stay_extension"],
  "risk_level": "MEDIUM",
  "approval_id": null
}
```
