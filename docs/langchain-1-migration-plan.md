# LangChain 1.0 create_agent-First Migration

## 결정

Agent Runtime의 production orchestration은 LangChain 1.0 `create_agent`를 중심으로 둔다.
`create_agent(response_format=...)`, LangChain middleware, LangChain tools가 런타임 경계다.

## LangGraph 처리

`langgraph` 의존성은 당장 제거하지 않는다. LangChain `create_agent`가 내부적으로
LangGraph 기반 실행 객체를 만들 수 있기 때문이다. 제거 대상은 repo가 직접 조립하던
custom `backend/app/agent_runtime/legacy_graph/workflow.py`와 `legacy_graph/nodes/*` production import다.

## P0 범위

- `backend/app/agent_runtime/langchain_v1/`를 production runtime으로 사용한다.
- `/api/v1/agent/run`의 `user_message`와 `user_request`는 모두 `AgentRuntimeInput.user_message`로 정규화한다.
- `WorkBridgeAgentResponse` structured output을 기존 `AgentRunResponse` shape으로 변환한다.
- approval은 resume 없는 pending-only 방식이다.
- `LangChainRuntimeStateStore`는 process-local in-memory hot store이고,
  `/api/v1/agent/run`은 `agent_runtime_state_snapshots` DB snapshot도 best-effort로 저장한다.
  `/api/v1/agent/state/{request_id}`는 메모리에 없으면 DB snapshot으로 fallback한다.
- 승인 필요한 runtime snapshot은 `approvals.target_type=agent_runtime_state_snapshot` row를 만든다.
  공용 approval API의 승인/반려는 snapshot의 approval 상태만 갱신하고 agent resume,
  메시지 발송, 전문가 전달, 정부 제출은 실행하지 않는다.
  process-local `LangChainRuntimeStateStore`가 아직 살아 있으면 같은 approval status를 동기화하지만,
  이 역시 표시 상태 갱신일 뿐 agent resume은 아니다.
- Chroma workforce collections는 runtime retrieval의 주 경로이며 JSONL fallback을 쓰지 않는다.
- `WorkBridgeAgentResponse` 계열 schema는 strict mode이며 금지 후보 평가 필드와 D/F/case 근거 오용을 거부한다.
- Evidence/Safety는 runtime adapter 합성이 아니라 `EvidenceCaptureMiddleware`와 `WorkBridgeSafetyMiddleware`가 담당한다.
- Contact request는 `/agent/run`에서 legacy response bypass를 타지 않고 LangChain v1 request normalizer와 structured runtime을 지난다. 기존 contact service 동작은 service-level 테스트에서 보존한다.

## 후속 범위

- approval resume 후 실제 발송/제출 실행
- approval resume에 필요한 durable checkpoint 설계
- `legacy_graph/` 최종 삭제 또는 별도 archive 이동
- 운영 OpenAI model 품질 평가와 cost/latency monitoring
