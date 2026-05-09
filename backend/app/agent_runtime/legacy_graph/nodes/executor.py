"""Executor: plan의 required_agents를 순서대로 호출합니다."""
from app.agent_runtime.schemas import ForeignHiringState, Intent, EventType
from app.agent_runtime.rag_tayna.retriever import RAGRetriever
from app.agent_runtime.middleware.summarizer import maybe_summarize_contexts
from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event

_INTENT_QUERY_MAP: dict[str, str] = {
    Intent.VISA_CHECK.value: "비자 체류연장 갱신 절차 필요 서류",
    Intent.DOCUMENT_CHECK.value: "서류 제출 현황 누락 서류 목록",
    Intent.HIRING.value: "외국인 고용허가 채용 절차 EPS",
    Intent.CONTACT.value: "다국어 소통 메시지 안내",
    Intent.BRIEFING.value: "현황 요약 보고",
}


def executor_node(state: ForeignHiringState) -> ForeignHiringState:
    # 1. RAG 검색
    retriever = RAGRetriever()
    intents = state.detected_intents or []
    query_parts = [state.user_message]
    for intent in intents:
        hint = _INTENT_QUERY_MAP.get(intent.value)
        if hint:
            query_parts.append(hint)
    query = " ".join(query_parts)

    rag_result = retriever.search(query=query, k=5)
    rag_contexts = []
    if rag_result.found:
        for doc in rag_result.documents:
            rag_contexts.append({
                "source_id": doc.metadata.get("source_id", ""),
                "title": doc.metadata.get("title", ""),
                "evidence_grade": doc.metadata.get("evidence_grade", ""),
                "publisher": doc.metadata.get("publisher", ""),
                "content": doc.page_content,
            })

    # RAG contexts 요약 (글자수 초과 방지)
    rag_contexts = maybe_summarize_contexts(rag_contexts)
    state.rag_contexts = rag_contexts

    citation_ids = [ctx["source_id"] for ctx in rag_contexts]
    rag_event = make_event(
        event_type=EventType.RAG_RETRIEVED,
        request_id=state.request_id,
        summary=f"RAG 검색 완료. 결과 {len(rag_contexts)}건. found={rag_result.found}",
        step_name="executor",
        citation_ids=citation_ids,
    )
    log_event(state, rag_event)

    # 2. required_agents 호출
    required_agents = state.plan.required_agents or []

    for agent_name in required_agents:
        if agent_name == "visa_document_agent":
            _run_visa_agent(state)
        elif agent_name == "workforce_agent":
            _run_hiring_agent(state)
        elif agent_name == "multilingual_contact_agent":
            _run_contact_agent(state)

    # 3. risk_flags → state.plan.requires_approval 재판단
    if state.risk_flags and not state.plan.requires_approval:
        high_risks = [f for f in state.risk_flags if "긴급" in f or "초과" in f]
        if high_risks:
            risk_event = make_event(
                event_type=EventType.RISK_FLAGGED,
                request_id=state.request_id,
                summary=f"고위험 플래그 {len(high_risks)}건: {high_risks[0]}",
                step_name="executor",
                risk_level="HIGH",
            )
            log_event(state, risk_event)

    return state


def _run_visa_agent(state: ForeignHiringState) -> None:
    try:
        from app.agent_runtime.agents.visa_agent import run_visa_agent
        run_visa_agent(state)
    except Exception as e:
        state.agent_results.append({
            "agent": "visa_document_agent",
            "error": str(e),
        })


def _run_hiring_agent(state: ForeignHiringState) -> None:
    try:
        from app.agent_runtime.agents.hiring_agent import run_hiring_agent
        run_hiring_agent(state)
    except Exception as e:
        state.agent_results.append({
            "agent": "workforce_agent",
            "error": str(e),
        })


def _run_contact_agent(state: ForeignHiringState) -> None:
    try:
        from app.agent_runtime.agents.contact_agent import run_contact_agent
        run_contact_agent(state)
    except Exception as e:
        state.agent_results.append({
            "agent": "multilingual_contact_agent",
            "error": str(e),
        })
