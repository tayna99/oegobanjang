from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import inspect, select, text
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
    _migrate_contact_thread_columns(db)


def _migrate_contact_thread_columns(db: Session) -> None:
    inspector = inspect(db.get_bind())
    if not inspector.has_table("contact_threads"):
        return
    existing = {col["name"] for col in inspector.get_columns("contact_threads")}
    if "source_action_id" not in existing:
        db.execute(text("ALTER TABLE contact_threads ADD COLUMN source_action_id VARCHAR(120)"))
        db.commit()


def list_message_workers(company_id: str | None, db: Session) -> list[dict[str, Any]]:
    workers = _load_workers(company_id, db)
    worker_options = [
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
    return _dedupe_worker_options(worker_options)


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
    source_action_id: str | None = None,
    extra_context: str | None = None,
) -> dict[str, Any]:
    ensure_contact_thread_tables(db)
    worker = get_worker_profile_data(worker_id, db=db)
    if worker is None:
        raise ValueError("worker not found")

    resolved_purpose = message_purpose or determine_message_purpose_for_worker(worker_id, db)
    language_code = str(worker.get("preferred_language") or "ko")
    worker_name = _display_worker_name(worker)

    if resolved_purpose == "handoff_notification":
        korean_text = (
            f"[행정사 전달 알림] {worker_name} 근로자 건에 대해 담당자 검토가 완료되었습니다. "
            "관련 서류 및 검토 자료를 확인하여 처리해 주시기 바랍니다."
        )
        if extra_context:
            korean_text += f"\n\n{extra_context}"
        translated_text = korean_text
    else:
        user_request = f"{worker_name}에게 필요한 서류 요청 메시지 초안을 만들어줘."
        if extra_context:
            user_request += f"\n\n추가 맥락:\n{extra_context}"
        request = AgentRunRequest(
            user_request=user_request,
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
        source_action_id=source_action_id,
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
    source_action_id: str | None = None,
) -> ContactThread:
    worker_id = str(worker.get("id"))
    # action_id + title 조합으로 근로자용/행정사용 thread를 별도 구분
    if source_action_id:
        existing = db.execute(
            select(ContactThread)
            .where(ContactThread.source_action_id == source_action_id)
            .where(ContactThread.worker_id == worker_id)
            .where(ContactThread.title == title)
            .order_by(ContactThread.created_at.desc())
        ).scalars().first()
        if existing is not None:
            return existing
    else:
        thread = db.execute(
            select(ContactThread)
            .where(ContactThread.worker_id == worker_id)
            .where(ContactThread.title == title)
            .order_by(ContactThread.created_at.desc())
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
        source_action_id=source_action_id,
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
        "source_action_id": thread.source_action_id,
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
        query = query.where(Worker.status == "ACTIVE")
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
                    "status": row.status,
                }
                for row in rows
            ]
    except SQLAlchemyError:
        db.rollback()
    return [
        row for row in _seed_rows("workers.csv")
        if (not company_id or row.get("company_id") == company_id)
        and str(row.get("status") or "ACTIVE").upper() == "ACTIVE"
    ]


def _dedupe_worker_options(workers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for worker in workers:
        key = _worker_identity_key(worker)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(worker)
    return deduped


def _worker_identity_key(worker: dict[str, Any]) -> str:
    email = str(worker.get("email") or "").strip().lower()
    if email:
        return f"email:{email}"
    full_name = str(worker.get("full_name") or worker.get("name") or "").strip().lower()
    nationality = str(worker.get("nationality") or "").strip().lower()
    visa_type = str(worker.get("visa_type") or "").strip().lower()
    return f"profile:{full_name}:{nationality}:{visa_type}"


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
        "missing_document_request": "서류 요청",
        "handoff_notification": "행정사 전달 알림",
    }.get(purpose, "메시지 초안")


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)
