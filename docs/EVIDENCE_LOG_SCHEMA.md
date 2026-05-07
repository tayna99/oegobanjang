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
- OCR 원문
- 메시지 전문
- worker_reply 원문
- translated_ko 전문
- 근로자-facing message body 전문
- 상담 내용 전문
- 계약, 급여, 숙소, 의료 관련 원문
- API key, .env 값, token, secret
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
- translated_ko 전문
- 근로자-facing message body 전문
- 개인정보 원문

예시 요약:

```txt
message_draft_created → 베트남어 안전교육 안내 메시지 초안이 생성됨
worker_reply_summarized → 근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘
status_update_candidate_created → 사진 제출 예정 상태 후보가 생성됨
```

---

## 6. Handoff Package 이벤트

Handoff Package는 전문가 전달용 초안 생성 이벤트만 Evidence Log에 남긴다.

저장 가능:

- package type
- case type
- masked_worker_id
- risk_flags
- source_id 목록
- approval_required 여부
- approval.status
- handoff_blockers 요약
- handoff_package_draft_created 이벤트 요약

저장 금지:

- worker_id 원문
- worker_name 원문
- nationality
- worker_reply 원문
- translated_ko 전문
- 근로자-facing message body 전문
- 여권번호 원문
- 외국인등록번호 원문
- 전화번호 전체
- 주소 전체

Handoff Package 관련 이벤트는 아래 상태를 유지해야 한다.

```txt
package_type=expert_handoff_draft
approval_required=true
approval.status=PENDING
not_for_legal_judgment=true
raw_worker_reply_included=false
full_translation_included=false
message_body_included=false
```

DB 저장 시 Evidence Log 예시:

```txt
event_type=handoff_package_draft_created
summary=전문가 검토용 handoff package 초안이 생성되었습니다.
approval_required=true
approval.status=PENDING
```

Evidence Log에는 handoff package 전문을 저장하지 않는다.
저장된 handoff draft 조회 API도 같은 원칙을 따른다. 조회 응답은 safe detail view만 반환하며, package_json 원문이나 민감정보 원문을 노출하지 않는다.

---

## 7. 예시

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
