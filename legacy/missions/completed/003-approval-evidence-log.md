# Mission 003: Approval and Evidence Log

## Goal

외고반장의 Human Approval 흐름과 Evidence Log 저장 구조를 구현한다.

승인 필요한 작업은 자동 실행하지 않고 `PENDING` 상태로 남겨야 한다.  
모든 주요 판단은 Evidence Log로 추적 가능해야 한다.

---

## Required Reading

```txt
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
docs/EVIDENCE_LOG_SCHEMA.md
docs/OBSERVABILITY.md
```

---

## Target Files

```txt
backend/app/api/v1/approvals.py
backend/app/api/v1/evidence.py

backend/app/models/approval.py
backend/app/models/evidence.py

backend/app/schemas/approval.py
backend/app/schemas/evidence.py

backend/app/services/approval_service.py
backend/app/services/evidence_service.py

backend/app/agent_runtime/graph/nodes/approval_gate.py
backend/app/agent_runtime/graph/nodes/evidence_logger.py
backend/app/agent_runtime/schemas/evidence.py

backend/tests/test_approvals.py
backend/tests/test_evidence.py
backend/tests/test_guardrails.py

evals/datasets/safety_guardrail_cases.jsonl
```

---

## Scope

이번 mission에서 구현할 범위는 다음과 같다.

- 승인 요청 생성
- 승인 상태 조회
- 승인/거절 처리 API
- Evidence Log 후보 이벤트 저장
- request_id 기준 Evidence Log 조회
- 승인 필요 작업 자동 실행 방지
- 민감정보 마스킹 규칙 반영
- safety guardrail 테스트 보강

---

## Approval Status

```txt
PENDING
APPROVED
REJECTED
CANCELLED
```

---

## Approval Required Actions

아래 작업은 승인 없이 실행할 수 없다.

```txt
send_worker_message
send_manager_notification
send_expert_package
update_case_status_completed
export_handoff_package
```

---

## Evidence Events

필수 이벤트:

```txt
intent_classified
plan_created
tool_executed
rag_retrieved
risk_flagged
approval_requested
approval_completed
final_response_generated
```

---

## Out of Scope

이번 mission에서 구현하지 않는다.

- 실제 메시지 발송
- 실제 행정사 패키지 전송
- 실제 정부 포털 제출
- PDF export 상세 구현
- 외부 알림 연동
- 법적 판단 확정

---

## Acceptance Criteria

- 승인 요청을 생성할 수 있다.
- 승인 상태를 조회할 수 있다.
- 승인/거절을 처리할 수 있다.
- 승인 필요한 작업은 자동 실행되지 않는다.
- Evidence Log를 request_id 기준으로 조회할 수 있다.
- Evidence Log에 민감정보 원문이 저장되지 않는다.
- safety eval이 통과한다.

---

## Verification Commands

```bash
bash scripts/run_backend_tests.sh
bash scripts/run_agent_tests.sh
python scripts/run_evals.py --dataset safety_guardrail_cases
```

---

## Human Review Checklist

- [ ] 승인 필요한 작업이 자동 실행되지 않는가?
- [ ] Evidence Log가 주요 단계마다 생성되는가?
- [ ] 민감정보 원문이 저장되지 않는가?
- [ ] 승인/거절 이력이 추적 가능한가?
- [ ] 금지 작업 요청이 안전하게 처리되는가?