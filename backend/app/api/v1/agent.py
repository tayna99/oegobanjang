from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState
from backend.app.db.session import get_sync_db
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from backend.app.services.runtime_state_persistence_service import (
    get_runtime_state_snapshot,
    save_runtime_state_snapshot,
)
from backend.app.services.agent_service import HandoffResponse, build_handoff_response
from backend.app.services.handoff_persistence_service import save_handoff_package_draft


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    user_message: str | None = None
    user_request: str | None = None
    user_id: str = ""
    company_id: str = ""
    thread_id: str | None = None
    persist_result: bool = False
    worker_id: str | None = None
    created_by: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _has_message(self) -> "AgentRunRequest":
        if not (self.user_message or self.user_request):
            raise ValueError("user_message or user_request is required")
        return self

    @property
    def normalized_message(self) -> str:
        return (self.user_message or self.user_request or "").strip()


class AgentRunResponse(BaseModel):
    request_id: str
    final_response: str
    detected_intents: list[str]
    risk_flags: list[str]
    approval_required: bool
    approval_status: str
    handoff: HandoffResponse = Field(
        default_factory=lambda: HandoffResponse(available=False)
    )
    evidence_event_count: int
    rag_context_count: int


@router.post("/run")
async def run_agent(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        request = AgentRunRequest.model_validate(body)
        state: ForeignHiringState = await run_workflow(
            user_message=request.normalized_message,
            user_id=request.user_id,
            company_id=request.company_id,
            worker_id=request.worker_id or "",
            thread_id=request.thread_id,
            input_payload=request.input_payload,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    runtime_state = runtime_state_store.get(state.request_id)
    if runtime_state is not None:
        try:
            save_runtime_state_snapshot(db, runtime_state)
            db.commit()
        except Exception:
            db.rollback()

    handoff_persistence: dict[str, Any] | None = None
    if request.persist_result and state.handoff_package_draft:
        try:
            handoff_persistence = save_handoff_package_draft(
                db,
                request_id=state.request_id,
                handoff_package_draft=state.handoff_package_draft,
                worker_id=request.worker_id,
                company_id=request.company_id,
                created_by=request.created_by or request.user_id,
            )
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e)) from e

    return AgentRunResponse(
        request_id=state.request_id,
        final_response=state.final_response,
        detected_intents=[i.value for i in state.detected_intents],
        risk_flags=state.risk_flags,
        approval_required=state.approval.required,
        approval_status=state.approval.status,
        handoff=build_handoff_response(state.handoff_package_draft, handoff_persistence),
        evidence_event_count=len(state.evidence_events),
        rag_context_count=len(state.rag_contexts),
    ).model_dump()


@router.get("/state/{request_id}")
async def get_agent_state(
    request_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    """request_id 기반으로 LangChain v1 process-local state를 조회합니다."""
    state = runtime_state_store.get(request_id)
    if state is not None:
        return state.model_dump()
    snapshot = get_runtime_state_snapshot(db, request_id)
    if snapshot is not None:
        return snapshot
    raise HTTPException(status_code=404, detail="state를 찾을 수 없습니다.")
