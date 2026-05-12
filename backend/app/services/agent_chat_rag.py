from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.agent_runtime.rag.retriever import PolicyRetriever, tokenize
from app.config import get_settings


CANONICAL_INTENTS = {
    "quota_review",
    "visa_expiry",
    "contract_visa_conflict",
    "document_gap",
    "document_request_message",
    "reporting_deadline",
    "handoff_preview",
    "daily_briefing",
    "candidate_readiness",
    "evidence_audit_review",
}

RISK_TYPES_BY_INTENT: dict[str, tuple[str, ...]] = {
    "visa_expiry": ("visa_expiry", "missing_document", "contract_visa_conflict"),
    "document_gap": ("missing_document", "candidate_readiness"),
    "document_request_message": ("missing_document",),
    "contract_visa_conflict": ("contract_visa_conflict",),
    "reporting_deadline": ("reporting_deadline",),
    "quota_review": ("quota_review", "candidate_readiness"),
    "candidate_readiness": ("candidate_readiness",),
    "handoff_preview": (
        "visa_expiry",
        "missing_document",
        "contract_visa_conflict",
        "reporting_deadline",
    ),
    "evidence_audit_review": (
        "reporting_deadline",
        "contract_visa_conflict",
        "visa_expiry",
        "missing_document",
        "quota_review",
        "candidate_readiness",
    ),
}

INTENT_LABELS: dict[str, str] = {
    "visa_expiry": "비자 관련 업무",
    "document_gap": "서류 누락 업무",
    "contract_visa_conflict": "계약-체류기간 충돌 검토 업무",
    "reporting_deadline": "신고기한 업무",
    "quota_review": "채용/쿼터 검토 업무",
    "handoff_preview": "전문가 검토 패키지 업무",
    "document_request_message": "다국어 서류 요청 메시지 업무",
    "candidate_readiness": "후보자 서류 준비상태 확인 업무",
    "evidence_audit_review": "근거/감사 재현 업무",
    "daily_briefing": "오늘 확인할 외국인 고용 업무",
}

RISK_LABELS: dict[str, str] = {
    "visa_expiry": "체류기간 연장 준비",
    "missing_document": "체류/고용 서류 누락 확인",
    "contract_visa_conflict": "계약-체류기간 충돌 검토",
    "reporting_deadline": "고용변동 신고기한 확인",
    "quota_review": "신규 인력/쿼터 검토",
    "candidate_readiness": "후보자 서류 준비상태 확인",
}

DOCUMENT_LABELS: dict[str, str] = {
    "passport_copy": "여권 사본",
    "alien_registration_copy": "외국인등록증 사본",
    "alien_registration": "외국인등록증 사본",
    "standard_labor_contract": "표준근로계약서 사본",
}

FORBIDDEN_ACTION_TERMS: tuple[str, ...] = (
    "정부 포털",
    "바로 제출",
    "자동 제출",
    "카톡으로 바로",
    "문자로 바로",
    "승인 없이",
    "발송해줘",
    "보내버려",
    "완료 처리",
    "국적별 추천",
    "국적별로 추천",
    "국적별로 성실",
    "국적 선호",
    "성실할 사람 추천",
    "이탈 가능성",
    "국적별 점수",
    "국적별 순위",
    "나라별 추천",
)

INTENT_EXAMPLE_PHRASES: dict[str, tuple[str, ...]] = {
    "quota_review": (
        "사람 더 필요해",
        "사람이 부족해",
        "직원 더 뽑아야 해",
        "일할 사람 없어",
        "채용 좀 해야 할 것 같아",
    ),
    "visa_expiry": (
        "비자 뭐 해야 해",
        "비자 괜찮아",
        "기간 얼마 남았어",
        "끝나는 사람 있어",
        "만료되는 사람 있어",
    ),
    "contract_visa_conflict": (
        "날짜 안 맞는 거 있어",
        "계약이랑 비자 안 맞아",
        "둘이 날짜 겹쳐",
        "계약 끝나는 거랑 비자 끝나는 거 봐줘",
    ),
    "reporting_deadline": (
        "신고 기한 지난 케이스 있어",
        "고용변동 신고 봐줘",
        "신고기한 놓친 건 있어",
        "신고 늦은 케이스 있어",
        "고용변동 기한 확인해줘",
    ),
    "document_gap": (
        "뭐 빠졌어",
        "서류 빠진 거 있어",
        "안 낸 서류 있어",
        "여권 사본 받았어",
        "서류 다 됐어",
    ),
    "document_request_message": (
        "서류 달라고 해줘",
        "베트남어로 말해줘",
        "네팔어로 말해줘",
        "여권 보내달라고 써줘",
        "다시 보내달라고 문구 만들어줘",
        "직원한테 뭐라고 보내",
        "안내 메시지 만들어줘",
        "안내문 만들어줘",
        "교육장으로 오라고 안내해줘",
        "안전교육 안내문 만들어줘",
        "네팔어 안내문 만들어줘",
    ),
    "handoff_preview": (
        "행정사한테 뭐 보내야 해",
        "전문가한테 보낼 거 만들어줘",
        "검토자료 만들어줘",
        "누구한테 넘기면 돼",
        "보낼 묶음 만들어줘",
    ),
    "daily_briefing": (
        "오늘 뭐부터 해",
        "급한 거 뭐야",
        "급한 케이스만 정리해줘",
        "뭐가 제일 위험해",
        "먼저 볼 것만 알려줘",
        "오늘 할 일 알려줘",
        "이번 달 외국인 직원 중 급한 케이스만 정리해줘",
    ),
    "candidate_readiness": (
        "후보자 준비됐어",
        "새 사람 서류 됐어",
        "들어올 사람 문제 있어",
        "입국할 사람 뭐 빠졌어",
        "새로 올 사람 확인해줘",
    ),
    "evidence_audit_review": (
        "왜 그렇게 봤어",
        "근거 있어",
        "로그 보여줘",
        "기록 남아 있어",
        "어디 보고 말한 거야",
    ),
}


class AgentChatLLMQuery(BaseModel):
    query: str
    entities: dict[str, str] = Field(default_factory=dict)
    intent_candidates: list[str] = Field(default_factory=list)
    answer_style: str = "operational_brief"

    @field_validator("entities", mode="before")
    @classmethod
    def coerce_entities_to_strings(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): str(item) for key, item in value.items() if item is not None}


class AgentChatStructuredPlan(BaseModel):
    should_run: bool = True
    intent: str | None = None
    plan_steps: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    entities: dict[str, str] = Field(default_factory=dict)
    blocked_actions: list[str] = Field(default_factory=list)
    approval_required: bool = True
    execution_allowed: bool = True
    target_service: str = "rag_first_chat"


@dataclass(frozen=True)
class RAGFirstChatContext:
    company_id: str
    user_role: str
    fallback_plan: dict[str, Any]


@dataclass(frozen=True)
class RAGFirstPreflight:
    llm_query: AgentChatLLMQuery
    rag_results: list[dict[str, Any]]
    intent: str
    llm_used: bool
    llm_error: str | None = None
    blocked: bool = False


class OpenAIAgentChatQueryPlanner:
    """OpenAI smoke/dev planner. It only creates a search query schema."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def enabled(self) -> bool:
        return bool(
            self.settings.agent_chat_openai_smoke_enabled
            and self.settings.openai_api_key
        )

    def plan(self, message: str) -> AgentChatLLMQuery:
        if not self.enabled():
            return AgentChatLLMQuery(query=message)

        llm = ChatOpenAI(
            model=self.settings.agent_chat_openai_model,
            temperature=0,
            openai_api_key=self.settings.openai_api_key,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You convert Korean foreign-worker operations questions into a strict JSON object. "
                        "Return keys: query, entities, intent_candidates, answer_style. "
                        f"intent_candidates must be from {sorted(CANONICAL_INTENTS)}. "
                        "Do not decide legal eligibility, recommend people, or approve/send anything."
                    )
                ),
                HumanMessage(content=message),
            ]
        )
        raw = str(response.content or "").strip()
        parsed = json.loads(raw)
        query = AgentChatLLMQuery.model_validate(parsed)
        query.intent_candidates = [
            intent for intent in query.intent_candidates if intent in CANONICAL_INTENTS
        ]
        if not query.query.strip():
            query.query = message
        return query


def prepare_agent_chat_rag_first(
    message: str,
    *,
    llm_planner: OpenAIAgentChatQueryPlanner | None = None,
) -> RAGFirstPreflight:
    planner = llm_planner or OpenAIAgentChatQueryPlanner()
    rag_results = PolicyRetriever(_build_static_rag_chunks()).search(
        message,
        top_k=8,
        answer_evidence_only=False,
    )
    try:
        llm_query = planner.plan(message)
        llm_error = None
    except Exception as exc:
        llm_query = AgentChatLLMQuery(query=message)
        llm_error = exc.__class__.__name__

    blocked = _has_forbidden_action(message) or _has_forbidden_action(llm_query.query)
    if not rag_results:
        return RAGFirstPreflight(
            llm_query=llm_query,
            rag_results=[],
            intent="unsupported",
            llm_used=planner.enabled(),
            llm_error=llm_error,
            blocked=blocked,
        )

    return RAGFirstPreflight(
        llm_query=llm_query,
        rag_results=rag_results,
        intent=_select_intent(rag_results, llm_query),
        llm_used=planner.enabled(),
        llm_error=llm_error,
        blocked=blocked,
    )


def run_agent_chat_rag_first(
    *,
    message: str,
    daily_briefing: Any,
    context: RAGFirstChatContext,
    llm_planner: OpenAIAgentChatQueryPlanner | None = None,
    preflight: RAGFirstPreflight | None = None,
) -> dict[str, Any]:
    preflight = preflight or prepare_agent_chat_rag_first(
        message,
        llm_planner=llm_planner,
    )
    llm_query = preflight.llm_query
    if preflight.blocked:
        return _forbidden_response(
            message=message,
            daily_briefing=daily_briefing,
            llm_query=llm_query,
            llm_used=preflight.llm_used,
        )

    chunks = _build_operational_chunks(daily_briefing)
    results = PolicyRetriever(chunks).search(
        llm_query.query,
        top_k=8,
        answer_evidence_only=False,
    )

    if not results:
        results = preflight.rag_results

    intent = preflight.intent if preflight.intent != "unsupported" else _select_intent(results, llm_query)
    selected_items = _select_daily_briefing_items(daily_briefing.items, intent)
    actions = _selected_actions(daily_briefing.recommended_actions, selected_items)
    sources = _selected_sources(daily_briefing.citation_summaries, selected_items, results)
    answer = _rag_answer(
        daily_briefing,
        intent,
        selected_items=selected_items,
        selected_actions=actions,
        rag_hits=results,
    )
    structured_plan = AgentChatStructuredPlan(
        intent=intent,
        plan_steps=[
            "retrieve_rag_intent_chunks",
            "plan_with_llm_from_rag_context",
            "load_rule_db_state_for_selected_intent",
            "return_grounded_answer",
        ],
        required_context=_required_context(intent),
        entities=llm_query.entities,
        approval_required=True,
        execution_allowed=True,
        target_service="rag_first_chat",
    )

    return {
        "answer": answer,
        "final_response": answer,
        "route": "rag_first_chat",
        "llm_used": preflight.llm_used,
        "latency_mode": "llm_plan_fast_answer" if preflight.llm_used else "rag_first_fast",
        "tool_calls": [
            {
                "name": "agent_chat_rag_search",
                "route": "rag_first_chat",
                "intent": intent,
                "result_count": len(preflight.rag_results),
                "action_count": 0,
                "source_count": len(
                    {
                        citation_id
                        for result in preflight.rag_results
                        for citation_id in result.get("metadata", {}).get("citation_ids", [])
                    }
                ),
            },
            {
                "name": "agent_chat_llm_plan",
                "route": "rag_first_chat",
                "intent": intent,
                "result_count": 1 if not preflight.llm_error else 0,
                "action_count": 0,
                "source_count": len(preflight.rag_results),
            },
            {
                "name": "daily_briefing_lookup",
                "route": "rag_first_chat",
                "intent": intent,
                "result_count": len(selected_items),
                "action_count": len(actions),
                "source_count": len(sources),
            }
        ],
        "actions": [action.model_dump() for action in actions],
        "sources": [source.model_dump() for source in sources],
        "detected_intents": [intent],
        "approval_required": daily_briefing.approval_required,
        "approval_status": "pending" if daily_briefing.approval_required else "not_required",
        "daily_briefing": daily_briefing.model_dump(),
        "structured_plan": structured_plan.model_dump(),
        "rag_hits": [_rag_hit_view(result) for result in results],
        "retrieval_source_types": sorted(
            {
                str(result.get("metadata", {}).get("source_type", "operational_case"))
                for result in results
            }
        ),
        "llm_provider": "openai" if preflight.llm_used else None,
        "fallback_used": False,
        "fallback_reason": preflight.llm_error,
    }


def _build_operational_chunks(daily_briefing: Any) -> list[dict[str, Any]]:
    actions_by_id = {action.action_id: action for action in daily_briefing.recommended_actions}
    citations_by_id = {
        citation.citation_id: citation for citation in daily_briefing.citation_summaries
    }
    chunks: list[dict[str, Any]] = []

    for item in daily_briefing.items:
        intent = _intent_for_item(item.risk_type)
        action_labels = [
            str(actions_by_id[action_id].label)
            for action_id in item.next_action_ids
            if action_id in actions_by_id
        ]
        citation_titles = [
            citations_by_id[citation_id].title
            for citation_id in item.citation_ids
            if citation_id in citations_by_id
        ]
        text = " ".join(
            [
                INTENT_LABELS.get(intent, intent),
                RISK_LABELS.get(item.risk_type, item.risk_type),
                _domain_terms(intent),
                item.subject_id,
                _risk_timing(item),
                _document_list(item.missing_documents),
                " ".join(action_labels),
                " ".join(citation_titles),
                "담당자 승인 필요 외부 발송 금지 정부 제출 금지",
            ]
        )
        chunks.append(
            _chunk(
                chunk_id=f"op_{item.item_id}",
                title=RISK_LABELS.get(item.risk_type, item.risk_type),
                text=text,
                source_type="operational_case",
                intent=intent,
                risk_type=item.risk_type,
                case_id=item.case_id,
                citation_ids=item.citation_ids,
                action_ids=item.next_action_ids,
                approval_required=True,
            )
        )

    chunks.append(
        _chunk(
            chunk_id=f"briefing_{daily_briefing.briefing_run_id}",
            title="Daily Risk Briefing",
            text=(
                "오늘 위험한 건 급한 케이스 이번 달 브리핑 우선순위 "
                "Daily Risk Briefing"
            ),
            source_type="operational_case",
            intent="daily_briefing",
            risk_type="daily_briefing",
            case_id=daily_briefing.briefing_run_id,
            citation_ids=[],
            action_ids=[],
            approval_required=daily_briefing.approval_required,
        )
    )

    for intent in sorted(CANONICAL_INTENTS - {"evidence_audit_review"}):
        chunks.append(
            _chunk(
                chunk_id=f"intent_{intent}_{daily_briefing.briefing_run_id}",
                title=_generic_title(intent),
                text=(
                    f"{_generic_title(intent)} "
                    f"{_domain_terms(intent)} "
                    "운영 업무 검색용 마스킹 스냅샷 담당자 승인 필요"
                ),
                source_type="operational_case",
                intent=intent,
                risk_type=intent,
                case_id=daily_briefing.briefing_run_id,
                citation_ids=[],
                action_ids=[],
                approval_required=True,
            )
        )

    for action in daily_briefing.recommended_actions:
        item = next(
            (
                candidate
                for candidate in daily_briefing.items
                if action.action_id in candidate.next_action_ids
            ),
            None,
        )
        if action.action_type == "request_document":
            chunks.append(
                _chunk(
                    chunk_id=f"action_{action.action_id}",
                    title="Document request message draft",
                    text=(
                        "다국어 서류 요청 메시지 베트남어 요청 문구 초안 서류 보완 "
                        "여권 사본 표준근로계약서 외국인등록증 근로자에게 보내기 전 승인 필요 "
                        f"{action.label} {item.subject_id if item else action.subject_id}"
                    ),
                    source_type="action_draft",
                    intent="document_request_message",
                    risk_type=item.risk_type if item else "missing_document",
                    case_id=action.case_id,
                    citation_ids=action.citation_ids,
                    action_ids=[action.action_id],
                    approval_required=action.approval_required,
                )
            )
        if action.action_type == "create_handoff":
            chunks.append(
                _chunk(
                    chunk_id=f"action_{action.action_id}",
                    title="Expert handoff draft",
                    text=(
                        "행정사 노무사 전문가 검토 자료 패키지 handoff 전달할 패키지 넘길 자료 "
                        "검토용 자료 묶음 갱신 건 담당자 승인 필요 "
                        f"{action.label} {item.subject_id if item else action.subject_id}"
                    ),
                    source_type="action_draft",
                    intent="handoff_preview",
                    risk_type=item.risk_type if item else "handoff_preview",
                    case_id=action.case_id,
                    citation_ids=action.citation_ids,
                    action_ids=[action.action_id],
                    approval_required=action.approval_required,
                )
            )

    chunks.append(
        _chunk(
            chunk_id=f"evidence_{daily_briefing.briefing_run_id}",
            title="Evidence and Audit Review",
            text=(
                "판단 근거 감사 로그 evidence audit review 기록 재현 왜 그렇게 판단했는지 "
                "근거 문서 승인 이력 출처 보고 말한 어떤 출처 tool_executed "
                "rag_retrieved approval_requested"
            ),
            source_type="evidence_event",
            intent="evidence_audit_review",
            risk_type="evidence_audit_review",
            case_id=daily_briefing.briefing_run_id,
            citation_ids=[
                citation.citation_id for citation in daily_briefing.citation_summaries[:5]
            ],
            action_ids=[],
            approval_required=False,
        )
    )

    for citation in daily_briefing.citation_summaries:
        chunks.append(
            _chunk(
                chunk_id=f"citation_{citation.citation_id}",
                title=citation.title,
                text=(
                    f"{citation.title} {citation.source} 공식 근거 절차 citation "
                    "체류 비자 서류 고용허가 신고기한 계약 쿼터"
                ),
                source_type="official_policy",
                intent=_intent_for_citation(citation),
                risk_type="official_policy",
                case_id="",
                citation_ids=[citation.citation_id],
                action_ids=[],
                approval_required=False,
            )
        )

    return chunks


def _build_static_rag_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for intent in sorted(CANONICAL_INTENTS):
        source_type = "evidence_event" if intent == "evidence_audit_review" else "operational_case"
        if intent in {"document_request_message", "handoff_preview"}:
            source_type = "action_draft"
        chunks.append(
            _chunk(
                chunk_id=f"intent_static_{intent}",
                title=_generic_title(intent),
                text=(
                    f"{_generic_title(intent)} "
                    f"{_domain_terms(intent)} "
                    "RAG intent snapshot official policy operational case action draft evidence"
                ),
                source_type=source_type,
                intent=intent,
                risk_type=intent,
                case_id="intent_snapshot",
                citation_ids=[],
                action_ids=[],
                approval_required=True,
            )
        )
    return chunks


def _chunk(
    *,
    chunk_id: str,
    title: str,
    text: str,
    source_type: str,
    intent: str,
    risk_type: str,
    case_id: str,
    citation_ids: list[str],
    action_ids: list[str],
    approval_required: bool,
) -> dict[str, Any]:
    return {
        "source_id": chunk_id,
        "chunk_id": chunk_id,
        "title": title,
        "text": text,
        "metadata": {
            "source_id": chunk_id,
            "title": title,
            "source_type": source_type,
            "intent": intent,
            "risk_type": risk_type,
            "case_id": case_id,
            "citation_ids": citation_ids,
            "action_ids": action_ids,
            "approval_required": approval_required,
            "evidence_grade": "E",
            "publisher": "WorkBridge",
        },
    }


def _select_intent(
    results: list[dict[str, Any]],
    llm_query: AgentChatLLMQuery,
) -> str:
    phrase_intent = _exact_phrase_intent(llm_query.query)
    if phrase_intent:
        return phrase_intent

    for result in results:
        metadata = result.get("metadata", {})
        if (
            metadata.get("source_type") == "action_draft"
            and metadata.get("intent") in {"document_request_message", "handoff_preview"}
            and float(result.get("score") or 0) >= 0.5
            and _intent_query_bonus(str(metadata["intent"]), llm_query.query) >= 0.6
        ):
            return str(metadata["intent"])
    intent_scores: dict[str, float] = {}
    for result in results:
        metadata = result.get("metadata", {})
        intent = str(metadata.get("intent") or "")
        if intent not in CANONICAL_INTENTS:
            continue
        source_type = str(metadata.get("source_type") or "")
        source_weight = 1.0
        if source_type == "action_draft" and intent in {"document_request_message", "handoff_preview"}:
            source_weight = 1.15
        elif source_type == "official_policy":
            source_weight = 0.85
        weighted_score = float(result.get("score") or 0.0) * source_weight
        intent_scores[intent] = max(intent_scores.get(intent, 0.0), weighted_score)
    for intent in CANONICAL_INTENTS:
        intent_scores[intent] = intent_scores.get(intent, 0.0) + _intent_query_bonus(
            intent,
            llm_query.query,
        )
    for candidate in llm_query.intent_candidates:
        if candidate in CANONICAL_INTENTS:
            if any(result.get("metadata", {}).get("intent") == candidate for result in results):
                intent_scores[candidate] = intent_scores.get(candidate, 0.0) + 0.25
    if intent_scores:
        return max(intent_scores.items(), key=lambda item: (item[1], item[0]))[0]
    for candidate in llm_query.intent_candidates:
        if candidate in CANONICAL_INTENTS:
            if any(result.get("metadata", {}).get("intent") == candidate for result in results):
                return candidate
    for result in results:
        intent = str(result.get("metadata", {}).get("intent") or "")
        if intent in CANONICAL_INTENTS:
            return intent
    return "daily_briefing"


def _rag_answer(
    result: Any,
    intent: str,
    *,
    selected_items: list[Any],
    selected_actions: list[Any],
    rag_hits: list[dict[str, Any]],
) -> str:
    if intent == "evidence_audit_review":
        citation_ids = {
            citation_id
            for hit in rag_hits
            for citation_id in hit.get("metadata", {}).get("citation_ids", [])
        }
        return "\n".join(
            [
                f"RAG 검색으로 {INTENT_LABELS[intent]}를 찾았습니다.",
                f"- 재현 가능한 Evidence/Audit Review 이벤트: {len(result.evidence_event_ids)}개",
                f"- 연결된 근거 문서: {len(citation_ids)}개 citation",
                "- 다음 처리: 판단 기록 열람 / 근거 문서 확인 / 담당자 승인 이력 확인",
                "민감정보 원문은 응답에 포함하지 않았고, 외부 발송이나 제출은 수행하지 않았습니다.",
            ]
        )

    if not selected_items:
        return (
            f"RAG 검색으로 {INTENT_LABELS.get(intent, intent)}를 찾았지만 "
            "오늘 기준 확인된 운영 항목은 없습니다. 외부 발송이나 제출은 수행하지 않았습니다."
        )

    actions_by_id = {action.action_id: action for action in selected_actions}
    lines = [f"RAG 검색으로 {INTENT_LABELS.get(intent, intent)} {len(selected_items)}건을 찾았습니다."]
    for item in selected_items[:5]:
        action_labels = [
            _action_label(actions_by_id[action_id])
            for action_id in item.next_action_ids
            if action_id in actions_by_id
        ]
        if action_labels:
            action_labels.append("담당자 승인 요청")
        else:
            action_labels.append("담당자 확인")
        lines.append(
            "- "
            f"{item.subject_id}: "
            f"{RISK_LABELS.get(item.risk_type, item.risk_type)} "
            f"({_risk_timing(item)}, {item.severity})"
        )
        lines.append(f"  누락 서류: {_document_list(item.missing_documents)}")
        lines.append(f"  다음 처리: {' / '.join(dict.fromkeys(action_labels))}")
    lines.append("외부 발송, 정부 제출, 상태 완료 처리는 아직 수행하지 않았습니다.")
    return "\n".join(lines)


def _not_found_response(
    *,
    message: str,
    daily_briefing: Any | None,
    llm_query: AgentChatLLMQuery,
    llm_used: bool,
) -> dict[str, Any]:
    structured_plan = AgentChatStructuredPlan(
        should_run=False,
        intent="unsupported",
        plan_steps=["generate_rag_query", "retrieve_operational_and_policy_chunks"],
        required_context=["rag"],
        entities=llm_query.entities,
        approval_required=True,
        execution_allowed=False,
        target_service="rag_first_chat",
    )
    answer = (
        "RAG 검색에서 관련 업무나 공식 근거를 찾지 못했습니다. "
        "질문을 업무, 대상자, 서류, 기한 중 하나와 함께 다시 입력해 주세요."
    )
    return {
        "answer": answer,
        "final_response": answer,
        "route": "rag_first_chat",
        "llm_used": llm_used,
        "latency_mode": "llm_plan_fast_answer" if llm_used else "rag_first_fast",
        "tool_calls": [
            {
                "name": "agent_chat_rag_search",
                "route": "rag_first_chat",
                "intent": "unsupported",
                "result_count": 0,
                "action_count": 0,
                "source_count": 0,
            }
        ],
        "actions": [],
        "sources": [],
        "detected_intents": ["unsupported"],
        "approval_required": True,
        "approval_status": "not_required",
        "daily_briefing": daily_briefing.model_dump() if daily_briefing is not None else None,
        "structured_plan": structured_plan.model_dump(),
        "rag_hits": [],
        "retrieval_source_types": [],
        "llm_provider": "openai" if llm_used else None,
        "fallback_used": False,
    }


def rag_first_not_found_response(
    *,
    message: str,
    preflight: RAGFirstPreflight,
) -> dict[str, Any]:
    return _not_found_response(
        message=message,
        daily_briefing=None,
        llm_query=preflight.llm_query,
        llm_used=preflight.llm_used,
    )


def _forbidden_response(
    *,
    message: str,
    daily_briefing: Any | None,
    llm_query: AgentChatLLMQuery,
    llm_used: bool,
) -> dict[str, Any]:
    answer = (
        "외부 발송, 정부 제출, 상태 완료 처리는 담당자 승인 없이 수행할 수 없습니다. "
        "초안 생성이나 검토 패키지 준비처럼 승인 전 단계로 다시 요청해 주세요."
    )
    structured_plan = AgentChatStructuredPlan(
        should_run=False,
        intent="unsupported",
        plan_steps=["guardrail_check"],
        required_context=[],
        entities=llm_query.entities,
        blocked_actions=["external_send_or_submit_without_approval"],
        approval_required=True,
        execution_allowed=False,
        target_service="rag_first_chat",
    )
    return {
        "answer": answer,
        "final_response": answer,
        "route": "unsupported",
        "llm_used": llm_used,
        "latency_mode": "llm_guardrail" if llm_used else "fast_guardrail",
        "tool_calls": [],
        "actions": [],
        "sources": [],
        "detected_intents": ["unsupported"],
        "approval_required": True,
        "approval_status": "not_required",
        "daily_briefing": daily_briefing.model_dump() if daily_briefing is not None else None,
        "structured_plan": structured_plan.model_dump(),
        "rag_hits": [],
        "retrieval_source_types": [],
        "llm_provider": "openai" if llm_used else None,
        "fallback_used": False,
    }


def rag_first_forbidden_response(
    *,
    message: str,
    preflight: RAGFirstPreflight,
) -> dict[str, Any]:
    return _forbidden_response(
        message=message,
        daily_briefing=None,
        llm_query=preflight.llm_query,
        llm_used=preflight.llm_used,
    )


def _intent_for_item(risk_type: str) -> str:
    if risk_type == "visa_expiry":
        return "visa_expiry"
    if risk_type == "missing_document":
        return "document_gap"
    if risk_type == "contract_visa_conflict":
        return "contract_visa_conflict"
    if risk_type == "reporting_deadline":
        return "reporting_deadline"
    if risk_type == "quota_review":
        return "quota_review"
    if risk_type == "candidate_readiness":
        return "candidate_readiness"
    return "daily_briefing"


def _intent_for_citation(citation: Any) -> str:
    text = f"{citation.citation_id} {citation.title}".casefold()
    if "quota" in text or "쿼터" in text:
        return "quota_review"
    if "계약" in text:
        return "contract_visa_conflict"
    if "서류" in text:
        return "document_gap"
    if "신고" in text:
        return "reporting_deadline"
    return "visa_expiry"


def _select_daily_briefing_items(items: list[Any], intent: str) -> list[Any]:
    risk_types = RISK_TYPES_BY_INTENT.get(intent)
    if not risk_types:
        return items[:5]
    return [item for item in items if item.risk_type in risk_types][:5]


def _selected_actions(actions: list[Any], items: list[Any]) -> list[Any]:
    action_ids = {
        action_id
        for item in items
        for action_id in item.next_action_ids
    }
    return [action for action in actions if action.action_id in action_ids]


def _selected_sources(
    sources: list[Any],
    items: list[Any],
    rag_hits: list[dict[str, Any]],
) -> list[Any]:
    citation_ids = {
        citation_id
        for item in items
        for citation_id in item.citation_ids
    }
    citation_ids.update(
        citation_id
        for hit in rag_hits
        for citation_id in hit.get("metadata", {}).get("citation_ids", [])
    )
    return [source for source in sources if source.citation_id in citation_ids]


def _rag_hit_view(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata", {})
    return {
        "chunk_id": result.get("chunk_id"),
        "source_id": result.get("source_id"),
        "title": result.get("title"),
        "source_type": metadata.get("source_type", "operational_case"),
        "intent": metadata.get("intent"),
        "risk_type": metadata.get("risk_type"),
        "case_id": metadata.get("case_id"),
        "citation_ids": metadata.get("citation_ids", []),
        "action_ids": metadata.get("action_ids", []),
        "score": result.get("score"),
    }


def _required_context(intent: str) -> list[str]:
    if intent == "evidence_audit_review":
        return ["rag", "evidence_events", "citations"]
    if intent in {"document_request_message", "handoff_preview"}:
        return ["rag", "cases", "actions", "approvals", "citations"]
    if intent == "candidate_readiness":
        return ["rag", "candidates", "candidate_documents"]
    if intent == "quota_review":
        return ["rag", "company", "quota"]
    return ["rag", "workers", "documents", "citations"]


def _risk_timing(item: Any) -> str:
    if item.expired:
        if item.days_overdue is not None:
            return f"만료 후 {item.days_overdue}일 경과"
        return "기한 경과"
    if item.d_day is not None:
        return f"D-{item.d_day}"
    return "기한 확인 필요"


def _document_list(documents: list[str]) -> str:
    if not documents:
        return "현재 응답 범위에서 확인된 누락 없음"
    return ", ".join(DOCUMENT_LABELS.get(document, document) for document in documents)


def _action_label(action: Any) -> str:
    if action.action_type == "request_document":
        return "누락서류 요청 초안 보기"
    if action.action_type == "create_handoff":
        return "전문가 검토 패키지 초안 보기"
    return str(action.label)


def _domain_terms(intent: str) -> str:
    terms = {
        "quota_review": (
            "인원이 필요해 인원 필요해 인원 필요 인력이 필요해 인력이 모자라 "
            "충원 사람 더 뽑아 채용 하고 싶어 추가 채용 "
            "신규 외국인 근로자 고용허가 쿼터 준비 이번 라인 생산팀 "
            "추가로 뽑을 수 있어 e 9 새로 받을 준비 충원 가능 인원"
        ),
        "visa_expiry": (
            "비자 체류기간 체류만료 체류 만료 기존 직원 직원들 갱신 확인 "
            "다음 일 손볼 것 만료 가까운 순서 다가오는 임박한 "
            "먼저 챙길 얼마 안 남은 이번 주 갱신해야 e 9 만료 리스크"
        ),
        "contract_visa_conflict": (
            "계약 종료 체류만료 날짜 안 맞는 엇갈린 충돌 겹치는 "
            "근로계약 비자랑 안 맞는 계약기간 비교 비자는 남았는데 "
            "계약은 끝나는 경우 계약서 날짜 계약기간이랑 사람 찾아줘 "
            "계약 만료랑 체류 만료 비교해줘"
        ),
        "reporting_deadline": (
            "고용변동 신고 신고기한 신고 기한 기한 지난 케이스 "
            "기한 놓친 신고 늦은 고용변동 기한 확인 보고 마감"
        ),
        "document_gap": (
            "갱신 서류 빠진 누락 누락된 빈칸 보완 체크 점검 여권 사본 "
            "표준근로계약서 모아줘 없는 직원 제출 준비 안 된 빠진 사람 완성됐는지"
        ),
        "candidate_readiness": (
            "후보자 입국 전 준비 안 된 서류 준비상태 요건 매칭 점수 제외 추천 제외 "
            "신규 후보 항목 후보별 제출 준비 입국 예정자"
        ),
        "document_request_message": (
            "다국어 베트남어 서류 요청 메시지 문자 초안 알려주는 문구 "
            "서류 다시 달라고 말해줘 보내달라고 작성 근로계약서 사본 요청 "
            "네팔어 안내문 안내 메시지 안전교육 교육장 직원에게 공손하게"
        ),
        "handoff_preview": (
            "행정사 노무사 전문가 검토 패키지 handoff 전달 넘길 자료 묶어줘 "
            "검토자료 노무사에게 넘길 초안 전문가 전달용 승인 전에 볼"
        ),
        "evidence_audit_review": (
            "판단 근거 감사 로그 evidence audit 기록 재현 왜 출처 보고 방금 판단 로그 감사용"
        ),
        "daily_briefing": (
            "오늘 위험 급한 케이스 브리핑 우선순위 이번 달 급한 순서 "
            "리스크 높은 제일 먼저 처리 반장이 봐야"
        ),
    }
    examples = " ".join(INTENT_EXAMPLE_PHRASES.get(intent, ()))
    return f"{terms.get(intent, '')} {examples}".strip()


def _generic_title(intent: str) -> str:
    if intent == "daily_briefing":
        return "Daily Risk Briefing"
    return INTENT_LABELS.get(intent, intent)


def _has_forbidden_action(text: str) -> bool:
    normalized = text.replace(" ", "")
    return any(term.replace(" ", "") in normalized for term in FORBIDDEN_ACTION_TERMS)


def _intent_query_bonus(intent: str, query: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    domain_tokens = set(tokenize(_domain_terms(intent)))
    overlap = query_tokens & domain_tokens
    token_bonus = (len(overlap) / max(len(query_tokens), 1)) * 1.2
    normalized_query = _normalize_for_phrase(query)
    phrase_bonus = 0.0
    for phrase in INTENT_EXAMPLE_PHRASES.get(intent, ()):
        normalized_phrase = _normalize_for_phrase(phrase)
        if normalized_phrase and (
            normalized_phrase in normalized_query
            or normalized_query in normalized_phrase
        ):
            phrase_bonus = max(phrase_bonus, 1.6)
    return token_bonus + phrase_bonus


def _normalize_for_phrase(text: str) -> str:
    return "".join(tokenize(text))


def _exact_phrase_intent(query: str) -> str | None:
    normalized_query = _normalize_for_phrase(query)
    matches: list[tuple[int, str]] = []
    for intent, phrases in INTENT_EXAMPLE_PHRASES.items():
        for phrase in phrases:
            normalized_phrase = _normalize_for_phrase(phrase)
            if normalized_phrase and normalized_phrase in normalized_query:
                matches.append((len(normalized_phrase), intent))
    if not matches:
        return None
    return max(matches, key=lambda match: match[0])[1]
