from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_runtime.langchain_v1.middleware import redact_pii
from backend.app.models.evidence import EvidenceLog


class EvidenceForbiddenError(ValueError):
    pass


def list_evidence_logs_for_request(
    db: Session,
    *,
    request_id: str,
    company_id: str | None,
) -> dict[str, Any]:
    if not company_id:
        raise EvidenceForbiddenError("evidence access forbidden")

    logs = db.scalars(
        select(EvidenceLog)
        .where(
            EvidenceLog.request_id == request_id,
            EvidenceLog.company_id == company_id,
        )
        .order_by(EvidenceLog.created_at.asc(), EvidenceLog.id.asc())
    ).all()

    items = [_safe_log_item(log) for log in logs]
    return {
        "request_id": request_id,
        "count": len(items),
        "items": items,
    }


def _safe_log_item(log: EvidenceLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "event_type": log.event_type,
        "agent_name": log.agent_name,
        "tool_name": log.tool_name,
        "summary": _safe_text(log.summary),
        "source_ids": [_safe_text(str(item)) for item in _loads_list(log.source_ids)],
        "approval_required": bool(log.approval_required),
        "risk_flags": [_safe_text(str(item)) for item in _loads_list(log.risk_flags)],
        "request_id": log.request_id,
        "company_id": log.company_id,
        "approval_id": log.approval_id,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _loads_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return [_safe_text(value)]
    if isinstance(loaded, list):
        return loaded
    return [loaded]


def _safe_text(value: str) -> str:
    return redact_pii(value)
