from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_runtime.langchain_v1.middleware import redact_pii
from app.agent_runtime.langchain_v1.schemas import LangChainRuntimeState
from backend.app.models.approval import Approval
from backend.app.models.runtime_state import (
    RUNTIME_STATE_TARGET_TYPE,
    AgentRuntimeStateSnapshot,
)


RUNTIME_STATE_APPROVAL_REASON = (
    "LangChain runtime 결과를 외부 전달하거나 후속 실행하기 전 담당자 승인이 필요합니다."
)


def save_runtime_state_snapshot(
    db: Session,
    state: LangChainRuntimeState,
) -> AgentRuntimeStateSnapshot:
    payload = _snapshot_payload(state)
    snapshot = db.get(AgentRuntimeStateSnapshot, state.request_id)
    if snapshot is None:
        snapshot = AgentRuntimeStateSnapshot(request_id=state.request_id)
        db.add(snapshot)

    snapshot.user_id = state.input.user_id or None
    snapshot.company_id = state.input.company_id or None
    snapshot.worker_id = state.input.worker_id or None
    snapshot.candidate_id = state.input.candidate_id or None
    snapshot.final_response = payload["structured_response"].get("final_response", "")
    snapshot.structured_response_json = _dumps(payload["structured_response"])
    snapshot.evidence_events_json = _dumps(payload["evidence_events"])
    snapshot.approval_json = _dumps(payload["approval"])
    snapshot.interrupt_metadata_json = _dumps(payload["interrupt_metadata"])
    snapshot.input_json = _dumps(payload["input"])
    db.flush()
    _sync_runtime_state_approval(db, snapshot=snapshot, state=state)
    db.flush()
    return snapshot


def get_runtime_state_snapshot(
    db: Session,
    request_id: str,
) -> dict[str, Any] | None:
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        return None
    approval = _get_runtime_state_approval(db, snapshot.request_id)
    approval_payload = _loads(snapshot.approval_json)
    if approval is not None:
        approval_payload.update(_approval_metadata(approval))
    return {
        "request_id": snapshot.request_id,
        "input": _loads(snapshot.input_json),
        "structured_response": _loads(snapshot.structured_response_json),
        "evidence_events": _loads(snapshot.evidence_events_json),
        "approval": approval_payload,
        "interrupt_metadata": _loads(snapshot.interrupt_metadata_json),
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
    }


def runtime_state_target_status(snapshot: AgentRuntimeStateSnapshot) -> str:
    approval_payload = _loads(snapshot.approval_json)
    return str(approval_payload.get("status") or "PENDING")


def mark_runtime_state_snapshot_reviewed(
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
) -> None:
    """승인 상태만 snapshot에 반영합니다. 외부 발송/제출/resume은 하지 않습니다."""

    _attach_approval_to_snapshot(snapshot, approval)


def _snapshot_payload(state: LangChainRuntimeState) -> dict[str, Any]:
    return _redact_value(state.model_dump(mode="json"))


def _sync_runtime_state_approval(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    state: LangChainRuntimeState,
) -> None:
    if not state.approval.required:
        return

    approval = _get_runtime_state_approval(db, snapshot.request_id)
    if approval is None:
        approval = Approval(
            target_type=RUNTIME_STATE_TARGET_TYPE,
            target_id=snapshot.request_id,
            status="PENDING",
            requested_by=state.input.created_by or state.input.user_id or None,
            reason=state.approval.reason or RUNTIME_STATE_APPROVAL_REASON,
        )
        db.add(approval)
        db.flush()

    _attach_approval_to_snapshot(snapshot, approval)


def _get_runtime_state_approval(
    db: Session,
    request_id: str,
) -> Approval | None:
    return db.scalar(
        select(Approval)
        .where(
            Approval.target_type == RUNTIME_STATE_TARGET_TYPE,
            Approval.target_id == request_id,
        )
        .order_by(Approval.created_at.desc())
    )


def _attach_approval_to_snapshot(
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
) -> None:
    approval_payload = _loads(snapshot.approval_json)
    approval_payload.update(_approval_metadata(approval))
    snapshot.approval_json = _dumps(approval_payload)

    structured_response = _loads(snapshot.structured_response_json)
    structured_approval = structured_response.get("approval")
    if isinstance(structured_approval, dict):
        structured_approval["status"] = approval.status
    snapshot.structured_response_json = _dumps(structured_response)


def _approval_metadata(approval: Approval) -> dict[str, Any]:
    return {
        "approval_id": approval.id,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "status": approval.status,
        "reviewed_by": approval.reviewed_by,
        "reviewed_at": approval.reviewed_at.isoformat()
        if approval.reviewed_at
        else None,
        "reason": approval.reason,
    }


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_value(item) for key, item in value.items()}
    return value


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}
