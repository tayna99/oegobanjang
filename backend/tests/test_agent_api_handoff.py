from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend.app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
from backend.app.agent_runtime.schemas import ApprovalStatus, ForeignHiringState
from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.approval import Approval
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
