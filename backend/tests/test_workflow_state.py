from __future__ import annotations

from app.agent_runtime.langchain_v1.middleware import build_blocked_response, redact_pii
from app.agent_runtime.langchain_v1.runtime import to_foreign_hiring_state
from app.agent_runtime.langchain_v1.schemas import (
    AgentRuntimeInput,
    ApprovalBlock,
    HandoffDraft,
    LangChainRuntimeState,
    WorkBridgeAgentResponse,
)


def test_runtime_redaction_masks_raw_pii() -> None:
    text = "연락처는 010-1234-5678, 여권번호는 M12345678입니다."

    redacted = redact_pii(text)

    assert "010-1234-5678" not in redacted
    assert "M12345678" not in redacted
    assert "[REDACTED]" in redacted


def test_blocked_response_does_not_echo_sensitive_input() -> None:
    response = build_blocked_response(
        reason="010-1234-5678 M12345678 자동 제출 금지",
        user_message="정부 포털에 바로 제출해줘",
    )

    dumped = response.model_dump_json()
    assert "010-1234-5678" not in dumped
    assert "M12345678" not in dumped
    assert response.approval.required is True


def test_final_response_handoff_notice_comes_from_safe_handoff_contract() -> None:
    runtime_state = LangChainRuntimeState(
        request_id="handoff-final",
        input=AgentRuntimeInput(
            request_id="handoff-final",
            user_message="전문가 검토 준비해줘",
            company_id="company-001",
        ),
        structured_response=WorkBridgeAgentResponse(
            final_response="handoff package 초안이 준비되었습니다. 자동 전달 없이 담당자 승인이 필요합니다.",
            detected_intents=["DOCUMENT_CHECK"],
            approval=ApprovalBlock(required=True, status="PENDING"),
            handoff=HandoffDraft(
                available=True,
                package_type="expert_handoff_draft",
                approval_required=True,
                approval_status="PENDING",
                payload={
                    "worker_reply": "Tôi có hộ chiếu, ảnh mai gửi.",
                    "worker_name": "Nguyen Van A",
                    "passport_number": "M12345678",
                },
            ),
        ),
        approval=ApprovalBlock(required=True, status="PENDING"),
    )

    compat = to_foreign_hiring_state(runtime_state)
    payload = compat.model_dump_json()

    assert "handoff package 초안" in compat.final_response
    assert "자동 전달" in compat.final_response
    assert "담당자 승인" in compat.final_response
    assert "Tôi có hộ chiếu" not in payload
    assert "Nguyen Van A" not in payload
    assert "M12345678" not in payload
