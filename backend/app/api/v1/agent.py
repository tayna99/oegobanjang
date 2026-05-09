from __future__ import annotations

import re
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
from backend.app.services.agent_service import (
    AgentRunRequest as ContactAgentRunRequest,
    HandoffResponse,
    build_handoff_response,
    run_agent as run_contact_agent,
)
from backend.app.agent_runtime.langchain_v1.contact_artifact_store import (
    pop_contact_artifacts,
)
from backend.app.agent_runtime.langchain_v1.contact_subagents import (
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
    run_contact_onboarding_subagent,
    run_worker_reply_interpreter_subagent,
)
from backend.app.services.contact_persistence_service import (
    SourceMessageValidationError,
    resolve_source_message_for_status_update,
    save_message_draft_result,
    save_worker_reply_summary_result,
)
from backend.app.services.handoff_persistence_service import save_handoff_package_draft
from app.services.daily_briefing_planner import plan_daily_briefing_from_message
from app.services.daily_briefing_service import build_sqlalchemy_daily_briefing_service


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
    persistence: dict[str, Any] = Field(default_factory=dict)
    evidence_event_count: int
    rag_context_count: int
    daily_briefing: dict[str, Any] | None = None
    structured_plan: dict[str, Any] | None = None


class AgentResumeRequest(BaseModel):
    action_type: str


class AgentCheckpointResumeRequest(BaseModel):
    action_type: str
    resume_value: Any | None = None


@router.post("/run")
async def run_agent(
    body: dict[str, Any] = Body(...),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    if "user_request" in body and "user_message" not in body:
        contact_payload = dict(body.get("input_payload") or {})
        for key in ("worker_id", "company_id", "persist_result", "created_by", "user_id"):
            if key in body and key not in contact_payload:
                contact_payload[key] = body[key]
        contact_request = ContactAgentRunRequest(
            user_request=str(body["user_request"]),
            input_payload=contact_payload,
        )
        return run_contact_agent(contact_request, db=db).model_dump()

    try:
        request = AgentRunRequest.model_validate(body)
        normalized_payload, resolved_worker_id = _normalize_worker_lookup(
            db,
            company_id=request.company_id,
            worker_id=request.worker_id or "",
            input_payload=request.input_payload,
        )
        daily_briefing_plan = plan_daily_briefing_from_message(request.normalized_message)
        if daily_briefing_plan.should_run:
            service = build_sqlalchemy_daily_briefing_service(db)
            result = service.run_daily_briefing(
                company_id=request.company_id,
                date=None,
                user_role=x_user_role,
                allowed_company_ids=[x_company_id] if x_company_id else None,
            )
            db.commit()
            return AgentRunResponse(
                request_id=result.briefing_run_id,
                final_response=(
                    "오늘 기준 외국인 고용 운영 리스크 브리핑을 생성했습니다. "
                    "추천 액션은 모두 담당자 승인 대기 상태입니다."
                ),
                detected_intents=[daily_briefing_plan.intent or "daily_briefing"],
                risk_flags=[
                    item.risk_type
                    for item in result.items
                    if item.severity in {"CRITICAL", "HIGH"}
                ],
                approval_required=result.approval_required,
                approval_status="pending" if result.approval_required else "not_required",
                evidence_event_count=len(result.evidence_event_ids),
                rag_context_count=len(
                    [
                        summary
                        for summary in result.citation_summaries
                        if summary.validation_status == "validated"
                    ]
                ),
                daily_briefing=result.model_dump(),
                structured_plan=daily_briefing_plan.model_dump(),
            ).model_dump()
        state: ForeignHiringState = await run_workflow(
            user_message=request.normalized_message,
            user_id=request.user_id,
            company_id=request.company_id,
            worker_id=resolved_worker_id,
            thread_id=request.thread_id,
            input_payload=normalized_payload,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": str(e.args[0]) if e.args else "TENANT_SCOPE_VIOLATION",
                "message": "Requested company is outside the allowed company scope.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except LookupError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": str(e.args[0]) if e.args else "MISSING_REQUIRED_CONTEXT",
                "message": "Required company or worker context is missing.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": str(e.args[0]) if e.args else "STATE_SAVE_FAILED",
                "message": "Agent request failed safely.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    runtime_state = runtime_state_store.get(state.request_id)
    raw_runtime_payload = (
        dict(runtime_state.raw_input_payload)
        if runtime_state is not None and runtime_state.raw_input_payload
        else normalized_payload
    )
    if runtime_state is not None:
        try:
            save_runtime_state_snapshot(db, runtime_state)
            db.commit()
        except Exception:
            db.rollback()

    contact_artifacts = pop_contact_artifacts(state.request_id)
    handoff_persistence: dict[str, Any] | None = None
    contact_message_persistence: dict[str, Any] | None = None
    status_update_persistence: dict[str, Any] | None = None
    if request.persist_result:
        try:
            if state.handoff_package_draft:
                handoff_persistence = save_handoff_package_draft(
                    db,
                    request_id=state.request_id,
                    handoff_package_draft=state.handoff_package_draft,
                    worker_id=resolved_worker_id,
                    company_id=request.company_id,
                    created_by=request.created_by or request.user_id,
                )
            contact_message_persistence = _save_contact_message_artifact(
                db,
                request=request,
                request_id=state.request_id,
                worker_id=resolved_worker_id,
                input_payload=raw_runtime_payload,
                artifacts=contact_artifacts,
            )
            status_update_persistence = _save_worker_reply_artifact(
                db,
                request=request,
                request_id=state.request_id,
                worker_id=resolved_worker_id,
                input_payload=raw_runtime_payload,
                artifacts=contact_artifacts,
            )
            if handoff_persistence or contact_message_persistence or status_update_persistence:
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
        persistence=_build_persistence_response(
            enabled=request.persist_result,
            handoff_persistence=handoff_persistence,
            contact_message_persistence=contact_message_persistence,
            status_update_persistence=status_update_persistence,
            contact_artifacts=contact_artifacts,
        ),
        evidence_event_count=len(state.evidence_events),
        rag_context_count=len(state.rag_contexts),
    ).model_dump()


def _save_contact_message_artifact(
    db: Session,
    *,
    request: AgentRunRequest,
    request_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = artifacts.get(CONTACT_ONBOARDING_SUB_AGENT)
    if not _is_persistable_contact_artifact(artifact):
        artifact = _build_contact_onboarding_artifact_from_input(
            db=db,
            request=request,
            worker_id=worker_id,
            input_payload=input_payload,
        )
    if not _is_persistable_contact_artifact(artifact):
        return None
    if not request.company_id or not worker_id:
        return None
    message = save_message_draft_result(
        db,
        agent_result=artifact,
        worker_id=worker_id,
        company_id=request.company_id,
        created_by=request.created_by or request.user_id,
        request_id=request_id,
    )
    return {
        "contact_message_id": message.id,
        "approval_id": message.approval_id,
        "status": message.status,
    }


def _is_persistable_contact_artifact(artifact: Any) -> bool:
    return (
        isinstance(artifact, dict)
        and str(artifact.get("status") or "").upper() == "SUCCESS"
        and bool(artifact.get("korean_text"))
        and bool(artifact.get("message_purpose"))
        and bool(artifact.get("language_code"))
    )


def _build_contact_onboarding_artifact_from_input(
    *,
    db: Session,
    request: AgentRunRequest,
    worker_id: str,
    input_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not worker_id:
        return None
    language_code = input_payload.get("language_code")
    message_purpose = input_payload.get("message_purpose")
    if not language_code or not message_purpose:
        return None
    try:
        return run_contact_onboarding_subagent(
            worker_id=worker_id,
            language_code=str(language_code),
            message_purpose=str(message_purpose),
            user_request=request.normalized_message,
            due_date=input_payload.get("due_date"),
            contact_person=str(input_payload.get("contact_person") or "담당자"),
            training_date=input_payload.get("training_date"),
            training_time=input_payload.get("training_time"),
            location=input_payload.get("location"),
            worker_name=input_payload.get("worker_name")
            or _worker_name_for_persistence(db, worker_id, request.company_id)
            or _worker_name_hint_from_message(request.normalized_message),
        )
    except Exception:
        return None


def _worker_name_for_persistence(
    db: Session,
    worker_id: str,
    company_id: str,
) -> str | None:
    if not worker_id or not company_id:
        return None
    worker = db.get(Worker, worker_id)
    if worker is None or worker.company_id != company_id:
        return None
    return worker.name


def _worker_name_hint_from_message(message: str) -> str | None:
    match = re.search(r"(?:직원|근로자)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})", message)
    if match:
        return match.group(1).strip()
    match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", message)
    return match.group(1).strip() if match else None


def _save_worker_reply_artifact(
    db: Session,
    *,
    request: AgentRunRequest,
    request_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = artifacts.get(WORKER_REPLY_INTERPRETER_SUB_AGENT)
    if not _is_persistable_worker_reply_artifact(artifact):
        artifact = _build_worker_reply_artifact_from_input(
            worker_id=worker_id,
            input_payload=input_payload,
        )
    if not _is_persistable_worker_reply_artifact(artifact):
        return None
    if not request.company_id or not worker_id:
        return None
    source_message_id = input_payload.get("source_message_id")
    if source_message_id:
        try:
            resolve_source_message_for_status_update(
                db,
                source_message_id=str(source_message_id),
                company_id=request.company_id,
                worker_id=worker_id,
            )
        except SourceMessageValidationError as exc:
            return {
                "saved": False,
                "reason": exc.reason,
                "status_update_candidate_ids": [],
                "approval_ids": [],
            }
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=artifact,
        worker_id=worker_id,
        company_id=request.company_id,
        request_id=request_id,
        source_message_id=str(source_message_id) if source_message_id else None,
        requested_by=request.created_by or request.user_id,
        worker_reply=input_payload.get("worker_reply"),
    )
    result = {
        "saved": True,
        "status_update_candidate_ids": [candidate.id for candidate in candidates],
        "approval_ids": [
            candidate.approval_id for candidate in candidates if candidate.approval_id
        ],
    }
    if source_message_id:
        result["source_message_id"] = str(source_message_id)
    return result


def _is_persistable_worker_reply_artifact(artifact: Any) -> bool:
    return (
        isinstance(artifact, dict)
        and str(artifact.get("status") or "").upper() == "SUCCESS"
        and artifact.get("manager_review_required") is True
        and bool(artifact.get("status_update_candidates"))
    )


def _build_worker_reply_artifact_from_input(
    *,
    worker_id: str,
    input_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not worker_id:
        return None
    if input_payload.get("task_type") != "worker_reply_summary":
        return None
    language_code = input_payload.get("language_code")
    worker_reply = input_payload.get("worker_reply")
    if not language_code or not worker_reply:
        return None
    try:
        artifact = run_worker_reply_interpreter_subagent(
            worker_id=worker_id,
            language_code=str(language_code),
            worker_reply=str(worker_reply),
            use_llm_translation=bool(input_payload.get("use_llm_translation", False)),
        )
    except Exception:
        return None
    artifact.pop("worker_reply", None)
    return artifact


def _build_persistence_response(
    *,
    enabled: bool,
    handoff_persistence: dict[str, Any] | None,
    contact_message_persistence: dict[str, Any] | None,
    status_update_persistence: dict[str, Any] | None,
    contact_artifacts: dict[str, Any],
) -> dict[str, Any]:
    handoff_saved = bool(handoff_persistence)
    contact_saved = bool(contact_message_persistence)
    status_update_saved = bool(
        status_update_persistence and status_update_persistence.get("saved", True)
    )
    contact_artifact_available = CONTACT_ONBOARDING_SUB_AGENT in contact_artifacts
    worker_reply_artifact_available = WORKER_REPLY_INTERPRETER_SUB_AGENT in contact_artifacts
    return {
        "enabled": enabled,
        "saved": bool(enabled and (handoff_saved or contact_saved or status_update_saved)),
        "handoff": (
            {
                "saved": True,
                "draft_id": handoff_persistence.get("handoff_package_draft_id"),
                "approval_id": handoff_persistence.get("approval_id"),
                "status": handoff_persistence.get("status"),
            }
            if handoff_saved
            else {"saved": False, "reason": "handoff package draft not available"}
        ),
        "contact_message": (
            {
                "saved": True,
                "id": contact_message_persistence.get("contact_message_id"),
                "approval_id": contact_message_persistence.get("approval_id"),
                "status": contact_message_persistence.get("status"),
            }
            if contact_saved
            else {
                "saved": False,
                "reason": "contact artifact not available"
                if not contact_artifact_available
                else "contact artifact not persisted",
            }
        ),
        "status_update_candidates": (
            {
                "saved": True,
                **(
                    {"source_message_id": status_update_persistence.get("source_message_id")}
                    if status_update_persistence.get("source_message_id")
                    else {}
                ),
                "ids": status_update_persistence.get("status_update_candidate_ids", []),
                "approval_ids": status_update_persistence.get("approval_ids", []),
            }
            if status_update_saved
            else {
                "saved": False,
                "reason": (
                    status_update_persistence.get("reason")
                    if status_update_persistence
                    else "worker reply artifact not available"
                    if not worker_reply_artifact_available
                    else "worker reply artifact not persisted"
                ),
                "ids": [],
                "approval_ids": [],
            }
        ),
    }


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
    if worker_id:
        return payload, worker_id
    if not worker_name:
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
