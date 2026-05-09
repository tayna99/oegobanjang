"""Workforce Agent: 채용·고용허가 절차 안내, 후보자 서류 준비 상태 확인."""
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.agent_runtime.schemas import ForeignHiringState, EventType
from app.agent_runtime.tools.registry import (
    get_worker_profile,
    search_policy_documents,
    get_document_requirements,
    generate_expert_handoff_package_draft,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event
from app.config import get_settings

_TOOLS = [
    get_worker_profile,
    search_policy_documents,
    get_document_requirements,
    generate_expert_handoff_package_draft,
]

_SYSTEM_PROMPT = """당신은 외국인 고용 운영 시스템의 채용·고용허가 전문 에이전트입니다.

역할:
- 외국인 고용허가 절차 안내
- 채용 단계별 필요 서류 안내
- 사업장 등록 절차 안내

제약:
- 국적별 선호 또는 차별적 추천을 하지 않습니다.
- 후보자의 성실도나 이탈 가능성을 판단하지 않습니다.
- 모든 안내에 공식 근거(EPS 절차, 법령)를 명시합니다.

사용 가능한 tools: get_worker_profile, search_policy_documents,
get_document_requirements, generate_expert_handoff_package_draft"""


def run_hiring_agent(state: ForeignHiringState) -> dict[str, Any]:
    """workforce_agent 실행."""
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
    if state.rag_contexts:
        for ctx in state.rag_contexts[:3]:
            context_parts.append(
                f"[{ctx.get('title', '')} / Grade {ctx.get('evidence_grade', '')}]\n{ctx.get('content', '')[:300]}"
            )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    tool_results = []
    risk_flags_new = []

    try:
        response = llm.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_fn = next((t for t in _TOOLS if t.name == tool_call["name"]), None)
                if not tool_fn:
                    continue
                result = tool_fn.invoke(tool_call.get("args", {}))
                if isinstance(result, dict):
                    tool_results.append(result)
                    risk_flags_new.extend(result.get("risk_flags", []))

        agent_result = {
            "agent": "workforce_agent",
            "summary": response.content or "tool 호출 완료",
            "tool_calls": len(tool_results),
            "risk_flags": risk_flags_new,
        }

    except Exception as e:
        agent_result = {
            "agent": "workforce_agent",
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
        agent_name="workforce_agent",
        step_name="hiring_agent",
        summary=f"workforce_agent 실행. tool {len(tool_results)}건",
    )
    log_event(state, event)

    return agent_result
