# LangChain 1.0 Ideal Day-1 Design (Reference)

> 작성일: 2026-05-09
> 목적: "day 1부터 LangChain 1.0이었다면 어떻게 설계했을까"의 사고 실험 결과. 향후 비슷한 도메인 안전 중심 LLM 시스템 설계 시 참고용.
> 주의: 이 문서는 **현재 코드 변경 계획이 아닌 reference design**이다. 실제 마이그레이션은 `docs/langchain-1-migration-plan.md`를 따른다.

---

## 한 줄 결론

**Schema-first + Chain 추상화 + Validator 분리 + 단일 `rag/` 패키지.** fake judgment chain(Mission 008~013) 우회 단계가 통째로 사라지고, 모든 LLM 호출이 day 1부터 `with_structured_output`을 거친다.

---

## 0. 폴더 구조 (이상적 버전)

```
backend/app/agent_runtime/
├── runner.py
├── graph/                          # LangGraph (변경 없음)
│   ├── workflow.py
│   ├── state.py
│   └── nodes/
│       ├── intent_router.py        # IntentChain 사용
│       ├── planner.py
│       ├── state_loader.py
│       ├── executor.py
│       ├── aggregator.py
│       ├── approval_gate.py
│       ├── handoff_package.py
│       ├── final_response.py       # FinalResponseChain 사용
│       └── evidence_logger.py
├── llm/                            # ★ Schema-first 구조
│   ├── runtime_mode.py             # RuntimeMode enum
│   ├── chains/
│   │   ├── base.py                 # ★ BaseStructuredChain 추상화
│   │   ├── intent_chain.py
│   │   ├── workforce_chain.py
│   │   ├── visa_chain.py
│   │   ├── contact_chain.py
│   │   ├── final_response_chain.py
│   │   └── handoff_draft_chain.py
│   ├── schemas/
│   │   ├── intent.py
│   │   ├── workforce.py
│   │   ├── visa.py
│   │   ├── contact.py
│   │   ├── final_response.py
│   │   └── handoff.py
│   ├── validators/                 # ★ day 1부터 분리
│   │   ├── safety.py
│   │   ├── evidence.py
│   │   └── business_rule.py
│   └── prompts/
│       └── workforce.py
├── agents/
│   ├── workforce_agent.py
│   ├── visa_agent.py
│   └── contact_agent.py
├── rag/                            # ★ 팀별 분기 없음 (rag_hyunwook/rag_tayna 통합)
│   ├── chunking.py
│   ├── domain_splitters.py
│   ├── raw_ingest.py
│   ├── embeddings.py
│   ├── vector_store.py
│   └── retriever.py
├── tools/                          # 5-tier contract (변경 없음)
│   ├── registry.py
│   ├── safe_read.py
│   ├── safe_calculate.py
│   ├── safe_draft.py
│   └── approval_required.py
└── middleware/
    ├── pii_filter.py               # 외국인등록번호·여권 도메인 특화
    ├── call_limiter.py
    └── summarizer.py
```

---

## 1. `pyproject.toml` — day 1부터 strict lock

```toml
[project]
dependencies = [
    "langchain>=1.2,<2",
    "langchain-core>=1.3,<2",
    "langchain-openai>=1.2,<2",
    "langchain-chroma>=1.1,<2",
    "langchain-text-splitters>=1.1,<2",
    "langgraph>=0.2,<1",
    "pydantic>=2.7,<3",
    # ...
]
```

---

## 2. `llm/runtime_mode.py` — enum 첫날부터

```python
from enum import Enum


class RuntimeMode(str, Enum):
    """LLM chain 호출 분기. 기본값은 deterministic (LLM 안 부름)."""
    DETERMINISTIC = "deterministic"
    LANGCHAIN_JUDGMENT = "langchain_judgment"

    @classmethod
    def default(cls) -> "RuntimeMode":
        return cls.DETERMINISTIC
```

---

## 3. `llm/schemas/intent.py` — schema-first

```python
from pydantic import BaseModel, Field
from app.agent_runtime.schemas import Intent  # 도메인 enum 별도 정의


class IntentClassification(BaseModel):
    """LangChain 1.0 structured output용. with_structured_output에 그대로 넘김."""
    intents: list[Intent] = Field(
        default_factory=list,
        description="감지된 intent. UNSUPPORTED_*는 차단 사유.",
    )
    rationale: str = Field(
        default="",
        description="분류 근거 한 줄. 디버깅 용도.",
    )
```

---

## 4. `llm/schemas/workforce.py` — Pydantic 한 곳에 모음

```python
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class WorkforceRequestDraft(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    region: str | None = None
    visa_type: str = "E-9"
    needed_headcount: int | None = None
    requested_role: str | None = None
    housing_provided: bool | None = None
    shift_type: str | None = None
    desired_start_date: str | None = None


class CandidateReadinessItem(BaseModel):
    candidate_id: str
    readiness_status: Literal[
        "ready", "additional_check_needed",
        "missing_required_items", "needs_onboarding_info",
        "blocked_due_to_forbidden_judgment",
    ]
    ready_items: list[str] = Field(default_factory=list)
    missing_or_unconfirmed_items: list[str] = Field(default_factory=list)
    safe_description: str
    forbidden_judgment_used: bool = False


class HandoffQuestion(BaseModel):
    target: Literal["sending_agency", "admin_scrivener", "manager"]
    question: str


class RiskFlag(BaseModel):
    risk_type: Literal[
        "missing_required_input", "missing_official_evidence",
        "human_approval_required", "forbidden_candidate_judgment",
    ]
    level: Literal["low", "medium", "high"] = "medium"
    message: str


class ApprovalBlock(BaseModel):
    requires_human_approval: bool = True
    approval_reason: str
    blocked_actions: list[Literal[
        "auto_send_to_candidate",
        "auto_send_to_sending_agency",
        "auto_send_to_admin_scrivener",
        "auto_submit_to_government_portal",
        "final_visa_eligibility_decision",
        "candidate_scoring_or_ranking",
    ]] = Field(default_factory=list)

    @field_validator("requires_human_approval")
    @classmethod
    def _must_require_approval(cls, v: bool) -> bool:
        if not v:
            raise ValueError("workforce response must require human approval")
        return v


class EvidenceReference(BaseModel):
    source_id: str
    title: str = ""
    doc_type: str = ""
    evidence_grade: Literal["A", "B", "C", "D", "E", "F"]
    used_for: str


class WorkforceAgentResponse(BaseModel):
    """with_structured_output(WorkforceAgentResponse, strict=True) 그대로 넘김."""
    agent: Literal["workforce_agent"] = "workforce_agent"
    intent: Literal[
        "new_hiring", "candidate_review",
        "workforce_request_update", "handoff_question_generation",
        "unsupported_candidate_judgment",
    ]
    status: Literal["draft_ready", "needs_more_input", "needs_human_review", "blocked"]
    summary: str
    workforce_request: WorkforceRequestDraft
    missing_inputs: list[dict] = Field(default_factory=list)
    required_checks: list[dict] = Field(default_factory=list)
    candidate_readiness: list[CandidateReadinessItem] = Field(default_factory=list)
    handoff_questions: list[HandoffQuestion] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    approval: ApprovalBlock
    evidence: list[EvidenceReference] = Field(default_factory=list)
    next_actions: list[dict] = Field(default_factory=list)
```

**중요**: `model_validator`로 forbidden phrase reject 같은 건 schema 안에 넣지 않음. 별도 validator로 분리 — 이게 day 1부터 했어야 할 분리.

---

## 5. `llm/validators/safety.py` — 별도 파일로 분리

```python
from app.agent_runtime.llm.schemas.workforce import WorkforceAgentResponse


FORBIDDEN_CANDIDATE_JUDGMENT_TERMS = (
    "성실", "성격", "오래 일할", "장기근속", "이탈 가능성",
    "도망", "좋은 사람", "더 나은 후보", "국적별", "우대",
    "추천", "보다 낫", "더 낫",
    "비자 발급 가능", "비자 가능", "비자 불가능", "최종 판정",
)


class SafetyValidationError(Exception):
    """Forbidden phrase / 가치 판단 위반 — silent fallback 금지, blocked로 명시."""
    def __init__(self, term: str, location: str):
        self.term = term
        self.location = location
        super().__init__(f"forbidden term '{term}' at {location}")


def validate_safety(response: WorkforceAgentResponse) -> None:
    """Fail-closed safety validator. 위반 시 SafetyValidationError raise."""
    _check_text(response.summary, "summary")

    for item in response.candidate_readiness:
        _check_text(item.safe_description, f"candidate_readiness[{item.candidate_id}]")
        if item.forbidden_judgment_used:
            raise SafetyValidationError("forbidden_judgment_used=true", "candidate_readiness")

    for q in response.handoff_questions:
        _check_text(q.question, "handoff_question")

    if response.intent == "unsupported_candidate_judgment":
        if response.status not in ("blocked", "needs_human_review"):
            raise SafetyValidationError(
                "unsupported_candidate_judgment must be blocked",
                "intent/status mismatch",
            )


def _check_text(text: str, location: str) -> None:
    for term in FORBIDDEN_CANDIDATE_JUDGMENT_TERMS:
        if term in text:
            raise SafetyValidationError(term, location)
```

---

## 6. `llm/validators/evidence.py`

```python
from app.agent_runtime.llm.schemas.workforce import WorkforceAgentResponse


class EvidenceValidationError(Exception):
    pass


# F=합성, D=참고용 -> 공식 근거로 못 씀
DISALLOWED_AS_OFFICIAL_EVIDENCE = {"D", "F"}
OFFICIAL_USED_FOR = {"required_checks", "legal_or_administrative_review"}


def validate_evidence(
    response: WorkforceAgentResponse,
    retrieved_source_ids: set[str],
) -> None:
    """LLM이 인용한 source_id가 실제 retrieved에 있는지 + grade 정책 검사."""
    for ev in response.evidence:
        if ev.source_id not in retrieved_source_ids:
            raise EvidenceValidationError(
                f"evidence source_id '{ev.source_id}' not in retrieved chunks"
            )
        if (ev.evidence_grade in DISALLOWED_AS_OFFICIAL_EVIDENCE
                and ev.used_for in OFFICIAL_USED_FOR):
            raise EvidenceValidationError(
                f"grade={ev.evidence_grade} cannot be used as official evidence "
                f"(used_for={ev.used_for})"
            )
```

---

## 7. `llm/validators/business_rule.py`

```python
from typing import Any
from app.agent_runtime.llm.schemas.workforce import WorkforceAgentResponse


class BusinessRuleValidationError(Exception):
    pass


def validate_business_rules(
    response: WorkforceAgentResponse,
    rule_result: dict[str, Any],
) -> None:
    """Rule Base 결과와 LLM 출력의 일관성 검사."""
    # Rule이 승인 필요라고 했는데 LLM이 false로 했으면 차단
    if rule_result.get("requires_human_approval") is True:
        if response.approval.requires_human_approval is not True:
            raise BusinessRuleValidationError(
                "rule says approval required, but LLM set false"
            )

    # forbidden 감지 시 status가 blocked/review가 아니면 차단
    if rule_result.get("forbidden_judgment_detected") is True:
        if response.status not in ("blocked", "needs_human_review"):
            raise BusinessRuleValidationError(
                "forbidden judgment detected but status not blocked/review"
            )

    # missing field가 ready_items로 들어가면 모순
    missing = set(rule_result.get("missing_candidate_fields", []))
    for item in response.candidate_readiness:
        ready = set(item.ready_items)
        conflict = missing & ready
        if conflict:
            raise BusinessRuleValidationError(
                f"candidate {item.candidate_id} ready_items conflict with missing: {conflict}"
            )
```

---

## 8. `llm/chains/base.py` — Base 추상화 (day 1부터)

```python
from __future__ import annotations
from typing import Generic, TypeVar
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.config import get_settings


T = TypeVar("T", bound=BaseModel)


class StructuredChainError(Exception):
    """schema retry 후에도 실패. blocked로 노출, silent fallback 금지."""


class BaseStructuredChain(Generic[T]):
    """LangChain 1.0 with_structured_output 표준 래퍼.

    모든 LLM chain의 부모 클래스. day 1부터 일관된 패턴 강제.
    """
    schema: type[T]
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_retries: int = 2
    method: str = "json_schema"  # OpenAI Structured Outputs

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                f"OPENAI_API_KEY required for {type(self).__name__}. "
                "Use deterministic runtime_mode if API key is unavailable."
            )
        self._llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.openai_api_key,
            max_retries=self.max_retries,
        ).with_structured_output(
            self.schema,
            method=self.method,
            include_raw=True,  # 디버깅용 raw + parsing_error 추적
        )

    def _invoke(self, messages: list[BaseMessage]) -> T:
        result = self._llm.invoke(messages)
        # include_raw=True면 {"raw", "parsed", "parsing_error"} dict
        if isinstance(result, dict):
            if result.get("parsing_error"):
                raise StructuredChainError(
                    f"parse error: {result['parsing_error']}"
                )
            parsed = result.get("parsed")
            if not isinstance(parsed, self.schema):
                raise StructuredChainError(
                    f"unexpected output type: {type(parsed)}"
                )
            return parsed
        return result

    def evidence_metadata(self, raw_payload: dict | None = None) -> dict:
        """Evidence Log에 저장할 metadata만. raw 원문은 절대 저장 X."""
        import hashlib
        raw = (raw_payload or {}).get("raw")
        raw_str = str(raw) if raw is not None else ""
        return {
            "model_name": self.model,
            "raw_present": bool(raw),
            "raw_content_hash": hashlib.sha256(raw_str.encode()).hexdigest()[:16],
            "parsing_error": (raw_payload or {}).get("parsing_error"),
        }
```

---

## 9. `llm/chains/intent_chain.py` — 깔끔한 적용

```python
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent_runtime.llm.chains.base import BaseStructuredChain
from app.agent_runtime.llm.schemas.intent import IntentClassification


_SYSTEM = (
    "당신은 외국인 고용 운영 시스템의 Intent 분류기입니다. "
    "사용자 메시지를 분석해 해당하는 intent를 모두 골라주세요. "
    "지원: HIRING/VISA_CHECK/DOCUMENT_CHECK/CONTACT/BRIEFING. "
    "지원하지 않는 요청은 UNSUPPORTED_VALUE_JUDGMENT/UNSUPPORTED_LEGAL_JUDGMENT/"
    "UNSUPPORTED_AUTO_SUBMISSION 중 하나로 분류하세요."
)


class IntentChain(BaseStructuredChain[IntentClassification]):
    schema = IntentClassification

    def classify(self, user_message: str) -> IntentClassification:
        return self._invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=user_message),
        ])
```

---

## 10. `llm/chains/workforce_chain.py` — validator 통합

```python
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent_runtime.llm.chains.base import BaseStructuredChain
from app.agent_runtime.llm.schemas.workforce import WorkforceAgentResponse
from app.agent_runtime.llm.prompts.workforce import (
    build_workforce_system_prompt,
    build_workforce_task_prompt,
)
from app.agent_runtime.llm.validators.safety import validate_safety
from app.agent_runtime.llm.validators.evidence import validate_evidence
from app.agent_runtime.llm.validators.business_rule import validate_business_rules


class WorkforceJudgmentChain(BaseStructuredChain[WorkforceAgentResponse]):
    schema = WorkforceAgentResponse

    def invoke(
        self,
        *,
        user_request: str,
        company_context: dict,
        candidate_context: list[dict],
        rag_results: list[dict],
        rule_results: dict[str, Any],
    ) -> WorkforceAgentResponse:
        # 1. LLM 호출 + schema 강제
        response = self._invoke([
            SystemMessage(content=build_workforce_system_prompt()),
            HumanMessage(content=build_workforce_task_prompt(
                user_request=user_request,
                company_context=company_context,
                candidate_context=candidate_context,
                rag_results=rag_results,
                rule_results=rule_results,
            )),
        ])

        # 2. Validator 3종 fail-closed
        validate_safety(response)
        validate_evidence(
            response,
            retrieved_source_ids={
                r.get("source_id") for r in rag_results if r.get("source_id")
            },
        )
        validate_business_rules(response, rule_results)

        return response
```

---

## 11. `graph/state.py` — runtime_mode 첫날부터

```python
from typing import Any
from pydantic import BaseModel, Field
from app.agent_runtime.schemas import Intent
from app.agent_runtime.llm.runtime_mode import RuntimeMode


class ForeignHiringState(BaseModel):
    request_id: str
    user_id: str
    company_id: str
    worker_id: str = ""
    candidate_id: str = ""
    user_message: str

    runtime_mode: RuntimeMode = Field(default_factory=RuntimeMode.default)

    # Routing
    detected_intents: list[Intent] = Field(default_factory=list)

    # Loaded
    company_context: dict[str, Any] = Field(default_factory=dict)
    candidate_context: list[dict[str, Any]] = Field(default_factory=list)

    # RAG
    rag_contexts: list[dict[str, Any]] = Field(default_factory=list)

    # Agent results
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    workforce_llm_response: dict[str, Any] | None = None
    visa_llm_response: dict[str, Any] | None = None
    contact_llm_response: dict[str, Any] | None = None

    # Convergence
    aggregated_output: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    approval: dict[str, Any] | None = None

    # Cross-cutting
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
```

---

## 12. `graph/nodes/intent_router.py` — 35줄로 끝

```python
from app.agent_runtime.graph.state import ForeignHiringState
from app.agent_runtime.graph.nodes.evidence_logger import make_event, log_event
from app.agent_runtime.schemas import EventType
from app.agent_runtime.llm.chains.intent_chain import IntentChain


_chain: IntentChain | None = None


def _get_chain() -> IntentChain | None:
    global _chain
    if _chain is None:
        try:
            _chain = IntentChain()
        except RuntimeError:
            _chain = None  # API key 없음 — empty intents
    return _chain


def intent_router_node(state: ForeignHiringState) -> ForeignHiringState:
    chain = _get_chain()
    intents = []
    if chain is not None:
        try:
            result = chain.classify(state.user_message)
            intents = list(result.intents)
        except Exception:
            intents = []
    state.detected_intents = intents
    return log_event(state, make_event(
        event_type=EventType.INTENT_CLASSIFIED,
        request_id=state.request_id,
        summary=f"감지된 intent: {[i.value for i in intents]}",
        step_name="intent_router",
    ))
```

**현재 64줄 → 35줄. 백틱 hack, `json.loads`, enum 변환 코드 0줄.**

---

## 13. `agents/workforce_agent.py` — runtime_mode 분기 첫날부터

```python
from typing import Any
from pydantic import ValidationError

from app.agent_runtime.graph.state import ForeignHiringState
from app.agent_runtime.llm.runtime_mode import RuntimeMode
from app.agent_runtime.llm.chains.workforce_chain import WorkforceJudgmentChain
from app.agent_runtime.llm.validators.safety import SafetyValidationError
from app.agent_runtime.llm.validators.evidence import EvidenceValidationError
from app.agent_runtime.llm.validators.business_rule import BusinessRuleValidationError
from app.agent_runtime.middleware.call_limiter import check_llm_limit


def run_workforce_agent(state: ForeignHiringState) -> dict[str, Any]:
    allowed, reason = check_llm_limit(state)
    if not allowed:
        return {"error": reason, "agent": "workforce_agent"}

    # 1. 항상 deterministic readiness builder를 먼저 돌림
    runtime_output = build_hiring_readiness_result(...)

    # 2. FORBIDDEN은 chain 호출 전 차단 (silent fallback 금지)
    if runtime_output.get("status") == "FORBIDDEN":
        state.agent_results.append({"agent": "workforce_agent", **runtime_output})
        return runtime_output

    # 3. langchain_judgment 모드일 때만 LLM
    if state.runtime_mode == RuntimeMode.LANGCHAIN_JUDGMENT:
        try:
            chain = WorkforceJudgmentChain()
            response = chain.invoke(
                user_request=state.user_message,
                company_context=state.company_context,
                candidate_context=state.candidate_context,
                rag_results=state.rag_contexts,
                rule_results=runtime_output,
            )
            state.workforce_llm_response = response.model_dump()
            runtime_output["llm_response_attached"] = True
        except RuntimeError as exc:
            # API key 없음 — 명시적 skip
            runtime_output["llm_response_attached"] = False
            runtime_output["llm_skip_reason"] = str(exc)
        except (SafetyValidationError, EvidenceValidationError,
                BusinessRuleValidationError, ValidationError) as exc:
            # validator 실패 — blocked로 명시 (silent fallback 금지)
            runtime_output["llm_response_attached"] = False
            runtime_output["status"] = "BLOCKED"
            runtime_output["blocked_reason"] = f"LLM validator rejected: {exc}"

    state.agent_results.append({"agent": "workforce_agent", **runtime_output})
    return runtime_output
```

---

## 14. `graph/workflow.py` — LangGraph 구조는 동일

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent_runtime.graph.state import ForeignHiringState
from app.agent_runtime.graph.nodes import (
    intent_router_node, planner_node, state_loader_node,
    executor_node, aggregator_node, approval_gate_node,
    handoff_package_node, final_response_node,
)


def build_workflow() -> StateGraph:
    graph = StateGraph(ForeignHiringState)
    for name, fn in [
        ("intent_router", intent_router_node),
        ("planner", planner_node),
        ("state_loader", state_loader_node),
        ("executor", executor_node),
        ("aggregator", aggregator_node),
        ("approval_gate", approval_gate_node),
        ("handoff_package", handoff_package_node),
        ("final_response", final_response_node),
    ]:
        graph.add_node(name, fn)
    graph.set_entry_point("intent_router")
    edges = ["intent_router", "planner", "state_loader", "executor",
             "aggregator", "approval_gate", "handoff_package", "final_response"]
    for src, dst in zip(edges, edges[1:]):
        graph.add_edge(src, dst)
    graph.add_edge("final_response", END)
    return graph


_compiled = None


def get_compiled_app():
    global _compiled
    if _compiled is None:
        _compiled = build_workflow().compile(checkpointer=MemorySaver())
    return _compiled
```

**LangChain 버전과 무관. day 1부터 같음.**

---

## 15. 테스트 — schema-first면 깔끔해짐

```python
# tests/test_workforce_chain.py
from unittest.mock import patch
import pytest
from app.agent_runtime.llm.chains.workforce_chain import WorkforceJudgmentChain
from app.agent_runtime.llm.validators.safety import SafetyValidationError


@patch("app.agent_runtime.llm.chains.base.ChatOpenAI")
@patch("app.agent_runtime.llm.chains.base.get_settings")
def test_chain_rejects_forbidden_phrase_via_safety_validator(mock_settings, mock_chat) -> None:
    mock_settings.return_value.openai_api_key = "sk-test"
    raw_response = _make_workforce_response_with_text(summary="이 후보는 성실해 보입니다.")
    mock_chat.return_value.with_structured_output.return_value.invoke.return_value = {
        "raw": "...", "parsed": raw_response, "parsing_error": None,
    }
    chain = WorkforceJudgmentChain()
    with pytest.raises(SafetyValidationError):
        chain.invoke(
            user_request="채용 준비",
            company_context={}, candidate_context=[],
            rag_results=[{"source_id": "eps_employer_process"}],
            rule_results={"requires_human_approval": True},
        )
```

---

## 무엇이 달라졌나 — 현재 코드 vs day-1 1.0

| 영역 | 현재 (점진 진화 결과) | day-1 1.0이었다면 |
|---|---|---|
| `intent_router_node` | 64줄 + 백틱 hack | 35줄, JSON 파싱 0줄 |
| LLM call abstraction | 없음 (각 파일이 직접 `ChatOpenAI`) | `BaseStructuredChain` 한 곳 |
| Schema location | `workforce_contract.py` 하나에 다 섞임 | `llm/schemas/`, `llm/validators/`로 분리 |
| Fake judgment chain (Mission 008~013) | 만들었다가 정리됨 (코드 자취 있음) | **존재 자체가 없음** |
| `langchain_runtime/` 빈 폴더 | 잔재 | 없음 |
| `rag_hyunwook` / `rag_tayna` | 팀별 분기, 거의 동일 코드 | `rag/` 단일 패키지 |
| Validator 분리 | `model_validator` 안에서 한 번에 | safety / evidence / business_rule 3 파일 |
| Evidence Log raw text | 정책 정해지는 중 | day 1부터 hash + metadata만 |
| `pyproject.toml` lock | `>=0.3.0` 느슨 | `>=1.2,<2` strict |
| `runtime_mode` | 없다가 다시 도입 | 처음부터 enum + default deterministic |

---

## 핵심 패턴 한 줄 요약

**`BaseStructuredChain[T]` 추상화 한 클래스 + `validators/` 폴더 3개 + `runtime_mode` enum + Chroma-only RAG 단일 폴더.** 이 4가지를 day 1에 박았다면 지금의 P0 4 PR이 아예 필요 없었음. 다만 **LangGraph 9-node 골격, Tool 5-tier, 단일 approval gate, evidence_logger cross-cutting은 동일** — 이 부분은 framework 결정이 아니라 도메인 결정이라 같았을 것.

---

## 학습 — 다음 비슷한 프로젝트에 적용할 원칙

1. **LangChain 메이저 버전은 day 1부터 좁게 lock.** `>=0.3.0` 같은 느슨한 제약은 lock vs 의도 괴리를 만든다.

2. **모든 LLM 호출은 `BaseStructuredChain[T]` 하나의 추상화를 통과시킨다.** 각 chain은 schema와 prompt만 다름.

3. **Validator는 schema와 분리한다.** `model_validator(mode="after")`는 즉시 reject용으로만 쓰고, 도메인 정책은 `validators/safety.py`, `validators/evidence.py`, `validators/business_rule.py` 3개 파일로 분리.

4. **`runtime_mode` enum을 첫날부터 박는다.** `deterministic`이 default, LLM 호출은 explicit opt-in.

5. **`include_raw=True`로 받되 raw 원문은 Evidence Log에 저장하지 않는다.** hash + token usage + parsing_error만.

6. **팀별 폴더 분기를 만들지 않는다.** `rag/`는 하나, validator 정책도 하나.

7. **Fake provider 단계를 별도로 만들지 않는다.** schema strict + `MAX_RETRIES`로 schema retry가 자연스러운 fallback 역할을 함.

8. **LangGraph는 framework 결정과 무관하게 유지.** 단일 approval gate, evidence_logger, 9-node 직선 파이프라인은 도메인 안전 규칙의 코드 표현.

9. **Silent fallback 금지.** validator 실패는 `blocked` / `error`로 명시적으로 노출.

10. **Tool 5-tier contract는 day 1부터.** FORBIDDEN tool은 등록 자체가 안 되고, APPROVAL_REQUIRED는 단일 게이트 통과 후만 SUCCESS.

---

## 참고

- 실제 마이그레이션 계획: `docs/langchain-1-migration-plan.md`
- LangChain 1.0 학습 로드맵: https://www.notion.so/0d54b612422382aa96b88165473ff63f
- 5️⃣ LLM 호출 체인 구성 & 결과 파싱: https://www.notion.so/35b4b612422380ec9964fb27162c2b05
- 도메인 안전 규칙: `AGENTS.md`, `docs/SECURITY_GUARDRAILS.md`
