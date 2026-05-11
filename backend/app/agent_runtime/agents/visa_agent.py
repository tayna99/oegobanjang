"""Visa Document Agent: 비자 상태 확인, 서류 누락 계산, handoff 패키지 초안 생성.

오케스트레이터 → 서브에이전트 2개 구조:
  run_visa_agent()
      ├── _run_visa_risk_sub_agent()       비자 위험도 전담
      └── _run_document_priority_sub_agent()  서류 우선순위 전담
"""
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
    assess_visa_risk,
    assess_document_priority,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event
from app.config import get_settings

# 서브에이전트 1: 비자 위험도 전담
_VISA_RISK_TOOLS = [
    get_worker_profile,
    get_visa_status,
    assess_visa_risk,
]

# 서브에이전트 2: 서류 우선순위 전담
_DOC_PRIORITY_TOOLS = [
    get_document_status,
    get_document_requirements,
    search_policy_documents,
    assess_document_priority,
]

# 메인 오케스트레이터: handoff 초안 전용
_HANDOFF_TOOLS = [
    generate_expert_handoff_package_draft,
]

_VISA_RISK_SYSTEM_PROMPT = """당신은 비자 만료 위험도만 분석하는 전문 서브에이전트입니다.

역할:
- assess_visa_risk를 반드시 호출해 비자 유형별 준비 기간과 계약 만료 교차 분석을 수행합니다.
- get_worker_profile, get_visa_status로 현재 상태를 먼저 조회합니다.

제약:
- 비자 가능 여부를 확정하지 않습니다.
- 법률·노무 자문을 제공하지 않습니다.
- 위험도 수치와 날짜 근거만 제시합니다.

사용 가능한 tools: get_worker_profile, get_visa_status, assess_visa_risk"""

_DOC_PRIORITY_SYSTEM_PROMPT = """당신은 서류 누락 우선순위만 분석하는 전문 서브에이전트입니다.

역할:
- assess_document_priority를 반드시 호출해 CRITICAL/SUPPLEMENTARY 분류를 수행합니다.
- get_document_status, get_document_requirements로 현황을 먼저 파악합니다.
- search_policy_documents로 서류 요건의 RAG 근거를 포함합니다.

제약:
- 비자 가능 여부를 확정하지 않습니다.
- 서류 현황과 우선순위 분류만 출력합니다.
- 공식 근거가 없으면 "공식 근거를 찾지 못했습니다. 행정사 검토 필요"라고 답합니다.

사용 가능한 tools: get_document_status, get_document_requirements, search_policy_documents, assess_document_priority"""


def _invoke_tools(response: Any, tools: list) -> tuple[list, list, list[Citation]]:
    """tool_calls 처리 후 (tool_results, risk_flags, citations) 반환."""
    tool_results: list[dict] = []
    risk_flags: list[str] = []
    citations: list[Citation] = []

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        return tool_results, risk_flags, citations

    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        tool_fn = next((t for t in tools if t.name == tool_name), None)
        if not tool_fn:
            continue
        result = tool_fn.invoke(tool_args)
        if isinstance(result, dict):
            tool_results.append(result)
            risk_flags.extend(result.get("risk_flags", []))
            for c in result.get("citations", []):
                citations.append(Citation(**c) if isinstance(c, dict) else c)

    return tool_results, risk_flags, citations


def _run_visa_risk_sub_agent(
    state: ForeignHiringState,
    worker_id: str,
    llm_base: ChatOpenAI,
) -> dict[str, Any]:
    """비자 위험도 전담 서브에이전트."""
    llm = llm_base.bind_tools(_VISA_RISK_TOOLS)

    context_parts = [f"사용자 질문: {state.user_message}"]
    if worker_id:
        context_parts.append(f"대상 근로자 ID: {worker_id}")

    messages = [
        SystemMessage(content=_VISA_RISK_SYSTEM_PROMPT),
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    try:
        response = llm.invoke(messages)
        tool_results, risk_flags, citations = _invoke_tools(response, _VISA_RISK_TOOLS)

        result = {
            "sub_agent": "visa_risk_sub_agent",
            "summary": response.content or "비자 위험도 분석 완료",
            "tool_calls": len(tool_results),
            "tool_results": tool_results,
            "risk_flags": risk_flags,
            "citations": [c.model_dump() for c in citations],
        }
    except Exception as e:
        result = {
            "sub_agent": "visa_risk_sub_agent",
            "error": str(e),
            "tool_calls": 0,
            "tool_results": [],
            "risk_flags": [],
            "citations": [],
        }

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="visa_document_agent",
        step_name="visa_risk_sub_agent",
        summary=f"visa_risk_sub_agent 실행. tool 호출 {result.get('tool_calls', 0)}건, risk {len(result.get('risk_flags', []))}건",
        risk_level="HIGH" if any("긴급" in f or "초과" in f or "CRITICAL" in f for f in result.get("risk_flags", [])) else "MEDIUM" if result.get("risk_flags") else "LOW",
    )
    log_event(state, event)

    return result


def _run_document_priority_sub_agent(
    state: ForeignHiringState,
    worker_id: str,
    llm_base: ChatOpenAI,
    case_type: str = "stay_extension",
) -> dict[str, Any]:
    """서류 우선순위 전담 서브에이전트."""
    llm = llm_base.bind_tools(_DOC_PRIORITY_TOOLS)

    context_parts = [f"사용자 질문: {state.user_message}"]
    if worker_id:
        context_parts.append(f"대상 근로자 ID: {worker_id}")
    context_parts.append(f"케이스 유형: {case_type}")
    if state.rag_contexts:
        for ctx in state.rag_contexts[:3]:
            context_parts.append(
                f"[{ctx.get('title', '')} / Grade {ctx.get('evidence_grade', '')}]\n{ctx.get('content', '')[:300]}"
            )

    messages = [
        SystemMessage(content=_DOC_PRIORITY_SYSTEM_PROMPT),
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    try:
        response = llm.invoke(messages)
        tool_results, risk_flags, citations = _invoke_tools(response, _DOC_PRIORITY_TOOLS)

        result = {
            "sub_agent": "document_priority_sub_agent",
            "summary": response.content or "서류 우선순위 분석 완료",
            "tool_calls": len(tool_results),
            "tool_results": tool_results,
            "risk_flags": risk_flags,
            "citations": [c.model_dump() for c in citations],
        }
    except Exception as e:
        result = {
            "sub_agent": "document_priority_sub_agent",
            "error": str(e),
            "tool_calls": 0,
            "tool_results": [],
            "risk_flags": [],
            "citations": [],
        }

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="visa_document_agent",
        step_name="document_priority_sub_agent",
        summary=f"document_priority_sub_agent 실행. tool 호출 {result.get('tool_calls', 0)}건, risk {len(result.get('risk_flags', []))}건",
        risk_level="HIGH" if any("CRITICAL" in f or "신청 불가" in f for f in result.get("risk_flags", [])) else "MEDIUM" if result.get("risk_flags") else "LOW",
    )
    log_event(state, event)

    return result


def run_visa_agent(state: ForeignHiringState, worker_id: str | None = None) -> dict[str, Any]:
    """visa_document_agent 오케스트레이터. 서브에이전트 2개를 순차 실행해 결과를 합칩니다."""
    allowed, reason = check_llm_limit(state)
    if not allowed:
        return {"error": reason}

    settings = get_settings()
    llm_base = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    _worker_id = worker_id or ""

    # 서브에이전트 1: 비자 위험도
    risk_result = _run_visa_risk_sub_agent(state, _worker_id, llm_base)

    # 서브에이전트 2: 서류 우선순위
    doc_result = _run_document_priority_sub_agent(state, _worker_id, llm_base)

    # 두 결과 병합
    all_tool_results = risk_result.get("tool_results", []) + doc_result.get("tool_results", [])
    all_risk_flags = risk_result.get("risk_flags", []) + doc_result.get("risk_flags", [])
    all_citations: list[Citation] = []
    for c in risk_result.get("citations", []) + doc_result.get("citations", []):
        all_citations.append(Citation(**c) if isinstance(c, dict) else c)

    # CRITICAL 위험이 있을 때 handoff 초안 생성
    has_critical = any(
        "CRITICAL" in f or "긴급" in f or "신청 불가" in f for f in all_risk_flags
    )
    handoff_result: dict | None = None
    if has_critical and _worker_id:
        llm_handoff = llm_base.bind_tools(_HANDOFF_TOOLS)
        handoff_msg = [
            SystemMessage(content="CRITICAL 위험이 감지됐습니다. generate_expert_handoff_package_draft를 호출해 행정사 전달 패키지 초안을 생성하세요."),
            {"role": "user", "content": f"근로자 ID: {_worker_id}\n위험 플래그: {all_risk_flags}"},
        ]
        try:
            handoff_response = llm_handoff.invoke(handoff_msg)
            h_results, h_flags, h_citations = _invoke_tools(handoff_response, _HANDOFF_TOOLS)
            all_tool_results.extend(h_results)
            all_risk_flags.extend(h_flags)
            all_citations.extend(h_citations)
            handoff_result = {"tool_calls": len(h_results), "risk_flags": h_flags}
        except Exception as e:
            handoff_result = {"error": str(e)}

    agent_result = {
        "agent": "visa_document_agent",
        "sub_agents": [
            {"name": risk_result.get("sub_agent"), "tool_calls": risk_result.get("tool_calls", 0), "risk_flags": risk_result.get("risk_flags", [])},
            {"name": doc_result.get("sub_agent"), "tool_calls": doc_result.get("tool_calls", 0), "risk_flags": doc_result.get("risk_flags", [])},
        ],
        "handoff_triggered": has_critical,
        "handoff": handoff_result,
        "summary": f"비자위험도: {risk_result.get('summary', '')} | 서류우선순위: {doc_result.get('summary', '')}",
        "tool_calls": len(all_tool_results),
        "risk_flags": all_risk_flags,
    }

    state.agent_results.append(agent_result)
    state.tool_results.extend(all_tool_results)
    state.risk_flags.extend(all_risk_flags)

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="visa_document_agent",
        step_name="visa_agent",
        summary=f"visa_document_agent 완료. 서브에이전트 2개, 전체 tool {len(all_tool_results)}건, risk {len(all_risk_flags)}건",
        risk_level="HIGH" if any("긴급" in f or "초과" in f or "CRITICAL" in f for f in all_risk_flags) else "MEDIUM" if all_risk_flags else "LOW",
    )
    log_event(state, event)

    return agent_result
