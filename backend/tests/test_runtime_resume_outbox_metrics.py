from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy import inspect as sqlalchemy_inspect
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
from backend.app.models.approval import Approval  # noqa: E402
from backend.app.models.evidence import EvidenceLog  # noqa: E402
from backend.app.models.runtime_execution import (  # noqa: E402
    AgentCheckpoint,
    ApprovalAction,
    DeliveryOutbox,
    RuntimeMetric,
)
from backend.app.models.runtime_state import (  # noqa: E402
    RUNTIME_STATE_TARGET_TYPE,
    AgentRuntimeStateSnapshot,
)
from backend.app.services.approval_service import approve_approval_for_company  # noqa: E402
from backend.app.services.runtime_resume_service import (  # noqa: E402
    BLOCKED_RESUME_ACTIONS,
    INTERNAL_RESUME_ACTIONS,
    RuntimeResumeForbiddenError,
    create_runtime_resume_plan,
    resume_runtime_action_for_company,
)
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
    def override_db():
        return db

    app.dependency_overrides[get_sync_db] = override_db
    return TestClient(app)


def _clear_client_override() -> None:
    app.dependency_overrides.pop(get_sync_db, None)


def _runtime_state(request_id: str = "runtime-resume-outbox-001") -> LangChainRuntimeState:
    approval = ApprovalBlock(
        required=True,
        status="PENDING",
        reason="외부 전달 전 담당자 승인이 필요합니다.",
        blocked_actions=["auto_send_to_admin_scrivener", "auto_submit_to_government_portal"],
    )
    return LangChainRuntimeState(
        request_id=request_id,
        input=AgentRuntimeInput(
            request_id=request_id,
            user_message="E-9 신규 채용 요청서와 행정사 확인 질문 준비",
            user_id="manager-001",
            company_id="company-001",
        ),
        structured_response=WorkBridgeAgentResponse(
            final_response="신규 채용 준비 초안입니다.",
            detected_intents=["HIRING"],
            approval=approval,
            evidence_events=[],
            domain_payload={"draft_id": "draft-001"},
        ),
        approval=approval,
        evidence_events=[
            {
                "event_type": "tool_executed",
                "tool_name": "retrieve_workforce_materials",
                "metadata": {"tool_name": "retrieve_workforce_materials", "duration_ms": 12.5},
            },
            {
                "event_type": "rag_retrieved",
                "metadata": {
                    "retrieval_count": 4,
                    "source_ids": ["eps_employer_process"],
                    "duration_ms": 12.5,
                },
            },
            {
                "event_type": "final_response_generated",
                "metadata": {
                    "model_name": "gpt-4o-mini",
                    "duration_ms": 87.2,
                    "token_usage": {"input_tokens": 100, "output_tokens": 40},
                    "parsing_error": None,
                },
            },
            {
                "event_type": "approval_requested",
                "metadata": {"reason": "외부 전달 전 승인 필요"},
            },
        ],
    )


def _runtime_approval(db: Session) -> Approval:
    approval = db.scalar(
        select(Approval).where(Approval.target_type == RUNTIME_STATE_TARGET_TYPE)
    )
    assert approval is not None
    return approval


def test_runtime_resume_outbox_metrics_migration_and_env_import(tmp_path, monkeypatch) -> None:
    migration_files = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT_DIR / "backend/migrations/versions").glob("*.py")
    )
    env_source = (ROOT_DIR / "backend/migrations/env.py").read_text(encoding="utf-8")

    assert "approval_actions" in migration_files
    assert "delivery_outbox" in migration_files
    assert "agent_checkpoints" in migration_files
    assert "runtime_metrics" in migration_files
    assert "ApprovalAction" in env_source
    assert "RuntimeMetric" in env_source

    db_path = tmp_path / "runtime-resume.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    config = Config(str(ROOT_DIR / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "backend/migrations"))

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    tables = set(sqlalchemy_inspect(engine).get_table_names())
    assert {"approval_actions", "delivery_outbox", "agent_checkpoints", "runtime_metrics"} <= tables

    command.downgrade(config, "base")
    tables_after_downgrade = set(sqlalchemy_inspect(engine).get_table_names())
    assert "approval_actions" not in tables_after_downgrade
    assert "runtime_metrics" not in tables_after_downgrade


def test_runtime_approval_creates_actions_outbox_checkpoint_metrics_and_evidence() -> None:
    db = _db()
    snapshot = save_runtime_state_snapshot(db, _runtime_state())
    approval = _runtime_approval(db)
    db.commit()

    approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-001",
        reviewed_by="manager-001",
        reason="검토 완료",
    )
    db.commit()

    actions = db.scalars(select(ApprovalAction).order_by(ApprovalAction.action_type)).all()
    action_by_type = {row.action_type: row for row in actions}
    assert set(INTERNAL_RESUME_ACTIONS) <= set(action_by_type)
    assert set(BLOCKED_RESUME_ACTIONS) <= set(action_by_type)
    assert action_by_type["finalize_internal_draft"].status == "COMPLETED"
    assert action_by_type["prepare_external_delivery"].status == "PENDING"
    assert action_by_type["auto_submit_to_government_portal"].status == "BLOCKED"

    outbox = db.scalar(select(DeliveryOutbox))
    assert outbox is not None
    assert outbox.request_id == snapshot.request_id
    assert outbox.status == "PENDING"
    assert outbox.outbox_type == "external_delivery_preparation"
    assert "auto_submit_to_government_portal" in json.loads(outbox.blocked_actions_json)

    checkpoint = db.scalar(select(AgentCheckpoint))
    assert checkpoint is not None
    assert checkpoint.request_id == snapshot.request_id
    assert checkpoint.approval_id == approval.id
    assert checkpoint.checkpoint_type == "approval_resume"
    assert checkpoint.status == "READY"
    assert "finalize_internal_draft" in json.loads(checkpoint.allowed_actions_json)
    assert "auto_send_to_candidate" in json.loads(checkpoint.blocked_actions_json)
    assert "auto_send_to_sending_agency" in json.loads(checkpoint.blocked_actions_json)

    metrics = db.scalars(select(RuntimeMetric)).all()
    metric_types = {row.metric_type for row in metrics}
    assert {"tool_call", "rag_retrieval", "model_call", "run_summary"} <= metric_types
    summary_metric = next(row for row in metrics if row.metric_type == "run_summary")
    assert summary_metric.retrieval_count == 4
    assert summary_metric.approval_pending_count == 1

    event_types = [
        row.event_type
        for row in db.scalars(
            select(EvidenceLog).where(EvidenceLog.approval_id == approval.id)
        )
    ]
    assert "approval_action_created" in event_types
    assert "delivery_outbox_queued" in event_types
    assert "agent_checkpoint_created" in event_types


def test_runtime_resume_plan_is_idempotent_and_keeps_external_actions_blocked() -> None:
    db = _db()
    snapshot = save_runtime_state_snapshot(db, _runtime_state("runtime-idempotent-001"))
    approval = _runtime_approval(db)
    approval.status = "APPROVED"
    db.flush()

    first = create_runtime_resume_plan(db, snapshot=snapshot, approval=approval)
    second = create_runtime_resume_plan(db, snapshot=snapshot, approval=approval)

    assert first["checkpoint_id"] == second["checkpoint_id"]
    assert db.scalar(select(func.count()).select_from(AgentCheckpoint)) == 1
    assert db.scalar(select(func.count()).select_from(DeliveryOutbox)) == 1
    assert db.scalar(
        select(func.count())
        .select_from(ApprovalAction)
        .where(ApprovalAction.action_type == "auto_send_to_candidate")
    ) == 1
    assert db.scalar(
        select(func.count())
        .select_from(ApprovalAction)
        .where(ApprovalAction.action_type == "auto_send_to_sending_agency")
    ) == 1

    with pytest.raises(RuntimeResumeForbiddenError):
        resume_runtime_action_for_company(
            db,
            request_id=snapshot.request_id,
            action_type="auto_send_to_candidate",
            company_id="company-001",
        )


def test_agent_resume_api_allows_internal_actions_only() -> None:
    db = _db()
    save_runtime_state_snapshot(db, _runtime_state("runtime-resume-api-001"))
    approval = _runtime_approval(db)
    db.commit()
    approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-001",
        reviewed_by="manager-001",
    )
    db.commit()

    client = _client_with_db(db)
    try:
        allowed = client.post(
            "/api/v1/agent/resume/runtime-resume-api-001",
            headers={"X-Company-Id": "company-001"},
            json={"action_type": "finalize_internal_draft"},
        )
        blocked = client.post(
            "/api/v1/agent/resume/runtime-resume-api-001",
            headers={"X-Company-Id": "company-001"},
            json={"action_type": "auto_submit_to_government_portal"},
        )
        metrics = client.get(
            "/api/v1/agent/metrics/runtime-resume-api-001",
            headers={"X-Company-Id": "company-001"},
        )
    finally:
        _clear_client_override()

    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "COMPLETED"
    assert allowed.json()["external_delivery_executed"] is False
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "resume action forbidden"
    assert metrics.status_code == 200, metrics.text
    assert metrics.json()["request_id"] == "runtime-resume-api-001"
    assert metrics.json()["summary"]["retrieval_count"] == 4


def test_agent_resume_status_api_returns_safe_checkpoint_action_and_outbox_summary() -> None:
    db = _db()
    save_runtime_state_snapshot(db, _runtime_state("runtime-resume-status-001"))
    approval = _runtime_approval(db)
    db.commit()
    approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-001",
        reviewed_by="manager-001",
    )
    db.commit()

    client = _client_with_db(db)
    try:
        response = client.get(
            "/api/v1/agent/resume/runtime-resume-status-001",
            headers={"X-Company-Id": "company-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request_id"] == "runtime-resume-status-001"
    assert body["checkpoint"]["status"] == "READY"
    assert body["checkpoint"]["resume_token_present"] is True
    assert "resume_token" not in body["checkpoint"]
    assert body["outbox"]["status"] == "PENDING"
    assert body["outbox"]["external_delivery_executed"] is False
    assert set(body["allowed_actions"]) == set(INTERNAL_RESUME_ACTIONS)
    assert set(body["blocked_actions"]) == set(BLOCKED_RESUME_ACTIONS)
    assert body["actions"]["auto_submit_to_government_portal"]["status"] == "BLOCKED"
    assert body["actions"]["auto_send_to_sending_agency"]["status"] == "BLOCKED"


def test_internal_resume_action_writes_evidence_and_updates_checkpoint_without_sending() -> None:
    db = _db()
    save_runtime_state_snapshot(db, _runtime_state("runtime-resume-evidence-001"))
    approval = _runtime_approval(db)
    db.commit()
    approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-001",
        reviewed_by="manager-001",
    )
    db.commit()

    result = resume_runtime_action_for_company(
        db,
        request_id="runtime-resume-evidence-001",
        action_type="mark_handoff_package_ready",
        company_id="company-001",
    )
    db.commit()

    checkpoint = db.scalar(select(AgentCheckpoint))
    outbox = db.scalar(select(DeliveryOutbox))
    event_types = [
        row.event_type
        for row in db.scalars(
            select(EvidenceLog).where(EvidenceLog.approval_id == approval.id)
        )
    ]

    assert result["status"] == "COMPLETED"
    assert result["external_delivery_executed"] is False
    assert checkpoint.status == "INTERNAL_ACTION_COMPLETED"
    assert outbox.status == "PENDING"
    assert "resume_action_completed" in event_types
