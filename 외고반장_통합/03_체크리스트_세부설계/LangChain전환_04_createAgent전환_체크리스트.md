# LangChain 1.0 `create_agent`-First 전환 체크리스트

## 목적

이 문서는 `create_agent(response_format=...) + middleware + tools`를 중심으로 LangChain 1.0 런타임을 적용하기 위한 실행 체크리스트다.

핵심 방향은 다음과 같다.

- `langchain_v1`을 새 기본 runtime으로 둔다.
- 기존 custom `BaseStructuredChain`은 core runtime에서 사용하지 않는다.
- 기존 custom `graph/workflow.py`, `graph/nodes/*` orchestration은 production 경로에서 제거한다.
- 단, `langgraph` dependency 자체는 제거하지 않는다. `create_agent` 내부가 LangGraph 기반이므로, 제거 대상은 repo가 직접 관리하던 custom graph runtime이다.
- 외부 API shape은 유지한다.
- Human Approval, Evidence Log, RAG/DB/Rule/LLM 역할 분리는 기존 도메인 원칙을 유지한다.

---

## 0. 전환 방향 확인

- [ ] 이번 전환의 기본 runtime은 `langchain_v1`이다.
- [ ] `create_agent(response_format=...) + middleware + tools`를 런타임 중심으로 둔다.
- [ ] 기존 custom `BaseStructuredChain`은 core runtime에서 사용하지 않는다.
- [ ] 기존 custom `graph/workflow.py`, `graph/nodes/*` orchestration은 production 경로에서 제거한다.
- [ ] 단, `langgraph` dependency 자체는 제거하지 않는다.
- [ ] 제거 대상은 custom graph runtime이지 LangChain 내부 LangGraph가 아님을 문서에 명시한다.
- [ ] 외부 API shape은 유지한다.
- [ ] 기존 프론트/API consumer가 깨지지 않도록 adapter layer를 둔다.
- [ ] Human Approval, Evidence Log, RAG/DB/Rule/LLM 역할 분리는 기존 도메인 원칙을 유지한다.

---

## 1. 새 패키지 구조 생성 체크

`backend/app/agent_runtime/langchain_v1/` 패키지를 만든다.

- [ ] `backend/app/agent_runtime/langchain_v1/__init__.py` 생성
- [ ] `backend/app/agent_runtime/langchain_v1/agent_factory.py` 생성
- [ ] `backend/app/agent_runtime/langchain_v1/runtime.py` 생성
- [ ] `backend/app/agent_runtime/langchain_v1/schemas.py` 생성
- [ ] `backend/app/agent_runtime/langchain_v1/middleware.py` 생성
- [ ] `backend/app/agent_runtime/langchain_v1/tools.py` 생성
- [ ] 필요 시 `backend/app/agent_runtime/langchain_v1/state_store.py` 생성
- [ ] 필요 시 `backend/app/agent_runtime/langchain_v1/adapters.py` 생성
- [ ] 필요 시 `backend/app/agent_runtime/langchain_v1/config.py` 생성

---

## 2. `schemas.py` 체크

새 structured output 계약을 정의한다.

- [ ] `WorkBridgeAgentResponse` top-level schema를 만든다.
- [ ] `WorkforceAgentResponse`를 포함한다.
- [ ] `VisaAgentResponse`를 포함한다.
- [ ] `ContactAgentResponse`를 포함한다.
- [ ] `FinalResponseDraft`를 포함한다.
- [ ] `HandoffDraft` 또는 `HandoffDraftResponse`를 포함한다.
- [ ] 기존 response 계약을 `WorkBridgeAgentResponse`로 통합한다.
- [ ] 기존 `AgentRunResponse`는 adapter에서 변환하도록 둔다.

### 2-1. `WorkBridgeAgentResponse` 필수 필드 체크

- [ ] `final_response`
- [ ] `detected_intents`
- [ ] `risk_flags`
- [ ] `approval`
- [ ] `handoff`
- [ ] `evidence_events`
- [ ] `rag_contexts`
- [ ] `domain_payload`
- [ ] `blocked_reason`

### 2-2. Schema 안전 규칙 체크

- [ ] 후보 추천/성실도/장기근속/이탈 예측 필드를 허용하지 않는다.
- [ ] 국적별 선호/우열 필드를 허용하지 않는다.
- [ ] 비자 최종판정 필드를 허용하지 않는다.
- [ ] 자동 발송/자동 제출을 허용하지 않는다.
- [ ] 외부 전달은 반드시 `approval_required=true` 또는 `approval.status=PENDING`으로 표현한다.
- [ ] evidence에는 `source_id`, `doc_type`, `evidence_grade`, `used_for`를 포함한다.
- [ ] D/F/case evidence가 공식 근거로 쓰이지 않도록 schema/validator에서 차단한다.

---

## 3. `agent_factory.py` 체크

`create_agent` 생성 지점을 하나로 모은다.

- [ ] `create_workbridge_agent(model=...)` 함수를 만든다.
- [ ] `create_agent()`를 호출한다.
- [ ] `model`을 외부에서 주입할 수 있게 한다.
- [ ] fake model 주입이 가능해야 한다.
- [ ] 실제 테스트에서 OpenAI API를 호출하지 않도록 한다.
- [ ] `tools`를 factory에 주입한다.
- [ ] `middleware`를 factory에 주입한다.
- [ ] `system_prompt`를 factory에서 연결한다.
- [ ] `response_format=WorkBridgeAgentResponse`를 연결한다.
- [ ] schema generation failure를 structured blocked/error response로 처리한다.
- [ ] production runtime에서는 이 factory만 agent 생성 진입점으로 사용한다.

예상 구조:

```python
agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt,
    middleware=middleware,
    response_format=WorkBridgeAgentResponse,
)
```

---

## 4. `runtime.py` 체크

`/api/v1/agent/run`에서 호출하는 단일 실행 진입점을 만든다.

- [ ] `run_langchain_v1_agent()` 함수를 만든다.
- [ ] 기존 `run_workflow()`는 내부적으로 `run_langchain_v1_agent()`를 호출하게 한다.
- [ ] API/runner가 custom `graph.workflow`를 직접 import하지 않게 한다.
- [ ] `AgentRuntimeInput`을 만든다.
- [ ] `user_message`와 `user_request`를 모두 `AgentRuntimeInput.user_message`로 정규화한다.
- [ ] 기존 `/agent/run`의 `user_request` contact-agent 우회 분기를 제거한다.
- [ ] contact-agent 우회 분기는 `langchain_v1` request normalizer로 흡수한다.
- [ ] `structured_response`를 받아 adapter로 기존 응답 shape에 맞춘다.
- [ ] runtime preflight를 먼저 실행한다.
- [ ] missing OpenAI key를 silent deterministic fallback으로 숨기지 않는다.
- [ ] Chroma collection empty도 structured blocked/error response로 반환한다.
- [ ] missing tool registry도 structured blocked/error response로 반환한다.

---

## 5. API Compatibility Adapter 체크

외부 API 응답 구조는 유지한다.

- [ ] `structured_response` → 기존 `AgentRunResponse` 변환 adapter를 만든다.
- [ ] 기존 프론트에서 기대하는 필드를 유지한다.
- [ ] 기존 `approval_required` 필드를 유지한다.
- [ ] 기존 `approval_status` 필드를 유지한다.
- [ ] 기존 `request_id` 필드를 유지한다.
- [ ] 기존 contact persistence 동작을 유지한다.
- [ ] 기존 approval 저장 동작을 유지한다.
- [ ] 기존 handoff 저장 동작을 유지한다.
- [ ] `ForeignHiringState`는 P0에서 compatibility DTO로만 유지한다.
- [ ] 내부 orchestration state는 `LangChainRuntimeState`와 `WorkBridgeAgentResponse`가 담당한다.
- [ ] 기존 API 응답 변환이 필요한 곳에서만 `ForeignHiringState` 호환 필드를 채운다.

---

## 6. State Store 체크

`/api/v1/agent/state/{request_id}` 충돌을 별도로 처리한다.

- [ ] custom graph `MemorySaver` 조회를 제거한다.
- [ ] `LangChainRuntimeStateStore`를 만든다.
- [ ] P0에서는 process-local in-memory store로 구현한다.
- [ ] `request_id` 기준 latest structured_response를 저장한다.
- [ ] `request_id` 기준 evidence_events를 저장한다.
- [ ] `request_id` 기준 approval 상태를 저장한다.
- [ ] `request_id` 기준 interrupt metadata를 저장한다.
- [ ] `/agent/state/{request_id}`가 새 store를 조회하게 한다.
- [ ] DB 영속 저장은 후속 mission으로 분리한다.
- [ ] approval resume/send는 후속 mission으로 분리한다.

---

## 7. Tools 전환 체크

기존 safe tool들을 LangChain tool로 wrapping한다.

- [ ] 기존 safe read tool을 LangChain tool로 wrapping한다.
- [ ] 기존 safe calculate tool을 LangChain tool로 wrapping한다.
- [ ] 기존 safe draft tool을 LangChain tool로 wrapping한다.
- [ ] approval-required tool을 LangChain tool로 wrapping한다.
- [ ] `retrieve_workforce_materials` tool을 만든다.
- [ ] `workforce_official` Chroma collection을 tool에서 검색한다.
- [ ] `workforce_templates` Chroma collection을 tool에서 검색한다.
- [ ] JSONL/PolicyRetriever fallback은 runtime에서 제거한다.
- [ ] `case/D/F` record는 공식 근거로 반환하지 않는다.
- [ ] approval-required tool은 실제 실행하지 않는다.
- [ ] approval-required tool은 `NEEDS_APPROVAL` 결과만 반환한다.
- [ ] 외부 발송 tool은 실제 발송하지 않는다.
- [ ] 정부 제출 tool은 실제 제출하지 않는다.
- [ ] 행정사 전달 tool은 실제 전달하지 않는다.
- [ ] 모든 tool call은 evidence event로 기록한다.

---

## 8. Middleware 구성 체크

LangChain middleware를 공식 런타임 경계로 사용한다.

### 8-1. PII Middleware

- [ ] 외국인등록번호 redaction
- [ ] 여권번호 redaction
- [ ] 전화번호 redaction
- [ ] 이메일 redaction
- [ ] raw PII가 structured_response에 남지 않도록 한다.
- [ ] raw PII가 Evidence Log metadata에 저장되지 않도록 한다.

### 8-2. WorkBridge Safety Middleware

- [ ] 후보 추천 요청 차단
- [ ] 국적 선호 요청 차단
- [ ] 성실도 판단 요청 차단
- [ ] 장기근속 가능성 예측 차단
- [ ] 이탈 예측 차단
- [ ] 비자 최종판정 차단
- [ ] 법률 자문처럼 보이는 답변 차단
- [ ] 자동 발송/자동 제출 표현 차단

### 8-3. Evidence Capture Middleware

- [ ] `intent_classified` event 생성
- [ ] `rag_retrieved` event 생성
- [ ] `tool_executed` event 생성
- [ ] `approval_requested` event 생성
- [ ] `final_response_generated` event 생성
- [ ] tool name 기록
- [ ] source_id 기록
- [ ] evidence_grade 기록
- [ ] model_name 기록
- [ ] parsing_error 기록
- [ ] raw content 원문은 저장하지 않는다.
- [ ] raw_content_hash만 저장한다.

### 8-4. Human-in-the-loop Middleware

- [ ] 외부 발송 전 interrupt
- [ ] export 전 interrupt
- [ ] 정부 제출 전 interrupt
- [ ] 행정사 전달 전 interrupt
- [ ] interrupt 발생 시 API는 `approval_required=true`를 반환한다.
- [ ] interrupt 발생 시 API는 `approval_status=PENDING`을 반환한다.
- [ ] interrupt metadata를 state store에 저장한다.
- [ ] P0에서는 resume을 구현하지 않는다.
- [ ] 승인 후 자동 resume/send는 후속 mission으로 분리한다.

### 8-5. Summarization Middleware

- [ ] 긴 RAG context를 요약한다.
- [ ] citation-preserving summary를 요구한다.
- [ ] preserved citations를 남긴다.
- [ ] omitted sections를 남긴다.
- [ ] confidence를 남긴다.
- [ ] P0에서 필수 구현인지 후순위인지 결정한다.

---

## 9. Approval Handling 체크

P0에서는 resume 없는 pending-only 방식으로 고정한다.

- [ ] approval-required tool은 실제 실행하지 않는다.
- [ ] approval-required tool은 `NEEDS_APPROVAL` 결과만 반환한다.
- [ ] runtime adapter는 `NEEDS_APPROVAL`을 `approval_required=true`로 합성한다.
- [ ] runtime adapter는 `approval_status=PENDING`을 반환한다.
- [ ] HumanInTheLoopMiddleware interrupt는 2차 안전망으로 둔다.
- [ ] HITL interrupt가 발생해도 pending response를 합성한다.
- [ ] state store에 approval 상태를 저장한다.
- [ ] evidence log에 `approval_requested` event를 저장한다.
- [ ] 담당자 승인 이후 실제 외부 발송은 구현하지 않는다.
- [ ] 담당자 승인 이후 정부 제출은 구현하지 않는다.
- [ ] 담당자 승인 이후 행정사 전달은 구현하지 않는다.
- [ ] approval resume/send는 후속 mission으로 분리한다.

---

## 10. RAG Runtime 체크

RAG runtime은 Chroma-only로 유지한다.

- [ ] `workforce_official` collection을 사용한다.
- [ ] `workforce_templates` collection을 사용한다.
- [ ] `retrieve_workforce_materials` tool로 Chroma retrieval을 노출한다.
- [ ] JSONL fallback을 제거한다.
- [ ] PolicyRetriever fallback을 제거한다.
- [ ] `case/D/F` record를 공식 근거로 반환하지 않는다.
- [ ] retrieval 결과에는 `source_id`가 있다.
- [ ] retrieval 결과에는 `title`이 있다.
- [ ] retrieval 결과에는 `doc_type`이 있다.
- [ ] retrieval 결과에는 `evidence_grade`가 있다.
- [ ] retrieval 결과에는 `summary` 또는 content snippet이 있다.
- [ ] Chroma collection empty 시 structured blocked/error response를 반환한다.
- [ ] retrieval eval을 유지한다.
- [ ] `Hit@3 >= 0.80` gate를 유지한다.

---

## 11. Dependency Migration 체크

`pyproject.toml` 의존성을 명확히 좁힌다.

- [ ] `langchain>=1.2,<2`
- [ ] `langchain-core>=1.3,<2`
- [ ] `langchain-openai>=1.2,<2`
- [ ] `langchain-chroma>=1.1,<2`
- [ ] `langchain-text-splitters>=1.1,<2`
- [ ] `langgraph`는 유지한다.
- [ ] `langgraph`는 `create_agent` 내부 의존성으로 유지한다고 문서화한다.
- [ ] lock file 갱신
- [ ] dependency migration 후 test green 확인

---

## 12. Runtime Config 체크

새 runtime config를 추가한다.

- [ ] `openai_model`
- [ ] `langchain_runtime_enabled`
- [ ] `chroma_workforce_official_collection`
- [ ] `chroma_workforce_templates_collection`
- [ ] `chroma_persist_directory`
- [ ] missing config는 preflight에서 structured error 처리한다.
- [ ] 운영에서 API key 없음은 silent fallback하지 않는다.
- [ ] 테스트에서는 fake model injection을 사용한다.

---

## 13. Test Model Injection 체크

테스트는 실제 OpenAI 호출 없이 돌아가야 한다.

- [ ] `create_workbridge_agent(model=...)` 형태로 fake model을 주입할 수 있다.
- [ ] fake model이 structured_response를 반환할 수 있다.
- [ ] fake model이 malformed output을 반환하는 테스트가 가능하다.
- [ ] fake model이 forbidden judgment output을 반환하는 테스트가 가능하다.
- [ ] fake model이 approval-required action을 유도하는 테스트가 가능하다.
- [ ] backend test는 실제 OpenAI API key 없이 통과한다.

---

## 14. Custom Graph Runtime 제거 체크

production 경로에서 custom graph import를 제거한다.

- [ ] API/runner가 `app.agent_runtime.graph.workflow`를 import하지 않는다.
- [ ] `run_workflow()`는 `run_langchain_v1_agent()` adapter로 전환한다.
- [ ] 기존 `intent_router` node 책임은 agent/middleware/schema로 이동한다.
- [ ] 기존 `planner` node 책임은 agent/tool planning으로 이동한다.
- [ ] 기존 `executor` node 책임은 agent tool call로 이동한다.
- [ ] 기존 `approval_gate` node 책임은 approval-required tool + HITL middleware + adapter로 이동한다.
- [ ] 기존 `final_response` node 책임은 structured response로 이동한다.
- [ ] green 이후 custom graph 파일을 `legacy_graph/`로 격리한다.
- [ ] production import가 0개인지 테스트로 고정한다.
- [ ] custom graph 파일 삭제는 green 이후 결정한다.

---

## 15. API Normalization 체크

`/agent/run` 입력을 정규화한다.

- [ ] 기존 `user_message` 요청을 지원한다.
- [ ] 기존 `user_request` 요청을 지원한다.
- [ ] 둘 다 `AgentRuntimeInput.user_message`로 정규화한다.
- [ ] contact-agent 우회 분기를 제거한다.
- [ ] contact-agent 우회 분기는 `langchain_v1` request normalizer로 흡수한다.
- [ ] legacy endpoint가 필요하면 별도로 분리한다.
- [ ] 기존 contact persistence는 adapter에서 유지한다.
- [ ] 기존 approval 저장은 adapter에서 유지한다.
- [ ] 기존 handoff 저장은 adapter에서 유지한다.

---

## 16. Runtime Preflight 체크

실행 전 실패 조건을 먼저 확인한다.

- [ ] OpenAI key 존재 여부 확인
- [ ] Chroma persist directory 존재 여부 확인
- [ ] `workforce_official` collection 존재 여부 확인
- [ ] `workforce_templates` collection 존재 여부 확인
- [ ] tool registry 존재 여부 확인
- [ ] response schema 생성 가능 여부 확인
- [ ] runtime config 유효성 확인
- [ ] preflight 실패 시 structured blocked/error response 반환
- [ ] preflight 실패를 Evidence Log에 기록
- [ ] preflight 실패 시 silent deterministic fallback하지 않는다.

---

## 17. Evidence Event Mapping 체크

Event mapping을 고정한다.

- [ ] agent start 또는 first model call → `intent_classified`
- [ ] retrieval tool call → `rag_retrieved`
- [ ] any tool call → `tool_executed`
- [ ] HITL interrupt → `approval_requested`
- [ ] structured response 완료 → `final_response_generated`
- [ ] blocked/safety failure → `safety_blocked`
- [ ] preflight failure → `runtime_preflight_failed`
- [ ] schema validation failure → `schema_validation_failed`

---

## 18. Test Plan 체크

### 18-1. Agent Factory Test

- [ ] `test_langchain_v1_agent_factory.py` 작성
- [ ] `create_agent`가 생성되는지 검증
- [ ] tools가 주입되는지 검증
- [ ] middleware가 주입되는지 검증
- [ ] `response_format=WorkBridgeAgentResponse`가 연결되는지 검증
- [ ] fake model 주입이 가능한지 검증

### 18-2. Runtime Test

- [ ] `test_langchain_v1_runtime.py` 작성
- [ ] `/agent/run`이 structured_response 기반 결과를 반환하는지 검증
- [ ] 기존 API shape이 유지되는지 검증
- [ ] preflight failure가 structured error로 반환되는지 검증
- [ ] missing OpenAI key가 silent fallback되지 않는지 검증

### 18-3. Middleware Test

- [ ] `test_langchain_v1_middleware.py` 작성
- [ ] PII redaction 검증
- [ ] forbidden judgment block 검증
- [ ] approval interrupt 검증
- [ ] evidence event 생성 검증
- [ ] raw PII가 로그에 저장되지 않는지 검증

### 18-4. State Store Test

- [ ] `test_langchain_v1_state_store.py` 작성
- [ ] `/agent/state/{request_id}`가 custom graph `MemorySaver` 없이 동작하는지 검증
- [ ] latest state 조회 검증
- [ ] structured_response 조회 검증
- [ ] evidence_events 조회 검증
- [ ] approval 상태 조회 검증

### 18-5. Chroma Runtime Test

- [ ] `test_workforce_chroma_only_runtime.py` 작성
- [ ] runtime retrieval이 Chroma collection만 쓰는지 검증
- [ ] JSONL fallback이 호출되지 않는지 검증
- [ ] PolicyRetriever fallback이 호출되지 않는지 검증
- [ ] D/F/case evidence가 공식 근거로 반환되지 않는지 검증

### 18-6. No Custom Graph Import Test

- [ ] `test_no_custom_graph_runtime_imports.py` 작성
- [ ] API가 custom `graph.workflow`를 import하지 않는지 검증
- [ ] runner가 custom `graph.workflow`를 import하지 않는지 검증
- [ ] production 경로 import가 0개인지 검증

---

## 19. Full Gate 체크

- [ ] `uv run pytest backend/tests -q` 통과
- [ ] `uv run python scripts/evaluate_workforce_retrieval.py --dataset evals/datasets/workforce_retrieval_quality_cases.csv --top-k 5 --min-hit-at-3 0.80` 통과
- [ ] retrieval Hit@3 0.80 이상
- [ ] safety block 테스트 0 fail
- [ ] approval pending 테스트 0 fail
- [ ] PII redaction 테스트 0 fail
- [ ] custom graph production import 0개
- [ ] API compatibility 테스트 통과

---

## 20. Docs Migration 체크

아래 문서를 `create_agent` runtime 기준으로 갱신한다.

- [ ] `AGENTS.md` 갱신
- [ ] `docs/ARCHITECTURE.md` 갱신
- [ ] `docs/API_CONTRACT.md` 갱신
- [ ] `docs/EVIDENCE_LOG_SCHEMA.md` 갱신
- [ ] `docs/langchain-1-migration-plan.md` 갱신
- [ ] custom graph runtime 제거/legacy 격리 정책 문서화
- [ ] `langgraph` dependency 유지 이유 문서화
- [ ] Approval pending-only 정책 문서화
- [ ] raw content 원문 로그 저장 금지 정책 문서화
- [ ] Chroma-only runtime 정책 문서화
- [ ] `create_agent(response_format=WorkBridgeAgentResponse)` 중심 런타임 구조 문서화
- [ ] `WorkBridgeAgentResponse` top-level schema 문서화
- [ ] API compatibility adapter 동작 문서화
- [ ] `/agent/run` 입력 정규화 정책 문서화
- [ ] `/agent/state/{request_id}` 새 state store 조회 방식 문서화
- [ ] approval resume/send 미구현 상태와 후속 mission 분리 방침 문서화
- [ ] production에서 custom graph import 0개를 유지해야 한다는 원칙 문서화
- [ ] Evidence event mapping 문서화
- [ ] PII redaction 범위 문서화
- [ ] fake model 기반 테스트 전략 문서화
- [ ] docs migration 완료 여부를 최종 완료 기준에 포함

---

# 최종 완료 기준

아래가 만족되면 `create_agent`-First 전환 1차 완료로 볼 수 있다.

- [ ] `langchain_v1` 패키지 생성 완료
- [ ] `WorkBridgeAgentResponse` top-level schema 확정
- [ ] `create_workbridge_agent()` 구현 완료
- [ ] `run_langchain_v1_agent()` 구현 완료
- [ ] `/api/v1/agent/run`이 새 runtime을 사용
- [ ] 기존 API response shape 유지
- [ ] `/api/v1/agent/state/{request_id}`가 새 state store를 사용
- [ ] custom graph workflow production import 제거
- [ ] `BaseStructuredChain` core runtime 사용 제거
- [ ] Chroma-only retrieval 유지
- [ ] JSONL/PolicyRetriever fallback 제거
- [ ] approval-required tool이 실제 실행하지 않고 `NEEDS_APPROVAL` 반환
- [ ] API가 `approval_required=true`, `approval_status=PENDING` 반환 가능
- [ ] approval resume/send 미구현 상태가 명확히 문서화됨
- [ ] PII redaction 적용
- [ ] forbidden judgment block 적용
- [ ] Evidence event mapping 적용
- [ ] raw content 원문이 Evidence Log에 저장되지 않음
- [ ] fake model injection 가능
- [ ] backend tests green
- [ ] retrieval eval gate 통과
- [ ] docs migration 완료

---

## 한 줄 요약

이 체크리스트의 핵심은 custom graph orchestration을 production 경로에서 줄이고, `create_agent(response_format=WorkBridgeAgentResponse)`를 단일 런타임 중심으로 세우되, Approval은 pending-only, RAG는 Chroma-only, Evidence Log는 raw 원문 저장 금지, 테스트는 fake model 기반으로 고정하는 것이다.
