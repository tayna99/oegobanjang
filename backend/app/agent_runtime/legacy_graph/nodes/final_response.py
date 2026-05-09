from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent_runtime.schemas import ForeignHiringState, Intent, EventType
from app.agent_runtime.middleware.pii_filter import mask_pii
from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event
from app.config import get_settings

_UNSUPPORTED_MESSAGES: dict[str, str] = {
    Intent.UNSUPPORTED_VALUE_JUDGMENT.value: "근로자 성실도 평가, 이탈 예측 등의 가치 판단은 제공하지 않습니다.",
    Intent.UNSUPPORTED_LEGAL_JUDGMENT.value: "비자 가능 여부 확정이나 법률·노무 자문은 제공하지 않습니다. 행정사 또는 노무사에게 문의하세요.",
    Intent.UNSUPPORTED_AUTO_SUBMISSION.value: "정부 포털 자동 제출이나 비자 신청 대행은 지원하지 않습니다.",
}
_HANDOFF_DRAFT_NOTICE = (
    "전문가 검토용 handoff package 초안이 생성되었습니다.\n"
    "자동 전달은 하지 않으며, 담당자 승인 전에는 외부로 전송되지 않습니다."
)

_SYSTEM_PROMPT = """당신은 외국인 고용 운영 시스템의 응답 생성기입니다.
사용자 질문, 검색된 공식 문서, 에이전트 분석 결과를 바탕으로 정확하고 간결한 답변을 생성합니다.

답변 원칙:
- 법령(Grade A) > 공식 절차(Grade B) > 서식(Grade C) > 안전자료(Grade D) 순으로 근거를 인용합니다.
- 각 주장에는 "[출처명]" 형태로 인용을 포함합니다.
- 위험 플래그(D-30 이하, 서류 누락)가 있으면 앞에 강조합니다.
- 공식 근거가 없으면 "공식 근거를 찾지 못했습니다. 행정사 또는 노무사 검토가 필요합니다."라고 답합니다.
- 비자 가능 여부나 법적 확답은 제공하지 않습니다.
- 민감정보(여권번호, 외국인등록번호, 전화번호 전체)는 포함하지 않습니다."""


def _build_context_text(rag_contexts: list[dict]) -> str:
    if not rag_contexts:
        return "검색된 공식 문서 없음"
    lines = []
    for ctx in rag_contexts:
        grade = ctx.get("evidence_grade", "")
        title = ctx.get("title", "")
        content = ctx.get("content", "")[:300]
        lines.append(f"[{title} / Grade {grade}]\n{content}")
    return "\n\n".join(lines)


def _build_agent_summary(agent_results: list[dict]) -> str:
    if not agent_results:
        return ""
    parts = []
    for r in agent_results:
        agent = r.get("agent", "")
        summary = r.get("summary", "")
        risk_flags = r.get("risk_flags", [])
        if summary:
            parts.append(f"[{agent}] {summary}")
        for flag in risk_flags:
            parts.append(f"  ⚠ {flag}")
    return "\n".join(parts)


def _append_handoff_notice(state: ForeignHiringState) -> None:
    if not state.handoff_package_draft:
        return
    if not state.final_response:
        state.final_response = _HANDOFF_DRAFT_NOTICE
        return
    if _HANDOFF_DRAFT_NOTICE in state.final_response:
        return
    state.final_response = f"{state.final_response}\n\n{_HANDOFF_DRAFT_NOTICE}"


def final_response_node(state: ForeignHiringState) -> ForeignHiringState:
    intents = state.detected_intents or []

    unsupported_msgs = [
        _UNSUPPORTED_MESSAGES[i.value]
        for i in intents
        if i.value in _UNSUPPORTED_MESSAGES
    ]

    context_text = _build_context_text(state.rag_contexts)
    agent_summary = _build_agent_summary(state.agent_results)

    no_rag = not state.rag_contexts
    no_agents = not state.agent_results
    only_unsupported = bool(unsupported_msgs) and no_rag and no_agents

    if only_unsupported:
        state.final_response = "\n".join(unsupported_msgs)
    elif no_rag and no_agents:
        state.final_response = "공식 근거를 찾지 못했습니다. 행정사 또는 노무사 검토가 필요합니다."
    else:
        settings = get_settings()
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key,
        )

        user_prompt_parts = [f"질문: {state.user_message}"]
        if context_text != "검색된 공식 문서 없음":
            user_prompt_parts.append(f"검색된 공식 문서:\n{context_text}")
        if agent_summary:
            user_prompt_parts.append(f"에이전트 분석 결과:\n{agent_summary}")
        if state.risk_flags:
            user_prompt_parts.append(f"위험 플래그:\n" + "\n".join(f"- {f}" for f in state.risk_flags))
        if unsupported_msgs:
            user_prompt_parts.append("주의사항:\n" + "\n".join(unsupported_msgs))

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content="\n\n".join(user_prompt_parts)),
        ]

        try:
            response = llm.invoke(messages)
            # PII 마스킹 적용
            state.final_response = mask_pii(response.content)
        except Exception as e:
            state.final_response = f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    _append_handoff_notice(state)

    citation_ids = [ctx.get("source_id", "") for ctx in state.rag_contexts]
    event = make_event(
        event_type=EventType.FINAL_RESPONSE_GENERATED,
        request_id=state.request_id,
        summary=f"최종 응답 생성. RAG {len(state.rag_contexts)}건, agents {len(state.agent_results)}건",
        step_name="final_response",
        citation_ids=citation_ids,
        risk_level="HIGH" if any("긴급" in f or "초과" in f for f in state.risk_flags) else "LOW",
    )
    return log_event(state, event)
