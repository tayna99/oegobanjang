"""Phase 3a stub: approval_required=True인 경우 승인 대기 상태로 전환합니다.
실제 Human-in-the-loop 처리는 Phase 3b에서 구현합니다."""
from app.agent_runtime.schemas import (
    ApprovalStatus,
    EventType,
    ForeignHiringState,
    ToolContractLevel,
    ToolStatus,
)
from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event


_APPROVAL_REQUIRED_ACTIONS = {
    "worker_message_send",
    "expert_handoff_transfer",
    "external_export",
    "government_submission",
    "case_completion",
    "status_update_apply",
}


def approval_gate_node(state: ForeignHiringState) -> ForeignHiringState:
    aggregated_requires_approval = bool(state.aggregated_output.get("approval_required"))
    approval_reasons = _approval_reasons(state)
    if state.plan.requires_approval or aggregated_requires_approval or approval_reasons:
        state.approval = ApprovalStatus(
            required=True,
            status="PENDING",
            reason=_approval_reason_text(approval_reasons),
        )
        event = make_event(
            event_type=EventType.APPROVAL_REQUESTED,
            request_id=state.request_id,
            summary=f"승인 필요 작업 감지. 담당자 확인 대기 중. 사유: {state.approval.reason}",
            step_name="approval_gate",
            risk_level="MEDIUM",
        )
        return log_event(state, event)

    state.approval = ApprovalStatus(required=False, status="NOT_REQUIRED")
    return state


def _approval_reasons(state: ForeignHiringState) -> list[str]:
    reasons: list[str] = []
    for reason in state.aggregated_output.get("approval_reasons") or []:
        text = str(reason)
        if text:
            reasons.append(text)

    for tool_result in state.tool_results:
        if (
            tool_result.approval_required
            or tool_result.status == ToolStatus.NEEDS_APPROVAL
            or tool_result.tool_grade == ToolContractLevel.APPROVAL_REQUIRED
        ):
            reasons.append(tool_result.tool_name)

    if state.plan.requires_approval:
        reasons.append("plan_requires_approval")

    if state.aggregated_output.get("approval_required") and not reasons:
        reasons.append("aggregated_output_requires_approval")

    protected_actions = [
        reason for reason in reasons if reason in _APPROVAL_REQUIRED_ACTIONS
    ]
    return _dedupe([*protected_actions, *reasons])


def _approval_reason_text(reasons: list[str]) -> str:
    if not reasons:
        return "담당자 승인 후 실행 가능한 작업이 포함되어 있습니다."
    joined = ", ".join(reasons)
    return f"담당자 승인 후 실행 가능한 작업이 포함되어 있습니다: {joined}"


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
