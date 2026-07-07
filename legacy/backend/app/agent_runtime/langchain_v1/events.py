from __future__ import annotations

from typing import Any

from app.agent_runtime.schemas import EvidenceEvent, EventType


def make_event(
    *,
    event_type: EventType,
    request_id: str,
    summary: str,
    agent_name: str | None = None,
    step_name: str | None = None,
    citation_ids: list[str] | None = None,
    risk_level: str = "LOW",
    metadata: dict[str, Any] | None = None,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_type=event_type,
        request_id=request_id,
        agent_name=agent_name,
        step_name=step_name,
        summary=summary,
        citation_ids=citation_ids or [],
        risk_level=risk_level,
        metadata=metadata or {},
    )


def event_to_reference(event: EvidenceEvent) -> dict[str, Any]:
    return {
        "event_type": event.event_type.value,
        "summary": event.summary,
        "used_for": event.step_name or "",
        "metadata": event.metadata,
    }
