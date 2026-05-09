from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.agent_runtime.langchain_v1.schemas import ApprovalBlock, WorkBridgeAgentResponse
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.approval import Approval
from backend.app.models.runtime_state import AgentRuntimeStateSnapshot


class FakeAgent:
    async def ainvoke(self, payload, *, context=None):
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="상태 스냅샷 저장 테스트입니다.",
                detected_intents=["HIRING"],
                approval=ApprovalBlock(required=True, status="PENDING", reason="검토 필요"),
                blocked_reason="",
            )
        }


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


def _client_with_db_and_fake_agent(db: Session, monkeypatch) -> TestClient:
    async def fake_run_workflow(*args, **kwargs):
        from app.agent_runtime.langchain_v1.runtime import (
            normalize_runtime_input,
            run_langchain_v1_agent,
            to_foreign_hiring_state,
        )

        runtime_input = normalize_runtime_input(
            user_message=kwargs["user_message"],
            user_id=kwargs.get("user_id", ""),
            company_id=kwargs.get("company_id", ""),
            worker_id=kwargs.get("worker_id", ""),
            input_payload=kwargs.get("input_payload", {}),
        )
        state = await run_langchain_v1_agent(runtime_input, agent=FakeAgent())
        return to_foreign_hiring_state(state)

    def override_db():
        return db

    monkeypatch.setattr("backend.app.api.v1.agent.run_workflow", fake_run_workflow)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow, raising=False)
    app.dependency_overrides[get_sync_db] = override_db
    return TestClient(app)


def test_agent_run_persists_runtime_state_snapshot_and_redacts_pii(monkeypatch) -> None:
    runtime_state_store.clear()
    db = _db()
    client = _client_with_db_and_fake_agent(db, monkeypatch)

    try:
        response = client.post(
            "/api/v1/agent/run",
            json={
                "user_message": "010-1234-5678 M12345678 사업장 E-9 채용 준비해줘",
                "user_id": "manager-1",
                "company_id": "company-1",
            },
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    request_id = response.json()["request_id"]
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    assert snapshot is not None
    assert snapshot.company_id == "company-1"
    approval_payload = json.loads(snapshot.approval_json)
    approval = db.get(Approval, approval_payload["approval_id"])
    assert approval is not None
    assert approval.target_type == "agent_runtime_state_snapshot"
    assert approval.target_id == request_id
    assert approval.status == "PENDING"
    serialized = json.dumps(
        {
            "input": snapshot.input_json,
            "structured_response": snapshot.structured_response_json,
            "evidence": snapshot.evidence_events_json,
        },
        ensure_ascii=False,
    )
    assert "010-1234-5678" not in serialized
    assert "M12345678" not in serialized
    assert "[REDACTED]" in serialized


def test_agent_state_endpoint_falls_back_to_db_snapshot(monkeypatch) -> None:
    runtime_state_store.clear()
    db = _db()
    client = _client_with_db_and_fake_agent(db, monkeypatch)

    try:
        response = client.post(
            "/api/v1/agent/run",
            json={"user_message": "E-9 채용 준비해줘", "company_id": "company-1"},
        )
        assert response.status_code == 200, response.text
        request_id = response.json()["request_id"]
        runtime_state_store.clear()

        state_response = client.get(f"/api/v1/agent/state/{request_id}")
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert state_response.status_code == 200, state_response.text
    body = state_response.json()
    assert body["request_id"] == request_id
    assert body["structured_response"]["final_response"] == "상태 스냅샷 저장 테스트입니다."
    assert body["approval"]["status"] == "PENDING"
    assert body["approval"]["approval_id"]
