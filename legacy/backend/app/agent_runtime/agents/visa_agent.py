"""Visa Document Agent: 비자 상태 확인, 서류 누락 계산, handoff 패키지 초안 생성.

오케스트레이터 → 서브에이전트 2개 구조:
  run_visa_agent()
      ├── _run_visa_risk_sub_agent()       비자 위험도 전담 (LLM ReAct 루프)
      └── _run_document_priority_sub_agent()  서류 우선순위 전담 (LLM ReAct 루프)

각 서브에이전트는 자체 LLM을 가지고, 결과를 보고 추가 tool 호출 여부를 스스로 판단한다.
"""
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agent_runtime.schemas import ForeignHiringState, EventType
from app.agent_runtime.schemas.tool import Citation
from app.agent_runtime.tools.registry import (
    get_worker_profile, get_visa_status, get_document_status,
    search_policy_documents, get_document_requirements,
    generate_expert_handoff_package_draft,
    assess_visa_risk,
    assess_document_priority,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event
from app.config import get_settings


# 서브에이전트 1: 비자 위험도 전담
# LLM이 get_worker_profile → assess_visa_risk 순으로 호출하고,
# CRITICAL 판단 시 get_visa_status 추가 호출 여부도 스스로 결정
_VISA_RISK_TOOLS = [
    get_worker_profile,
    get_visa_status,
    assess_visa_risk,
]

# 서브에이전트 2: 서류 우선순위 전담
# LLM이 get_document_status → assess_document_priority 순으로 호출하고,
# 누락 서류 CRITICAL 시 search_policy_documents 추가 호출 여부도 스스로 결정
_DOC_PRIORITY_TOOLS = [
    get_document_status,
    get_document_requirements,
    search_policy_documents,
    assess_document_priority,
]

# 오케스트레이터: CRITICAL 감지 시 handoff 초안 생성
_HANDOFF_TOOLS = [
    generate_expert_handoff_package_draft,
]

_VISA_RISK_SYSTEM_PROMPT = """당신은 비자 만료 위험도를 분석하는 전문 서브에이전트입니다.

분석 절차:
1. get_worker_profile로 근로자 기본 정보를 먼저 조회합니다.
2. assess_visa_risk를 호출해 비자 유형별 준비 기간과 계약 만료 교차 분석을 수행합니다.
3. risk_level이 CRITICAL 또는 HIGH이면 get_visa_status로 비자 상세 정보를 추가 조회합니다.
4. 분석이 완료되면 tool 호출을 멈춥니다.

제약:
- 비자 가능 여부를 확정하지 않습니다.
- 법률·노무 자문을 제공하지 않습니다.
- 위험도 수치와 날짜 근거만 제시합니다."""

_DOC_PRIORITY_SYSTEM_PROMPT = """당신은 서류 누락 우선순위를 분석하는 전문 서브에이전트입니다.

분석 절차:
1. get_document_status로 현재 제출된 서류 현황을 조회합니다.
2. assess_document_priority를 호출해 CRITICAL/SUPPLEMENTARY 분류를 수행합니다.
3. CRITICAL 누락 서류가 있으면 search_policy_documents로 공식 근거를 추가 조회합니다.
4. 분석이 완료되면 tool 호출을 멈춥니다.

제약:
- 비자 가능 여부를 확정하지 않습니다.
- 서류 현황과 우선순위 분류만 출력합니다.
- 공식 근거가 없으면 "공식 근거를 찾지 못했습니다. 행정사 검토 필요"라고 답합니다."""


def _invoke_tools_with_messages(
    response: Any,
    tools: list,
) -> tuple[list[dict], list[str], list[Citation], list[ToolMessage]]:
    """tool_calls를 실행하고 (tool_results, risk_flags, citations, tool_messages) 반환."""
    tool_results: list[dict] = []
    risk_flags: list[str] = []
    citations: list[Citation] = []
    tool_messages: list[ToolMessage] = []

    if not (hasattr(response, "tool_calls") and response.tool_calls):
        return tool_results, risk_flags, citations, tool_messages

    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id", tool_name)
        tool_fn = next((t for t in tools if t.name == tool_name), None)
        if not tool_fn:
            continue
        result = tool_fn.invoke(tool_args)
        if isinstance(result, dict):
            tool_results.append(result)
            risk_flags.extend(result.get("risk_flags", []))
            for c in result.get("citations", []):
                citations.append(Citation(**c) if isinstance(c, dict) else c)
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

    return tool_results, risk_flags, citations, tool_messages


def _tool_call_key(tool_call: dict[str, Any]) -> tuple[str, str]:
    return (
        str(tool_call.get("name", "")),
        repr(sorted((tool_call.get("args") or {}).items())),
    )


def _new_tool_calls(response: Any, seen_tool_calls: set[tuple[str, str]]) -> list[dict[str, Any]]:
    tool_calls = getattr(response, "tool_calls", None) or []
    new_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        key = _tool_call_key(tool_call)
        if key in seen_tool_calls:
            continue
        seen_tool_calls.add(key)
        new_calls.append(tool_call)
    return new_calls


def _format_rag_contexts(state: ForeignHiringState) -> str:
    contexts = getattr(state, "rag_contexts", None) or []
    lines: list[str] = []
    for context in contexts:
        if not isinstance(context, dict):
            continue
        title = context.get("title") or context.get("source_id") or "source"
        grade = context.get("evidence_grade") or context.get("grade") or "unknown"
        content = context.get("content") or context.get("text") or ""
        lines.append(f"- {title} ({grade}): {content}")
    return "\n".join(lines)


def _run_visa_risk_sub_agent(
    state: ForeignHiringState,
    worker_id: str,
    llm_base: ChatOpenAI,
) -> dict[str, Any]:
    """비자 위험도 전담 서브에이전트. LLM이 상황을 보고 tool 호출 여부를 판단한다."""
    llm = llm_base.bind_tools(_VISA_RISK_TOOLS)
    messages: list[Any] = [
        SystemMessage(content=_VISA_RISK_SYSTEM_PROMPT),
        HumanMessage(content=f"근로자 ID: {worker_id}"),
    ]
    tool_results: list[dict] = []
    risk_flags: list[str] = []
    citations: list[Citation] = []

    seen_tool_calls: set[tuple[str, str]] = set()

    try:
        for _ in range(4):  # 최대 4회 판단 루프
            response = llm.invoke(messages)
            messages.append(response)
            new_tool_calls = _new_tool_calls(response, seen_tool_calls)
            if not new_tool_calls:
                break
            response.tool_calls = new_tool_calls
            results, flags, cits, tool_msgs = _invoke_tools_with_messages(response, _VISA_RISK_TOOLS)
            tool_results.extend(results)
            risk_flags.extend(flags)
            citations.extend(cits)
            messages.extend(tool_msgs)

        risk_summary = " | ".join(risk_flags) if risk_flags else "위험 없음"
        result = {
            "sub_agent": "visa_risk_sub_agent",
            "summary": f"비자 위험도 분석 완료: {risk_summary}",
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
    """서류 우선순위 전담 서브에이전트. LLM이 상황을 보고 tool 호출 여부를 판단한다."""
    llm = llm_base.bind_tools(_DOC_PRIORITY_TOOLS)
    user_parts = [f"근로자 ID: {worker_id}, 케이스 유형: {case_type}"]
    rag_context = _format_rag_contexts(state)
    if rag_context:
        user_parts.append(f"참고 공식 문서:\n{rag_context}")
    messages: list[Any] = [
        SystemMessage(content=_DOC_PRIORITY_SYSTEM_PROMPT),
        HumanMessage(content="\n\n".join(user_parts)),
    ]
    tool_results: list[dict] = []
    risk_flags: list[str] = []
    citations: list[Citation] = []

    seen_tool_calls: set[tuple[str, str]] = set()

    try:
        for _ in range(4):  # 최대 4회 판단 루프
            response = llm.invoke(messages)
            messages.append(response)
            new_tool_calls = _new_tool_calls(response, seen_tool_calls)
            if not new_tool_calls:
                break
            response.tool_calls = new_tool_calls
            results, flags, cits, tool_msgs = _invoke_tools_with_messages(response, _DOC_PRIORITY_TOOLS)
            tool_results.extend(results)
            risk_flags.extend(flags)
            citations.extend(cits)
            messages.extend(tool_msgs)

        risk_summary = " | ".join(risk_flags) if risk_flags else "누락 없음"
        result = {
            "sub_agent": "document_priority_sub_agent",
            "summary": f"서류 우선순위 분석 완료: {risk_summary}",
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
        model=settings.openai_model,
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    _worker_id = worker_id or ""

    # 서브에이전트 1: 비자 위험도 (LLM 판단)
    risk_result = _run_visa_risk_sub_agent(state, _worker_id, llm_base)

    # 서브에이전트 2: 서류 우선순위 (LLM 판단)
    doc_result = _run_document_priority_sub_agent(state, _worker_id, llm_base)

    # 두 결과 병합
    all_tool_results = risk_result.get("tool_results", []) + doc_result.get("tool_results", [])
    all_risk_flags = risk_result.get("risk_flags", []) + doc_result.get("risk_flags", [])
    all_citations: list[Citation] = []
    for c in risk_result.get("citations", []) + doc_result.get("citations", []):
        all_citations.append(Citation(**c) if isinstance(c, dict) else c)

    # 오케스트레이터 LLM이 risk_flags 종합 검토 후 handoff 필요 여부 판단
    has_critical = any(
        "CRITICAL" in f or "긴급" in f or "신청 불가" in f for f in all_risk_flags
    )
    handoff_result: dict | None = None
    if _worker_id:
        llm_handoff = llm_base.bind_tools(_HANDOFF_TOOLS)
        handoff_msg = [
            SystemMessage(
                content=(
                    "서브에이전트 2개의 분석 결과를 검토하라. "
                    "CRITICAL 위험 또는 필수 서류 누락이 있으면 "
                    "generate_expert_handoff_package_draft를 호출해 행정사 패키지를 준비하라. "
                    "위험이 MEDIUM/LOW이고 서류도 완비됐으면 handoff 불필요 — tool을 호출하지 않는다."
                )
            ),
            HumanMessage(
                content=(
                    f"근로자 ID: {_worker_id}\n"
                    f"비자 위험도 요약: {risk_result.get('summary', '')}\n"
                    f"서류 우선순위 요약: {doc_result.get('summary', '')}\n"
                    f"위험 플래그: {all_risk_flags}"
                )
            ),
        ]
        try:
            handoff_response = llm_handoff.invoke(handoff_msg)
            h_results, h_flags, h_citations, _ = _invoke_tools_with_messages(
                handoff_response, _HANDOFF_TOOLS
            )
            all_tool_results.extend(h_results)
            all_risk_flags.extend(h_flags)
            all_citations.extend(h_citations)
            handoff_triggered = len(h_results) > 0
            handoff_result = {"tool_calls": len(h_results), "risk_flags": h_flags}
        except Exception as e:
            handoff_triggered = has_critical
            handoff_result = {"error": str(e)}
    else:
        handoff_triggered = False

    agent_result = {
        "agent": "visa_document_agent",
        "sub_agents": [
            {
                "name": risk_result.get("sub_agent"),
                "tool_calls": risk_result.get("tool_calls", 0),
                "risk_flags": risk_result.get("risk_flags", []),
                "tool_results": risk_result.get("tool_results", []),
            },
            {
                "name": doc_result.get("sub_agent"),
                "tool_calls": doc_result.get("tool_calls", 0),
                "risk_flags": doc_result.get("risk_flags", []),
                "tool_results": doc_result.get("tool_results", []),
            },
        ],
        "handoff_triggered": handoff_triggered,
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
