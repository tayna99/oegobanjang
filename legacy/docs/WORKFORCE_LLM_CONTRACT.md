# Workforce LLM Prompt And JSON Contract

이 문서는 인력확보 Agent가 LLM을 사용할 때 지켜야 하는 프롬프트와 출력 JSON 계약을 정의한다.

핵심 목적은 LLM이 자유롭게 후보를 추천하거나 법적 판단처럼 말하지 못하게 막고, DB/RAG/Rule 결과를 다음 노드가 바로 쓸 수 있는 구조화 JSON으로 바꾸는 것이다.

## Execution Flow

```txt
사용자 요청
-> 회사/후보 DB 조회
-> RAG 근거 검색
-> Rule Base 누락값/금지판단 확인
-> Workforce Prompt Builder
-> LLM JSON Generator
-> Workforce JSON Validator
-> UI 카드 / Evidence Log / Human Approval
```

## System Prompt Contract

고정 system prompt는 다음 원칙을 반드시 포함한다.

- 인력확보 Agent는 후보 추천기가 아니라 신규 고용 준비 조건 정리 Agent다.
- 후보자의 성격, 성실도, 장기근속 가능성, 이탈 가능성을 판단하지 않는다.
- 국적별 선호나 우열을 말하지 않는다.
- 후보 비교는 제출 준비도, 입력값 충족 여부, 추가 확인 필요 항목 기준으로만 한다.
- 비자 가능/불가능을 최종 판정하지 않는다.
- 공식 근거가 부족하면 행정사 검토 필요로 표시한다.
- 송출회사나 행정사에게 전달하기 전에는 사람 승인이 필요하다.
- 출력은 지정된 JSON 구조로만 한다.
- JSON 밖에 설명 문장을 쓰지 않는다.

구현 위치:

```txt
backend/app/agent_runtime/llm/workforce_contract.py
```

주요 함수:

```txt
build_workforce_system_prompt()
build_workforce_task_prompt()
parse_workforce_agent_response()
```

## Task Prompt Inputs

Task prompt는 매 요청마다 다음 입력을 포함한다.

- `[사용자 요청]`
- `[회사 DB 정보]`
- `[후보자 DB 정보]`
- `[RAG 검색 결과]`
- `[Rule Base 결과]`
- `[출력 요구]`

RAG는 공식 근거와 템플릿 재료를 제공하고, 회사/후보 상태값은 DB/CSV/Rule Base에서 제공한다.

## Output JSON Contract

LLM 응답은 반드시 `WorkforceAgentResponse` schema를 통과해야 한다.

Top-level required keys:

```txt
agent
intent
status
summary
workforce_request
missing_inputs
required_checks
candidate_readiness
handoff_questions
risk_flags
approval
evidence
next_actions
```

허용 intent:

```txt
new_hiring
candidate_review
workforce_request_update
handoff_question_generation
unsupported_candidate_judgment
```

허용 status:

```txt
draft_ready
needs_more_input
needs_human_review
blocked
```

후보 준비도 상태는 기존 runtime 호환값과 체크리스트 용어를 모두 허용한다.

```txt
ready
additional_check_needed
missing_required_info
missing_required_items
needs_confirmation
needs_onboarding_info
blocked_due_to_forbidden_judgment
not_applicable
```

## Candidate Readiness Safety

`candidate_readiness`는 사람 평가가 아니라 제출 준비도 확인 결과다.

허용:

```txt
후보 CAN001은 여권과 숙소 안내는 확인되었지만, 사진과 건강검진 확인이 필요합니다.
```

금지:

```txt
후보 CAN001은 성실해 보입니다.
후보 CAN001은 오래 일할 사람입니다.
베트남 후보가 네팔 후보보다 낫습니다.
```

금지 표현이 `summary` 또는 `candidate_readiness.safe_description`에 들어가면 schema validation에서 실패한다.

비자 가능/불가능 최종판정 표현도 schema validation에서 실패한다.

```txt
비자 발급 가능
비자 가능
비자 불가능
최종 판정
```

## Runtime Adapter

현재 deterministic `hiring_agent` output은 기존 호환성을 위해 `output`에 그대로 남긴다. 동시에 새 JSON 계약을 만족하는 `structured_response`를 추가한다.

```txt
agent_result["output"] = 기존 runtime shape
agent_result["structured_response"] = WorkforceAgentResponse.model_dump()
```

이렇게 하면 기존 UI/테스트를 깨지 않으면서, 다음 UI 카드/Evidence Log/후속 Agent는 새 JSON 계약을 사용할 수 있다.

## Evidence Log Metadata

`FINAL_RESPONSE_GENERATED` 이벤트에는 LLM 계약 검증 metadata를 남긴다. 원문 PII를 남기지 않기 위해 회사/후보 DB row 전체가 아니라 row ref와 key 목록만 기록한다.

저장 항목:

```txt
system_prompt_version
task_prompt_version
llm_output_schema
json_validation_status
intent
status
structured_response_keys
company_row_ref
candidate_row_refs
company_context_keys
candidate_context_keys
rag_source_ids
evidence_grades
rule_results
blocked_actions
human_approval_required
```

`APPROVAL_REQUESTED` 이벤트에는 `blocked_actions`, `human_approval_required`, `approval_reason`을 남긴다.

## Verification

Focused tests:

```powershell
uv run pytest backend/tests/test_workforce_llm_contract.py backend/tests/test_hiring_readiness_result.py -q
```

Full backend gate:

```powershell
uv run pytest backend/tests -q
```
