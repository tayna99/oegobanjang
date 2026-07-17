"""오케스트레이션 계약(enum·레지스트리) 스냅샷 — 값이 바뀌면 의도적 변경인지 확인해야 한다."""

from __future__ import annotations

from oe_rag.orchestration.contracts import (
    APPROVAL_REQUIRED_ACTIONS,
    APPROVAL_REQUIRED_TOOLS,
    AUTO_ACTION_BLOCKLIST,
    FORBIDDEN_TOOL_NAMES,
    EventType,
    Intent,
    ToolContractLevel,
    ToolResult,
    ToolStatus,
)


def test_intent_enum_has_exactly_legacy_eight() -> None:
    assert {i.value for i in Intent} == {
        "HIRING",
        "VISA_CHECK",
        "DOCUMENT_CHECK",
        "CONTACT",
        "BRIEFING",
        "UNSUPPORTED_VALUE_JUDGMENT",
        "UNSUPPORTED_LEGAL_JUDGMENT",
        "UNSUPPORTED_AUTO_SUBMISSION",
    }


def test_tool_contract_has_five_levels() -> None:
    assert {l.value for l in ToolContractLevel} == {
        "SAFE_READ",
        "SAFE_CALCULATE",
        "SAFE_DRAFT",
        "APPROVAL_REQUIRED",
        "FORBIDDEN",
    }


def test_event_type_covers_presentation_six() -> None:
    presentation_six = {
        "intent_classified",
        "rag_retrieved",
        "tool_executed",
        "risk_flagged",
        "approval_requested",
        "final_response_generated",
    }
    assert presentation_six <= {e.value for e in EventType}
    assert len(EventType) == 9


def test_approval_action_registry_is_canonical() -> None:
    assert APPROVAL_REQUIRED_TOOLS == (
        "send_worker_message",
        "send_expert_package",
        "update_case_status_completed",
    )
    assert AUTO_ACTION_BLOCKLIST == (
        "auto_send_to_candidate",
        "auto_send_to_sending_agency",
        "auto_send_to_admin_scrivener",
        "auto_submit_to_government_portal",
    )
    assert set(APPROVAL_REQUIRED_ACTIONS) == set(APPROVAL_REQUIRED_TOOLS) | set(AUTO_ACTION_BLOCKLIST)


def test_forbidden_tools_are_never_registered_anywhere() -> None:
    """FORBIDDEN 등급 tool은 등록 자체 금지 — rag 소스 전체에 해당 이름의 @tool이 없어야 한다."""
    import pathlib

    src_root = pathlib.Path(__file__).resolve().parents[1] / "src" / "oe_rag"
    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN_TOOL_NAMES:
            if f"def {name}(" in text:
                offenders.append(f"{path.name}:{name}")
    assert not offenders, f"FORBIDDEN tool이 정의됨: {offenders}"


def test_tool_result_defaults() -> None:
    result = ToolResult(
        tool_name="get_worker_profile",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
    )
    assert result.approval_required is False
    assert result.citations == []
    assert result.risk_flags == []
