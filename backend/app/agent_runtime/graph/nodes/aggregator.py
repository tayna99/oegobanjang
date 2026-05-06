"""Aggregator: 여러 agent 결과와 RAG/tool 근거를 하나의 case output으로 합칩니다."""
from __future__ import annotations

from app.agent_runtime.graph.nodes.evidence_logger import make_event, log_event
from app.agent_runtime.schemas import EventType, ForeignHiringState, ToolStatus


def aggregator_node(state: ForeignHiringState) -> ForeignHiringState:
    agent_names = _dedupe(
        str(result.get("agent"))
        for result in state.agent_results
        if result.get("agent")
    )
    summaries = [
        {
            "agent": str(result.get("agent", "")),
            "summary": str(result.get("summary", "")),
        }
        for result in state.agent_results
        if result.get("summary")
    ]
    risk_flags = _dedupe(
        [
            *state.risk_flags,
            *[
                str(flag)
                for result in state.agent_results
                for flag in result.get("risk_flags", [])
            ],
            *[
                str(flag)
                for tool_result in state.tool_results
                for flag in tool_result.risk_flags
            ],
        ]
    )
    approval_required = bool(
        state.plan.requires_approval
        or any(bool(result.get("approval_required")) for result in state.agent_results)
        or any(
            tool_result.approval_required or tool_result.status == ToolStatus.NEEDS_APPROVAL
            for tool_result in state.tool_results
        )
    )
    citation_ids = _dedupe(
        [
            *[
                str(context.get("source_id"))
                for context in state.rag_contexts
                if context.get("source_id")
            ],
            *[
                citation.source_id
                for tool_result in state.tool_results
                for citation in tool_result.citations
            ],
        ]
    )
    risk_level = _risk_level(risk_flags=risk_flags, approval_required=approval_required)
    state.aggregated_output = {
        "agent_count": len(agent_names),
        "agents": agent_names,
        "summaries": summaries,
        "risk_flags": risk_flags,
        "risk_level": risk_level,
        "approval_required": approval_required,
        "citation_ids": citation_ids,
        "tool_count": len(state.tool_results),
        "rag_context_count": len(state.rag_contexts),
    }

    if risk_flags:
        event = make_event(
            event_type=EventType.RISK_FLAGGED,
            request_id=state.request_id,
            summary=f"Aggregator risk 분류: {risk_level}, risk {len(risk_flags)}건",
            step_name="aggregator",
            citation_ids=citation_ids,
            risk_level=risk_level,
        )
    else:
        event = make_event(
            event_type=EventType.TOOL_EXECUTED,
            request_id=state.request_id,
            summary=f"Aggregator 실행. agent {len(agent_names)}개 결과 통합",
            step_name="aggregator",
            citation_ids=citation_ids,
            risk_level=risk_level,
        )
    return log_event(state, event)


def _risk_level(*, risk_flags: list[str], approval_required: bool) -> str:
    joined = " ".join(risk_flags)
    if any(token in joined for token in ("긴급", "초과", "D-30", "D-day 30", "HIGH")):
        return "HIGH"
    if risk_flags or approval_required:
        return "MEDIUM"
    return "LOW"


def _dedupe(values) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped
