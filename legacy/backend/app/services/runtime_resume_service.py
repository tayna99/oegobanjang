from __future__ import annotations

import json
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.approval import Approval
from backend.app.models.evidence import EvidenceLog
from backend.app.models.runtime_execution import (
    AgentCheckpoint,
    ApprovalAction,
    DeliveryOutbox,
)
from backend.app.models.runtime_state import AgentRuntimeStateSnapshot


INTERNAL_RESUME_ACTIONS = (
    "finalize_internal_draft",
    "mark_handoff_package_ready",
    "prepare_external_delivery",
)
COMPLETED_INTERNAL_ACTIONS = {
    "finalize_internal_draft",
    "mark_handoff_package_ready",
}
PENDING_INTERNAL_ACTIONS = {"prepare_external_delivery"}
BLOCKED_RESUME_ACTIONS = (
    "auto_send_to_candidate",
    "auto_send_to_sending_agency",
    "auto_send_to_admin_scrivener",
    "auto_submit_to_government_portal",
)


class RuntimeResumeNotFoundError(ValueError):
    pass


class RuntimeResumeForbiddenError(ValueError):
    pass


class RuntimeResumeConflictError(ValueError):
    pass


def create_runtime_resume_plan(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
) -> dict[str, Any]:
    """Create safe post-approval execution records.

    This never sends messages, transfers expert packages, exports documents, or
    submits to government portals. It only records internal completion, queues
    a preparation-only outbox item, and creates a durable checkpoint.
    """

    if approval.status != "APPROVED":
        raise RuntimeResumeConflictError("approval must be approved")

    checkpoint = _ensure_checkpoint(db, snapshot=snapshot, approval=approval)
    actions = [
        _ensure_action(
            db,
            snapshot=snapshot,
            approval=approval,
            action_type=action_type,
            status=_internal_action_status(action_type),
            blocked_reason=None,
        )
        for action_type in INTERNAL_RESUME_ACTIONS
    ]
    blocked_actions = [
        _ensure_action(
            db,
            snapshot=snapshot,
            approval=approval,
            action_type=action_type,
            status="BLOCKED",
            blocked_reason="External delivery, candidate messaging, and government submission remain blocked.",
        )
        for action_type in BLOCKED_RESUME_ACTIONS
    ]
    outbox = _ensure_outbox(db, snapshot=snapshot, approval=approval)
    _save_resume_evidence_logs(
        db,
        snapshot=snapshot,
        approval=approval,
        checkpoint=checkpoint,
        outbox=outbox,
    )
    db.flush()
    return {
        "checkpoint_id": checkpoint.id,
        "resume_token": checkpoint.resume_token,
        "action_ids": [row.id for row in actions],
        "blocked_action_ids": [row.id for row in blocked_actions],
        "outbox_id": outbox.id,
        "allowed_actions": list(INTERNAL_RESUME_ACTIONS),
        "blocked_actions": list(BLOCKED_RESUME_ACTIONS),
    }


def resume_runtime_action_for_company(
    db: Session,
    *,
    request_id: str,
    action_type: str,
    company_id: str,
) -> dict[str, Any]:
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        raise RuntimeResumeNotFoundError("runtime checkpoint not found")
    if not company_id or snapshot.company_id != company_id:
        raise RuntimeResumeForbiddenError("runtime resume access forbidden")
    if action_type in BLOCKED_RESUME_ACTIONS:
        raise RuntimeResumeForbiddenError("resume action forbidden")
    if action_type not in INTERNAL_RESUME_ACTIONS:
        raise RuntimeResumeForbiddenError("resume action forbidden")

    action = db.scalar(
        select(ApprovalAction).where(
            ApprovalAction.request_id == request_id,
            ApprovalAction.action_type == action_type,
        )
    )
    if action is None:
        raise RuntimeResumeNotFoundError("resume action not found")

    if action_type in COMPLETED_INTERNAL_ACTIONS:
        action.status = "COMPLETED"
        _mark_checkpoint_status(
            db,
            request_id=request_id,
            approval_id=action.approval_id,
            status="INTERNAL_ACTION_COMPLETED",
        )
        _ensure_resume_action_evidence(
            db,
            snapshot=snapshot,
            approval_id=action.approval_id,
            action_type=action_type,
        )
    else:
        action.status = "PENDING"
    db.flush()
    return {
        "request_id": request_id,
        "action_type": action_type,
        "status": action.status,
        "approval_id": action.approval_id,
        "external_delivery_executed": False,
        "government_submission_executed": False,
    }


def get_runtime_resume_summary_for_company(
    db: Session,
    *,
    request_id: str,
    company_id: str,
) -> dict[str, Any]:
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        raise RuntimeResumeNotFoundError("runtime checkpoint not found")
    if not company_id or snapshot.company_id != company_id:
        raise RuntimeResumeForbiddenError("runtime resume access forbidden")

    checkpoint = db.scalar(
        select(AgentCheckpoint)
        .where(AgentCheckpoint.request_id == request_id)
        .order_by(AgentCheckpoint.created_at.desc())
    )
    if checkpoint is None:
        raise RuntimeResumeNotFoundError("runtime checkpoint not found")

    actions = db.scalars(
        select(ApprovalAction)
        .where(ApprovalAction.request_id == request_id)
        .order_by(ApprovalAction.action_type)
    ).all()
    outbox = db.scalar(
        select(DeliveryOutbox)
        .where(DeliveryOutbox.request_id == request_id)
        .order_by(DeliveryOutbox.created_at.desc())
    )
    return {
        "request_id": request_id,
        "checkpoint": {
            "checkpoint_id": checkpoint.id,
            "checkpoint_type": checkpoint.checkpoint_type,
            "status": checkpoint.status,
            "resume_token_present": bool(checkpoint.resume_token),
            "last_error": checkpoint.last_error,
        },
        "allowed_actions": _loads(checkpoint.allowed_actions_json),
        "blocked_actions": _loads(checkpoint.blocked_actions_json),
        "actions": {
            action.action_type: {
                "status": action.status,
                "blocked_reason": action.blocked_reason,
            }
            for action in actions
        },
        "outbox": _outbox_payload(outbox),
    }


def _ensure_checkpoint(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
) -> AgentCheckpoint:
    idempotency_key = _key("checkpoint", snapshot.request_id, approval.id)
    existing = _by_idempotency_key(db, AgentCheckpoint, idempotency_key)
    if existing is not None:
        return existing
    checkpoint = AgentCheckpoint(
        request_id=snapshot.request_id,
        approval_id=approval.id,
        checkpoint_type="approval_resume",
        resume_token=str(uuid5(NAMESPACE_URL, idempotency_key)),
        allowed_actions_json=_dumps(list(INTERNAL_RESUME_ACTIONS)),
        blocked_actions_json=_dumps(list(BLOCKED_RESUME_ACTIONS)),
        status="READY",
        idempotency_key=idempotency_key,
        last_error=None,
    )
    db.add(checkpoint)
    db.flush()
    return checkpoint


def _ensure_action(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
    action_type: str,
    status: str,
    blocked_reason: str | None,
) -> ApprovalAction:
    idempotency_key = _key("action", snapshot.request_id, approval.id, action_type)
    existing = _by_idempotency_key(db, ApprovalAction, idempotency_key)
    if existing is not None:
        return existing
    action = ApprovalAction(
        approval_id=approval.id,
        request_id=snapshot.request_id,
        action_type=action_type,
        status=status,
        idempotency_key=idempotency_key,
        blocked_reason=blocked_reason,
        metadata_json=_dumps(
            {
                "external_delivery_executed": False,
                "government_submission_executed": False,
            }
        ),
    )
    db.add(action)
    db.flush()
    return action


def _ensure_outbox(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
) -> DeliveryOutbox:
    idempotency_key = _key("outbox", snapshot.request_id, approval.id, "prepare")
    existing = _by_idempotency_key(db, DeliveryOutbox, idempotency_key)
    if existing is not None:
        return existing
    outbox = DeliveryOutbox(
        approval_id=approval.id,
        request_id=snapshot.request_id,
        outbox_type="external_delivery_preparation",
        target_channel="internal_review",
        status="PENDING",
        idempotency_key=idempotency_key,
        payload_json=_dumps(
            {
                "source": "agent_runtime_state_snapshot",
                "snapshot_request_id": snapshot.request_id,
                "note": "Preparation only. No external message or submission is executed.",
            }
        ),
        blocked_actions_json=_dumps(list(BLOCKED_RESUME_ACTIONS)),
    )
    db.add(outbox)
    db.flush()
    return outbox


def _save_resume_evidence_logs(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval: Approval,
    checkpoint: AgentCheckpoint,
    outbox: DeliveryOutbox,
) -> None:
    event_specs = [
        (
            "approval_action_created",
            "Approved internal runtime actions were recorded; external actions remain blocked.",
            {"allowed_actions": list(INTERNAL_RESUME_ACTIONS), "blocked_actions": list(BLOCKED_RESUME_ACTIONS)},
        ),
        (
            "delivery_outbox_queued",
            "Preparation-only delivery outbox item was queued without sending externally.",
            {"outbox_id": outbox.id, "status": outbox.status},
        ),
        (
            "agent_checkpoint_created",
            "Durable resume checkpoint was created for internal approved actions only.",
            {"checkpoint_id": checkpoint.id, "resume_token": checkpoint.resume_token},
        ),
    ]
    existing_types = set(
        db.scalars(
            select(EvidenceLog.event_type).where(
                EvidenceLog.approval_id == approval.id,
                EvidenceLog.event_type.in_([event_type for event_type, _, _ in event_specs]),
            )
        ).all()
    )
    for event_type, summary, metadata in event_specs:
        if event_type in existing_types:
            continue
        db.add(
            EvidenceLog(
                event_type=event_type,
                agent_name="approval_api",
                tool_name=None,
                summary=summary,
                source_ids=_dumps([]),
                approval_required=True,
                risk_flags=_dumps([]),
                request_id=snapshot.request_id,
                company_id=snapshot.company_id,
                worker_id=snapshot.worker_id,
                approval_id=approval.id,
            )
        )


def _mark_checkpoint_status(
    db: Session,
    *,
    request_id: str,
    approval_id: str,
    status: str,
) -> None:
    checkpoint = db.scalar(
        select(AgentCheckpoint).where(
            AgentCheckpoint.request_id == request_id,
            AgentCheckpoint.approval_id == approval_id,
        )
    )
    if checkpoint is not None:
        checkpoint.status = status


def _ensure_resume_action_evidence(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    approval_id: str,
    action_type: str,
) -> None:
    existing = db.scalar(
        select(EvidenceLog).where(
            EvidenceLog.approval_id == approval_id,
            EvidenceLog.event_type == "resume_action_completed",
            EvidenceLog.summary == f"Internal runtime action completed: {action_type}",
        )
    )
    if existing is not None:
        return
    db.add(
        EvidenceLog(
            event_type="resume_action_completed",
            agent_name="approval_api",
            tool_name=None,
            summary=f"Internal runtime action completed: {action_type}",
            source_ids=_dumps([]),
            approval_required=True,
            risk_flags=_dumps([]),
            request_id=snapshot.request_id,
            company_id=snapshot.company_id,
            worker_id=snapshot.worker_id,
            approval_id=approval_id,
        )
    )


def _outbox_payload(outbox: DeliveryOutbox | None) -> dict[str, Any]:
    if outbox is None:
        return {
            "available": False,
            "status": None,
            "external_delivery_executed": False,
            "government_submission_executed": False,
        }
    return {
        "available": True,
        "outbox_id": outbox.id,
        "outbox_type": outbox.outbox_type,
        "target_channel": outbox.target_channel,
        "status": outbox.status,
        "blocked_actions": _loads(outbox.blocked_actions_json),
        "external_delivery_executed": False,
        "government_submission_executed": False,
    }


def _internal_action_status(action_type: str) -> str:
    if action_type in COMPLETED_INTERNAL_ACTIONS:
        return "COMPLETED"
    if action_type in PENDING_INTERNAL_ACTIONS:
        return "PENDING"
    return "BLOCKED"


def _by_idempotency_key(
    db: Session,
    model: type[AgentCheckpoint] | type[ApprovalAction] | type[DeliveryOutbox],
    idempotency_key: str,
) -> Any | None:
    return db.scalar(select(model).where(model.idempotency_key == idempotency_key))


def _key(*parts: str) -> str:
    return ":".join(str(part) for part in parts)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []
