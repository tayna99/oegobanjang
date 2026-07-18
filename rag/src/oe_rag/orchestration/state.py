"""OrchestrationState — 직선 파이프라인의 공유 상태.

발표 통합 아키텍처의 원칙("Agent 간 직접 호출 금지 — 모두 shared state로 소통")대로
모든 노드는 이 상태만 읽고 부분 갱신을 반환한다. LangGraph StateGraph(TypedDict) 기반.

evidence_events는 각 노드가 append하는 dict 목록(직렬화 안전) — 영속화는 backend 책임.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class OrchestrationState(TypedDict, total=False):
    # 입력
    request_id: str
    thread_id: str
    user_message: str  # input_guard 통과 후에는 PII 마스킹본
    context_snapshot: dict[str, Any]  # backend가 주입한 ContextSnapshot(v1) — 없으면 빈 dict

    # input_guard 산출
    blocked: bool
    blocked_reason: str
    pii_masked: bool

    # intent_router / planner 산출
    route: dict[str, Any]  # RoutePlan.model_dump()

    # executor 산출 — 미션별 결과 (순차 실행, append-only)
    mission_results: Annotated[list[dict[str, Any]], operator.add]

    # aggregator 산출
    aggregated: dict[str, Any]

    # approval_gate 산출
    approval: dict[str, Any]

    # 최종 구조화 응답 (RagAnswer.model_dump() 호환)
    structured_response: dict[str, Any]

    # 전 노드가 append하는 증빙 이벤트 (EvidenceEvent.model_dump())
    evidence_events: Annotated[list[dict[str, Any]], operator.add]
