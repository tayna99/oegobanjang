"""Phase 3a stub: approval_required=True인 경우 승인 대기 상태로 전환합니다.
실제 Human-in-the-loop 처리는 Phase 3b에서 구현합니다."""
from app.agent_runtime.schemas import ForeignHiringState, EventType, ApprovalStatus
from app.agent_runtime.graph.nodes.evidence_logger import make_event, log_event


def approval_gate_node(state: ForeignHiringState) -> ForeignHiringState:
    aggregated_requires_approval = bool(state.aggregated_output.get("approval_required"))
    if state.plan.requires_approval or aggregated_requires_approval:
        state.approval = ApprovalStatus(
            required=True,
            status="PENDING",
            reason="담당자 승인 후 실행 가능한 작업이 포함되어 있습니다.",
        )
        event = make_event(
            event_type=EventType.APPROVAL_REQUESTED,
            request_id=state.request_id,
            summary="승인 필요 작업 감지. 담당자 확인 대기 중.",
            step_name="approval_gate",
            risk_level="MEDIUM",
        )
        return log_event(state, event)

    state.approval = ApprovalStatus(required=False, status="NOT_REQUIRED")
    return state
