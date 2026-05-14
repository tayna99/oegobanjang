from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

LANGUAGE_LABELS = {"vi": "Tiếng Việt", "id": "Bahasa Indonesia", "ko": "한국어", "en": "English"}
from ..db.base import Base
from ..models.contact import (
    ContactAttachment,
    ContactThread,
    ContactThreadMessage,
)
from ..models.worker import Worker
from .agent_service import AgentRunRequest, run_agent
from .context_data_service import _seed_rows, get_worker_profile_data
from .document_service import (
    determine_message_purpose_for_worker,
    ensure_document_requests_for_purpose,
)


CONTACT_TABLES = [
    ContactThread.__table__,
    ContactThreadMessage.__table__,
    ContactAttachment.__table__,
]


def ensure_contact_thread_tables(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=CONTACT_TABLES)


def list_message_workers(company_id: str | None, db: Session) -> list[dict[str, Any]]:
    workers = _load_workers(company_id, db)
    return [
        {
            "id": worker.get("id"),
            "name": _display_worker_name(worker),
            "full_name": worker.get("name"),
            "nationality": worker.get("nationality"),
            "language_code": worker.get("preferred_language") or "ko",
            "language_label": LANGUAGE_LABELS.get(worker.get("preferred_language") or "ko", "한국어"),
            "email": worker.get("email") or _demo_email(worker),
            "contact_channel": worker.get("contact_channel") or "email",
            "visa_type": worker.get("visa_type"),
        }
        for worker in workers
    ]


def list_threads(company_id: str | None, db: Session) -> list[dict[str, Any]]:
    ensure_contact_thread_tables(db)
    query = select(ContactThread).order_by(ContactThread.last_message_at.desc())
    if company_id:
        query = query.where(ContactThread.company_id == company_id)
    threads = list(db.execute(query).scalars())
    return [_thread_payload(thread, db) for thread in threads]


def get_thread(thread_id: str, db: Session) -> dict[str, Any] | None:
    ensure_contact_thread_tables(db)
    thread = db.get(ContactThread, thread_id)
    if thread is None:
        return None
    return _thread_payload(thread, db, include_messages=True)


def create_message_draft(
    *,
    worker_id: str,
    company_id: str | None,
    message_purpose: str | None,
    due_date: str | None,
    user_id: str | None,
    db: Session,
) -> dict[str, Any]:
    ensure_contact_thread_tables(db)
    worker = get_worker_profile_data(worker_id, db=db)
    if worker is None:
        raise ValueError("worker not found")

    resolved_purpose = message_purpose or determine_message_purpose_for_worker(worker_id, db)
    language_code = str(worker.get("preferred_language") or "ko")
    worker_name = _display_worker_name(worker)
    request = AgentRunRequest(
        user_request=f"{worker_name}에게 필요한 서류 요청 메시지 초안을 만들어줘.",
        input_payload={
            "worker_id": worker_id,
            "company_id": company_id or worker.get("company_id"),
            "language_code": language_code,
            "message_purpose": resolved_purpose,
            "due_date": due_date,
            "worker_name": worker_name,
            "contact_person": "김대리",
            "created_by": user_id,
            "persist_result": False,
        },
    )
    result = run_agent(request, db=None)
    agent_payload = result.agent_results.get("multilingual_contact_agent", {})
    korean_text = str(agent_payload.get("korean_text") or "담당자 확인이 필요한 메시지 초안입니다.")
    translated_text = str(agent_payload.get("translated_text") or korean_text)

    ensure_document_requests_for_purpose(
        worker_id=worker_id,
        company_id=company_id or worker.get("company_id"),
        message_purpose=resolved_purpose,
        due_date=due_date,
        db=db,
    )

    title = _purpose_label(resolved_purpose)
    thread = _get_or_create_thread(
        db,
        worker=worker,
        title=f"{worker_name} · {title}",
        status="초안",
        company_id=company_id or worker.get("company_id"),
    )
    duplicate = _find_duplicate_outbound_message(
        db,
        thread_id=thread.id,
        body_original=translated_text,
        body_ko=korean_text,
    )
    if duplicate is not None:
        thread.status = "초안"
        thread.title = f"{worker_name} · {title}"
        thread.last_message_at = duplicate.created_at or _now()
        db.commit()
        return _thread_payload(thread, db, include_messages=True)

    message = ContactThreadMessage(
        id=_id("msg"),
        thread_id=thread.id,
        company_id=thread.company_id,
        worker_id=worker_id,
        direction="OUTBOUND",
        source="LANGCHAIN",
        language_code=language_code,
        body_original=translated_text,
        body_ko=korean_text,
        status="초안",
    )
    db.add(message)
    thread.status = "초안"
    thread.title = f"{worker_name} · {title}"
    thread.last_message_at = _now()
    db.commit()
    return _thread_payload(thread, db, include_messages=True)


def _find_duplicate_outbound_message(
    db: Session,
    *,
    thread_id: str,
    body_original: str,
    body_ko: str,
) -> ContactThreadMessage | None:
    return (
        db.execute(
            select(ContactThreadMessage)
            .where(ContactThreadMessage.thread_id == thread_id)
            .where(ContactThreadMessage.direction == "OUTBOUND")
            .where(ContactThreadMessage.source == "LANGCHAIN")
            .where(ContactThreadMessage.body_original == body_original)
            .where(ContactThreadMessage.body_ko == body_ko)
            .order_by(ContactThreadMessage.created_at.desc())
        )
        .scalars()
        .first()
    )


def _get_or_create_thread(
    db: Session,
    *,
    worker: dict[str, Any],
    title: str,
    status: str,
    company_id: str | None,
) -> ContactThread:
    worker_id = str(worker.get("id"))
    thread = db.execute(
        select(ContactThread).where(ContactThread.worker_id == worker_id).order_by(ContactThread.created_at.desc())
    ).scalars().first()
    if thread is not None:
        return thread
    thread = ContactThread(
        id=_id("thr"),
        company_id=company_id or worker.get("company_id"),
        worker_id=worker_id,
        channel="portal",
        status=status,
        title=title,
    )
    db.add(thread)
    db.flush()
    return thread


def _thread_payload(thread: ContactThread, db: Session, include_messages: bool = False) -> dict[str, Any]:
    worker = get_worker_profile_data(thread.worker_id, db=db) or {"id": thread.worker_id}
    messages = list(
        db.execute(
            select(ContactThreadMessage)
            .where(ContactThreadMessage.thread_id == thread.id)
            .order_by(ContactThreadMessage.created_at.asc())
        ).scalars()
    )
    latest = messages[-1] if messages else None
    payload = {
        "id": thread.id,
        "company_id": thread.company_id,
        "worker": {
            "id": thread.worker_id,
            "name": _display_worker_name(worker),
            "full_name": worker.get("name"),
            "nationality": worker.get("nationality"),
            "language_code": worker.get("preferred_language") or "ko",
            "language_label": LANGUAGE_LABELS.get(worker.get("preferred_language") or "ko", "한국어"),
            "email": worker.get("email") or _demo_email(worker),
            "contact_channel": worker.get("contact_channel") or "email",
            "visa_type": worker.get("visa_type"),
        },
        "title": thread.title,
        "status": thread.status,
        "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        "last_message_preview": (latest.body_ko or latest.body_original)[:90] if latest else "",
        "message_count": len(messages),
    }
    if include_messages:
        payload["messages"] = [_message_payload(message, db) for message in messages]
    return payload


def _message_payload(message: ContactThreadMessage, db: Session) -> dict[str, Any]:
    attachments = list(
        db.execute(
            select(ContactAttachment).where(ContactAttachment.message_id == message.id)
        ).scalars()
    )
    return {
        "id": message.id,
        "thread_id": message.thread_id,
        "worker_id": message.worker_id,
        "direction": message.direction,
        "source": message.source,
        "language_code": message.language_code,
        "body_original": message.body_original,
        "body_ko": message.body_ko,
        "status": message.status,
        "sender_email": message.sender_email,
        "received_at": message.received_at.isoformat() if message.received_at else None,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "attachments": [
            {
                "id": attachment.id,
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "size": attachment.size,
                "doc_type": _doc_type_from_storage_path(attachment.storage_path),
            }
            for attachment in attachments
        ],
    }


def _doc_type_from_storage_path(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    parts = storage_path.replace("\\", "/").split("/")
    if "worker_documents" not in parts:
        return None
    index = parts.index("worker_documents")
    if len(parts) > index + 2:
        return parts[index + 2]
    return None


def _load_workers(company_id: str | None, db: Session) -> list[dict[str, Any]]:
    try:
        query = select(Worker)
        if company_id:
            query = query.where(Worker.company_id == company_id)
        rows = list(db.execute(query.order_by(Worker.name)).scalars())
        if rows:
            return [
                {
                    "id": row.id,
                    "company_id": row.company_id,
                    "name": row.name,
                    "nationality": row.nationality,
                    "preferred_language": row.preferred_language,
                    "email": row.email,
                    "contact_channel": row.contact_channel,
                    "visa_type": row.visa_type,
                }
                for row in rows
            ]
    except SQLAlchemyError:
        db.rollback()
    return [
        row for row in _seed_rows("workers.csv")
        if not company_id or row.get("company_id") == company_id
    ]


def _display_worker_name(worker: dict[str, Any]) -> str:
    name = str(worker.get("name") or worker.get("id") or "worker")
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return name


def _demo_email(worker: dict[str, Any]) -> str:
    name = str(worker.get("name") or "worker").lower().replace(" ", ".")
    return f"{name}@worker.oegobanjang.test"


def _purpose_label(purpose: str) -> str:
    return {
        "passport_request": "여권 사본 요청",
        "photo_request": "증명사진 요청",
        "arc_request": "외국인등록증 사본 요청",
        "safety_training_notice": "안전교육 안내",
    }.get(purpose, "메시지 초안")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)
