# LangChain 1.0 create_agent-First Migration

## 결정

Agent Runtime의 production orchestration은 LangChain 1.0 `create_agent`를 중심으로 둔다.
`create_agent(response_format=...)`, LangChain middleware, LangChain tools가 runtime 경계다.

## LangGraph 처리

`langgraph` 의존성은 당장 제거하지 않는다. LangChain `create_agent`가 내부적으로
LangGraph 기반 실행 객체를 만들 수 있기 때문이다.

제거 대상은 repo가 직접 조립하던 custom graph workflow다.
`backend/app/agent_runtime/legacy_graph/workflow.py`와 `legacy_graph/nodes/*`는 archive 영역이며
production import 대상이 아니다.

## P0 완료 범위

- `backend/app/agent_runtime/langchain_v1/`를 production runtime으로 사용한다.
- `/api/v1/agent/run`은 `user_message`와 `user_request`를 모두 `AgentRuntimeInput.user_message`로 정규화한다.
- `WorkBridgeAgentResponse` structured output을 기존 `AgentRunResponse` shape으로 변환한다.
- approval은 resume 없는 pending-only 방식이다.
- `LangChainRuntimeStateStore`는 process-local hot store이고, `/api/v1/agent/run`은 `agent_runtime_state_snapshots` DB snapshot도 저장한다.
- `/api/v1/agent/state/{request_id}`는 메모리에 없으면 DB snapshot으로 fallback한다.
- Chroma workforce collections가 runtime retrieval의 주 경로이며 JSONL fallback은 runtime에서 사용하지 않는다.
- `WorkBridgeAgentResponse` 계열 schema는 strict mode이며 후보 점수화/국적 선호/이탈 예측 필드와 D/F/case 근거 오용을 거부한다.
- Evidence/Safety는 `EvidenceCaptureMiddleware`와 `WorkBridgeSafetyMiddleware`가 담당한다.
- Contact request는 legacy bypass 없이 LangChain v1 request normalizer와 structured runtime으로 진입한다.

## 2026-05-09 후속 구현

- `agent_runtime_state_snapshots` Alembic migration을 추가했다.
- `users`, `companies`, `workers`, `candidates`, `document_requirements`, `worker_documents` context tables 모델과 migration을 추가했다.
- `context_data_service`를 추가해 runtime tool이 DB context repository를 우선 조회하게 했다.
- `safe_read`, `safe_calculate`, `safe_draft`에서 CSV 직접 읽기를 제거하고 context service로 격리했다.
- seed CSV는 데모 fixture/fallback으로만 남긴다.
- 승인 후에도 외부 발송/정부 제출/agent resume은 실행하지 않고, 내부 초안 확정과 internal handoff 준비 완료 상태만 snapshot에 표시한다.
- approval review 시 `approval_reviewed`, `resume_requested`, `resume_completed_or_blocked` evidence log를 남긴다.
- LangChain middleware model/tool/retrieval metadata에 latency, retrieval count, token usage 가능 값을 남긴다.

## 후속 범위

- approval resume 이후 실제 메시지 발송/전문가 전달/정부 제출 실행은 별도 보안 설계 이후 진행한다.
- durable checkpoint 기반 resume 설계는 별도 mission으로 분리한다.
- `legacy_graph/` 최종 삭제 또는 별도 archive 이동은 legacy 테스트 이전 완료 후 결정한다.
- 운영 OpenAI model 품질, 비용, latency monitoring은 deterministic/fake test와 분리해 운영 eval job으로 관리한다.
