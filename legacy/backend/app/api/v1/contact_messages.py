from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_sync_db
from ...services.contact_thread_service import (
    create_expert_thread,
    create_message_draft,
    create_thread_message,
    get_thread,
    list_message_workers,
    list_threads,
    save_contact_attachment_file,
    update_thread_message,
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


class ThreadMessageRequest(BaseModel):
    body_ko: str
    body_original: str | None = None
    language_code: str | None = None
    source: str = "MANAGER"
    status: str = "담당자 입력"
    direction: str = "OUTBOUND"


class UpdateThreadMessageRequest(BaseModel):
    body_ko: str
    body_original: str | None = None


class ExpertThreadRequest(BaseModel):
    worker_id: str
    company_id: str | None = None
    body_ko: str


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
    channel: str | None = None,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    threads = list_threads(company_id, channel, db)
    if message_type:
        threads = [t for t in threads if t.get("message_type") == message_type]
    return {"threads": threads}


@router.get("/threads/{thread_id}")
def get_contact_thread(thread_id: str, db: Session = Depends(get_sync_db)) -> dict[str, Any]:
    thread = get_thread(thread_id, db)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@router.post("/threads/{thread_id}/messages")
def create_contact_thread_message(
    thread_id: str,
    body: ThreadMessageRequest,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return create_thread_message(
            thread_id=thread_id,
            body_ko=body.body_ko,
            body_original=body.body_original,
            language_code=body.language_code,
            source=body.source,
            status=body.status,
            direction=body.direction,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/threads/{thread_id}/messages/form")
def create_contact_thread_message_form(
    thread_id: str,
    body_ko: str = Form(...),
    body_original: str | None = Form(default=None),
    language_code: str | None = Form(default="ko"),
    source: str = Form(default="MANAGER"),
    status: str = Form(default="담당자 입력"),
    direction: str = Form(default="OUTBOUND"),
    files: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    saved_attachments: list[dict[str, Any]] = []
    for file in files or []:
        saved_attachments.append(
            save_contact_attachment_file(
                thread_id=thread_id,
                original_filename=file.filename or "attachment.bin",
                file_obj=file.file,
                content_type=file.content_type,
            )
        )
    try:
        return create_thread_message(
            thread_id=thread_id,
            body_ko=body_ko,
            body_original=body_original,
            language_code=language_code,
            source=source,
            status=status,
            direction=direction,
            attachments=saved_attachments,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/messages/{message_id}")
def update_contact_thread_message(
    message_id: str,
    body: UpdateThreadMessageRequest,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return update_thread_message(
            message_id=message_id,
            body_ko=body.body_ko,
            body_original=body.body_original,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/expert-threads")
def create_contact_expert_thread(
    body: ExpertThreadRequest,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return create_expert_thread(
            worker_id=body.worker_id,
            company_id=body.company_id,
            body_ko=body.body_ko,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
