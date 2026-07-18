"""오케스트레이터 — plans/BACKEND_CONNECT.md B3'(2-phase: /intent → 스냅샷 → /graph/run).

backend가 rag 서비스를 호출하는 유일한 사용자 흐름 진입점이다:
1. `POST /intent`로 의도 확정(라우팅은 rag가 결정론으로 계산 — backend는 그 결과만 소비)
2. `route.required_context`로 `context_service.build_context_snapshot()` 조립
   (tenant scope 강제 + Risk Rule Engine 실행 — severity가 여기서 확정된다)
3. `POST /graph/run` SSE를 구독하며 프레임마다: RunStep 기록(kind는 rag 값을 그대로
   저장 — db/schema.sql의 CHECK 허용값과 완전히 일치함을 확인했다) + EvidenceEvent
   기록(evidence_ingest 재사용) + citations upsert(structured 프레임의 answer.citations)

case_id 제약: `runs.case_id`는 커맨드 런에서 NULL 허용이지만 `approvals.case_id`는
NOT NULL이다. 이번 그래프(M7)는 아직 case를 만들지 않으므로(케이스 생성은 Daily
Briefing/G6의 Rule 엔진 몫), approval이 필요한 답변은 `run.status="waiting_approval"`
+ `result_summary`로만 표시하고 실제 `approvals` 행은 만들지 않는다 — case가 있는
흐름(승인 페이지에서 온 재실행 등)과 연결되는 시점에 채울 후속 작업이다.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.models.run import Run, RunStep
from app.services import context_service
from app.services.evidence_ingest import ingest_rag_evidence_event, upsert_citations
from app.services.rag_client import RagServiceError, fetch_intent, stream_graph_run

# runs.status CHECK — db/schema.sql 정본.
_TERMINAL_COMPLETED = "completed"
_TERMINAL_WAITING_APPROVAL = "waiting_approval"
_TERMINAL_FAILED = "failed"


async def execute_command_run(
    db: Session,
    *,
    company_id: str,
    user_id: str,
    message: str,
    thread_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """자연어 커맨드 런 실행 — 진행 상황을 dict 프레임으로 yield하며 동시에 DB에 기록한다.

    프레임 종류: {"type": "run_created", "run_id": ...} → {"type": "step", ...}* →
    {"type": "evidence", ...}* → {"type": "structured", ...} → {"type": "done", ...}
    (API 레이어가 이걸 그대로 SSE로 재직렬화한다 — api/v1/runs.py)
    """
    run_id = new_id()
    run = Run(
        id=run_id,
        company_id=company_id,
        case_id=None,  # 커맨드 런 — case 생성은 별도 흐름(G6/후속)
        started_by="user",
        started_by_user_id=user_id,
        agent_name="orchestration_graph",
        status="running",
        goal_text=message[:2000],
        started_at=dt.datetime.now(dt.UTC),
    )
    db.add(run)
    db.commit()  # get_db는 자동 커밋하지 않는다 — 클라이언트가 run_id를 받는 즉시 조회 가능해야 함
    yield {"type": "run_created", "run_id": run_id}

    try:
        route = await fetch_intent(message)
    except RagServiceError as exc:
        _mark_run_failed(db, run, f"intent 조회 실패: {exc}")
        yield {"type": "error", "detail": str(exc)}
        return

    if not route.get("should_run"):
        run.status = _TERMINAL_COMPLETED
        run.result_summary = f"차단됨: intent={route.get('intent')}"
        run.ended_at = dt.datetime.now(dt.UTC)
        db.commit()
        yield {"type": "route", "route": route}
        yield {"type": "done", "run_id": run_id, "status": run.status}
        return

    yield {"type": "route", "route": route}

    snapshot = context_service.build_context_snapshot(
        db,
        company_id=company_id,
        required_context=route.get("required_context", []),
    )

    seq = 0
    final_structured: dict[str, Any] | None = None
    final_approval: dict[str, Any] | None = None
    try:
        async for sse_event in stream_graph_run(
            message=message,
            thread_id=thread_id or run_id,
            request_id=run_id,
            context_snapshot=snapshot.model_dump(mode="json"),
        ):
            if sse_event.event == "step":
                seq += 1
                _record_run_step(db, run_id=run_id, company_id=company_id, seq=seq, step=sse_event.data)
                db.commit()
                yield {"type": "step", "step": sse_event.data}
            elif sse_event.event == "evidence":
                ingest_rag_evidence_event(db, company_id=company_id, event=sse_event.data, run_id=run_id)
                db.commit()
                yield {"type": "evidence", "event": sse_event.data}
            elif sse_event.event == "structured":
                final_structured = sse_event.data.get("answer")
                final_approval = sse_event.data.get("approval")
                yield {"type": "structured", "data": sse_event.data}
            elif sse_event.event == "error":
                _mark_run_failed(db, run, str(sse_event.data.get("detail", "unknown error")))
                yield {"type": "error", "detail": sse_event.data.get("detail")}
                return
            elif sse_event.event == "done":
                break
    except RagServiceError as exc:
        _mark_run_failed(db, run, f"graph/run 스트림 실패: {exc}")
        yield {"type": "error", "detail": str(exc)}
        return

    if final_structured and final_structured.get("citations"):
        upsert_citations(db, company_id=company_id, citations=final_structured["citations"])

    approval_required = bool(final_approval and final_approval.get("required"))
    run.status = _TERMINAL_WAITING_APPROVAL if approval_required else _TERMINAL_COMPLETED
    run.result_summary = (final_structured or {}).get("final_response", "")[:2000]
    run.ended_at = dt.datetime.now(dt.UTC)
    db.commit()

    yield {"type": "done", "run_id": run_id, "status": run.status, "approval_required": approval_required}


def _record_run_step(db: Session, *, run_id: str, company_id: str, seq: int, step: dict[str, Any]) -> None:
    db.add(
        RunStep(
            id=new_id(),
            company_id=company_id,
            run_id=run_id,
            seq=seq,
            kind=str(step.get("kind", "thinking")),
            label=str(step.get("label", ""))[:500],
            detail=(str(step.get("detail")) if step.get("detail") else None),
        )
    )


def _mark_run_failed(db: Session, run: Run, reason: str) -> None:
    run.status = _TERMINAL_FAILED
    run.result_summary = reason[:2000]
    run.ended_at = dt.datetime.now(dt.UTC)
    db.commit()
