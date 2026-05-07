"""Handoff Package node: 고위험/전문가 전달 케이스에 draft만 생성합니다."""
from __future__ import annotations

from app.agent_runtime.graph.nodes.evidence_logger import make_event, log_event
from app.agent_runtime.schemas import EventType, ForeignHiringState
from app.agent_runtime.tools.safe_draft import (
    build_handoff_package_draft_from_aggregated_output,
)

_HANDOFF_APPROVAL_REASONS = {
    "expert_handoff_package_draft",
    "expert_handoff_transfer",
}


def handoff_package_node(state: ForeignHiringState) -> ForeignHiringState:
    if not _should_create_handoff_package(state.aggregated_output):
        return state

    state.handoff_package_draft = build_handoff_package_draft_from_aggregated_output(
        state.aggregated_output,
        company_context=state.company_context,
        worker_context=state.worker_context,
    )
    citation_ids = state.handoff_package_draft.get("evidence", {}).get("citation_ids") or []
    event = make_event(
        event_type=EventType.HANDOFF_PACKAGE_DRAFT_CREATED,
        request_id=state.request_id,
        summary="전문가 검토용 handoff package 초안이 생성되었습니다.",
        step_name="handoff_package",
        citation_ids=[str(source_id) for source_id in citation_ids],
        risk_level=str(state.aggregated_output.get("risk_level") or "MEDIUM"),
    )
    return log_event(state, event)


def _should_create_handoff_package(aggregated_output: dict) -> bool:
    if str(aggregated_output.get("risk_level", "")).upper() == "HIGH":
        return True
    approval_reasons = {str(reason) for reason in aggregated_output.get("approval_reasons") or []}
    return bool(approval_reasons & _HANDOFF_APPROVAL_REASONS)
