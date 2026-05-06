from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState
from backend.app.db.session import get_sync_db
from backend.app.services.agent_service import (
    AgentRunRequest as ContactAgentRunRequest,
    run_agent as run_contact_agent,
)


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    user_message: str
    user_id: str
    company_id: str
    thread_id: str | None = None


class AgentRunResponse(BaseModel):
    request_id: str
    final_response: str
    detected_intents: list[str]
    risk_flags: list[str]
    approval_required: bool
    approval_status: str
    evidence_event_count: int
    rag_context_count: int


@router.post("/run")
async def run_agent(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    if "user_request" in body:
        request = ContactAgentRunRequest.model_validate(body)
        return run_contact_agent(request, db=db).model_dump()

    try:
        request = AgentRunRequest.model_validate(body)
        state: ForeignHiringState = await run_workflow(
            user_message=request.user_message,
            user_id=request.user_id,
            company_id=request.company_id,
            thread_id=request.thread_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return AgentRunResponse(
        request_id=state.request_id,
        final_response=state.final_response,
        detected_intents=[i.value for i in state.detected_intents],
        risk_flags=state.risk_flags,
        approval_required=state.approval.required,
        approval_status=state.approval.status,
        evidence_event_count=len(state.evidence_events),
        rag_context_count=len(state.rag_contexts),
    ).model_dump()


@router.get("/state/{request_id}")
async def get_agent_state(request_id: str) -> dict:
    """thread_id 기반으로 저장된 state를 조회합니다. (MemorySaver 기반 - 프로세스 내 유지)"""
    from app.agent_runtime.graph.workflow import get_compiled_app

    app = get_compiled_app()
    try:
        config = {"configurable": {"thread_id": request_id}}
        state_snapshot = app.get_state(config)
        if state_snapshot and state_snapshot.values:
            return state_snapshot.values
        raise HTTPException(status_code=404, detail="state를 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
