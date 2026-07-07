from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.evidence import EvidenceLog


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


def _client_with_db(db: Session) -> TestClient:
    def override_db():
        return db

    app.dependency_overrides[get_sync_db] = override_db
    return TestClient(app)


def _clear_client_override() -> None:
    app.dependency_overrides.pop(get_sync_db, None)


def _add_log(
    db: Session,
    *,
    request_id: str,
    company_id: str,
    event_type: str = "tool_executed",
    summary: str = "도구 실행 요약",
    source_ids: list[str] | None = None,
    risk_flags: list[str] | None = None,
    worker_id: str | None = "worker-sensitive-001",
    approval_id: str | None = None,
) -> EvidenceLog:
    log = EvidenceLog(
        event_type=event_type,
        agent_name="langchain_v1",
        tool_name="retrieve_workforce_materials",
        summary=summary,
        source_ids=json.dumps(source_ids or ["eps_employer_process"], ensure_ascii=False),
        approval_required=False,
        risk_flags=json.dumps(risk_flags or [], ensure_ascii=False),
        request_id=request_id,
        company_id=company_id,
        worker_id=worker_id,
        approval_id=approval_id,
    )
    db.add(log)
    db.flush()
    return log


def test_evidence_api_lists_logs_by_request_and_company_without_sensitive_ids() -> None:
    db = _db()
    first = _add_log(
        db,
        request_id="request-001",
        company_id="company-001",
        event_type="intent_classified",
    )
    second = _add_log(
        db,
        request_id="request-001",
        company_id="company-001",
        event_type="final_response_generated",
        approval_id="approval-001",
    )
    _add_log(db, request_id="request-001", company_id="company-other")
    _add_log(db, request_id="request-other", company_id="company-001")
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/evidence",
            params={"request_id": "request-001"},
            headers={"X-Company-Id": "company-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request_id"] == "request-001"
    assert body["count"] == 2
    assert [item["id"] for item in body["items"]] == [first.id, second.id]
    assert body["items"][1]["approval_id"] == "approval-001"

    payload = json.dumps(body, ensure_ascii=False)
    assert "worker-sensitive-001" not in payload
    assert "contact_message_id" not in payload
    assert "status_update_candidate_id" not in payload


def test_evidence_api_requires_company_header() -> None:
    db = _db()
    _add_log(db, request_id="request-001", company_id="company-001")
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/evidence",
            params={"request_id": "request-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 403


def test_evidence_api_redacts_pii_even_if_stored_log_contains_it() -> None:
    db = _db()
    _add_log(
        db,
        request_id="request-001",
        company_id="company-001",
        summary="010-1234-5678 M12345678 원문 없이 처리됨",
        source_ids=["eps_employer_process", "M12345678"],
        risk_flags=["010-1234-5678 확인 필요"],
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/evidence",
            params={"request_id": "request-001"},
            headers={"X-Company-Id": "company-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    payload = json.dumps(response.json(), ensure_ascii=False)
    assert "010-1234-5678" not in payload
    assert "M12345678" not in payload
    assert "[REDACTED]" in payload
