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

from app.agent_runtime.langchain_v1.schemas import (  # noqa: E402
    AgentRuntimeInput,
    ApprovalBlock,
    LangChainRuntimeState,
    WorkBridgeAgentResponse,
)
from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_sync_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.company import Company  # noqa: E402
from backend.app.models.worker import Worker  # noqa: E402
from backend.app.services.runtime_state_persistence_service import (  # noqa: E402
    save_runtime_state_snapshot,
)


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
    app.dependency_overrides[get_sync_db] = lambda: db
    return TestClient(app)


def _clear_client_override() -> None:
    app.dependency_overrides.pop(get_sync_db, None)


def _runtime_state(
    request_id: str,
    *,
    company_id: str = "company-metrics-001",
    blocked: bool = False,
    approval_pending: bool = True,
    retrieval_count: int = 2,
    model_duration_ms: float = 100.0,
    tool_duration_ms: float = 20.0,
) -> LangChainRuntimeState:
    approval = ApprovalBlock(
        required=approval_pending,
        status="PENDING" if approval_pending else "NOT_REQUIRED",
        reason="승인 대기" if approval_pending else "",
    )
    return LangChainRuntimeState(
        request_id=request_id,
        input=AgentRuntimeInput(
            request_id=request_id,
            user_message="Nguyen 체류 확인",
            user_id="manager-001",
            company_id=company_id,
        ),
        structured_response=WorkBridgeAgentResponse(
            final_response="요약",
            detected_intents=["VISA_CHECK"],
            approval=approval,
            blocked_reason="blocked" if blocked else "",
        ),
        approval=approval,
        evidence_events=[
            {
                "event_type": "tool_executed",
                "metadata": {"tool_name": "retrieve_workforce_materials", "duration_ms": tool_duration_ms},
            },
            {
                "event_type": "rag_retrieved",
                "metadata": {"retrieval_count": retrieval_count, "duration_ms": tool_duration_ms},
            },
            {
                "event_type": "final_response_generated",
                "metadata": {
                    "model_name": "fake-model",
                    "duration_ms": model_duration_ms,
                    "token_usage": {"input_tokens": 11, "output_tokens": 7},
                    "raw_content_hash": "abc123",
                    "parsing_error": "parse" if blocked else None,
                },
            },
        ],
    )


def test_company_level_metrics_summary_aggregates_redacted_runtime_counters() -> None:
    db = _db()
    save_runtime_state_snapshot(
        db,
        _runtime_state(
            "metrics-001",
            retrieval_count=3,
            model_duration_ms=120.0,
            tool_duration_ms=30.0,
        ),
    )
    save_runtime_state_snapshot(
        db,
        _runtime_state(
            "metrics-002",
            blocked=True,
            approval_pending=False,
            retrieval_count=5,
            model_duration_ms=80.0,
            tool_duration_ms=10.0,
        ),
    )
    save_runtime_state_snapshot(
        db,
        _runtime_state("metrics-other-company", company_id="company-other", retrieval_count=99),
    )
    db.commit()

    client = _client_with_db(db)
    try:
        response = client.get(
            "/api/v1/agent/metrics",
            headers={"X-Company-Id": "company-metrics-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_id"] == "company-metrics-001"
    assert body["summary"]["run_count"] == 2
    assert body["summary"]["retrieval_count"] == 8
    assert body["summary"]["blocked_count"] == 1
    assert body["summary"]["approval_pending_count"] == 1
    assert body["summary"]["provider_error_count"] == 1
    assert body["summary"]["avg_model_duration_ms"] == 100.0
    assert body["summary"]["avg_tool_duration_ms"] == 20.0
    serialized = json.dumps(body, ensure_ascii=False)
    assert "Nguyen" not in serialized
    assert "user_message" not in serialized


def test_agent_run_resolves_unique_worker_name_without_exposing_name(monkeypatch) -> None:
    db = _db()
    db.add(Company(id="company-worker-001", name="샘플테크", industry="제조", region="충북"))
    db.add(
        Worker(
            id="worker-001",
            company_id="company-worker-001",
            name="Nguyen Van A",
            status="ACTIVE",
        )
    )
    db.commit()
    captured = {}

    async def fake_run_workflow(**kwargs):
        captured.update(kwargs)
        from app.agent_runtime.schemas import ApprovalStatus, ForeignHiringState

        return ForeignHiringState(
            request_id="worker-lookup-run-001",
            final_response="근로자 정보를 확인했습니다.",
            approval=ApprovalStatus(required=False, status="NOT_REQUIRED"),
        )

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)

    client = _client_with_db(db)
    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "Nguyen 체류만료 확인해줘",
                "user_id": "manager-001",
                "company_id": "company-worker-001",
                "input_payload": {"worker_name": "Nguyen Van A"},
            },
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    assert captured["worker_id"] == "worker-001"
    assert captured["input_payload"]["worker_lookup_status"] == "matched"
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "Nguyen Van A" not in serialized


def test_agent_run_marks_worker_name_lookup_ambiguous_without_breaking_request(monkeypatch) -> None:
    db = _db()
    db.add(Company(id="company-worker-002", name="샘플테크", industry="제조", region="충북"))
    db.add_all(
        [
            Worker(
                id="worker-a",
                company_id="company-worker-002",
                name="Nguyen",
                status="ACTIVE",
            ),
            Worker(
                id="worker-b",
                company_id="company-worker-002",
                name="Nguyen",
                status="ACTIVE",
            ),
        ]
    )
    db.commit()
    captured = {}

    async def fake_run_workflow(**kwargs):
        captured.update(kwargs)
        from app.agent_runtime.schemas import ApprovalStatus, ForeignHiringState

        return ForeignHiringState(
            request_id="worker-lookup-ambiguous-001",
            final_response="추가 확인이 필요합니다.",
            approval=ApprovalStatus(required=True, status="PENDING"),
        )

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)

    client = _client_with_db(db)
    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "Nguyen 체류만료 확인해줘",
                "user_id": "manager-001",
                "company_id": "company-worker-002",
                "input_payload": {"worker_name": "Nguyen"},
            },
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    assert captured["worker_id"] == ""
    assert captured["input_payload"]["worker_lookup_status"] == "ambiguous"
    assert "worker_lookup_candidates" not in captured["input_payload"]
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "Nguyen" not in serialized
