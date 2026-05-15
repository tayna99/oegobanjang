from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_sync_db
from ...services.contact_thread_service import (
    create_message_draft,
    get_thread,
    list_message_workers,
    list_threads,
)

router = APIRouter(prefix="/contact", tags=["contact"])


class DraftMessageRequest(BaseModel):
    worker_id: str
    company_id: str | None = None
    message_purpose: str | None = None
    due_date: str | None = None
    user_id: str | None = "user-demo-001"
    source_action_id: str | None = None
    extra_context: str | None = None


@router.get("/workers")
def get_contact_workers(
    company_id: str | None = None,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    return {"workers": list_message_workers(company_id, db)}


@router.get("/threads")
def get_contact_threads(
    company_id: str | None = None,
    message_type: str | None = Query(default=None),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    threads = list_threads(company_id, db)
    if message_type:
        threads = [t for t in threads if t.get("message_type") == message_type]
    return {"threads": threads}


@router.get("/threads/{thread_id}")
def get_contact_thread(thread_id: str, db: Session = Depends(get_sync_db)) -> dict[str, Any]:
    thread = get_thread(thread_id, db)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@router.post("/messages/draft")
def create_contact_message_draft(
    body: DraftMessageRequest,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return create_message_draft(
            worker_id=body.worker_id,
            company_id=body.company_id,
            message_purpose=body.message_purpose,
            due_date=body.due_date,
            user_id=body.user_id,
            db=db,
            source_action_id=body.source_action_id,
            extra_context=body.extra_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
