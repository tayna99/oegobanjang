from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend.app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
import backend.app.services.agent_service as agent_service_module
from backend.app.config import BACKEND_DIR, normalize_database_url
from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.services.agent_service import AgentRunRequest, run_agent


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
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def _message_payload(*, persist_result: bool | None = None) -> dict[str, Any]:
    input_payload: dict[str, Any] = {
        "task_type": "message_draft",
        "worker_id": "worker-demo-001",
        "company_id": "company-demo-001",
        "worker_name": "Nguyen",
        "language_code": "vi",
        "message_purpose": "safety_training_notice",
        "training_date": "2026-05-10",
        "training_time": "10:00",
        "location": "교육장",
        "contact_person": "담당자",
    }
    if persist_result is not None:
        input_payload["persist_result"] = persist_result
    return {
        "user_request": "베트남 근로자에게 안전교육 안내 메시지 작성해줘",
        "input_payload": input_payload,
    }


def _reply_payload(*, persist_result: bool = True) -> dict[str, Any]:
    return {
        "user_request": "베트남어 답변을 요약하고 서류 상태 업데이트 후보를 만들어줘",
        "input_payload": {
            "task_type": "worker_reply_summary",
            "worker_id": "worker-demo-001",
            "company_id": "company-demo-001",
            "language_code": "vi",
            "worker_reply": "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi.",
            "message_purpose": "document_reply",
            "persist_result": persist_result,
        },
    }


def _run(payload: dict[str, Any], db: Session) -> dict[str, Any]:
    response = run_agent(AgentRunRequest.model_validate(payload), db=db)
    return response.model_dump()


def test_relative_sqlite_url_is_normalized_from_backend_dir() -> None:
    normalized = normalize_database_url("sqlite:///./data/oegobanjang.sqlite3")
    expected_path = (BACKEND_DIR / "data/oegobanjang.sqlite3").resolve().as_posix()

    assert normalized == f"sqlite:///{expected_path}"


def test_persist_result_missing_does_not_write_db(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()

    body = _run(_message_payload(), db)

    assert body["agent_results"]["multilingual_contact_agent"]["status"] == "SUCCESS"
    assert body["persistence"]["enabled"] is False
    assert body["persistence"]["saved"] is False
    assert db.scalar(select(ContactMessage)) is None
    assert db.scalar(select(Approval)) is None
    assert db.scalar(select(EvidenceLog)) is None


def test_persist_result_true_without_worker_id_returns_clear_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()
    payload = _message_payload(persist_result=True)
    payload["input_payload"].pop("worker_id")

    body = _run(payload, db)

    assert body["persistence"]["enabled"] is False
    assert body["persistence"]["saved"] is False
    assert body["persistence"]["reason"] == "worker_id is required for persistence"
    assert db.scalar(select(ContactMessage)) is None
    assert db.scalar(select(Approval)) is None
    assert db.scalar(select(EvidenceLog)) is None


def test_persist_result_true_without_company_id_returns_clear_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()
    payload = _message_payload(persist_result=True)
    payload["input_payload"].pop("company_id")

    body = _run(payload, db)

    assert body["persistence"]["enabled"] is False
    assert body["persistence"]["saved"] is False
    assert body["persistence"]["reason"] == "company_id is required for persistence"
    assert db.scalar(select(ContactMessage)) is None
    assert db.scalar(select(Approval)) is None
    assert db.scalar(select(EvidenceLog)) is None


def test_message_draft_persist_result_true_writes_pending_records(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()

    body = _run(_message_payload(persist_result=True), db)

    persistence = body["persistence"]
    assert persistence["enabled"] is True
    assert persistence["saved"] is True
    assert persistence["contact_message_id"]
    assert persistence["approval_id"]
    assert persistence["evidence_log_ids"]

    message = db.get(ContactMessage, persistence["contact_message_id"])
    approval = db.get(Approval, persistence["approval_id"])
    logs = db.scalars(select(EvidenceLog)).all()

    assert message is not None
    assert message.company_id == "company-demo-001"
    assert message.status == "PENDING_APPROVAL"
    assert message.approval_required is True
    assert message.sent_at is None
    assert approval is not None
    assert approval.status == "PENDING"
    assert approval.target_type == "contact_message"
    assert logs
    assert all(log.company_id == "company-demo-001" for log in logs)
    assert all(message.korean_text not in log.summary for log in logs)
    assert all((message.translated_text or "") not in log.summary for log in logs)


def test_worker_reply_summary_persist_result_true_writes_candidate_approvals(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()
    payload = _reply_payload(persist_result=True)
    worker_reply = payload["input_payload"]["worker_reply"]

    body = _run(payload, db)

    persistence = body["persistence"]
    assert persistence["enabled"] is True
    assert persistence["saved"] is True
    assert persistence["status_update_candidate_ids"]
    assert persistence["approval_ids"]
    assert persistence["evidence_log_ids"]

    candidates = db.scalars(select(StatusUpdateCandidate)).all()
    approvals = db.scalars(select(Approval)).all()
    logs = db.scalars(select(EvidenceLog)).all()

    assert len(candidates) == len(approvals)
    assert candidates
    assert logs
    for candidate in candidates:
        assert candidate.company_id == "company-demo-001"
        assert candidate.status == "PENDING_REVIEW"
        assert candidate.manager_review_required is True
        assert candidate.approval_id
        assert candidate.status != "APPLIED"
    for approval in approvals:
        assert approval.status == "PENDING"
        assert approval.target_type == "status_update_candidate"
    assert all(log.company_id == "company-demo-001" for log in logs)
    assert worker_reply not in json.dumps([log.summary for log in logs], ensure_ascii=False)


def test_failed_agent_result_is_not_persisted(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()
    payload = _message_payload(persist_result=True)
    payload["input_payload"]["message_purpose"] = "unknown_purpose"

    body = _run(payload, db)

    result = body["agent_results"]["multilingual_contact_agent"]
    assert result["status"] == "FAILED"
    assert body["persistence"]["saved"] is False
    assert body["persistence"]["reason"] == "agent result is not successful"
    assert db.scalar(select(ContactMessage)) is None
    assert db.scalar(select(Approval)) is None
    assert db.scalar(select(EvidenceLog)) is None


def test_persistence_error_does_not_fail_successful_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )

    def broken_save(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database is unavailable")

    monkeypatch.setattr(
        agent_service_module,
        "save_message_draft_result",
        broken_save,
    )
    db = _db()

    body = _run(_message_payload(persist_result=True), db)

    result = body["agent_results"]["multilingual_contact_agent"]
    assert result["status"] == "SUCCESS"
    assert body["persistence"]["enabled"] is True
    assert body["persistence"]["saved"] is False
    assert body["persistence"]["reason"] == "persistence_error"
    assert "RuntimeError" in body["persistence"]["error"]


def test_persisted_outputs_do_not_contain_forbidden_finalization_markers(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_rag_tool,
    )
    db = _db()

    body = _run(_message_payload(persist_result=True), db)
    serialized = json.dumps(body, ensure_ascii=False)

    assert "auto_sent" not in serialized
    assert "status_finalized" not in serialized
    assert "government_submission" not in serialized
    message = db.get(ContactMessage, body["persistence"]["contact_message_id"])
    assert message is not None
    assert message.sent_at is None
