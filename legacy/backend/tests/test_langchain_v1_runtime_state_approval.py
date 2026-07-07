from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.agent_runtime.langchain_v1.schemas import (
    AgentRuntimeInput,
    ApprovalBlock,
    LangChainRuntimeState,
    WorkBridgeAgentResponse,
)
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft
from backend.app.models.runtime_state import RUNTIME_STATE_TARGET_TYPE, AgentRuntimeStateSnapshot
from backend.app.services.approval_service import (
    ApprovalForbiddenError,
    approve_approval_for_company,
    get_approval_detail_for_company,
    reject_approval_for_company,
)
from backend.app.services.runtime_state_persistence_service import (
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


def _runtime_state(*, request_id: str = "runtime-request-001") -> LangChainRuntimeState:
    approval = ApprovalBlock(
        required=True,
        status="PENDING",
        reason="외부 전달 전 담당자 검토가 필요합니다.",
        blocked_actions=["auto_send_to_sending_agency"],
    )
    return LangChainRuntimeState(
        request_id=request_id,
        input=AgentRuntimeInput(
            request_id=request_id,
            user_message="010-1234-5678 M12345678 E-9 신규 채용 요청서 만들어줘",
            user_id="manager-demo",
            company_id="company-runtime-001",
        ),
        structured_response=WorkBridgeAgentResponse(
            final_response="신규 채용 요청서 초안은 승인 전 외부 전달되지 않습니다.",
            detected_intents=["HIRING"],
            approval=approval,
            evidence_events=[],
        ),
        approval=approval,
        evidence_events=[
            {
                "event_type": "approval_requested",
                "summary": "외부 전달 전 담당자 승인 필요",
                "approval_required": True,
            }
        ],
        interrupt_metadata={
            "tool_name": "send_handoff_questions",
            "reason": "승인 전 외부 전달 금지",
        },
    )


def _runtime_approval(db: Session) -> Approval:
    approval = db.scalar(
        select(Approval).where(Approval.target_type == RUNTIME_STATE_TARGET_TYPE)
    )
    assert approval is not None
    return approval


def test_runtime_snapshot_save_creates_pending_approval_without_external_targets() -> None:
    db = _db()
    snapshot = save_runtime_state_snapshot(db, _runtime_state())
    db.commit()

    approval = _runtime_approval(db)
    assert approval.target_type == RUNTIME_STATE_TARGET_TYPE
    assert approval.target_id == snapshot.request_id
    assert approval.status == "PENDING"

    saved_snapshot = db.get(AgentRuntimeStateSnapshot, snapshot.request_id)
    approval_payload = json.loads(saved_snapshot.approval_json)
    assert approval_payload["approval_id"] == approval.id
    assert approval_payload["status"] == "PENDING"
    assert approval_payload["target_type"] == RUNTIME_STATE_TARGET_TYPE

    serialized = json.dumps(
        {
            "input": saved_snapshot.input_json,
            "approval": saved_snapshot.approval_json,
        },
        ensure_ascii=False,
    )
    assert "010-1234-5678" not in serialized
    assert "M12345678" not in serialized

    assert db.scalar(select(func.count()).select_from(ContactMessage)) == 0
    assert db.scalar(select(func.count()).select_from(HandoffPackageDraft)) == 0


def test_runtime_state_approval_updates_snapshot_only_without_resume_or_send() -> None:
    db = _db()
    snapshot = save_runtime_state_snapshot(db, _runtime_state())
    approval = _runtime_approval(db)
    db.commit()

    result = approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-runtime-001",
        reviewed_by="manager-demo",
        reason="검토 완료",
    )
    db.commit()

    assert result["approval_status"] == "APPROVED"
    assert result["target_status"] == "APPROVED"
    assert result["target_type"] == RUNTIME_STATE_TARGET_TYPE

    saved_snapshot = db.get(AgentRuntimeStateSnapshot, snapshot.request_id)
    approval_payload = json.loads(saved_snapshot.approval_json)
    structured_response = json.loads(saved_snapshot.structured_response_json)
    assert approval_payload["status"] == "APPROVED"
    assert approval_payload["reviewed_by"] == "manager-demo"
    assert structured_response["approval"]["status"] == "APPROVED"

    assert db.scalar(select(func.count()).select_from(ContactMessage)) == 0
    assert db.scalar(select(func.count()).select_from(HandoffPackageDraft)) == 0

    review_log = db.scalar(
        select(EvidenceLog).where(EvidenceLog.approval_id == approval.id)
    )
    assert review_log is not None
    assert review_log.event_type == "agent_runtime_state_approved"
    assert review_log.request_id == snapshot.request_id
    assert review_log.company_id == "company-runtime-001"


def test_runtime_state_approval_updates_hot_state_store() -> None:
    runtime_state_store.clear()
    db = _db()
    state = _runtime_state(request_id="runtime-request-hot-store-001")
    runtime_state_store.save(state)
    save_runtime_state_snapshot(db, state)
    approval = _runtime_approval(db)
    db.commit()

    result = approve_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-runtime-001",
        reviewed_by="manager-demo",
    )
    db.commit()

    assert result["approval_status"] == "APPROVED"
    saved_state = runtime_state_store.get(state.request_id)
    assert saved_state is not None
    assert saved_state.approval.status == "APPROVED"
    assert saved_state.structured_response.approval.status == "APPROVED"
    assert saved_state.structured_response.approval.required is True


def test_runtime_state_rejection_updates_snapshot_only() -> None:
    db = _db()
    snapshot = save_runtime_state_snapshot(
        db,
        _runtime_state(request_id="runtime-request-reject-001"),
    )
    approval = _runtime_approval(db)
    db.commit()

    result = reject_approval_for_company(
        db,
        approval_id=approval.id,
        company_id="company-runtime-001",
        reviewed_by="manager-demo",
        reason="보완 필요",
    )
    db.commit()

    assert result["approval_status"] == "REJECTED"
    assert result["target_status"] == "REJECTED"
    saved_snapshot = db.get(AgentRuntimeStateSnapshot, snapshot.request_id)
    approval_payload = json.loads(saved_snapshot.approval_json)
    structured_response = json.loads(saved_snapshot.structured_response_json)
    assert approval_payload["status"] == "REJECTED"
    assert structured_response["approval"]["status"] == "REJECTED"

    review_log = db.scalar(
        select(EvidenceLog).where(EvidenceLog.approval_id == approval.id)
    )
    assert review_log is not None
    assert review_log.event_type == "agent_runtime_state_rejected"


def test_runtime_state_approval_respects_company_scope() -> None:
    db = _db()
    save_runtime_state_snapshot(db, _runtime_state())
    approval = _runtime_approval(db)
    db.commit()

    with pytest.raises(ApprovalForbiddenError):
        get_approval_detail_for_company(
            db,
            approval_id=approval.id,
            company_id="other-company",
        )
