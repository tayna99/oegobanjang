from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.evidence import EvidenceLog
from backend.app.models.runtime_execution import (
    AgentCheckpoint,
    ApprovalAction,
    DeliveryOutbox,
)
from backend.app.models.runtime_state import AgentRuntimeStateSnapshot


READY_FOR_INTERNAL_REVIEW = "READY_FOR_INTERNAL_REVIEW"
OUTBOX_READY_CHECKPOINT_STATUS = "OUTBOX_READY_FOR_INTERNAL_REVIEW"


class RuntimeOutboxNotFoundError(ValueError):
    pass


class RuntimeOutboxForbiddenError(ValueError):
    pass


class RuntimeOutboxConflictError(ValueError):
    pass


def prepare_runtime_delivery_outbox_for_company(
    db: Session,
    *,
    request_id: str,
    company_id: str,
) -> dict[str, Any]:
    """Move a preparation-only outbox item into internal review.

    This is intentionally not a delivery executor. It never sends a message,
    exports a package, transfers to an external expert, or submits to a
    government portal. It only marks the approved preparation package as ready
    for a human/internal reviewer.
    """

    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        raise RuntimeOutboxNotFoundError("runtime state snapshot not found")
    if not company_id or snapshot.company_id != company_id:
        raise RuntimeOutboxForbiddenError("runtime outbox access forbidden")

    outbox = db.scalar(
        select(DeliveryOutbox)
        .where(DeliveryOutbox.request_id == request_id)
        .order_by(DeliveryOutbox.created_at.desc())
    )
    if outbox is None:
        raise RuntimeOutboxNotFoundError("delivery outbox not found")
    if (
        outbox.outbox_type != "external_delivery_preparation"
        or outbox.target_channel != "internal_review"
    ):
        raise RuntimeOutboxForbiddenError("delivery outbox target is not internal review")
    if outbox.status not in {"PENDING", READY_FOR_INTERNAL_REVIEW}:
        raise RuntimeOutboxConflictError(f"delivery outbox is not preparable: {outbox.status}")

    action = db.scalar(
        select(ApprovalAction).where(
            ApprovalAction.request_id == request_id,
            ApprovalAction.approval_id == outbox.approval_id,
            ApprovalAction.action_type == "prepare_external_delivery",
        )
    )
    if action is None:
        raise RuntimeOutboxNotFoundError("prepare_external_delivery action not found")
    if action.status == "BLOCKED":
        raise RuntimeOutboxForbiddenError("prepare_external_delivery action is blocked")

    outbox.status = READY_FOR_INTERNAL_REVIEW
    action.status = "COMPLETED"

    checkpoint = db.scalar(
        select(AgentCheckpoint).where(
            AgentCheckpoint.request_id == request_id,
            AgentCheckpoint.approval_id == outbox.approval_id,
        )
    )
    if checkpoint is not None:
        checkpoint.status = OUTBOX_READY_CHECKPOINT_STATUS

    _ensure_outbox_prepared_evidence(
        db,
        snapshot=snapshot,
        outbox=outbox,
    )
    db.flush()
    return _prepared_payload(outbox, checkpoint=checkpoint, action=action)


def _ensure_outbox_prepared_evidence(
    db: Session,
    *,
    snapshot: AgentRuntimeStateSnapshot,
    outbox: DeliveryOutbox,
) -> None:
    existing = db.scalar(
        select(EvidenceLog).where(
            EvidenceLog.request_id == snapshot.request_id,
            EvidenceLog.approval_id == outbox.approval_id,
            EvidenceLog.event_type == "delivery_outbox_prepared",
        )
    )
    if existing is not None:
        return
    db.add(
        EvidenceLog(
            event_type="delivery_outbox_prepared",
            agent_name="approval_api",
            tool_name=None,
            summary="Preparation-only delivery outbox is ready for internal review; no external delivery was executed.",
            source_ids=_dumps([]),
            approval_required=True,
            risk_flags=_dumps([]),
            request_id=snapshot.request_id,
            company_id=snapshot.company_id,
            worker_id=snapshot.worker_id,
            approval_id=outbox.approval_id,
        )
    )


def _prepared_payload(
    outbox: DeliveryOutbox,
    *,
    checkpoint: AgentCheckpoint | None,
    action: ApprovalAction,
) -> dict[str, Any]:
    return {
        "request_id": outbox.request_id,
        "outbox_id": outbox.id,
        "outbox_type": outbox.outbox_type,
        "target_channel": outbox.target_channel,
        "status": outbox.status,
        "blocked_actions": _loads(outbox.blocked_actions_json),
        "action_type": action.action_type,
        "action_status": action.status,
        "checkpoint_status": checkpoint.status if checkpoint is not None else None,
        "message_sent": False,
        "external_delivery_executed": False,
        "government_submission_executed": False,
    }


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []
