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
- risk_flagged
- approval_requested
- approval_completed
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
| step_name | varchar | 실행 단계 |
| event_type | varchar | 이벤트 유형 |
| tool_name | varchar nullable | 실행 Tool |
| input_snapshot | jsonb | 입력 스냅샷 |
| output_snapshot | jsonb | 출력 스냅샷 |
| citation_ids | jsonb | 참조 문서 ID |
| risk_level | varchar | LOW/MEDIUM/HIGH |
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

저장 가능한 정보:

- 마스킹된 식별자
- 문서 보유 여부
- source_id
- 판단 요약
- 승인 상태
- 처리 시각

---

## 5. 예시

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