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
from backend.app.services.langchain_checkpoint_service import (
    save_langchain_checkpoint_metadata,
)
from backend.app.services.runtime_metrics_service import save_runtime_metrics_from_state


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
    save_langchain_checkpoint_metadata(db, state)
    save_runtime_metrics_from_state(db, state)
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
    """승인 상태를 snapshot에 반영합니다.

    승인 이후에도 외부 발송, 정부 제출, agent resume은 실행하지 않습니다.
    APPROVED 상태에서는 내부 초안 확정/내부 handoff 준비 완료까지만 표시합니다.
    """

    _attach_approval_to_snapshot(snapshot, approval)
    if approval.status == "APPROVED":
        _attach_limited_resume_marker(snapshot)


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


def _attach_limited_resume_marker(snapshot: AgentRuntimeStateSnapshot) -> None:
    resume_payload = {
        "requested": True,
        "status": "completed_or_blocked",
        "completed_actions": [
            "approved_draft_finalization",
            "internal_handoff_package_ready",
        ],
        "blocked_actions": [
            "external_delivery",
            "government_submission",
            "auto_send_to_candidate",
            "auto_send_to_sending_agency",
            "auto_send_to_admin_scrivener",
        ],
        "note": "승인 후에도 외부 발송/전달/제출은 실행하지 않고 내부 준비 상태만 갱신합니다.",
    }
    approval_payload = _loads(snapshot.approval_json)
    approval_payload["resume"] = resume_payload
    snapshot.approval_json = _dumps(approval_payload)

    structured_response = _loads(snapshot.structured_response_json)
    domain_payload = structured_response.setdefault("domain_payload", {})
    if isinstance(domain_payload, dict):
        domain_payload["approval_resume"] = resume_payload
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
