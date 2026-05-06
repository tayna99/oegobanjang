from app.agent_runtime.graph.nodes.approval_gate import approval_gate_node
from app.agent_runtime.graph.nodes.planner import planner_node
from app.agent_runtime.schemas import ForeignHiringState, Intent


def test_contact_intent_requires_human_approval() -> None:
    state = ForeignHiringState(
        request_id="approval-case",
        user_message="근로자에게 비자 만료 안내 문자를 보내줘",
        detected_intents=[Intent.CONTACT],
    )

    planned = planner_node(state)
    approved = approval_gate_node(planned)

    assert approved.plan.requires_approval is True
    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert any(event.event_type == "approval_requested" for event in approved.evidence_events)


def test_auto_submission_intent_is_not_planned_for_execution() -> None:
    state = ForeignHiringState(
        request_id="blocked-auto-submit",
        user_message="정부 포털에 비자 신청을 자동 제출해줘",
        detected_intents=[Intent.UNSUPPORTED_AUTO_SUBMISSION],
    )

    planned = planner_node(state)

    assert planned.plan.required_agents == []
    assert planned.plan.blocked is True
    assert "UNSUPPORTED_AUTO_SUBMISSION" in planned.plan.blocked_reasons
