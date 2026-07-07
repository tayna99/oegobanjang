# Observability

## 1. 목적

외고반장은 Agent 기반 워크플로우이므로, 단순 API 로그만으로는 충분하지 않다.

요청 단위, Agent 단계, Tool 실행, RAG 검색, 승인 상태, Evidence Log까지 추적해야 한다.

---

## 2. 공통 추적 키

모든 로그에는 가능하면 아래 값을 포함한다.

- request_id
- user_id
- company_id
- worker_id
- agent_name
- step_name
- tool_name

---

## 3. 로그 대상

### API 로그

- endpoint
- method
- status_code
- latency_ms
- request_id

### Agent 로그

- intent_router 실행 결과
- planner 실행 결과
- agent 실행 결과
- approval_required 여부
- final_response 생성 여부

### Tool 로그

- tool_name
- tool_grade
- status
- approval_required
- error

### RAG 로그

- query
- top_k
- returned_source_ids
- evidence_grade
- retrieval_latency_ms

### Safety 로그

- forbidden request 감지
- approval_required action 감지
- 민감정보 마스킹 여부

---

## 4. 주요 메트릭

- agent_run_count
- agent_run_latency_ms
- rag_retrieval_latency_ms
- approval_pending_count
- safety_violation_count
- evidence_log_missing_count
- failed_tool_count

---

## 5. 운영 원칙

- 민감정보 원문은 로그에 남기지 않는다.
- 금지 작업 요청은 safety event로 기록한다.
- approval_required 작업은 자동 실행하지 않고 pending 상태로 기록한다.
- Evidence Log 누락은 장애로 본다.