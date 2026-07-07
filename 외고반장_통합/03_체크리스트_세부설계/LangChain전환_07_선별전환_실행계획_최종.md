# 인력확보 Agent LangChain 1.x 선별 전환 계획

## Summary

두 문서의 공통 결론이 맞습니다. 최선안은 **LangGraph workflow, Chroma-only RAG, deterministic fallback, Approval Gate, Evidence Log는 유지**하고, LLM이 실제로 개입하는 지점만 LangChain 1.x의 `with_structured_output()`으로 전환하는 방식입니다.

공식 LangChain 문서도 structured output은 Pydantic schema 검증과 `include_raw=True`를 지원하며, `create_agent(response_format=...)`는 단일 agent loop에 적합합니다. 외고반장처럼 RAG → Rule → LLM → Validator → Approval → Evidence 순서가 중요한 시스템에서는 `create_agent` 전면 교체보다 기존 LangGraph 안에 structured LLM node를 끼우는 쪽이 안전합니다. 참고: [LangChain structured output](https://docs.langchain.com/oss/python/langchain/structured-output), [LangChain model structured output](https://docs.langchain.com/oss/python/langchain/models).

## Key Changes

- `intent_router_node`는 수동 JSON parsing을 제거하고 `IntentClassification` Pydantic schema + `ChatOpenAI.with_structured_output(..., method="json_schema", strict=True)`로 전환합니다. 실패 시 기존처럼 empty intent가 아니라 `UNSUPPORTED_*` 또는 structured blocker를 남기도록 테스트로 고정합니다.

- `WorkforceJudgmentChain`을 새로 추가합니다. 입력은 `WorkforceAgentPromptInput`, 출력은 기존 `WorkforceAgentResponse`입니다. `include_raw=True`를 켜되 Evidence Log에는 raw content 전체를 저장하지 않고 `raw_present`, `token_usage`, `model_name`, `parsing_error`, `raw_content_hash`만 저장합니다.

- `runtime_mode`를 명시적으로 추가합니다. 기본값은 `deterministic`이고, `langchain_judgment`일 때만 WorkforceJudgmentChain을 호출합니다. LLM 결과는 deterministic output을 즉시 덮어쓰지 않고 `structured_response.llm_candidate` 또는 `state.workforce_llm_response`로 보관한 뒤 validation 통과 시 UI/로그에 노출합니다.

- API는 실제 사용 중인 `backend/app/api/v1/agent.py`의 `AgentRunRequest`에 `runtime_mode` optional field를 추가합니다. `backend/app/schemas/agent.py`는 현재 0-byte라 이번 전환의 기준 파일로 쓰지 않습니다.

- Validator는 1차부터 분리합니다. `workforce_contract.py`의 Pydantic validator는 유지하되, 별도 `workforce_validators.py`에서 safety, evidence, business rule을 각각 검사합니다. 금지 판단, source_id 미조회, evidence_grade D/F 공식근거 오용, approval 누락은 모두 fail-closed 처리합니다.

- Dependency 의도도 고정합니다. `pyproject.toml`은 현재 느슨한 `>=0.3.0` 대신 lock과 맞춰 `langchain>=1.2,<2`, `langchain-core>=1.3,<2`, `langchain-openai>=1.2,<2`, `langchain-chroma>=1.1,<2`, `langchain-text-splitters>=1.1,<2`로 좁힙니다.

## Implementation Steps

- Task 1: Intent Router structured output 전환. 테스트를 먼저 추가해 백틱 JSON, 잘못된 JSON, unsupported judgment 요청이 모두 deterministic하게 처리되는지 검증한 뒤 수동 `json.loads` 경로를 제거합니다.

- Task 2: `WorkforceJudgmentChain` 추가. `with_structured_output(WorkforceAgentResponse, method="json_schema", strict=True, include_raw=True)`를 사용하고, API key가 없으면 명시적으로 skip reason을 반환하게 합니다.

- Task 3: runtime mode 연결. `ForeignHiringState`, `run_workflow`, `/api/v1/agent/run`에 `runtime_mode`를 전달하고, 기본값은 반드시 `deterministic`으로 유지합니다.

- Task 4: validation/evidence 강화. LLM output은 safety/evidence/business validator를 통과해야 하며, 결과는 `rag_retrieved`, `tool_executed`, `approval_requested`, `final_response_generated`에 prompt/schema/model/validation metadata로 남깁니다.

- Task 5: 문서와 eval 갱신. `docs/langchain-1-migration-plan.md`는 실제 API/schema 경로와 새 runtime boundary로 정정하고, `workforce_judgment_safety_cases.jsonl`을 추가해 후보 추천/국적 선호/성실도/비자 확정 판단을 차단합니다.

## Test Plan

- `test_intent_router_structured_output.py`: structured intent 반환, provider error, malformed model output, unsupported judgment routing 검증.

- `test_workforce_judgment_chain.py`: `with_structured_output` 호출, `include_raw=True` 결과 처리, API key 없음, parsing error, forbidden phrase reject 검증.

- `test_hiring_agent_runtime_mode.py`: deterministic 기본값에서 chain 미호출, `langchain_judgment`에서 chain 호출, FORBIDDEN 요청에서는 chain 호출 전 차단 검증.

- `test_workforce_validators.py`: source_id가 retrieved citations 안에 없으면 실패, D/F/case evidence를 공식 근거로 쓰면 실패, approval false면 실패, raw PII가 Evidence Log metadata에 저장되지 않음을 검증.

- Full gate: `uv run pytest backend/tests -q`, `uv run python scripts/evaluate_workforce_retrieval.py --dataset evals/datasets/workforce_retrieval_quality_cases.csv --top-k 5 --min-hit-at-3 0.80`.

## Assumptions

- LangGraph는 유지합니다. `create_agent`는 이번 범위에서 쓰지 않습니다.
- LLM은 실행자가 아니라 structured draft generator입니다. 발송, 제출, 외부 전달은 계속 Human Approval 이후입니다.
- Chroma runtime retrieval은 유지합니다. JSONL/PolicyRetriever fallback은 다시 열지 않습니다.
- 운영 기본값은 `deterministic`입니다. `langchain_judgment`는 명시 요청과 API key가 있을 때만 켜집니다.
- `include_raw=True`는 디버깅용으로 쓰되 raw text 원문은 Evidence Log에 저장하지 않습니다.
