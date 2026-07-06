# LangChain 1.x Structured Output 단계 전환 계획

## Summary

방향 확정합니다. **LangGraph는 workflow 오케스트레이션으로 유지**하고, LangChain 1.x는 각 LLM 호출부의 **structured output 계약 강화 계층**으로 단계 적용합니다.

최종 우선순위는 다음입니다.

```txt
P0: Intent Router + WorkforceJudgmentChain
P1: FinalResponse + VisaAgent + ContactAgent
P2: SafeDraft/HandoffDraft + Summarizer
P3: LangChain middleware 보조 검토
```

`create_agent` 전면 전환은 하지 않습니다. LLM은 실행자가 아니라 구조화된 초안 생성기이며, Chroma RAG, Rule Base, Approval Gate, Evidence Log는 계속 기존 구조가 주도합니다.

## Key Changes

- P0에서는 `intent_router_node`의 수동 JSON parsing을 `with_structured_output(IntentClassification)`으로 바꾸고, 인력확보 전용 `WorkforceJudgmentChain`을 추가합니다. 기본 runtime은 `deterministic`, 명시적으로 `langchain_judgment`일 때만 LLM structured candidate를 붙입니다.

- P1에서는 최종 응답과 기존 mission agent 출력도 schema화합니다. `FinalResponseDraft`, `VisaAgentResponse`, `ContactAgentResponse`를 추가해 자유 텍스트 응답, 비자 확정 표현, 자동 발송 표현, PII 노출을 차단합니다.

- P2에서는 대외 전달 초안과 긴 RAG context 요약을 schema화합니다. `SafeDraftResponse` 또는 `HandoffDraftResponse`는 `approval_required=true`, `blocked_actions`, `redacted_fields`, `citations`를 강제하고, `ContextSummary`는 `summary`, `preserved_citations`, `omitted_sections`, `confidence`를 강제합니다.

- P3에서는 LangChain built-in middleware를 바로 교체하지 않고 검토만 합니다. 현재 PII 필터, approval gate, evidence logger가 도메인 특화되어 있으므로, middleware는 보조 계층 또는 중복 방어선으로만 평가합니다.

## Implementation Phases

- P0 Task 1: Intent Router structured output 전환. 실패 시 empty intent로 조용히 빠지지 않고 unsupported/blocker 형태로 남기는 테스트를 먼저 작성합니다.

- P0 Task 2: `WorkforceJudgmentChain` 추가. `WorkforceAgentResponse`를 `with_structured_output(..., method="json_schema", strict=True, include_raw=True)`로 받되, Evidence Log에는 raw 원문 대신 hash/metadata만 저장합니다.

- P0 Task 3: `runtime_mode` 연결. `/api/v1/agent/run`, `run_workflow`, `ForeignHiringState`에 전달하고 default는 반드시 `deterministic`으로 둡니다.

- P1 Task 4: `FinalResponseDraft` 추가. 최종 응답은 `answer`, `citations`, `risk_notices`, `approval_notice`, `missing_evidence_notice`로 구조화하고, UI/로그는 이 구조를 기준으로 사용합니다.

- P1 Task 5: `VisaAgentResponse`, `ContactAgentResponse` 추가. 비자 가능 여부 확정, 법률 자문, 자동 발송 문구, raw PII 포함은 validator에서 차단합니다.

- P2 Task 6: `HandoffDraftResponse`와 `ContextSummary` 추가. 외부 전달 초안은 승인 전송 금지 상태를 schema로 강제하고, 긴 RAG 요약은 보존 citation과 생략 구간을 남깁니다.

- P3 Task 7: LangChain middleware 검토. Summarization/PII middleware는 기존 custom filter와 비교 평가만 하고, 대체는 별도 결정으로 분리합니다.

## Test Plan

- P0 tests: intent router structured output, malformed provider output, unsupported judgment routing, WorkforceJudgmentChain API key 없음, forbidden phrase reject, deterministic 기본값에서 chain 미호출.

- P1 tests: final response가 schema key를 항상 포함하는지, missing evidence 문구가 누락되지 않는지, Visa/Contact agent가 확정 판단/자동 발송/PII를 차단하는지 검증합니다.

- P2 tests: handoff draft가 항상 `approval_required=true`인지, blocked actions가 포함되는지, summary가 citation을 보존하고 omitted section을 기록하는지 검증합니다.

- Full gates: `uv run pytest backend/tests -q`, `uv run python scripts/evaluate_workforce_retrieval.py --dataset evals/datasets/workforce_retrieval_quality_cases.csv --top-k 5 --min-hit-at-3 0.80`.

## Assumptions

- LangGraph, Chroma-only RAG, Rule Base, Approval Gate, Evidence Log는 유지합니다.
- LLM structured output은 deterministic result를 즉시 덮어쓰지 않고 candidate/draft로 붙입니다.
- 외부 발송, 행정사 전달, 정부 제출은 계속 Human Approval 이후입니다.
- JSONL/PolicyRetriever runtime fallback은 다시 열지 않습니다.
- LangChain middleware 전면 도입은 P3 검토 전까지 하지 않습니다.
