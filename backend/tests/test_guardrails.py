from app.agent_runtime.graph.nodes.approval_gate import approval_gate_node
from app.agent_runtime.graph.nodes.planner import planner_node
from app.agent_runtime.schemas import (
    ForeignHiringState,
    Intent,
    ToolContractLevel,
    ToolResult,
    ToolStatus,
)


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


def test_expert_handoff_transfer_waits_for_approval() -> None:
    state = ForeignHiringState(
        request_id="expert-handoff-transfer",
        aggregated_output={
            "approval_required": True,
            "approval_reasons": ["expert_handoff_transfer"],
        },
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "expert_handoff_transfer" in approved.approval.reason


def test_external_export_waits_for_approval() -> None:
    state = ForeignHiringState(
        request_id="external-export",
        aggregated_output={
            "approval_required": True,
            "approval_reasons": ["external_export"],
        },
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "external_export" in approved.approval.reason


def test_government_submission_waits_for_approval_when_present_in_aggregation() -> None:
    state = ForeignHiringState(
        request_id="government-submission",
        aggregated_output={
            "approval_required": True,
            "approval_reasons": ["government_submission"],
        },
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "government_submission" in approved.approval.reason


def test_case_completion_waits_for_approval() -> None:
    state = ForeignHiringState(
        request_id="case-completion",
        aggregated_output={
            "approval_required": True,
            "approval_reasons": ["case_completion"],
        },
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "case_completion" in approved.approval.reason


def test_status_update_apply_waits_for_approval() -> None:
    state = ForeignHiringState(
        request_id="status-update-apply",
        aggregated_output={
            "approval_required": True,
            "approval_reasons": ["status_update_apply"],
        },
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "status_update_apply" in approved.approval.reason


def test_approval_required_tool_result_waits_for_approval() -> None:
    state = ForeignHiringState(
        request_id="tool-needs-approval",
        tool_results=[
            ToolResult(
                tool_name="send_expert_package",
                tool_grade=ToolContractLevel.APPROVAL_REQUIRED,
                status=ToolStatus.NEEDS_APPROVAL,
                approval_required=True,
            )
        ],
    )

    approved = approval_gate_node(state)

    assert approved.approval.required is True
    assert approved.approval.status == "PENDING"
    assert "send_expert_package" in approved.approval.reason
