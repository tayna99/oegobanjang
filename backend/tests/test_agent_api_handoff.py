from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend.app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
from backend.app.agent_runtime.schemas import ApprovalStatus, ForeignHiringState
from backend.app.agent_runtime.langchain_v1.contact_artifact_store import (
    save_contact_artifacts,
)
from backend.app.agent_runtime.langchain_v1.contact_subagents import (
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
)
from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft


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


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def _source_contact_message(
    db: Session,
    *,
    company_id: str = "company-1",
    worker_id: str = "worker-demo-001",
) -> ContactMessage:
    message = ContactMessage(
        company_id=company_id,
        worker_id=worker_id,
        message_purpose="document_reply",
        language_code="vi",
        korean_text="여권 사본 제출 요청 초안",
        translated_text="Vui lòng gửi bản sao hộ chiếu.",
        status="PENDING_APPROVAL",
        approval_required=True,
        sent_at=None,
    )
    db.add(message)
    db.flush()
    return message


def test_contact_runtime_response_includes_handoff_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        return ForeignHiringState(
            request_id="contact-normalized-state",
            final_response="다국어 메시지 초안은 담당자 승인 전 발송되지 않습니다.",
            handoff_package_draft={},
        )

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
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

    assert response.status_code == 200, response.text
    assert response.json()["handoff"] == {"available": False}


def test_langgraph_response_includes_handoff_unavailable_without_draft(monkeypatch) -> None:
    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        return ForeignHiringState(
            request_id="no-handoff-state",
            final_response="검토 결과입니다.",
            handoff_package_draft={},
        )

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "상태 확인해줘",
            "user_id": "user-1",
            "company_id": "company-1",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["handoff"] == {"available": False}


def test_langgraph_response_exposes_safe_handoff_summary_only(monkeypatch) -> None:
    worker_reply = "Tôi có hộ chiếu, ảnh mai gửi."
    translated_ko = "여권이 있고 사진은 내일 보내겠다는 답변입니다."
    message_body = "안녕하세요. 여권 사본을 제출해주세요."
    worker_id = "worker-demo-001"

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        return ForeignHiringState(
            request_id="handoff-state",
            final_response="전문가 검토용 handoff package 초안이 생성되었습니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
            handoff_package_draft={
                "package_type": "expert_handoff_draft",
                "approval_required": True,
                "approval": {"status": "PENDING"},
                "not_for_legal_judgment": True,
                "handoff_ready": False,
                "handoff_blockers": ["worker_context.visa_type 누락"],
                "raw_worker_reply_included": False,
                "full_translation_included": False,
                "message_body_included": False,
                "worker_reply": worker_reply,
                "translated_ko": translated_ko,
                "message_body": message_body,
                "worker_id": worker_id,
                "worker_name": "Nguyen Van A",
                "nationality": "Vietnam",
                "passport_number": "M12345678",
                "alien_registration_number": "900101-1234567",
                "phone": "010-1234-5678",
            },
        )

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "전문가 전달 초안 준비해줘",
            "user_id": "user-1",
            "company_id": "company-1",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handoff"] == {
        "available": True,
        "package_type": "expert_handoff_draft",
        "approval_required": True,
        "approval_status": "PENDING",
        "not_for_legal_judgment": True,
        "handoff_ready": False,
        "handoff_blockers": ["worker_context.visa_type 누락"],
        "raw_worker_reply_included": False,
        "full_translation_included": False,
        "message_body_included": False,
    }

    payload = json.dumps(body, ensure_ascii=False)
    assert worker_reply not in payload
    assert translated_ko not in payload
    assert message_body not in payload
    assert worker_id not in payload
    assert "Nguyen Van A" not in payload
    assert "Vietnam" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload


def test_langgraph_persist_result_saves_handoff_draft_and_returns_ids(monkeypatch) -> None:
    db = _db()

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        return ForeignHiringState(
            request_id="persisted-handoff-state",
            final_response="전문가 검토용 handoff package 초안이 생성되었습니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
            handoff_package_draft={
                "package_type": "expert_handoff_draft",
                "case_type": "stay_extension",
                "case_summary": {
                    "summary": "체류만료가 임박하여 서류 누락 여부 확인이 필요합니다.",
                    "risk_level": "HIGH",
                },
                "worker_summary": {
                    "masked_worker_id": "worker_***",
                    "visa_type": "E-9",
                    "stay_expires_at": "2026-06-01",
                    "contract_ends_at": "2026-05-25",
                },
                "document_summary": {"missing_documents": ["passport_copy"]},
                "contact_summary": {
                    "last_contact_summary": "근로자가 사진 추후 제출 의사를 밝혔습니다.",
                    "message_draft_exists": True,
                    "raw_worker_reply_included": False,
                    "full_translation_included": False,
                },
                "evidence": {
                    "citation_ids": ["gov24_stay_extension"],
                    "evidence_log_ids": [],
                    "not_for_legal_judgment": True,
                },
                "approval": {"approval_required": True, "status": "PENDING"},
                "approval_required": True,
                "not_for_legal_judgment": True,
                "raw_worker_reply_included": False,
                "full_translation_included": False,
                "message_body_included": False,
                "handoff_ready": True,
                "handoff_blockers": [],
                "risk_flags": ["D-30 임박"],
            },
        )

    def override_db():
        return db

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    app.dependency_overrides[get_sync_db] = override_db
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "전문가 전달 초안 준비해줘",
                "user_id": "manager-demo",
                "company_id": "company-1",
                "worker_id": "worker-demo-001",
                "persist_result": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handoff"]["available"] is True
    assert body["handoff"]["draft_id"]
    assert body["handoff"]["approval_id"]
    assert body["handoff"]["approval_status"] == "PENDING"

    draft = db.get(HandoffPackageDraft, body["handoff"]["draft_id"])
    approval = db.get(Approval, body["handoff"]["approval_id"])
    assert draft is not None
    assert draft.status == "PENDING_APPROVAL"
    assert draft.company_id == "company-1"
    assert draft.transferred_at is None
    assert approval.status == "PENDING"
    assert approval.target_type == "handoff_package_draft"

    payload = json.dumps(body, ensure_ascii=False)
    assert "worker-demo-001" not in payload
    assert "passport_number" not in payload
    assert "Tôi có hộ chiếu" not in payload


def test_langchain_response_persists_contact_message_artifact_with_handoff(
    monkeypatch,
) -> None:
    db = _db()
    request_id = "persisted-contact-handoff-state"
    korean_text = "여권 사본을 제출해 주세요."
    translated_text = "Vui lòng gửi bản sao hộ chiếu."

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        save_contact_artifacts(
            request_id,
            {
                CONTACT_ONBOARDING_SUB_AGENT: {
                    "status": "SUCCESS",
                    "worker_id": "worker-demo-001",
                    "message_purpose": "passport_request",
                    "language_code": "vi",
                    "korean_text": korean_text,
                    "translated_text": translated_text,
                    "approval_required": True,
                    "sent": False,
                    "sent_at": None,
                    "citations": [],
                    "risk_flags": [],
                    "evidence_events": [
                        {
                            "event_type": "message_draft_created",
                            "agent_name": "multilingual_contact_agent",
                            "summary": "다국어 메시지 초안을 생성했습니다.",
                            "source_ids": [],
                            "approval_required": True,
                        }
                    ],
                }
            },
        )
        return ForeignHiringState(
            request_id=request_id,
            final_response="전문가 검토용 handoff package와 다국어 메시지 초안이 생성되었습니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
            handoff_package_draft={
                "package_type": "expert_handoff_draft",
                "case_type": "stay_extension",
                "case_summary": {"summary": "서류 확인 필요", "risk_level": "MEDIUM"},
                "worker_summary": {"masked_worker_id": "worker_***", "visa_type": "E-9"},
                "document_summary": {"missing_documents": ["passport_copy"]},
                "contact_summary": {
                    "last_contact_summary": "메시지 초안 생성",
                    "message_draft_exists": True,
                    "raw_worker_reply_included": False,
                    "full_translation_included": False,
                },
                "evidence": {
                    "citation_ids": [],
                    "evidence_log_ids": [],
                    "not_for_legal_judgment": True,
                },
                "approval": {"approval_required": True, "status": "PENDING"},
                "approval_required": True,
                "not_for_legal_judgment": True,
                "raw_worker_reply_included": False,
                "full_translation_included": False,
                "message_body_included": False,
                "handoff_ready": True,
                "handoff_blockers": [],
                "risk_flags": [],
            },
        )

    def override_db():
        return db

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    app.dependency_overrides[get_sync_db] = override_db
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "전문가 전달 초안과 베트남어 여권 요청 메시지를 준비해줘",
                "user_id": "manager-demo",
                "company_id": "company-1",
                "worker_id": "worker-demo-001",
                "persist_result": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    persistence = body["persistence"]
    assert persistence["enabled"] is True
    assert persistence["saved"] is True
    assert persistence["handoff"]["saved"] is True
    assert persistence["contact_message"]["saved"] is True
    assert persistence["contact_message"]["id"]
    assert persistence["contact_message"]["approval_id"]
    assert persistence["status_update_candidates"]["saved"] is False

    message = db.get(ContactMessage, persistence["contact_message"]["id"])
    approval = db.get(Approval, persistence["contact_message"]["approval_id"])
    logs = db.scalars(select(EvidenceLog)).all()

    assert message is not None
    assert message.status == "PENDING_APPROVAL"
    assert message.approval_required is True
    assert message.sent_at is None
    assert approval is not None
    assert approval.status == "PENDING"
    assert approval.target_type == "contact_message"
    assert any(log.company_id == "company-1" for log in logs)
    assert all(korean_text not in log.summary for log in logs)
    assert all(translated_text not in log.summary for log in logs)

    payload = json.dumps(body, ensure_ascii=False)
    assert korean_text not in payload
    assert translated_text not in payload
    assert "worker-demo-001" not in payload
    assert "M12345678" not in payload


def test_langchain_response_persists_worker_reply_status_candidates(
    monkeypatch,
) -> None:
    db = _db()
    request_id = "persisted-worker-reply-state"
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        save_contact_artifacts(
            request_id,
            {
                WORKER_REPLY_INTERPRETER_SUB_AGENT: {
                    "status": "SUCCESS",
                    "worker_id": "worker-demo-001",
                    "language_code": "vi",
                    "translated_ko": translated_ko,
                    "summary_ko": "여권 보유, 사진은 내일 제출 예정",
                    "translation_provider": "rule_based",
                    "status_update_candidates": [
                        {
                            "target_type": "worker_document",
                            "field": "passport_copy",
                            "candidate_status": "SUBMITTED",
                            "confidence": "MEDIUM",
                            "summary": "여권 사본 보유 가능성이 있습니다.",
                            "is_final": False,
                        }
                    ],
                    "approval_required": True,
                    "manager_review_required": True,
                    "status_applied": False,
                    "risk_flags": [],
                    "evidence_events": [
                        {
                            "event_type": "worker_reply_summarized",
                            "agent_name": "multilingual_contact_agent",
                            "summary": "근로자 답변을 요약하고 상태 업데이트 후보를 생성했습니다.",
                            "source_ids": [],
                            "approval_required": True,
                        }
                    ],
                }
            },
        )
        return ForeignHiringState(
            request_id=request_id,
            final_response="근로자 답변 요약과 상태 업데이트 후보를 생성했습니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
        )

    def override_db():
        return db

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    app.dependency_overrides[get_sync_db] = override_db
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "Nguyen Van A가 베트남어로 답변했어. 답변을 요약하고 상태 업데이트 후보를 만들어줘.",
                "user_id": "manager-demo",
                "company_id": "company-1",
                "worker_id": "worker-demo-001",
                "persist_result": True,
                "input_payload": {
                    "language_code": "vi",
                    "task_type": "worker_reply_summary",
                    "message_purpose": "document_reply",
                    "worker_reply": worker_reply,
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    status_persistence = body["persistence"]["status_update_candidates"]
    assert status_persistence["saved"] is True
    assert status_persistence["ids"]
    assert status_persistence["approval_ids"]

    candidate = db.get(StatusUpdateCandidate, status_persistence["ids"][0])
    approval = db.get(Approval, status_persistence["approval_ids"][0])
    logs = db.scalars(select(EvidenceLog)).all()

    assert candidate is not None
    assert candidate.status == "PENDING_REVIEW"
    assert candidate.manager_review_required is True
    assert candidate.reviewed_at is None
    assert candidate.status != "APPLIED"
    assert approval is not None
    assert approval.status == "PENDING"
    assert approval.target_type == "status_update_candidate"
    assert all(worker_reply not in log.summary for log in logs)
    assert all(translated_ko not in log.summary for log in logs)

    payload = json.dumps(body, ensure_ascii=False)
    assert worker_reply not in payload
    assert translated_ko not in payload
    assert "worker-demo-001" not in payload


def test_worker_reply_status_candidates_link_valid_source_message(
    monkeypatch,
) -> None:
    db = _db()
    source_message = _source_contact_message(db)
    response = _post_worker_reply_status_candidate_request(
        monkeypatch,
        db,
        request_id="valid-source-message-state",
        source_message_id=source_message.id,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    status_persistence = body["persistence"]["status_update_candidates"]
    assert status_persistence["saved"] is True
    assert status_persistence["source_message_id"] == source_message.id
    assert status_persistence["ids"]

    candidate = db.get(StatusUpdateCandidate, status_persistence["ids"][0])
    approval = db.get(Approval, status_persistence["approval_ids"][0])
    assert candidate is not None
    assert candidate.source_message_id == source_message.id
    assert candidate.status == "PENDING_REVIEW"
    assert candidate.status != "APPLIED"
    assert approval is not None
    assert approval.status == "PENDING"


def test_worker_reply_status_candidates_allow_missing_source_message_id(
    monkeypatch,
) -> None:
    db = _db()
    response = _post_worker_reply_status_candidate_request(
        monkeypatch,
        db,
        request_id="no-source-message-state",
    )

    assert response.status_code == 200, response.text
    status_persistence = response.json()["persistence"]["status_update_candidates"]
    assert status_persistence["saved"] is True
    assert "source_message_id" not in status_persistence

    candidate = db.get(StatusUpdateCandidate, status_persistence["ids"][0])
    assert candidate is not None
    assert candidate.source_message_id is None
    assert candidate.status == "PENDING_REVIEW"


@pytest.mark.parametrize(
    ("source_message", "source_message_id", "expected_reason"),
    [
        (None, "missing-message", "source_message_id not found"),
        (
            {"company_id": "other-company", "worker_id": "worker-demo-001"},
            "created",
            "source_message_id company mismatch",
        ),
        (
            {"company_id": "company-1", "worker_id": "other-worker"},
            "created",
            "source_message_id worker mismatch",
        ),
    ],
)
def test_worker_reply_status_candidates_reject_invalid_source_message_scope(
    monkeypatch,
    source_message: dict[str, str] | None,
    source_message_id: str,
    expected_reason: str,
) -> None:
    db = _db()
    if source_message is not None:
        message = _source_contact_message(db, **source_message)
        source_message_id = message.id

    response = _post_worker_reply_status_candidate_request(
        monkeypatch,
        db,
        request_id=f"invalid-source-message-{expected_reason}",
        source_message_id=source_message_id,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    status_persistence = body["persistence"]["status_update_candidates"]
    assert status_persistence == {
        "saved": False,
        "reason": expected_reason,
        "ids": [],
        "approval_ids": [],
    }
    assert db.scalars(select(StatusUpdateCandidate)).all() == []
    assert db.scalars(
        select(Approval).where(Approval.target_type == "status_update_candidate")
    ).all() == []
    payload = json.dumps(body, ensure_ascii=False)
    assert "worker-demo-001" not in payload
    assert "Tôi có hộ chiếu" not in payload
    assert "여권은 있고 사진은 내일 보낼 수 있습니다." not in payload


def _post_worker_reply_status_candidate_request(
    monkeypatch,
    db: Session,
    *,
    request_id: str,
    source_message_id: str | None = None,
):
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."

    async def fake_run_workflow(*args, **kwargs) -> ForeignHiringState:
        save_contact_artifacts(
            request_id,
            {
                WORKER_REPLY_INTERPRETER_SUB_AGENT: {
                    "status": "SUCCESS",
                    "worker_id": "worker-demo-001",
                    "language_code": "vi",
                    "translated_ko": translated_ko,
                    "summary_ko": "여권 보유, 사진은 내일 제출 예정",
                    "translation_provider": "rule_based",
                    "status_update_candidates": [
                        {
                            "target_type": "worker_document",
                            "field": "passport_copy",
                            "candidate_status": "SUBMITTED",
                            "confidence": "MEDIUM",
                            "summary": "여권 사본 보유 가능성이 있습니다.",
                            "is_final": False,
                        }
                    ],
                    "approval_required": True,
                    "manager_review_required": True,
                    "status_applied": False,
                    "risk_flags": [],
                    "evidence_events": [
                        {
                            "event_type": "worker_reply_summarized",
                            "agent_name": "multilingual_contact_agent",
                            "summary": "근로자 답변을 요약하고 상태 업데이트 후보를 생성했습니다.",
                            "source_ids": [],
                            "approval_required": True,
                        }
                    ],
                }
            },
        )
        return ForeignHiringState(
            request_id=request_id,
            final_response="근로자 답변 요약과 상태 업데이트 후보를 생성했습니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
        )

    def override_db():
        return db

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    app.dependency_overrides[get_sync_db] = override_db
    client = TestClient(app)

    payload = {
        "language_code": "vi",
        "task_type": "worker_reply_summary",
        "message_purpose": "document_reply",
        "worker_reply": worker_reply,
    }
    if source_message_id is not None:
        payload["source_message_id"] = source_message_id
    try:
        return client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "Nguyen Van A가 베트남어로 답변했어. 답변을 요약하고 상태 업데이트 후보를 만들어줘.",
                "user_id": "manager-demo",
                "company_id": "company-1",
                "worker_id": "worker-demo-001",
                "persist_result": True,
                "input_payload": payload,
            },
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)
