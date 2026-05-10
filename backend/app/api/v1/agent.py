from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState
from backend.app.db.session import get_sync_db
from backend.app.models.worker import Worker
from backend.app.services.langchain_checkpoint_service import (
    LangChainCheckpointConflictError,
    LangChainCheckpointForbiddenError,
    LangChainCheckpointNotFoundError,
    resume_langchain_checkpoint_for_company,
)
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from backend.app.services.runtime_state_persistence_service import (
    get_runtime_state_snapshot,
    save_runtime_state_snapshot,
)
from backend.app.services.runtime_metrics_service import (
    RuntimeMetricsForbiddenError,
    RuntimeMetricsNotFoundError,
    get_runtime_metrics_summary_for_company,
    get_runtime_metrics_for_company,
)
from backend.app.services.runtime_resume_service import (
    RuntimeResumeForbiddenError,
    RuntimeResumeNotFoundError,
    get_runtime_resume_summary_for_company,
    resume_runtime_action_for_company,
)
from backend.app.services.runtime_outbox_service import (
    RuntimeOutboxConflictError,
    RuntimeOutboxForbiddenError,
    RuntimeOutboxNotFoundError,
    prepare_runtime_delivery_outbox_for_company,
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


class AgentResumeRequest(BaseModel):
    action_type: str


class AgentCheckpointResumeRequest(BaseModel):
    action_type: str
    resume_value: Any | None = None


@router.post("/run")
async def run_agent(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        request = AgentRunRequest.model_validate(body)
        normalized_payload, resolved_worker_id = _normalize_worker_lookup(
            db,
            company_id=request.company_id,
            worker_id=request.worker_id or "",
            input_payload=request.input_payload,
        )
        state: ForeignHiringState = await run_workflow(
            user_message=request.normalized_message,
            user_id=request.user_id,
            company_id=request.company_id,
            worker_id=resolved_worker_id,
            thread_id=request.thread_id,
            input_payload=normalized_payload,
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


@router.post("/resume/{request_id}")
async def resume_agent_runtime_action(
    request_id: str,
    body: AgentResumeRequest,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = resume_runtime_action_for_company(
            db,
            request_id=request_id,
            action_type=body.action_type,
            company_id=company_id,
        )
        db.commit()
        return result
    except RuntimeResumeNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="runtime resume action not found") from exc
    except RuntimeResumeForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="resume action forbidden") from exc


@router.get("/resume/{request_id}")
async def get_agent_runtime_resume_summary(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        return get_runtime_resume_summary_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
    except RuntimeResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="runtime resume action not found") from exc
    except RuntimeResumeForbiddenError as exc:
        raise HTTPException(status_code=403, detail="resume action forbidden") from exc


@router.get("/metrics/{request_id}")
async def get_agent_runtime_metrics(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        return get_runtime_metrics_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
    except RuntimeMetricsNotFoundError as exc:
        raise HTTPException(status_code=404, detail="runtime metrics not found") from exc
    except RuntimeMetricsForbiddenError as exc:
        raise HTTPException(status_code=403, detail="runtime metrics access forbidden") from exc


@router.get("/metrics")
async def get_agent_runtime_metrics_summary(
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
    from_at: str | None = Query(default=None, alias="from"),
    to_at: str | None = Query(default=None, alias="to"),
) -> dict[str, Any]:
    try:
        return get_runtime_metrics_summary_for_company(
            db,
            company_id=company_id,
            from_at=from_at,
            to_at=to_at,
        )
    except RuntimeMetricsForbiddenError as exc:
        raise HTTPException(status_code=403, detail="runtime metrics access forbidden") from exc


@router.post("/checkpoints/{request_id}/resume")
async def resume_agent_langchain_checkpoint(
    request_id: str,
    body: AgentCheckpointResumeRequest,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = await resume_langchain_checkpoint_for_company(
            db,
            request_id=request_id,
            action_type=body.action_type,
            company_id=company_id,
            resume_value=body.resume_value,
        )
        db.commit()
        return result
    except LangChainCheckpointNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="langchain checkpoint not found") from exc
    except LangChainCheckpointForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="langchain checkpoint resume forbidden") from exc
    except LangChainCheckpointConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="langchain checkpoint resume conflict") from exc


@router.post("/outbox/{request_id}/prepare")
async def prepare_agent_runtime_outbox(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = prepare_runtime_delivery_outbox_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
        db.commit()
        return result
    except RuntimeOutboxNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="runtime outbox not found") from exc
    except RuntimeOutboxForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="runtime outbox access forbidden") from exc
    except RuntimeOutboxConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="runtime outbox conflict") from exc


def _normalize_worker_lookup(
    db: Session,
    *,
    company_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    payload = dict(input_payload or {})
    worker_name = str(payload.pop("worker_name", "") or "").strip()
    if worker_id or not worker_name:
        return payload, worker_id
    if not company_id:
        payload["worker_lookup_status"] = "not_found"
        return payload, ""

    rows = db.scalars(
        select(Worker).where(
            Worker.company_id == company_id,
            Worker.name == worker_name,
            Worker.status == "ACTIVE",
        )
    ).all()
    if len(rows) == 1:
        payload["worker_lookup_status"] = "matched"
        return payload, rows[0].id
    if len(rows) > 1:
        payload["worker_lookup_status"] = "ambiguous"
        return payload, ""
    payload["worker_lookup_status"] = "not_found"
    return payload, ""
