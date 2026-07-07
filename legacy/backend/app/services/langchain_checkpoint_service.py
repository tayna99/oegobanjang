from __future__ import annotations

from typing import Any

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_runtime.langchain_v1.agent_factory import create_workbridge_agent
from app.agent_runtime.langchain_v1.checkpointing import (
    get_async_langchain_checkpointer,
    runtime_checkpoint_config,
)
from app.agent_runtime.langchain_v1.schemas import LangChainRuntimeState
from backend.app.models.approval import Approval
from backend.app.models.langchain_checkpoint import LangChainAgentCheckpoint
from backend.app.models.runtime_state import RUNTIME_STATE_TARGET_TYPE, AgentRuntimeStateSnapshot
from backend.app.services.runtime_resume_service import (
    BLOCKED_RESUME_ACTIONS,
    INTERNAL_RESUME_ACTIONS,
)


class LangChainCheckpointNotFoundError(ValueError):
    pass


class LangChainCheckpointForbiddenError(ValueError):
    pass


class LangChainCheckpointConflictError(ValueError):
    pass


def save_langchain_checkpoint_metadata(
    db: Session,
    state: LangChainRuntimeState,
) -> LangChainAgentCheckpoint | None:
    metadata = dict(state.checkpoint_metadata or {})
    thread_id = str(metadata.get("thread_id") or state.input.thread_id or "")
    checkpoint_ns = str(metadata.get("checkpoint_ns") or "")
    if not thread_id or not checkpoint_ns:
        return None

    row = db.scalar(
        select(LangChainAgentCheckpoint).where(
            LangChainAgentCheckpoint.request_id == state.request_id
        )
    )
    if row is None:
        row = LangChainAgentCheckpoint(request_id=state.request_id, thread_id=thread_id)
        db.add(row)

    row.thread_id = thread_id
    row.checkpoint_ns = checkpoint_ns
    row.latest_checkpoint_id = metadata.get("latest_checkpoint_id")
    row.interrupt_id = metadata.get("interrupt_id")
    row.status = str(metadata.get("status") or "RECORDED")
    row.resume_blocked_reason = metadata.get("resume_blocked_reason")
    db.flush()
    return row


async def resume_langchain_checkpoint_for_company(
    db: Session,
    *,
    request_id: str,
    action_type: str,
    company_id: str,
    resume_value: Any = None,
    agent: Any | None = None,
) -> dict[str, Any]:
    snapshot = db.get(AgentRuntimeStateSnapshot, request_id)
    if snapshot is None:
        raise LangChainCheckpointNotFoundError("runtime state not found")
    if not company_id or snapshot.company_id != company_id:
        raise LangChainCheckpointForbiddenError("checkpoint access forbidden")
    if action_type in BLOCKED_RESUME_ACTIONS or action_type not in INTERNAL_RESUME_ACTIONS:
        _mark_resume_blocked(
            db,
            request_id=request_id,
            reason="External delivery, candidate messaging, expert auto-send, and government submission remain blocked.",
        )
        raise LangChainCheckpointForbiddenError("checkpoint resume action forbidden")

    approval = db.scalar(
        select(Approval).where(
            Approval.target_type == RUNTIME_STATE_TARGET_TYPE,
            Approval.target_id == request_id,
        )
    )
    if approval is None or approval.status != "APPROVED":
        _mark_resume_blocked(
            db,
            request_id=request_id,
            reason="Runtime checkpoint resume requires APPROVED approval.",
        )
        raise LangChainCheckpointConflictError("runtime approval is not approved")

    checkpoint = db.scalar(
        select(LangChainAgentCheckpoint).where(
            LangChainAgentCheckpoint.request_id == request_id
        )
    )
    if checkpoint is None:
        raise LangChainCheckpointNotFoundError("langchain checkpoint metadata not found")

    selected_agent = agent or create_workbridge_agent(
        checkpointer=await get_async_langchain_checkpointer()
    )
    config = runtime_checkpoint_config(thread_id=checkpoint.thread_id)
    result = await selected_agent.ainvoke(
        Command(resume=resume_value or {"action_type": action_type}),
        config=config,
    )
    checkpoint.status = "RESUMED"
    checkpoint.resume_blocked_reason = None
    db.flush()
    return {
        "request_id": request_id,
        "action_type": action_type,
        "status": "RESUMED",
        "checkpoint_id": checkpoint.latest_checkpoint_id,
        "thread_id": checkpoint.thread_id,
        "result_present": result is not None,
        "external_delivery_executed": False,
        "government_submission_executed": False,
    }


def _mark_resume_blocked(db: Session, *, request_id: str, reason: str) -> None:
    checkpoint = db.scalar(
        select(LangChainAgentCheckpoint).where(
            LangChainAgentCheckpoint.request_id == request_id
        )
    )
    if checkpoint is not None:
        checkpoint.status = "RESUME_BLOCKED"
        checkpoint.resume_blocked_reason = reason
        db.flush()
