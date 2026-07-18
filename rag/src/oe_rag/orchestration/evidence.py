"""그래프 노드용 증빙 이벤트 헬퍼 — 요약은 항상 PII 마스킹을 거친다."""

from __future__ import annotations

from typing import Any

from .contracts import EventType, EvidenceEvent
from .guard import redact_pii


def make_event(
    *,
    event_type: EventType,
    request_id: str,
    summary: str,
    step_name: str,
    agent_name: str | None = None,
    citation_ids: list[str] | None = None,
    risk_level: str = "LOW",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """EvidenceEvent dict 생성 — summary는 redact, 원문·질의 전문은 넣지 않는 것이 계약."""
    event = EvidenceEvent(
        event_type=event_type,
        request_id=request_id,
        agent_name=agent_name,
        step_name=step_name,
        summary=redact_pii(summary),
        citation_ids=citation_ids or [],
        risk_level=risk_level,
        metadata=metadata or {},
    )
    return event.model_dump()
