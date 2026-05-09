from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.agent_runtime.langchain_v1.runtime import (  # noqa: E402
    normalize_runtime_input,
    run_langchain_v1_agent,
)
from app.agent_runtime.langchain_v1.schemas import (  # noqa: E402
    ApprovalBlock,
    WorkBridgeAgentResponse,
)
from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_sync_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.approval import Approval  # noqa: E402
from backend.app.models.langchain_checkpoint import LangChainAgentCheckpoint  # noqa: E402
from backend.app.models.runtime_state import RUNTIME_STATE_TARGET_TYPE  # noqa: E402
from backend.app.services.approval_service import approve_approval_for_company  # noqa: E402
from backend.app.services.runtime_state_persistence_service import (  # noqa: E402
    save_runtime_state_snapshot,
)


class _CheckpointFakeAgent:
    def __init__(self, *, interrupt: bool = False) -> None:
        self.interrupt = interrupt
        self.last_config = None
        self.resume_payloads: list[object] = []

    async def ainvoke(self, payload, *, context=None, config=None):
        self.last_config = config
        if self.interrupt:
            return {"__interrupt__": (SimpleNamespace(id="interrupt-001", value="approval"),)}
        if payload.__class__.__name__ == "Command":
            self.resume_payloads.append(payload)
            return {
                "structured_response": WorkBridgeAgentResponse(
                    final_response="승인된 내부 action을 재개했습니다.",
                    detected_intents=["HIRING"],
                    approval=ApprovalBlock(required=True, status="APPROVED"),
                )
            }
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="checkpoint 테스트 응답입니다.",
                detected_intents=["HIRING"],
                approval=ApprovalBlock(required=True, status="PENDING"),
            )
        }

    def get_state(self, config):
        return SimpleNamespace(
            config={
                "configurable": {
                    "thread_id": config["configurable"]["thread_id"],
                    "checkpoint_ns": config["configurable"]["checkpoint_ns"],
                    "checkpoint_id": "checkpoint-001",
                }
            },
            tasks=(),
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


def _runtime_approval(db: Session) -> Approval:
    approval = db.scalar(
        select(Approval).where(Approval.target_type == RUNTIME_STATE_TARGET_TYPE)
    )
    assert approval is not None
    return approval


@pytest.mark.asyncio
async def test_runtime_records_langgraph_checkpoint_metadata_with_thread_id() -> None:
    fake_agent = _CheckpointFakeAgent()
    runtime_input = normalize_runtime_input(
        user_message="E-9 신규 채용 준비",
        user_id="manager-001",
        company_id="company-001",
        thread_id="thread-checkpoint-001",
    )

    state = await run_langchain_v1_agent(runtime_input, agent=fake_agent)

    assert fake_agent.last_config == {
        "configurable": {
            "thread_id": "thread-checkpoint-001",
            "checkpoint_ns": "workbridge_langchain_v1",
        }
    }
    assert state.checkpoint_metadata["thread_id"] == "thread-checkpoint-001"
    assert state.checkpoint_metadata["latest_checkpoint_id"] == "checkpoint-001"


@pytest.mark.asyncio
async def test_runtime_persists_interrupt_checkpoint_metadata_with_snapshot() -> None:
    db = _db()
    runtime_input = normalize_runtime_input(
        user_message="행정사 전달 전 승인 요청",
        user_id="manager-001",
        company_id="company-001",
        thread_id="thread-interrupt-001",
    )

    state = await run_langchain_v1_agent(runtime_input, agent=_CheckpointFakeAgent(interrupt=True))
    save_runtime_state_snapshot(db, state)
    db.commit()

    checkpoint = db.scalar(select(LangChainAgentCheckpoint))
    assert checkpoint is not None
    assert checkpoint.request_id == state.request_id
    assert checkpoint.thread_id == "thread-interrupt-001"
    assert checkpoint.checkpoint_ns == "workbridge_langchain_v1"
    assert checkpoint.latest_checkpoint_id == "checkpoint-001"
    assert checkpoint.interrupt_id == "interrupt-001"
    assert checkpoint.status == "INTERRUPTED"


@pytest.mark.asyncio
async def test_internal_checkpoint_resume_requires_approved_runtime_state_and_blocks_external_actions(
    monkeypatch,
) -> None:
    db = _db()
    fake_agent = _CheckpointFakeAgent()
    state = await run_langchain_v1_agent(
        normalize_runtime_input(
            user_message="내부 검토 패키지 준비",
            user_id="manager-001",
            company_id="company-001",
            thread_id="thread-resume-001",
        ),
        agent=fake_agent,
    )
    save_runtime_state_snapshot(db, state)
    approval = _runtime_approval(db)
    db.commit()
    approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-001",
        reviewed_by="manager-001",
    )
    db.commit()

    monkeypatch.setattr(
        "backend.app.services.langchain_checkpoint_service.create_workbridge_agent",
        lambda **kwargs: fake_agent,
        raising=False,
    )
    client = _client_with_db(db)
    try:
        allowed = client.post(
            f"/api/v1/agent/checkpoints/{state.request_id}/resume",
            headers={"X-Company-Id": "company-001"},
            json={"action_type": "finalize_internal_draft", "resume_value": "approved"},
        )
        blocked = client.post(
            f"/api/v1/agent/checkpoints/{state.request_id}/resume",
            headers={"X-Company-Id": "company-001"},
            json={"action_type": "auto_submit_to_government_portal"},
        )
    finally:
        _clear_client_override()

    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "RESUMED"
    assert allowed.json()["external_delivery_executed"] is False
    assert blocked.status_code == 403
    assert fake_agent.resume_payloads
    assert fake_agent.resume_payloads[0].__class__.__name__ == "Command"


def test_langchain_agent_checkpoint_migration_is_registered() -> None:
    env_source = (ROOT_DIR / "backend/migrations/env.py").read_text(encoding="utf-8")
    migration_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT_DIR / "backend/migrations/versions").glob("*.py")
    )

    assert "LangChainAgentCheckpoint" in env_source
    assert "langchain_agent_checkpoints" in migration_text
