from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
from app.agent_runtime.langchain_v1.contact_subagents import (
    normalize_contact_subagents_payload,
    run_contact_onboarding_subagent,
    run_worker_reply_interpreter_subagent,
)
from app.agent_runtime.langchain_v1.tools import get_langchain_v1_tools


MOCK_CITATION = {
    "source_id": "mock_safety_source",
    "title": "Mock Safety Source",
    "publisher": "Mock Publisher",
    "doc_type": "safety",
    "evidence_grade": "B",
    "raw_path": "mock/path.html",
    "page_number": None,
    "citation_label": "Mock Publisher, Mock Safety Source",
}


def _mock_rag_tool(payload: Any) -> SimpleNamespace:
    return SimpleNamespace(citations=[MOCK_CITATION], risk_flags=[])


def test_contact_onboarding_subagent_creates_safe_draft(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )

    result = run_contact_onboarding_subagent(
        worker_id="worker-demo-001",
        worker_name="Nguyen",
        language_code="vi",
        message_purpose="safety_training_notice",
        user_request="베트남어 안전교육 안내 메시지 초안 생성",
        training_date="2026-05-10",
        training_time="10:00",
        location="교육장",
        contact_person="담당자",
    )

    assert result["sub_agent"] == "contact_onboarding_subagent"
    assert result["tool_grade"] == "SAFE_DRAFT"
    assert result["status"] == "SUCCESS"
    assert result["korean_text"]
    assert result["translated_text"]
    assert result["citations"]
    assert result["risk_flags"] == []
    assert result["evidence_events"]
    assert result["approval_required"] is True
    assert result["sent"] is False


def test_worker_reply_interpreter_subagent_creates_non_final_candidates() -> None:
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    result = run_worker_reply_interpreter_subagent(
        worker_id="worker-demo-001",
        language_code="vi",
        worker_reply=worker_reply,
    )

    assert result["sub_agent"] == "worker_reply_interpreter_subagent"
    assert result["tool_grade"] == "SAFE_DRAFT"
    assert result["status"] == "SUCCESS"
    assert result["translated_ko"]
    assert result["translation_provider"] == "rule_based"
    assert result["summary_ko"]
    assert result["status_update_candidates"]
    assert all(
        candidate["is_final"] is False
        for candidate in result["status_update_candidates"]
    )
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True
    assert result["status_applied"] is False

    evidence_payload = json.dumps(result["evidence_events"], ensure_ascii=False)
    assert worker_reply not in evidence_payload
    assert result["translated_ko"] not in evidence_payload


def test_langchain_v1_tool_list_includes_contact_subagent_tools() -> None:
    tool_names = {tool.name for tool in get_langchain_v1_tools()}

    assert "run_contact_onboarding" in tool_names
    assert "run_worker_reply_interpreter" in tool_names
    assert "generate_multilingual_message_draft" in tool_names


def test_normalize_contact_subagents_payload_converts_list_to_safe_dict() -> None:
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."
    domain_payload = {
        "contact_subagents": [
            {
                "sub_agent": "contact_onboarding_subagent",
                "status": "PENDING",
                "approval_required": True,
                "worker_id": "worker-demo-raw-001",
                "korean_text": "여권 사본을 2026-05-15까지 보내주세요.",
                "translated_text": "Vui lòng gửi bản sao hộ chiếu.",
                "risk_flags": [],
            },
            {
                "sub_agent": "worker_reply_interpreter_subagent",
                "status": "PENDING",
                "approval_required": True,
                "manager_review_required": True,
                "status_update_candidates": [{"is_final": False}],
                "worker_reply": worker_reply,
                "translated_ko": translated_ko,
                "phone": "010-1234-5678",
                "passport_number": "M12345678",
                "alien_registration_number": "900101-1234567",
                "risk_flags": [],
            },
        ]
    }

    normalized = normalize_contact_subagents_payload(domain_payload)
    contact_subagents = normalized["contact_subagents"]
    onboarding = contact_subagents["contact_onboarding_subagent"]
    interpreter = contact_subagents["worker_reply_interpreter_subagent"]

    assert isinstance(contact_subagents, dict)
    assert onboarding == {
        "status": "SUCCESS",
        "approval_required": True,
        "approval_status": "PENDING",
        "risk_flags": [],
    }
    assert interpreter["status"] == "SUCCESS"
    assert interpreter["approval_required"] is True
    assert interpreter["approval_status"] == "PENDING"
    assert interpreter["manager_review_required"] is True
    assert interpreter["status_update_candidate_count"] == 1

    payload_json = json.dumps(normalized, ensure_ascii=False)
    for forbidden in (
        worker_reply,
        translated_ko,
        "여권 사본을 2026-05-15까지 보내주세요.",
        "Vui lòng gửi bản sao hộ chiếu.",
        "worker-demo-raw-001",
        "010-1234-5678",
        "M12345678",
        "900101-1234567",
    ):
        assert forbidden not in payload_json
