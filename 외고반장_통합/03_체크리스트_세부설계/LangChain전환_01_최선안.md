# 인력 확보 에이전트 LangChain 1.0 전환 비교 및 최선안

## 1. 결론

현재 상황에서 최선의 수는 **LangGraph 골격은 유지하고, 그 안의 LLM 호출부만 LangChain 1.0 방식으로 선별 전환하는 것**이다.

즉, 전체 workflow를 `create_agent` 기반 자유 agent loop로 갈아엎는 것이 아니라, 아래 두 지점부터 `with_structured_output()`을 적용하는 것이 가장 현실적이다.

```text
P0 전환 대상
1. intent_router.py
2. WorkforceJudgmentChain 또는 workforce_chain.py
```

최종 권장 방향은 다음과 같다.

```text
LangGraph 유지
Approval Gate 유지
Deterministic fallback 유지
Evidence Log 유지

단, LLM 호출부는 LangChain 1.0 structured output으로 전환
```

한 문장으로 정리하면 다음과 같다.

> **with_structured_output()을 intent_router와 WorkforceJudgmentChain에 먼저 꽂고, LangGraph·approval gate·deterministic fallback은 그대로 두는 선별 전환이 최선이다.**

---

## 2. 현재 상황 요약

현재 코드 상태는 다음과 같이 볼 수 있다.

```text
LangChain 버전은 1.x 계열을 사용하고 있음
그러나 LangChain 1.0의 핵심 추상화는 아직 적극적으로 쓰지 않음
```

현재 쓰고 있는 것:

```text
- ChatOpenAI
- SystemMessage / HumanMessage
- @tool 데코레이터
- OpenAIEmbeddings
- Chroma
- RecursiveCharacterTextSplitter
```

아직 제대로 안 쓰고 있는 것:

```text
- with_structured_output()
- create_agent(response_format=...)
- LangChain 1.0 built-in middleware
```

특히 가장 큰 문제는 LLM 출력 처리다.

현재 문제:

```text
- LLM이 JSON처럼 보이는 문자열을 반환함
- 코드에서 json.loads로 직접 파싱함
- ```json 백틱을 직접 제거함
- enum 변환을 직접 처리함
- schema 검증을 수동으로 함
- 실패 원인 추적이 어려움
```

LangChain 1.0 전환의 가장 큰 이득은 이 부분을 줄이는 것이다.

```text
Before:
LLM 자유 텍스트 출력
→ 백틱 제거
→ json.loads
→ enum 변환
→ 수동 검증

After:
LLM.with_structured_output(PydanticSchema)
→ Pydantic 객체 반환
→ 추가 validator만 수행
```

---

## 3. 두 방식 비교

| 항목 | 붙여준 안 | 보강안 | 최종 판단 |
|---|---|---|---|
| 핵심 방향 | LangGraph 유지 + LLM 호출부만 1.0식 전환 | 동일 | 둘 다 맞음 |
| P0 범위 | intent_router.py, workforce_chain.py, hiring_agent.py 분기, 단위 테스트 | WorkforceJudgmentChain, validator, LangGraph node | 붙여준 안이 더 작고 실행 가능 |
| structured output | with_structured_output 사용 | 동일 | 반드시 도입 |
| include_raw | False | True 권장 | 개발/디버깅 단계는 True 권장 |
| fallback | deterministic 유지 | parser fallback + blocked fallback | 둘 다 필요 |
| validator | Pydantic model_validator 중심 | safety/evidence/business 분리 | P0는 model_validator, P1에서 분리 |
| create_agent | 도입 안 함 | 데모용만 가능 | 운영 workflow에는 도입하지 않음 |
| middleware | P1/P2 | P1/P2 | 지금은 미룸 |
| LangGraph | 유지 | 유지 | 반드시 유지 |

최종 판단은 다음과 같다.

```text
붙여준 안을 P0 메인으로 채택한다.
다만 include_raw=True, fallback, validator 분리를 추가 방향으로 가져간다.
```

---

## 4. 왜 LangGraph는 유지해야 하는가

LangChain 1.0의 `create_agent`는 단일 agent의 tool-use loop에는 좋다. 하지만 외고반장/인력 확보 에이전트는 단순 챗봇이나 자유로운 tool loop가 아니다.

이 프로젝트는 다음 조건이 중요하다.

```text
- RAG 검색 순서
- Rule Base 검증
- LLM 구조화 출력
- JSON 검증
- Human Approval
- Evidence Log
- 다음 에이전트 전달
```

이 흐름은 LLM이 매번 알아서 결정하면 안 된다. 특히 외국인 고용 도메인은 행정, 비자, 후보자 정보, 승인 기록이 얽혀 있기 때문에 **재현성**과 **감사 가능성**이 중요하다.

따라서 LangGraph를 유지해야 하는 이유는 다음과 같다.

```text
1. 단일 Approval Gate를 강제할 수 있다.
2. RAG → Rule → LLM → Validator → Approval 순서를 고정할 수 있다.
3. 같은 입력에 대해 같은 workflow를 재현하기 쉽다.
4. 각 Mission Agent가 같은 State를 공유할 수 있다.
5. Human-in-the-loop interrupt와 재개 흐름이 자연스럽다.
6. Evidence Log를 일관되게 남길 수 있다.
```

따라서 전환 방향은 다음이 아니다.

```text
나쁜 방향:
LangGraph 제거
→ create_agent 하나로 전체 workflow 대체
```

좋은 방향은 다음이다.

```text
좋은 방향:
LangGraph 유지
→ 각 노드 안의 LLM 호출부만 LangChain 1.0 structured output으로 교체
```

---

## 5. 최선의 아키텍처

최종 권장 구조는 다음과 같다.

```text
User Input
↓
LangGraph
↓
intent_router_node
  - with_structured_output(IntentClassification)
↓
state_loader
↓
rag_retriever
↓
rule_checker
↓
hiring_agent
  - 기본값: deterministic
  - runtime_mode="langchain_judgment"일 때만 LLM judgment 실행
↓
WorkforceJudgmentChain
  - ChatOpenAI.with_structured_output(WorkforceAgentResponse)
  - method="json_schema"
  - include_raw=True
  - parser fallback 유지
↓
Pydantic model_validator
↓
Safety / Evidence / Business Validator
↓
Approval Gate
↓
Evidence Log
↓
UI / 다음 에이전트
```

핵심은 `runtime_mode`다.

```text
기본 운영:
runtime_mode = "deterministic"

실험/고도화:
runtime_mode = "langchain_judgment"
```

처음부터 LLM 결과로 기존 deterministic 결과를 덮어쓰면 안 된다. 먼저 병렬로 붙여서 비교하고, validation을 통과한 결과만 사용하도록 해야 한다.

---

## 6. P0 전환 대상

## 6-1. PR1 — intent_router.py 구조화 출력 전환

목표는 수동 JSON parsing 제거다.

현재 문제:

```text
- LLM 응답을 문자열로 받음
- 백틱 제거
- json.loads
- Intent enum 변환
- 실패 시 빈 intent 처리
```

전환 후:

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class IntentClassification(BaseModel):
    intents: list[str] = Field(
        description="사용자 메시지에서 감지된 intent 목록"
    )

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
).with_structured_output(IntentClassification)

result = llm.invoke([
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessage(content=state.user_message),
])

state.detected_intents = result.intents
```

얻는 것:

```text
- json.loads 제거
- 백틱 제거 코드 제거
- enum 변환 코드 축소
- schema 기반 응답 유도
- intent router 코드 단순화
```

---

## 6-2. PR2 — WorkforceJudgmentChain 추가

현재 `workforce_contract.py`에는 이미 다음 자산이 있다.

```text
- WorkforceAgentResponse Pydantic Schema
- build_workforce_system_prompt()
- build_workforce_task_prompt()
- parse_workforce_agent_response()
- forbidden phrase validator
```

하지만 아직 부족한 것은 실제 LLM 호출 체인이다.

추가할 파일:

```text
llm/workforce_chain.py
또는
llm/workforce_judgment_chain.py
```

권장 코드 방향:

```python
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.agent_runtime.llm.workforce_contract import (
    WorkforceAgentPromptInput,
    WorkforceAgentResponse,
    build_workforce_system_prompt,
    build_workforce_task_prompt,
    parse_workforce_agent_response,
)
from app.config import get_settings


class WorkforceJudgmentChain:
    """RAG evidence + DB state + Rule result → WorkforceAgentResponse."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0):
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required for WorkforceJudgmentChain")

        self._base_llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

        self._structured_llm = self._base_llm.with_structured_output(
            WorkforceAgentResponse,
            method="json_schema",
            strict=True,
            include_raw=True,
        )

    def invoke(self, prompt_input: WorkforceAgentPromptInput) -> WorkforceAgentResponse:
        messages = [
            SystemMessage(content=build_workforce_system_prompt()),
            HumanMessage(content=build_workforce_task_prompt(prompt_input)),
        ]

        result = self._structured_llm.invoke(messages)

        if isinstance(result, dict):
            parsed = result.get("parsed")
            parsing_error = result.get("parsing_error")

            if parsed is not None and parsing_error is None:
                return parsed

            # structured output 실패 시 기존 parser fallback
            raw = self._base_llm.invoke(messages).content
            return parse_workforce_agent_response(raw)

        return result
```

붙여준 안과 비교했을 때 이 코드의 차이는 다음이다.

```text
- include_raw=True 사용
- structured output 실패 시 fallback 경로 명시
- 기존 parse_workforce_agent_response를 버리지 않고 안전망으로 유지
```

---

## 6-3. PR3 — hiring_agent.py에 runtime_mode 분기 추가

기존 deterministic 결과를 바로 대체하면 위험하다. 따라서 LLM judgment는 명시적으로 켜야 한다.

권장 구조:

```python
def run_hiring_agent(state: ForeignHiringState) -> dict[str, Any]:
    if not check_llm_limit(state):
        return {"status": "BLOCKED", "reason": "LLM call limit exceeded"}

    runtime_output = build_hiring_readiness_result(...)

    if state.runtime_mode == "langchain_judgment":
        chain = WorkforceJudgmentChain()
        prompt_input = WorkforceAgentPromptInput(
            user_request=state.user_message,
            company_context=state.company_context,
            candidate_context=state.candidate_context,
            rag_results=state.rag_contexts,
            rule_results=runtime_output,
        )
        response = chain.invoke(prompt_input)
        runtime_output["llm_response"] = response.model_dump(mode="json")

    return runtime_output
```

운영 원칙:

```text
- deterministic 결과는 기본값으로 유지
- LLM 결과는 별도 llm_response에 저장
- 즉시 기존 결과를 덮어쓰지 않음
- Evidence Log에 deterministic 결과와 LLM 결과를 함께 남김
```

---

## 6-4. PR4 — 단위 테스트 추가

테스트는 최소 아래를 포함해야 한다.

```text
- 정상 요청 → WorkforceAgentResponse 생성
- forbidden phrase 포함 → reject 또는 blocked
- unsupported_candidate_judgment → status blocked 또는 needs_human_review
- source_id 누락 → validation error
- approval.requires_human_approval 누락 → validation error
- OPENAI_API_KEY 없을 때 deterministic fallback
```

테스트 질문 예시:

```text
정상 요청:
베트남 E-9 근로자 3명 추가 채용 준비해줘.

후보 준비도 요청:
여권 있는 후보와 사진 없는 후보를 정리해줘.

금지 요청:
후보 A가 더 성실해?
베트남 후보가 네팔 후보보다 낫지?
오래 일할 사람 추천해줘.
```

---

## 7. P1 보강 대상

## 7-1. Validator 분리

P0에서는 `WorkforceAgentResponse.model_validator` 중심으로 가도 된다. 하지만 P1에서는 검증을 분리하는 것이 좋다.

권장 파일:

```text
llm/workforce_validators.py
```

분리할 validator:

```text
validate_workforce_safety()
- 후보 성실도
- 장기근속 가능성
- 이탈 가능성
- 국적 선호
- 비자 가능 단정 표현 검사

validate_workforce_evidence()
- response.evidence.source_id가 실제 retrieved_evidence 안에 있는지 확인
- 합성 데이터가 공식 근거로 쓰이지 않았는지 확인

validate_workforce_business_rules()
- Rule Base 결과와 LLM 출력이 충돌하지 않는지 확인
- requires_human_approval이 누락되지 않았는지 확인
```

이렇게 분리하면 실패 원인을 더 정확히 기록할 수 있다.

```text
나쁜 로그:
Validation failed

좋은 로그:
Safety validation failed: forbidden phrase "오래 일할" detected
Evidence validation failed: source_id not found in retrieved docs
Business validation failed: human approval required but missing
```

---

## 7-2. Evidence Log 강화

LLM 호출 결과는 반드시 감사 로그에 남겨야 한다.

저장할 것:

```text
- user_request
- detected_intents
- runtime_mode
- company_id
- candidate_ids
- retrieved_source_ids
- rule_result
- prompt_version
- schema_version
- raw_llm_output
- parsed_llm_response
- validation_status
- validation_errors
- approval_required
- blocked_actions
- created_at
```

이유는 단순하다.

```text
외국인 고용 도메인은 나중에 반드시 이런 질문이 생긴다.
왜 이 요청서를 만들었나?
어떤 근거 문서를 사용했나?
누가 승인했나?
어떤 후보 판단을 차단했나?
```

그래서 LLM 결과는 “생성물”이 아니라 “감사 가능한 이벤트”로 저장해야 한다.

---

## 8. P2로 미룰 것

지금 당장 하지 말아야 할 작업이다.

```text
- 전체 workflow를 create_agent로 교체
- LangGraph 제거
- Approval Gate 제거
- SummarizationMiddleware 전환
- PIIMiddleware 전환
- 모든 agent를 한 번에 structured output으로 전환
```

이유:

```text
- 변경 범위가 너무 커진다.
- 기존 deterministic 재현성이 깨질 수 있다.
- approval gate가 분산될 수 있다.
- 디버깅 포인트가 늘어난다.
- 발표 전 MVP 안정성이 떨어진다.
```

SummarizationMiddleware와 PIIMiddleware는 나중에 봐도 된다.

```text
P2 후보:
- summarizer.py → SummarizationMiddleware 검토
- pii_filter.py → PIIMiddleware + 외국인등록번호/여권번호 custom pattern 검토
```

---

## 9. LangChain 1.0 전환 우선순위

| 우선순위 | 작업 | 이유 |
|---|---|---|
| P0 | intent_router.py structured output 전환 | 가장 작고 효과 큼 |
| P0 | WorkforceJudgmentChain 추가 | 현재 LLM 호출 체인의 빈칸을 메움 |
| P0 | hiring_agent.py runtime_mode 분기 | deterministic 안정성 유지 |
| P0 | 단위 테스트 추가 | 안전 전환 검증 |
| P1 | safety/evidence/business validator 분리 | 디버깅 가능성 개선 |
| P1 | visa_agent/contact_agent 동일 패턴 적용 | 성공 패턴 확장 |
| P1 | final_response.py structured output 적용 | 최종 응답 안정화 |
| P2 | SummarizationMiddleware 검토 | LangGraph 구조와 충돌 가능성 확인 필요 |
| P2 | PIIMiddleware 검토 | 도메인 PII 패턴 추가 필요 |
| 유지 | LangGraph workflow | 안전 규칙 의존 |
| 유지 | Approval Gate | 단일 승인 지점 필요 |
| 유지 | Evidence Logger | 감사 가능성 필요 |
| 유지 | tools/*.py | 이미 1.0 스타일 |

---

## 10. pyproject.toml 수정 권장

현재 실제 lock은 LangChain 1.x라도, pyproject가 너무 느슨하면 팀원이 헷갈릴 수 있다.

권장:

```toml
[project]
dependencies = [
    "langchain>=1.2,<2",
    "langchain-core>=1.3,<2",
    "langchain-openai>=1.2,<2",
    "langchain-chroma>=1.1,<2",
    "langchain-text-splitters>=1.1,<2",
    "langgraph>=0.2,<1",
]
```

의도:

```text
- 우리는 LangChain 1.x 계열을 의도적으로 사용한다.
- 0.x 호환 코드가 아니라 1.x structured output 전환을 한다.
- 다만 LangGraph는 유지한다.
```

---

## 11. 최종 코드 구조

권장 파일 구조:

```text
backend/app/agent_runtime/
  llm/
    __init__.py
    workforce_contract.py          # 기존 유지: schema / prompt / parser
    workforce_chain.py             # 신규: LangChain 1.x structured output 호출부
    workforce_validators.py        # P1: safety/evidence/business validator

  graph/
    nodes/
      intent_router.py             # P0: structured output 전환
      workforce_llm_node.py         # 선택: chain 호출 노드 분리 시
      workforce_validation_node.py  # P1: validator 노드
      approval_gate_node.py         # 유지
      evidence_logger.py            # 유지

  agents/
    hiring_agent.py                 # P0: runtime_mode 분기 추가
```

---

## 12. 팀원에게 설명하는 문장

팀원에게는 이렇게 말하면 된다.

```text
LangChain 1.0을 쓴다는 건 LangGraph를 버린다는 뜻이 아니다.
우리 프로젝트에서는 LangGraph가 업무 순서와 승인 게이트를 책임지고,
LangChain 1.0의 with_structured_output이 LLM 출력 계약을 책임진다.

즉 LangGraph는 workflow runtime,
LangChain structured output은 JSON contract enforcement다.
```

더 짧게 말하면 다음과 같다.

```text
LangGraph는 길을 고정하고,
LangChain 1.0은 LLM 답변 모양을 고정한다.
```

---

## 13. 최종 한 문장

**최선의 수는 `with_structured_output()`을 `intent_router.py`와 `WorkforceJudgmentChain`에 먼저 적용하고, LangGraph·Approval Gate·Deterministic fallback은 그대로 유지하는 선별 전환이다. create_agent와 middleware 전면 도입은 뒤로 미루고, P0에서는 JSON 수동 파싱 제거와 WorkforceAgentResponse 구조화 출력 연결에 집중하는 것이 가장 안전하고 가성비가 높다.**
