from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_sync_db
from ...services.document_service import (
    accept_worker_document_request,
    get_contact_attachment_download,
    get_worker_document_download,
    list_all_worker_document_requests,
    list_worker_document_requests,
    reject_worker_document_request,
    save_worker_document_submission,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class RejectDocumentRequest(BaseModel):
    reason: str | None = None


@router.get("/worker-requests")
def get_worker_document_requests(
    worker_id: str,
    company_id: str | None = None,
    db: Session = Depends(get_sync_db),
) -> dict[str, list[dict[str, object]]]:
    return {"requests": list_worker_document_requests(worker_id, company_id, db)}


@router.get("/worker-requests/all")
def get_all_worker_document_requests(
    company_id: str | None = None,
    db: Session = Depends(get_sync_db),
) -> dict[str, list[dict[str, object]]]:
    return {"requests": list_all_worker_document_requests(company_id, db)}


@router.post("/worker-submissions")
def upload_worker_document_submission(
    worker_id: str = Form(...),
    doc_type: str = Form(...),
    company_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        request = save_worker_document_submission(
            worker_id=worker_id,
            company_id=company_id,
            doc_type=doc_type,
            original_filename=file.filename or "submission.bin",
            file_obj=file.file,
            content_type=file.content_type,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"request": request}


@router.post("/worker-requests/{worker_id}/{doc_type}/accept")
def accept_worker_document(
    worker_id: str,
    doc_type: str,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        request = accept_worker_document_request(
            worker_id=worker_id,
            doc_type=doc_type,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"request": request}


@router.post("/worker-requests/{worker_id}/{doc_type}/reject")
def reject_worker_document(
    worker_id: str,
    doc_type: str,
    body: RejectDocumentRequest | None = None,
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        request = reject_worker_document_request(
            worker_id=worker_id,
            doc_type=doc_type,
            reason=body.reason if body else None,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"request": request}


@router.get("/attachments/{attachment_id}/download")
def download_contact_attachment(
    attachment_id: str,
    db: Session = Depends(get_sync_db),
) -> FileResponse:
    try:
        payload = get_contact_attachment_download(attachment_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=payload["path"],
        filename=payload["filename"],
        media_type=payload["media_type"],
    )


@router.get("/worker-requests/{worker_id}/{doc_type}/download")
def download_worker_document(
    worker_id: str,
    doc_type: str,
    db: Session = Depends(get_sync_db),
) -> FileResponse:
    try:
        payload = get_worker_document_download(worker_id, doc_type, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=payload["path"],
        filename=payload["filename"],
        media_type=payload["media_type"],
    )
