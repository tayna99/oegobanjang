from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agent_runtime.langchain_v1.schemas import LangChainRuntimeState
from backend.app.models.runtime_execution import RuntimeMetric
from backend.app.models.runtime_state import AgentRuntimeStateSnapshot


def save_runtime_metrics_from_state(
    db: Session,
    state: LangChainRuntimeState,
) -> list[RuntimeMetric]:
    """Persist redacted runtime counters from middleware evidence.

    Raw prompts, raw model output, and PII-bearing content are not stored here.
    Re-saving the same request replaces derived metrics for idempotency.
    """

    db.execute(delete(RuntimeMetric).where(RuntimeMetric.request_id == state.request_id))
    metrics: list[RuntimeMetric] = []
    retrieval_total = 0
    provider_error_count = 0

    for event in state.evidence_events:
        event_type = str(event.get("event_type") or "")
        metadata = _dict(event.get("metadata"))
        if event_type == "tool_executed":
            metrics.append(
                RuntimeMetric(
                    request_id=state.request_id,
                    metric_type="tool_call",
                    tool_name=str(
                        metadata.get("tool_name") or event.get("tool_name") or ""
                    )
                    or None,
                    duration_ms=_float_or_none(metadata.get("duration_ms")),
                    metadata_json=_dumps(_safe_metadata(metadata)),
                )
            )
        elif event_type == "rag_retrieved":
            retrieval_count = _int_or_zero(metadata.get("retrieval_count"))
            retrieval_total += retrieval_count
            metrics.append(
                RuntimeMetric(
                    request_id=state.request_id,
                    metric_type="rag_retrieval",
                    duration_ms=_float_or_none(metadata.get("duration_ms")),
                    retrieval_count=retrieval_count,
                    metadata_json=_dumps(_safe_metadata(metadata)),
                )
            )
        elif event_type == "final_response_generated":
            parsing_error = metadata.get("parsing_error")
            provider_error_count += 1 if parsing_error else 0
            metrics.append(
                RuntimeMetric(
                    request_id=state.request_id,
                    metric_type="model_call",
                    model_name=str(metadata.get("model_name") or "") or None,
                    duration_ms=_float_or_none(metadata.get("duration_ms")),
                    token_usage_json=_dumps(_dict(metadata.get("token_usage"))),
                    provider_error_count=1 if parsing_error else 0,
                    metadata_json=_dumps(
                        {
                            "raw_present": bool(metadata.get("raw_present", False)),
                            "raw_content_hash": metadata.get("raw_content_hash"),
                            "parsing_error": parsing_error,
                        }
                    ),
                )
            )

    blocked_count = 1 if state.structured_response.blocked_reason else 0
    approval_pending_count = (
        1 if state.approval.required and state.approval.status == "PENDING" else 0
    )
    metrics.append(
        RuntimeMetric(
            request_id=state.request_id,
            metric_type="run_summary",
            retrieval_count=retrieval_total,
            blocked_count=blocked_count,
            approval_pending_count=approval_pending_count,
            provider_error_count=provider_error_count,
            metadata_json=_dumps(
                {
                    "detected_intents": state.structured_response.detected_intents,
                    "risk_flag_count": len(state.structured_response.risk_flags),
                }
            ),
        )
    )

    db.add_all(metrics)
    db.flush()
    return metrics


def get_runtime_metrics_for_company(
    db: Session,
    *,
    request_id: str,
    company_id: str,
) -> dict[str, Any]:
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        raise RuntimeMetricsNotFoundError("runtime state not found")
    if not company_id or snapshot.company_id != company_id:
        raise RuntimeMetricsForbiddenError("runtime metrics access forbidden")

    rows = db.scalars(
        select(RuntimeMetric)
        .where(RuntimeMetric.request_id == request_id)
        .order_by(RuntimeMetric.created_at, RuntimeMetric.metric_type)
    ).all()
    summary = _summary_payload(rows)
    return {
        "request_id": request_id,
        "summary": summary,
        "metrics": [_metric_payload(row) for row in rows],
    }


def get_runtime_metrics_summary_for_company(
    db: Session,
    *,
    company_id: str,
    from_at: str | None = None,
    to_at: str | None = None,
) -> dict[str, Any]:
    if not company_id:
        raise RuntimeMetricsForbiddenError("runtime metrics access forbidden")

    snapshot_stmt = select(AgentRuntimeStateSnapshot.request_id).where(
        AgentRuntimeStateSnapshot.company_id == company_id
    )
    from_dt = _datetime_or_none(from_at)
    to_dt = _datetime_or_none(to_at)
    if from_dt is not None:
        snapshot_stmt = snapshot_stmt.where(AgentRuntimeStateSnapshot.created_at >= from_dt)
    if to_dt is not None:
        snapshot_stmt = snapshot_stmt.where(AgentRuntimeStateSnapshot.created_at <= to_dt)
    request_ids = list(db.scalars(snapshot_stmt).all())
    if not request_ids:
        return {
            "company_id": company_id,
            "summary": _empty_company_summary(),
        }

    rows = db.scalars(
        select(RuntimeMetric).where(RuntimeMetric.request_id.in_(request_ids))
    ).all()
    model_durations = [
        row.duration_ms
        for row in rows
        if row.metric_type == "model_call" and row.duration_ms is not None
    ]
    tool_durations = [
        row.duration_ms
        for row in rows
        if row.metric_type == "tool_call" and row.duration_ms is not None
    ]
    run_rows = [row for row in rows if row.metric_type == "run_summary"]
    summary = {
        "run_count": len(set(request_ids)),
        "blocked_count": sum(row.blocked_count for row in run_rows),
        "approval_pending_count": sum(row.approval_pending_count for row in run_rows),
        "provider_error_count": sum(row.provider_error_count for row in run_rows),
        "retrieval_count": sum(row.retrieval_count for row in run_rows),
        "avg_model_duration_ms": _avg(model_durations),
        "avg_tool_duration_ms": _avg(tool_durations),
    }
    return {
        "company_id": company_id,
        "summary": summary,
    }


class RuntimeMetricsNotFoundError(ValueError):
    pass


class RuntimeMetricsForbiddenError(ValueError):
    pass


def _metric_payload(row: RuntimeMetric) -> dict[str, Any]:
    return {
        "metric_type": row.metric_type,
        "model_name": row.model_name,
        "tool_name": row.tool_name,
        "duration_ms": row.duration_ms,
        "token_usage": _loads(row.token_usage_json),
        "retrieval_count": row.retrieval_count,
        "blocked_count": row.blocked_count,
        "approval_pending_count": row.approval_pending_count,
        "provider_error_count": row.provider_error_count,
        "metadata": _loads(row.metadata_json),
    }


def _summary_payload(rows: list[RuntimeMetric]) -> dict[str, int]:
    run_summary = next((row for row in rows if row.metric_type == "run_summary"), None)
    if run_summary is not None:
        return {
            "retrieval_count": run_summary.retrieval_count,
            "blocked_count": run_summary.blocked_count,
            "approval_pending_count": run_summary.approval_pending_count,
            "provider_error_count": run_summary.provider_error_count,
        }
    return {
        "retrieval_count": sum(row.retrieval_count for row in rows),
        "blocked_count": sum(row.blocked_count for row in rows),
        "approval_pending_count": sum(row.approval_pending_count for row in rows),
        "provider_error_count": sum(row.provider_error_count for row in rows),
    }


def _empty_company_summary() -> dict[str, int | float]:
    return {
        "run_count": 0,
        "blocked_count": 0,
        "approval_pending_count": 0,
        "provider_error_count": 0,
        "retrieval_count": 0,
        "avg_model_duration_ms": 0.0,
        "avg_tool_duration_ms": 0.0,
    }


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _datetime_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "tool_name",
        "duration_ms",
        "retrieval_count",
        "source_ids",
        "evidence_grades",
        "doc_types",
        "raw_present",
        "raw_content_hash",
        "parsing_error",
    }
    return {key: value.get(key) for key in allowed_keys if key in value}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}
