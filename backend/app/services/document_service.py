from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import BinaryIO, Any
from uuid import uuid4

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from ..config import BACKEND_DIR
from ..db.base import Base
from ..models.contact import ContactAttachment, ContactThread, ContactThreadMessage
from ..models.daily_briefing import DailyBriefingDocumentSource
from ..models.document import WorkerDocument
from .context_data_service import get_worker_profile_data


DOCUMENT_TABLES = [WorkerDocument.__table__, DailyBriefingDocumentSource.__table__]
CONTACT_TABLES = [
    ContactThread.__table__,
    ContactThreadMessage.__table__,
    ContactAttachment.__table__,
]
UPLOAD_ROOT = BACKEND_DIR / "data" / "uploads" / "worker_documents"
DOCUMENT_PURPOSES = {
    "passport_request": ["passport_copy"],
    "photo_request": ["id_photo"],
    "arc_request": ["arc_copy"],
    "missing_document_request": ["passport_copy", "arc_copy", "id_photo"],
}
DOCUMENT_DEFINITIONS = {
    "passport_copy": {"doc_type": "passport_copy", "label": "여권 사본", "due_date": "2026-05-20"},
    "arc_copy": {"doc_type": "arc_copy", "label": "외국인등록증 사본", "due_date": "2026-05-20"},
    "id_photo": {"doc_type": "id_photo", "label": "증명사진", "due_date": "-"},
}
DAILY_BRIEFING_DOC_TYPE_ALIASES = {
    "arc_copy": ["arc_copy", "alien_registration"],
    "passport_copy": ["passport_copy"],
    "id_photo": ["id_photo"],
    "work_permit": ["work_permit"],
    "employment_contract": ["employment_contract", "labor_contract", "standard_labor_contract"],
    "labor_contract": ["labor_contract", "employment_contract", "standard_labor_contract"],
}


def ensure_document_tables(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=DOCUMENT_TABLES + CONTACT_TABLES)
    _ensure_worker_document_columns(db)


def list_worker_document_requests(worker_id: str, company_id: str | None, db: Session) -> list[dict[str, object]]:
    ensure_document_tables(db)
    rows = list(
        db.execute(
            select(WorkerDocument)
            .where(WorkerDocument.worker_id == worker_id)
            .order_by(WorkerDocument.doc_type.asc())
        ).scalars()
    )
    return [
        _request_payload(
            row,
            _definition_for(row.doc_type),
            worker_id,
            company_id,
        )
        for row in rows
    ]


def list_all_worker_document_requests(company_id: str | None, db: Session) -> list[dict[str, object]]:
    ensure_document_tables(db)
    query = select(WorkerDocument).order_by(WorkerDocument.worker_id.asc(), WorkerDocument.doc_type.asc())
    if company_id:
        query = query.where(WorkerDocument.company_id == company_id)
    rows = list(db.execute(query).scalars())
    return [
        _request_payload(
            row,
            _definition_for(row.doc_type),
            row.worker_id,
            row.company_id or company_id,
        )
        for row in rows
    ]


def determine_message_purpose_for_worker(worker_id: str, db: Session) -> str:
    ensure_document_tables(db)
    rows = list(
        db.execute(
            select(WorkerDocument).where(WorkerDocument.worker_id == worker_id)
        ).scalars()
    )
    if not rows:
        return "passport_request"
    pending = {row.doc_type for row in rows if row.status not in {"SUBMITTED", "ACCEPTED"}}
    if "passport_copy" in pending:
        return "passport_request"
    if "arc_copy" in pending:
        return "arc_request"
    if "id_photo" in pending:
        return "photo_request"
    return "passport_request"


def ensure_document_requests_for_purpose(
    *,
    worker_id: str,
    company_id: str | None,
    message_purpose: str,
    due_date: str | None,
    db: Session,
) -> list[dict[str, object]]:
    ensure_document_tables(db)
    requested: list[dict[str, object]] = []
    for doc_type in DOCUMENT_PURPOSES.get(message_purpose, []):
        definition = dict(_definition_for(doc_type))
        if due_date and definition["due_date"] != "-":
            definition["due_date"] = due_date
        row = db.execute(
            select(WorkerDocument).where(
                WorkerDocument.worker_id == worker_id,
                WorkerDocument.doc_type == doc_type,
            )
        ).scalar_one_or_none()
        if row is None:
            row = WorkerDocument(
                id=f"wdoc_{uuid4().hex[:12]}",
                company_id=company_id,
                worker_id=worker_id,
                doc_type=doc_type,
                status="REQUESTED",
                expires_at=definition["due_date"],
                notes="관리자 메시지로 요청됨",
            )
            db.add(row)
        elif row.status in {"MISSING", "REJECTED"}:
            row.status = "REQUESTED"
            row.expires_at = definition["due_date"]
        row.company_id = company_id or row.company_id
        requested.append(_request_payload(row, definition, worker_id, company_id))
    db.flush()
    return requested


def save_worker_document_submission(
    *,
    worker_id: str,
    company_id: str | None,
    doc_type: str,
    original_filename: str,
    file_obj: BinaryIO,
    content_type: str | None,
    db: Session,
) -> dict[str, object]:
    ensure_document_tables(db)
    if doc_type not in DOCUMENT_DEFINITIONS:
        raise ValueError("unsupported doc_type")

    now = datetime.now(timezone.utc)
    document_id = f"wdoc_{uuid4().hex[:12]}"
    safe_name = _safe_filename(original_filename or "submission.bin")
    target_dir = UPLOAD_ROOT / str(worker_id) / doc_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document_id}_{safe_name}"
    with target_path.open("wb") as output:
        shutil.copyfileobj(file_obj, output)

    row = db.execute(
        select(WorkerDocument).where(
            WorkerDocument.worker_id == worker_id,
            WorkerDocument.doc_type == doc_type,
        )
    ).scalar_one_or_none()
    if row is None:
        row = WorkerDocument(
            id=document_id,
            company_id=company_id,
            worker_id=worker_id,
            doc_type=doc_type,
        )
        db.add(row)
    row.company_id = company_id or row.company_id
    row.status = "SUBMITTED"
    row.file_path = str(target_path.relative_to(BACKEND_DIR.parent)).replace("\\", "/")
    row.submitted_at = now.isoformat()
    row.reviewed_at = None
    row.notes = f"근로자 포털 제출: {safe_name}"
    _create_upload_thread_message(
        db,
        worker_id=worker_id,
        company_id=company_id,
        doc_type=doc_type,
        filename=safe_name,
        content_type=content_type,
        file_size=target_path.stat().st_size,
        storage_path=str(target_path.relative_to(BACKEND_DIR.parent)).replace("\\", "/"),
    )
    db.commit()

    definition = _definition_for(doc_type)
    return _request_payload(row, definition, worker_id, company_id)


def accept_worker_document_request(
    *,
    worker_id: str,
    doc_type: str,
    db: Session,
) -> dict[str, object]:
    ensure_document_tables(db)
    row = db.execute(
        select(WorkerDocument).where(
            WorkerDocument.worker_id == worker_id,
            WorkerDocument.doc_type == doc_type,
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("document request not found")
    if row.status == "ACCEPTED":
        _sync_daily_briefing_document_source(
            db,
            worker_id=worker_id,
            company_id=row.company_id,
            doc_type=doc_type,
            status="ACCEPTED",
        )
        _refresh_daily_briefing_after_document_sync(db, row.company_id)
        db.commit()
        return _request_payload(row, _definition_for(doc_type), worker_id, row.company_id)
    if row.status != "SUBMITTED":
        raise ValueError("document is not submitted")
    row.status = "ACCEPTED"
    row.reviewed_at = datetime.now(timezone.utc).isoformat()
    row.notes = "담당자 확인 완료"
    _sync_daily_briefing_document_source(
        db,
        worker_id=worker_id,
        company_id=row.company_id,
        doc_type=doc_type,
        status="ACCEPTED",
    )
    _create_acceptance_thread_message(
        db,
        worker_id=worker_id,
        company_id=row.company_id,
        doc_type=doc_type,
    )
    _refresh_daily_briefing_after_document_sync(db, row.company_id)
    db.commit()
    return _request_payload(row, _definition_for(doc_type), worker_id, row.company_id)


def reject_worker_document_request(
    *,
    worker_id: str,
    doc_type: str,
    reason: str | None,
    db: Session,
) -> dict[str, object]:
    ensure_document_tables(db)
    row = db.execute(
        select(WorkerDocument).where(
            WorkerDocument.worker_id == worker_id,
            WorkerDocument.doc_type == doc_type,
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("document request not found")
    if row.status not in {"SUBMITTED", "ACCEPTED"}:
        raise ValueError("document is not reviewable")
    row.status = "REJECTED"
    row.reviewed_at = datetime.now(timezone.utc).isoformat()
    row.notes = reason.strip() if reason else "담당자 보완 요청"
    _sync_daily_briefing_document_source(
        db,
        worker_id=worker_id,
        company_id=row.company_id,
        doc_type=doc_type,
        status="MISSING",
    )
    _create_revision_request_thread_message(
        db,
        worker_id=worker_id,
        company_id=row.company_id,
        doc_type=doc_type,
        reason=row.notes,
    )
    _refresh_daily_briefing_after_document_sync(db, row.company_id)
    db.commit()
    return _request_payload(row, _definition_for(doc_type), worker_id, row.company_id)


def get_contact_attachment_download(attachment_id: str, db: Session) -> dict[str, Any]:
    ensure_document_tables(db)
    attachment = db.get(ContactAttachment, attachment_id)
    if attachment is None:
        raise ValueError("attachment not found")
    if not attachment.storage_path:
        raise ValueError("attachment file not found")
    path = (BACKEND_DIR.parent / attachment.storage_path).resolve()
    upload_root = UPLOAD_ROOT.resolve()
    try:
        path.relative_to(upload_root)
    except ValueError as exc:
        raise ValueError("attachment path is not allowed") from exc
    if not path.exists() or not path.is_file():
        raise ValueError("attachment file not found")
    return {
        "path": path,
        "filename": attachment.filename,
        "media_type": attachment.mime_type or "application/octet-stream",
    }


def get_worker_document_download(worker_id: str, doc_type: str, db: Session) -> dict[str, Any]:
    ensure_document_tables(db)
    row = db.execute(
        select(WorkerDocument).where(
            WorkerDocument.worker_id == worker_id,
            WorkerDocument.doc_type == doc_type,
        )
    ).scalar_one_or_none()
    if row is None or not row.file_path:
        raise ValueError("document file not found")
    path = (BACKEND_DIR.parent / row.file_path).resolve()
    upload_root = UPLOAD_ROOT.resolve()
    try:
        path.relative_to(upload_root)
    except ValueError as exc:
        raise ValueError("document path is not allowed") from exc
    if not path.exists() or not path.is_file():
        raise ValueError("document file not found")
    return {
        "path": path,
        "filename": path.name.split("_", 1)[-1] if "_" in path.name else path.name,
        "media_type": "application/octet-stream",
    }


def _request_payload(
    row: WorkerDocument | None,
    definition: dict[str, str],
    worker_id: str,
    company_id: str | None,
) -> dict[str, object]:
    return {
        "id": row.id if row else f"request_{definition['doc_type']}",
        "company_id": row.company_id if row else company_id,
        "worker_id": worker_id,
        "doc_type": definition["doc_type"],
        "label": definition["label"],
        "due_date": row.expires_at if row and row.expires_at else definition["due_date"],
        "status": row.status if row else "REQUESTED",
        "file_path": row.file_path if row else None,
        "submitted_at": row.submitted_at if row else None,
        "reviewed_at": row.reviewed_at if row else None,
        "notes": row.notes if row else None,
    }


def _sync_daily_briefing_document_source(
    db: Session,
    *,
    worker_id: str,
    company_id: str | None,
    doc_type: str,
    status: str,
) -> None:
    source_status = "MISSING" if status == "MISSING" else "ACCEPTED"
    aliases = DAILY_BRIEFING_DOC_TYPE_ALIASES.get(doc_type, [doc_type])
    matched = False
    for alias in aliases:
        row = db.execute(
            select(DailyBriefingDocumentSource).where(
                DailyBriefingDocumentSource.worker_id == worker_id,
                DailyBriefingDocumentSource.document_type == alias,
            )
        ).scalar_one_or_none()
        if row is None:
            continue
        row.status = source_status
        matched = True
    if not matched and company_id:
        canonical_doc_type = aliases[-1] if doc_type == "arc_copy" else aliases[0]
        db.add(
            DailyBriefingDocumentSource(
                id=f"{worker_id}:{canonical_doc_type}",
                worker_id=worker_id,
                document_type=canonical_doc_type,
                status=source_status,
                required=True,
                due_date=None,
            )
        )
    db.flush()


def _refresh_daily_briefing_after_document_sync(db: Session, company_id: str | None) -> None:
    if not company_id:
        return
    try:
        backend_path = str(BACKEND_DIR)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from .daily_briefing_service import build_sqlalchemy_daily_briefing_service

        target_date = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        service = build_sqlalchemy_daily_briefing_service(db)
        service.run_daily_briefing(
            company_id=company_id,
            date=target_date,
            user_role="admin",
            allowed_company_ids=[company_id],
        )
    except Exception:
        # Document review must remain durable even if briefing refresh is temporarily unavailable.
        return


def _definition_for(doc_type: str) -> dict[str, str]:
    return DOCUMENT_DEFINITIONS.get(
        doc_type,
        {"doc_type": doc_type, "label": doc_type, "due_date": "-"},
    )


def _create_upload_thread_message(
    db: Session,
    *,
    worker_id: str,
    company_id: str | None,
    doc_type: str,
    filename: str,
    content_type: str | None,
    file_size: int,
    storage_path: str,
) -> None:
    worker = get_worker_profile_data(worker_id, db=db) or {"id": worker_id}
    worker_name = _display_worker_name(worker)
    definition = _definition_for(doc_type)
    thread = db.execute(
        select(ContactThread)
        .where(ContactThread.worker_id == worker_id)
        .where(ContactThread.channel == "portal")
        .order_by(ContactThread.created_at.desc())
    ).scalars().first()
    if thread is None:
        thread = ContactThread(
            id=f"thr_{uuid4().hex[:12]}",
            company_id=company_id or worker.get("company_id"),
            worker_id=worker_id,
            channel="portal",
            status="응답 도착",
            title=f"{worker_name} · {definition['label']} 제출",
        )
        db.add(thread)
        db.flush()
    message = ContactThreadMessage(
        id=f"msg_{uuid4().hex[:12]}",
        thread_id=thread.id,
        company_id=thread.company_id or company_id,
        worker_id=worker_id,
        direction="INBOUND",
        source="WORKER_PORTAL",
        language_code=str(worker.get("preferred_language") or "ko"),
        body_original=f"{definition['label']} 파일을 제출했습니다.",
        body_ko=f"{definition['label']} 파일을 제출했습니다.",
        status="제출됨",
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    db.flush()
    db.add(
        ContactAttachment(
            id=f"att_{uuid4().hex[:12]}",
            message_id=message.id,
            filename=filename,
            mime_type=content_type,
            size=_format_size(file_size),
            storage_path=storage_path,
        )
    )
    thread.status = "응답 도착"
    thread.last_message_at = datetime.now(timezone.utc)


def _create_revision_request_thread_message(
    db: Session,
    *,
    worker_id: str,
    company_id: str | None,
    doc_type: str,
    reason: str,
) -> None:
    worker = get_worker_profile_data(worker_id, db=db) or {"id": worker_id}
    worker_name = _display_worker_name(worker)
    definition = _definition_for(doc_type)
    language_code = str(worker.get("preferred_language") or "ko")
    thread = db.execute(
        select(ContactThread)
        .where(ContactThread.worker_id == worker_id)
        .where(ContactThread.channel == "portal")
        .order_by(ContactThread.created_at.desc())
    ).scalars().first()
    if thread is None:
        thread = ContactThread(
            id=f"thr_{uuid4().hex[:12]}",
            company_id=company_id or worker.get("company_id"),
            worker_id=worker_id,
            channel="portal",
            status="보완 요청",
            title=f"{worker_name} · {definition['label']} 보완 요청",
        )
        db.add(thread)
        db.flush()
    body_ko = (
        f"{definition['label']} 확인 결과 보완이 필요합니다.\n"
        "확인 가능한 파일로 다시 제출해 주세요.\n"
        f"보완 사유: {reason}"
    )
    if language_code == "vi":
        localized_label = _localized_doc_label(doc_type, language_code)
        body_original = (
            f"{localized_label} cần được bổ sung.\n"
            "Vui lòng gửi lại tệp rõ ràng để người phụ trách có thể kiểm tra."
        )
    else:
        body_original = body_ko
    message = ContactThreadMessage(
        id=f"msg_{uuid4().hex[:12]}",
        thread_id=thread.id,
        company_id=thread.company_id or company_id,
        worker_id=worker_id,
        direction="OUTBOUND",
        source="MANAGER_REVIEW",
        language_code=language_code,
        body_original=body_original,
        body_ko=body_ko,
        status="보완 요청",
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    thread.status = "보완 요청"
    thread.last_message_at = datetime.now(timezone.utc)


def _create_acceptance_thread_message(
    db: Session,
    *,
    worker_id: str,
    company_id: str | None,
    doc_type: str,
) -> None:
    worker = get_worker_profile_data(worker_id, db=db) or {"id": worker_id}
    worker_name = _display_worker_name(worker)
    definition = _definition_for(doc_type)
    language_code = str(worker.get("preferred_language") or "ko")
    thread = db.execute(
        select(ContactThread)
        .where(ContactThread.worker_id == worker_id)
        .where(ContactThread.channel == "portal")
        .order_by(ContactThread.created_at.desc())
    ).scalars().first()
    if thread is None:
        thread = ContactThread(
            id=f"thr_{uuid4().hex[:12]}",
            company_id=company_id or worker.get("company_id"),
            worker_id=worker_id,
            channel="portal",
            status="승인 완료",
            title=f"{worker_name} · {definition['label']} 승인 완료",
        )
        db.add(thread)
        db.flush()
    body_ko = (
        f"{definition['label']}이 승인 처리됐습니다.\n"
        "제출해 주신 파일을 담당자가 확인했습니다."
    )
    if language_code == "vi":
        localized_label = _localized_doc_label(doc_type, language_code)
        body_original = (
            f"{localized_label} đã được phê duyệt.\n"
            "Người phụ trách đã kiểm tra tệp bạn gửi."
        )
    else:
        body_original = body_ko
    db.add(
        ContactThreadMessage(
            id=f"msg_{uuid4().hex[:12]}",
            thread_id=thread.id,
            company_id=thread.company_id or company_id,
            worker_id=worker_id,
            direction="OUTBOUND",
            source="MANAGER_REVIEW",
            language_code=language_code,
            body_original=body_original,
            body_ko=body_ko,
            status="승인 완료",
            created_at=datetime.now(timezone.utc),
        )
    )
    thread.status = "승인 완료"
    thread.last_message_at = datetime.now(timezone.utc)


def _display_worker_name(worker: dict[str, object]) -> str:
    name = str(worker.get("name") or worker.get("id") or "worker")
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return name


def _localized_doc_label(doc_type: str, language_code: str) -> str:
    if language_code == "vi":
        return {
            "passport_copy": "Bản sao hộ chiếu",
            "arc_copy": "Bản sao thẻ đăng ký người nước ngoài",
            "id_photo": "Ảnh thẻ",
        }.get(doc_type, "Tài liệu")
    return _definition_for(doc_type)["label"]


def _format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    if size >= 1024:
        return f"{round(size / 1024)}KB"
    return f"{size}B"


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9가-힣._-]+", "_", name)[:120] or "submission.bin"


def _ensure_worker_document_columns(db: Session) -> None:
    inspector = inspect(db.get_bind())
    if not inspector.has_table("worker_documents"):
        return
    existing = {column["name"] for column in inspector.get_columns("worker_documents")}
    migrations = {
        "file_path": "ALTER TABLE worker_documents ADD COLUMN file_path TEXT",
        "submitted_at": "ALTER TABLE worker_documents ADD COLUMN submitted_at VARCHAR(40)",
        "reviewed_at": "ALTER TABLE worker_documents ADD COLUMN reviewed_at VARCHAR(40)",
        "expires_at": "ALTER TABLE worker_documents ADD COLUMN expires_at VARCHAR(40)",
        "notes": "ALTER TABLE worker_documents ADD COLUMN notes TEXT",
    }
    for column, ddl in migrations.items():
        if column not in existing:
            db.execute(text(ddl))
    db.commit()
