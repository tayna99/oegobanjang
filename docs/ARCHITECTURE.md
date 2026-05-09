# Architecture

## 1. 전체 구조

외고반장은 초기 MVP에서 FastAPI backend 중심 구조를 사용한다.

```txt
frontend
→ backend FastAPI
   ├─ API
   ├─ DB services
   ├─ Agent Runtime
   ├─ RAG
   ├─ Approval
   └─ Evidence Log

data-pipeline
→ Chroma Vector DB

SQLite service DB
→ 서비스 데이터 저장 (`backend/data/oegobanjang.sqlite3`)
```

---

## 2. Backend

```txt
backend/
```

역할:

- 프론트엔드 API 제공
- DB 조회/저장
- Agent Runtime 실행
- 승인 처리
- Evidence Log 저장

---

## 3. Agent Runtime

```txt
backend/app/agent_runtime/
```

역할:

- LangChain 1.0 `create_agent(response_format=...)` 기반 Agent Execution
- LangChain tools를 통한 RAG Retrieval / DB·Rule 조회 / 초안 생성
- Middleware 기반 PII redaction, safety guardrail, call/tool limit, approval pending 처리
- structured_response를 기존 API 응답 shape으로 변환하는 compatibility adapter
- Evidence Log 후보 이벤트 생성

custom `backend/app/agent_runtime/legacy_graph/` workflow는 삭제했다. 단, `langgraph`
패키지는 LangChain `create_agent` 내부 구현과 durable checkpoint에 필요하므로 의존성에 남긴다.

LangChain v1 runtime은 strict `WorkBridgeAgentResponse` schema, runtime context,
`EvidenceCaptureMiddleware`, `WorkBridgeSafetyMiddleware`를 사용한다. tool 호출은
`tool_executed`, workforce retrieval은 `rag_retrieved`, approval-required tool/HITL interrupt는
`approval_requested` 후보 이벤트로 기록한다.

runtime state는 process-local `LangChainRuntimeStateStore`에 우선 저장하고,
동시에 `agent_runtime_state_snapshots` DB table에 PII-redacted snapshot으로 저장한다.
`/api/v1/agent/state/{request_id}`는 메모리 조회 실패 시 DB snapshot을 반환한다.
승인이 필요한 snapshot은 `approvals.target_type=agent_runtime_state_snapshot`으로 연결된다.
승인/반려는 snapshot의 approval 상태를 바꾸고, 승인 시에는 제한된 내부 action 기록,
준비용 outbox, checkpoint를 생성한다. 이 단계에서도 메시지 발송, 전문가 전달,
정부 제출은 실행하지 않는다.
process-local state가 아직 살아 있는 경우에도 approval API는 해당 hot state의 approval status를
동기화한다. 이 동기화 역시 상태 표시용이며 외부 실행을 하지 않는다.

승인 후 runtime 실행 기록은 아래 테이블로 분리한다.

```txt
approval_actions: 허용/차단 action 기록
delivery_outbox: 외부 전달 준비용 PENDING outbox. 발송 아님
agent_checkpoints: request_id/approval_id/resume_token/idempotency checkpoint
langchain_agent_checkpoints: LangGraph/LangChain execution checkpoint metadata
runtime_metrics: model/tool/retrieval/approval 관측값. 원문 PII 저장 금지
```

`GET /api/v1/agent/resume/{request_id}`는 checkpoint/action/outbox 상태를 안전 요약으로 반환한다.
`resume_token` 원문은 반환하지 않고 존재 여부만 표시한다.
`POST /api/v1/agent/resume/{request_id}`는 내부 action만 허용한다.
허용 action은 `finalize_internal_draft`, `mark_handoff_package_ready`,
`prepare_external_delivery`이고, 후보 메시지 자동 발송, 행정사 자동 전달,
송출회사 자동 전달, 정부 포털 제출은 계속 `403`으로 차단한다.
`POST /api/v1/agent/outbox/{request_id}/prepare`는 `delivery_outbox.status`를
`READY_FOR_INTERNAL_REVIEW`로만 바꾸며, `prepare_external_delivery` action과 checkpoint를
내부 검토 준비 완료 상태로 동기화한다. 이 endpoint도 실제 외부 발송, 전문가 전달,
정부 제출을 하지 않는다.
`POST /api/v1/agent/checkpoints/{request_id}/resume`은 approval이 `APPROVED`인
내부 action에 한해 LangGraph `Command(resume=...)`를 호출한다. 외부 action은 계속 `403`이다.
checkpoint SQLite 파일은 앱 DB와 분리해 `backend/data/langchain_checkpoints.sqlite3`에 둔다.

---

## 4. Frontend

역할:

- 대시보드
- 직원 관리
- 채용 요청
- 비자/체류 관리
- 서류 체크
- 다국어 메시지
- 승인 대기
- Evidence Log 조회

---

## 5. Data Pipeline

역할:

- 공식 문서 수집
- PDF/HTML/CSV 로딩
- chunking
- metadata 정규화
- Vector DB 적재

---

## 6. 데이터 저장소

### SQLite service DB

현재 MVP의 서비스 정형 데이터를 저장한다.
DB 파일은 backend 실행 기준 `backend/data/oegobanjang.sqlite3`이다.
Chroma와는 별도 저장소다.

- approvals
- contact_messages
- status_update_candidates
- handoff_package_drafts
- evidence_logs
- agent_runtime_state_snapshots
- approval_actions
- delivery_outbox
- agent_checkpoints
- langchain_agent_checkpoints
- runtime_metrics

아래 context tables는 2026-05-09 기준 SQLAlchemy 모델과 Alembic migration이 있다.
runtime tool은 이 DB context repository를 우선 조회하고, seed CSV는 데모/fixture fallback으로만 서비스 계층에 격리한다.

- users
- companies
- workers
- candidates
- document_requirements
- worker_documents

아래 context 영역은 아직 planned 상태다.

- worker_sensitive_profiles
- hiring_requests
- visas
- rag_sources

### Chroma

RAG 검색용 벡터 데이터를 저장한다.

- 법령
- 절차 안내
- 서식
- 안전/생활 안내
- 메시지 템플릿
- 합성 케이스

### Redis

초기 필수 구성요소는 아니다.

추후 아래 용도로 사용할 수 있다.

- 알림 중복 방지
- 백그라운드 작업 큐
- 짧은 캐시
- Agent 실행 상태 임시 저장

---

## 7. 요청 흐름

```txt
사용자 요청
→ frontend
→ backend API
→ Agent Runtime
→ LangChain create_agent
→ tools + middleware + structured_response
→ RAG/Rule/DB 조회 및 approval_required 판단
→ Evidence Log 저장
→ frontend 응답
```

---

## 8. 확장 기준

다음 조건이 생기면 Agent Runtime을 별도 서비스로 분리할 수 있다.

- Agent 실행 시간이 길어짐
- Agent 실행만 별도 스케일링해야 함
- 비동기 큐 기반 실행이 필요함
- 다른 서비스에서 Agent Runtime을 호출해야 함
- RAG/LLM 비용 모니터링을 독립적으로 해야 함
