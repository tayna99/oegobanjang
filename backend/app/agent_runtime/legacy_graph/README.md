# Legacy Graph Runtime

이 폴더는 LangChain 1.0 `create_agent` 전환 이전에 사용하던 custom LangGraph
workflow 보관 영역이다.

Production runtime은 이 폴더를 import하지 않는다. 현재 production 진입점은
`backend/app/agent_runtime/langchain_v1/`와 `backend/app/agent_runtime/runner.py`의
LangChain v1 adapter다.

유지 목적:

- 과거 graph node 단위 테스트의 참고 구현 보존
- migration diff 추적
- 후속 cleanup mission에서 안전하게 삭제할 수 있는 archive 경계 제공

주의:

- 새 기능은 이 폴더에 추가하지 않는다.
- API, runner, production agents에서 이 폴더를 import하면 안 된다.
- `langgraph` dependency는 LangChain `create_agent` 내부 구현 때문에 남길 수 있지만,
  repo가 직접 관리하는 orchestration은 이 legacy 구현으로 되돌리지 않는다.
