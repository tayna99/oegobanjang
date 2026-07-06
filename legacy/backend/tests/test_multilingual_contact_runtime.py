from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend.app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
import backend.app.services.agent_service as agent_service_module
from backend.app.agent_runtime.agents.multilingual_contact_agent import (
    MessageDraftInput,
    MultilingualContactAgent,
    WorkerReplySummaryInput,
)
from backend.app.main import app
from backend.app.agent_runtime.translation.translator import MockTranslationProvider


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
FORBIDDEN_OUTPUT_MARKERS = (
    "auto_sent",
    "sent=true",
    "status_finalized",
    "status_updated",
    "government_submission",
    "legal_judgment",
    "visa_approved",
)


def _mock_rag_tool(payload: Any) -> SimpleNamespace:
    return SimpleNamespace(citations=[MOCK_CITATION], risk_flags=[])


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    return TestClient(app)


def _post_agent(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    del client
    return agent_service_module.run_agent(
        agent_service_module.AgentRunRequest(
            user_request=payload["user_request"],
            input_payload=payload.get("input_payload", {}),
        ),
        db=None,
    ).model_dump()


def _contact_result(body: dict[str, Any]) -> dict[str, Any]:
    return body["agent_results"]["multilingual_contact_agent"]


def _assert_no_forbidden_runtime_markers(body: dict[str, Any]) -> None:
    serialized = json.dumps(body, ensure_ascii=False)
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        assert marker not in serialized
    assert '"sent": true' not in serialized


def _assert_message_draft_success(body: dict[str, Any], language_code: str) -> None:
    result = _contact_result(body)
    assert body["intent"] == "CONTACT"
    assert body["task_type"] == "message_draft"
    assert result["status"] == "SUCCESS"
    assert result["language_code"] == language_code
    assert result["korean_text"]
    assert result["translated_text"]
    assert result["citations"]
    assert result["citations"][0]["evidence_grade"] == "B"
    assert body["evidence_events"]
    assert result["approval_required"] is True
    assert body["approval"]["required"] is True
    assert body["approval"]["status"] == "PENDING"
    assert "담당자 승인" in body["final_response"]
    _assert_no_forbidden_runtime_markers(body)


def test_vi_safety_message_draft_runtime(monkeypatch) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "베트남 근로자에게 안전교육 안내 메시지 작성해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-001",
                "worker_name": "Nguyen",
                "language_code": "vi",
                "message_purpose": "safety_training_notice",
                "training_date": "2026-05-10",
                "training_time": "10:00",
                "location": "교육장",
                "contact_person": "담당자",
            },
        },
    )

    _assert_message_draft_success(body, "vi")


def test_id_safety_message_draft_runtime(monkeypatch) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "인도네시아 근로자에게 안전교육 안내 메시지 작성해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-002",
                "worker_name": "Budi",
                "language_code": "id",
                "message_purpose": "safety_training_notice",
                "training_date": "2026-05-10",
                "training_time": "10:00",
                "location": "교육장",
                "contact_person": "담당자",
            },
        },
    )

    _assert_message_draft_success(body, "id")


def test_vi_worker_reply_summary_creates_candidates_without_logging_raw_reply(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    body = _post_agent(
        client,
        {
            "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
            "input_payload": {
                "task_type": "worker_reply_summary",
                "worker_id": "worker-demo-001",
                "language_code": "vi",
                "worker_reply": worker_reply,
                "message_purpose": "document_reply",
            },
        },
    )

    result = _contact_result(body)
    assert body["intent"] == "CONTACT"
    assert body["task_type"] == "worker_reply_summary"
    assert result["status"] == "SUCCESS"
    assert result["translated_ko"]
    assert result["translation_provider"] == "rule_based"
    assert result["summary_ko"]
    assert result["status_update_candidates"]
    candidate_types = {
        candidate["candidate_type"]
        for candidate in result["status_update_candidates"]
    }
    assert "passport_received_candidate" in candidate_types
    assert "photo_pending_candidate" in candidate_types
    assert "expected_submission_date_candidate" in candidate_types
    assert all(
        "candidate" in candidate["candidate_type"]
        and candidate["is_final"] is False
        for candidate in result["status_update_candidates"]
    )
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True
    assert body["approval"]["required"] is True
    assert body["approval"]["status"] == "PENDING"
    evidence_payload = json.dumps(body["evidence_events"], ensure_ascii=False)
    assert worker_reply not in evidence_payload
    assert result["translated_ko"] not in evidence_payload
    _assert_no_forbidden_runtime_markers(body)


def test_worker_reply_summary_without_llm_option_uses_rule_based_provider(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."

    body = _post_agent(
        client,
        {
            "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
            "input_payload": {
                "task_type": "worker_reply_summary",
                "worker_id": "worker-demo-001",
                "language_code": "vi",
                "worker_reply": worker_reply,
            },
        },
    )

    result = _contact_result(body)
    assert result["translation_provider"] == "rule_based"
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True


def test_worker_reply_summary_with_llm_false_uses_rule_based_provider(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."

    body = _post_agent(
        client,
        {
            "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
            "input_payload": {
                "task_type": "worker_reply_summary",
                "worker_id": "worker-demo-001",
                "language_code": "vi",
                "worker_reply": worker_reply,
                "use_llm_translation": False,
            },
        },
    )

    result = _contact_result(body)
    assert result["translation_provider"] == "rule_based"
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True


def test_worker_reply_summary_with_llm_true_uses_injected_provider(
    monkeypatch,
) -> None:
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."
    provider = MockTranslationProvider(
        {("vi", "ko", "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."): translated_ko}
    )
    monkeypatch.setattr(
        agent_service_module,
        "LLMTranslationProvider",
        lambda: provider,
    )
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."

    body = _post_agent(
        client,
        {
            "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
            "input_payload": {
                "task_type": "worker_reply_summary",
                "worker_id": "worker-demo-001",
                "language_code": "vi",
                "worker_reply": worker_reply,
                "use_llm_translation": True,
            },
        },
    )

    result = _contact_result(body)
    evidence_payload = json.dumps(body["evidence_events"], ensure_ascii=False)
    assert result["translation_provider"] == "mock"
    assert result["translated_ko"] == translated_ko
    assert worker_reply not in evidence_payload
    assert translated_ko not in evidence_payload
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True


def test_worker_reply_summary_with_llm_true_without_api_key_falls_back(
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."

    body = _post_agent(
        client,
        {
            "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
            "input_payload": {
                "task_type": "worker_reply_summary",
                "worker_id": "worker-demo-001",
                "language_code": "vi",
                "worker_reply": worker_reply,
                "use_llm_translation": True,
            },
        },
    )

    result = _contact_result(body)
    evidence_payload = json.dumps(body["evidence_events"], ensure_ascii=False)
    assert result["translation_provider"] == "rule_based_fallback"
    assert "LLM_TRANSLATION_UNAVAILABLE" in result["risk_flags"]
    assert worker_reply not in evidence_payload
    assert result["translated_ko"] not in evidence_payload
    assert result["approval_required"] is True
    assert result["manager_review_required"] is True


def test_send_now_request_stays_draft_and_adds_approval_risk_flag(monkeypatch) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "Nguyen에게 베트남어로 바로 발송해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-001",
                "worker_name": "Nguyen",
                "language_code": "vi",
                "message_purpose": "safety_training_notice",
                "training_date": "2026-05-10",
                "training_time": "10:00",
                "location": "교육장",
                "contact_person": "담당자",
            },
        },
    )

    _assert_message_draft_success(body, "vi")
    result = _contact_result(body)
    assert "APPROVAL_REQUIRED_FOR_SEND" in result["risk_flags"]
    assert "APPROVAL_REQUIRED_FOR_SEND" in body["risk_flags"]


def test_message_draft_with_llm_option_keeps_template_translation(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "베트남 근로자에게 안전교육 안내 메시지 작성해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-001",
                "worker_name": "Nguyen",
                "language_code": "vi",
                "message_purpose": "safety_training_notice",
                "training_date": "2026-05-10",
                "training_time": "10:00",
                "location": "교육장",
                "contact_person": "담당자",
                "use_llm_translation": True,
            },
        },
    )

    result = _contact_result(body)
    assert result["status"] == "SUCCESS"
    assert result["translated_text"]
    assert result.get("translation_provider") is None
    assert "LLM_TRANSLATION_NOT_APPLIED_TO_MESSAGE_DRAFT" in result["risk_flags"]


def test_unknown_message_purpose_fails_with_template_not_found(monkeypatch) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "베트남 근로자에게 안내 메시지 작성해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-001",
                "worker_name": "Nguyen",
                "language_code": "vi",
                "message_purpose": "unknown_purpose",
                "contact_person": "담당자",
            },
        },
    )

    result = _contact_result(body)
    assert result["status"] == "FAILED"
    assert "TEMPLATE_NOT_FOUND" in result["risk_flags"]


def test_missing_required_placeholder_fails_with_missing_required_field(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "베트남 근로자에게 안전교육 안내 메시지 작성해줘",
            "input_payload": {
                "task_type": "message_draft",
                "worker_id": "worker-demo-001",
                "worker_name": "Nguyen",
                "language_code": "vi",
                "message_purpose": "safety_training_notice",
                "training_time": "10:00",
                "contact_person": "담당자",
            },
        },
    )

    result = _contact_result(body)
    assert result["status"] == "FAILED"
    assert "MISSING_REQUIRED_FIELD" in result["risk_flags"]


def test_natural_language_vi_message_request_is_extracted_and_runs(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "Nguyen한테 베트남어로 5월 10일 10시에 교육장에서 안전교육 있다고 안내 메시지 만들어줘",
            "input_payload": {
                "worker_id": "worker-demo-001",
                "contact_person": "담당자",
            },
        },
    )

    _assert_message_draft_success(body, "vi")
    result = _contact_result(body)
    assert "5월 10일" in result["korean_text"]
    assert "10시" in result["korean_text"]
    assert "교육장" in result["korean_text"]


def test_natural_language_worker_reply_summary_is_extracted(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    body = _post_agent(
        client,
        {
            "user_request": f"이 베트남어 답변 요약하고 서류 상태 후보 만들어줘: {worker_reply}",
            "input_payload": {
                "worker_id": "worker-demo-001",
            },
        },
    )

    result = _contact_result(body)
    assert body["task_type"] == "worker_reply_summary"
    assert result["status"] == "SUCCESS"
    assert result["summary_ko"]
    assert result["status_update_candidates"]
    evidence_payload = json.dumps(body["evidence_events"], ensure_ascii=False)
    assert worker_reply not in evidence_payload
    assert result["translated_ko"] not in evidence_payload
    _assert_no_forbidden_runtime_markers(body)


def test_natural_language_send_request_keeps_approval_required_flag(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)

    body = _post_agent(
        client,
        {
            "user_request": "Nguyen에게 베트남어로 5월 10일 10시에 교육장에서 안전교육 바로 발송해줘",
            "input_payload": {
                "worker_id": "worker-demo-001",
                "contact_person": "담당자",
            },
        },
    )

    _assert_message_draft_success(body, "vi")
    assert "APPROVAL_REQUIRED_FOR_SEND" in body["risk_flags"]
    assert "APPROVAL_REQUIRED_FOR_SEND" in _contact_result(body)["risk_flags"]


def test_message_draft_reflects_quality_checker_risk_flags(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    template_path = tmp_path / "message_templates.csv"
    template_path.write_text(
        "\n".join(
            [
                "purpose,target_language,korean_text,translated_text,required_fields,approval_required,review_status",
                "missing_document_request,vi,서류를 제출해 주세요. 문의는 {contact_person}에게 해 주세요.,Vui lòng nộp hồ sơ. Hãy liên hệ {contact_person}.,contact_person,true,approved",
            ]
        ),
        encoding="utf-8",
    )
    agent = MultilingualContactAgent(template_path=template_path)

    result = agent.generate_message_draft(
        MessageDraftInput(
            worker_id="worker-demo-001",
            language_code="vi",
            message_purpose="missing_document_request",
            due_date="2026-05-10",
            contact_person="담당자",
            user_request="서류 요청 메시지 작성",
            privacy_purpose="외국인 고용 업무 및 서류 확인",
        )
    )

    assert result.status == "SUCCESS"
    assert "PRIVACY_PURPOSE_MISSING" in result.risk_flags
    assert "DEADLINE_MISSING" in result.risk_flags
    assert "TRANSLATION_QUALITY_REVIEW_REQUIRED" in result.risk_flags


def test_message_draft_localizes_korean_placeholder_values(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    template_path = tmp_path / "message_templates.csv"
    template_path.write_text(
        "\n".join(
            [
                "purpose,target_language,korean_text,translated_text,required_fields,approval_required,review_status",
                "passport_request,vi,여권 사본을 {due_date}까지 보내주세요. 이 정보는 {privacy_purpose} 목적으로만 사용됩니다. 준비가 어려우면 {contact_person}에게 알려주세요.,Vui lòng gửi bản sao hộ chiếu trước {due_date}. Thông tin này chỉ được sử dụng cho mục đích {privacy_purpose}. Nếu bạn gặp khó khăn khi chuẩn bị vui lòng báo cho {contact_person}.,due_date|privacy_purpose|contact_person,true,approved",
            ]
        ),
        encoding="utf-8",
    )
    agent = MultilingualContactAgent(template_path=template_path)

    result = agent.generate_message_draft(
        MessageDraftInput(
            worker_id="worker-demo-001",
            language_code="vi",
            message_purpose="passport_request",
            due_date="2026-05-20",
            contact_person="김대리",
            user_request="여권 사본 요청 메시지 작성",
            privacy_purpose="외국인 고용 업무 및 서류 확인",
        )
    )

    assert result.status == "SUCCESS"
    assert result.korean_text
    assert "외국인 고용 업무 및 서류 확인" in result.korean_text
    assert "김대리" in result.korean_text
    assert result.translated_text
    assert "외국인 고용 업무 및 서류 확인" not in result.translated_text
    assert "김대리" not in result.translated_text
    assert "kiểm tra hồ sơ" in result.translated_text
    assert "người phụ trách" in result.translated_text


def test_worker_reply_summary_with_provider_keeps_evidence_events_sanitized() -> None:
    worker_reply = "Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi."
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."
    provider = MockTranslationProvider(
        {("vi", "ko", worker_reply): translated_ko}
    )
    agent = MultilingualContactAgent(translation_provider=provider)

    result = agent.summarize_worker_reply(
        WorkerReplySummaryInput(
            worker_id="worker-demo-001",
            language_code="vi",
            worker_reply=worker_reply,
        )
    )

    evidence_payload = json.dumps(result.evidence_events, ensure_ascii=False)
    assert result.translated_ko == translated_ko
    assert worker_reply not in evidence_payload
    assert translated_ko not in evidence_payload
    assert result.approval_required is True
    assert result.manager_review_required is True
