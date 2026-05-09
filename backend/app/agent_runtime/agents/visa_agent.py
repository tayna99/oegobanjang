"""Visa Document Agent: 비자 상태 확인, 서류 누락 계산, handoff 패키지 초안 생성."""
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.agent_runtime.schemas import ForeignHiringState, EventType
from app.agent_runtime.schemas.tool import Citation
from app.agent_runtime.tools.registry import (
    get_worker_profile, get_visa_status, get_document_status,
    search_policy_documents, get_document_requirements,
    calculate_visa_d_day, calculate_missing_documents, calculate_contract_gap,
    generate_expert_handoff_package_draft,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event
from app.config import get_settings

_TOOLS = [
    get_worker_profile,
    get_visa_status,
    get_document_status,
    search_policy_documents,
    get_document_requirements,
    calculate_visa_d_day,
    calculate_missing_documents,
    calculate_contract_gap,
    generate_expert_handoff_package_draft,
]

_SYSTEM_PROMPT = """당신은 외국인 고용 운영 시스템의 비자·서류 전문 에이전트입니다.

역할:
- 근로자 비자 상태 조회 및 D-day 계산
- 서류 누락 확인
- 행정사/노무사 전달 패키지 초안 생성

제약:
- 비자 가능 여부를 확정하지 않습니다.
- 법률·노무 자문을 제공하지 않습니다.
- 모든 판단에 RAG 근거(출처 포함)를 명시합니다.
- 공식 근거가 없으면 "공식 근거를 찾지 못했습니다. 행정사 검토 필요"라고 답합니다.

사용 가능한 tools: get_worker_profile, get_visa_status, get_document_status,
search_policy_documents, get_document_requirements, calculate_visa_d_day,
calculate_missing_documents, calculate_contract_gap, generate_expert_handoff_package_draft"""


def run_visa_agent(state: ForeignHiringState, worker_id: str | None = None) -> dict[str, Any]:
    """visa_document_agent 실행. tool_results와 risk_flags를 state에 추가합니다."""
    allowed, reason = check_llm_limit(state)
    if not allowed:
        return {"error": reason}

    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    ).bind_tools(_TOOLS)

    context_parts = [f"사용자 질문: {state.user_message}"]
    if worker_id:
        context_parts.append(f"대상 근로자 ID: {worker_id}")
    if state.rag_contexts:
        for ctx in state.rag_contexts[:3]:
            context_parts.append(f"[{ctx.get('title', '')} / Grade {ctx.get('evidence_grade', '')}]\n{ctx.get('content', '')[:300]}")

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    tool_results = []
    risk_flags_new = []
    citations: list[Citation] = []

    try:
        response = llm.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})

                tool_fn = next((t for t in _TOOLS if t.name == tool_name), None)
                if not tool_fn:
                    continue

                result = tool_fn.invoke(tool_args)
                if isinstance(result, dict):
                    tool_results.append(result)
                    risk_flags_new.extend(result.get("risk_flags", []))
                    for c in result.get("citations", []):
                        citations.append(Citation(**c) if isinstance(c, dict) else c)

        agent_result = {
            "agent": "visa_document_agent",
            "summary": response.content or "tool 호출 완료",
            "tool_calls": len(tool_results),
            "risk_flags": risk_flags_new,
        }

    except Exception as e:
        agent_result = {
            "agent": "visa_document_agent",
            "error": str(e),
            "tool_calls": 0,
            "risk_flags": [],
        }

    state.agent_results.append(agent_result)
    state.tool_results.extend(tool_results)
    state.risk_flags.extend(risk_flags_new)

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="visa_document_agent",
        step_name="visa_agent",
        summary=f"visa_document_agent 실행. tool 호출 {len(tool_results)}건, risk {len(risk_flags_new)}건",
        risk_level="HIGH" if any("긴급" in f or "초과" in f for f in risk_flags_new) else "MEDIUM" if risk_flags_new else "LOW",
    )
    log_event(state, event)

    return agent_result
