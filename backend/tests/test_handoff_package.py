from __future__ import annotations

import json

from app.agent_runtime.graph.nodes.handoff_package import handoff_package_node
from app.agent_runtime.schemas import ForeignHiringState
from app.agent_runtime.tools.safe_draft import (
    build_handoff_package_draft_from_aggregated_output,
    generate_expert_handoff_package_draft,
)


def test_expert_handoff_package_is_draft_only_and_masks_worker_identity() -> None:
    worker_id = "650e8400-e29b-41d4-a716-446655440001"

    result = generate_expert_handoff_package_draft.invoke(
        {"worker_id": worker_id, "case_type": "stay_extension"}
    )

    assert result["status"] == "SUCCESS"
    assert result["approval_required"] is True
    assert result["input_snapshot"]["masked_worker_id"] == "worker_***"
    assert "worker_id" not in result["input_snapshot"]

    package = result["output"]
    payload = json.dumps(package, ensure_ascii=False)
    assert package["package_type"] == "expert_handoff_draft"
    assert package["approval_required"] is True
    assert package["approval"]["status"] == "PENDING"
    assert package["not_for_legal_judgment"] is True
    assert package["raw_worker_reply_included"] is False
    assert package["full_translation_included"] is False
    assert package["message_body_included"] is False
    assert package["worker_summary"]["masked_worker_id"] == "worker_***"
    assert "worker_id" not in package["worker_summary"]
    assert "name" not in package["worker_summary"]
    assert "nationality" not in package["worker_summary"]
    assert worker_id not in payload
    assert "Nguyen Van A" not in payload
    assert "Vietnam" not in payload


def test_aggregated_output_handoff_builder_uses_fallbacks_and_blockers() -> None:
    package = build_handoff_package_draft_from_aggregated_output(
        {
            "summaries": [
                {
                    "agent": "visa_document_agent",
                    "summary": "서류 누락 확인 필요",
                }
            ],
            "risk_flags": ["D-30 임박"],
            "risk_level": "HIGH",
            "approval_required": True,
            "citation_ids": ["gov24_stay_extension"],
        },
        worker_context={
            "worker_id": "worker-demo-001",
            "visa_expires_at": "2026-06-01",
            "contract_ends_at": "2026-05-25",
        },
    )

    assert package["package_type"] == "expert_handoff_draft"
    assert package["approval"]["status"] == "PENDING"
    assert package["handoff_ready"] is False
    assert "worker_context.visa_type 누락" in package["handoff_blockers"]
    assert package["key_findings"][0]["summary"] == "서류 누락 확인 필요"
    assert package["case_summary"]["risk_reasons"] == ["D-30 임박"]
    assert package["approval_reasons"] == ["approval_required_action"]
    assert package["worker_summary"]["masked_worker_id"] == "worker_***"


def test_handoff_package_node_creates_draft_for_high_risk() -> None:
    state = ForeignHiringState(
        request_id="high-risk-handoff",
        aggregated_output={
            "risk_level": "HIGH",
            "approval_required": True,
            "risk_flags": ["D-30 임박"],
            "citation_ids": ["gov24_stay_extension"],
            "summaries": [{"agent": "visa_document_agent", "summary": "D-30 임박"}],
        },
        worker_context={
            "worker_id": "worker-demo-001",
            "visa_type": "E-9",
            "visa_expires_at": "2026-06-01",
            "contract_ends_at": "2026-05-25",
        },
    )

    result = handoff_package_node(state)

    draft = result.handoff_package_draft
    assert draft["package_type"] == "expert_handoff_draft"
    assert draft["approval_required"] is True
    assert draft["approval"]["status"] == "PENDING"
    assert draft["not_for_legal_judgment"] is True
    assert draft["raw_worker_reply_included"] is False
    assert draft["full_translation_included"] is False
    assert draft["message_body_included"] is False
    assert any(
        event.event_type.value == "handoff_package_draft_created"
        for event in result.evidence_events
    )


def test_handoff_package_node_creates_draft_for_expert_handoff_reason() -> None:
    state = ForeignHiringState(
        request_id="expert-reason-handoff",
        aggregated_output={
            "risk_level": "MEDIUM",
            "approval_required": True,
            "approval_reasons": ["expert_handoff_package_draft"],
            "summaries": [{"agent": "visa_document_agent", "summary": "전문가 검토 필요"}],
        },
        worker_context={"visa_type": "E-9"},
    )

    result = handoff_package_node(state)

    assert result.handoff_package_draft["package_type"] == "expert_handoff_draft"


def test_handoff_package_node_skips_low_or_medium_general_cases() -> None:
    state = ForeignHiringState(
        request_id="general-medium-case",
        aggregated_output={
            "risk_level": "MEDIUM",
            "approval_required": True,
            "approval_reasons": ["worker_message_draft"],
            "summaries": [{"agent": "multilingual_contact_agent", "summary": "메시지 초안"}],
        },
    )

    result = handoff_package_node(state)

    assert result.handoff_package_draft == {}
    assert not any(
        event.event_type.value == "handoff_package_draft_created"
        for event in result.evidence_events
    )


def test_handoff_package_node_draft_excludes_sensitive_raw_text() -> None:
    worker_reply = "Tôi có hộ chiếu, ảnh mai gửi."
    translated_ko = "여권이 있고 사진은 내일 보내겠다는 답변입니다."
    message_body = "안녕하세요. 여권 사본을 제출해주세요."
    worker_id = "worker-demo-001"

    state = ForeignHiringState(
        request_id="sensitive-handoff",
        aggregated_output={
            "risk_level": "HIGH",
            "approval_required": True,
            "risk_flags": ["D-30 임박"],
            "summaries": [{"agent": "visa_document_agent", "summary": "고위험 케이스"}],
        },
        worker_context={
            "worker_id": worker_id,
            "worker_name": "Nguyen Van A",
            "nationality": "Vietnam",
            "visa_type": "E-9",
            "visa_expires_at": "2026-06-01",
            "contract_ends_at": "2026-05-25",
            "worker_reply": worker_reply,
            "translated_ko": translated_ko,
            "message_body": message_body,
            "passport_number": "M12345678",
            "alien_registration_number": "900101-1234567",
            "phone": "010-1234-5678",
        },
    )

    result = handoff_package_node(state)
    payload = json.dumps(result.handoff_package_draft, ensure_ascii=False)

    assert worker_reply not in payload
    assert translated_ko not in payload
    assert message_body not in payload
    assert worker_id not in payload
    assert "Nguyen Van A" not in payload
    assert "Vietnam" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload
