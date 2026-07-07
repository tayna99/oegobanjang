from __future__ import annotations

import sys
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

LANGUAGE_LABELS = {"vi": "Tiếng Việt", "id": "Bahasa Indonesia", "ko": "한국어", "en": "English"}
from ..config import BACKEND_DIR
from ..db.base import Base
from ..models.contact import (
    ContactAttachment,
    ContactThread,
    ContactThreadMessage,
)
from ..models.document import WorkerDocument
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
CONTACT_UPLOAD_ROOT = BACKEND_DIR / "data" / "uploads" / "contact_attachments"


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
    if "message_type" not in existing:
        db.execute(text("ALTER TABLE contact_threads ADD COLUMN message_type VARCHAR(40)"))
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
            "visa_expires_at": worker.get("visa_expires_at"),
            "contract_starts_at": worker.get("contract_starts_at"),
            "contract_ends_at": worker.get("contract_ends_at"),
        }
        for worker in workers
    ]
    return _dedupe_worker_options(worker_options)


def list_threads(company_id: str | None, channel: str | None, db: Session) -> list[dict[str, Any]]:
    ensure_contact_thread_tables(db)
    query = select(ContactThread).order_by(ContactThread.last_message_at.desc())
    if company_id:
        query = query.where(ContactThread.company_id == company_id)
    if channel:
        query = query.where(ContactThread.channel == channel)
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
    elif resolved_purpose == "missing_document_request":
        korean_text = _build_worker_document_request_ko(worker_name, extra_context)
        translated_text = _build_worker_document_request_translated(
            worker_name, language_code, extra_context
        )
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

    if resolved_purpose != "handoff_notification":
        ensure_document_requests_for_purpose(
            worker_id=worker_id,
            company_id=company_id or worker.get("company_id"),
            message_purpose=resolved_purpose,
            due_date=due_date,
            db=db,
        )

    title = _purpose_label(resolved_purpose)
    msg_type = "scrivener_handoff" if resolved_purpose == "handoff_notification" else "worker_message"
    channel = "expert" if resolved_purpose == "handoff_notification" else "portal"
    thread_title = f"행정사 - {worker_name}" if channel == "expert" else f"{worker_name} · {title}"
    thread = _get_or_create_thread(
        db,
        worker=worker,
        title=thread_title,
        status="초안",
        company_id=company_id or worker.get("company_id"),
        source_action_id=source_action_id,
        message_type=msg_type,
        channel=channel,
    )
    duplicate = _find_duplicate_outbound_message(
        db,
        thread_id=thread.id,
        body_original=translated_text,
        body_ko=korean_text,
    )
    if duplicate is not None:
        thread.status = "초안"
        thread.title = thread_title
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
    thread.title = thread_title
    thread.last_message_at = _now()
    db.commit()
    return _thread_payload(thread, db, include_messages=True)


def create_thread_message(
    *,
    thread_id: str,
    body_ko: str,
    body_original: str | None,
    language_code: str | None,
    source: str,
    status: str,
    direction: str = "OUTBOUND",
    attachments: list[dict[str, Any]] | None = None,
    db: Session,
) -> dict[str, Any]:
    ensure_contact_thread_tables(db)
    thread = db.get(ContactThread, thread_id)
    if thread is None:
        raise ValueError("thread not found")
    body = body_ko.strip()
    if not body:
        raise ValueError("message body is required")
    message = ContactThreadMessage(
        id=_id("msg"),
        thread_id=thread.id,
        company_id=thread.company_id,
        worker_id=thread.worker_id,
        direction=direction,
        source=source,
        language_code=language_code or "ko",
        body_original=(body_original or body_ko).strip(),
        body_ko=body,
        status=status,
    )
    db.add(message)
    db.flush()
    for attachment in attachments or []:
        db.add(
            ContactAttachment(
                id=_id("att"),
                message_id=message.id,
                filename=str(attachment.get("filename") or "attachment.bin"),
                mime_type=attachment.get("mime_type"),
                size=attachment.get("size"),
                storage_path=attachment.get("storage_path"),
            )
        )
    thread.status = status
    thread.last_message_at = _now()
    db.commit()
    return _thread_payload(thread, db, include_messages=True)


def save_contact_attachment_file(
    *,
    thread_id: str,
    original_filename: str,
    file_obj: BinaryIO,
    content_type: str | None,
) -> dict[str, Any]:
    safe_name = _safe_filename(original_filename or "attachment.bin")
    upload_dir = CONTACT_UPLOAD_ROOT / thread_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex[:12]}_{safe_name}"
    target = upload_dir / filename
    with target.open("wb") as out_file:
        shutil.copyfileobj(file_obj, out_file)
    size = target.stat().st_size
    return {
        "filename": safe_name,
        "mime_type": content_type,
        "size": _format_size(size),
        "storage_path": str(target.relative_to(BACKEND_DIR.parent)).replace("\\", "/"),
    }


def create_expert_thread(
    *,
    worker_id: str,
    company_id: str | None,
    body_ko: str,
    db: Session,
) -> dict[str, Any]:
    ensure_contact_thread_tables(db)
    worker = get_worker_profile_data(worker_id, db=db)
    if worker is None:
        raise ValueError("worker not found")
    body = body_ko.strip()
    if not body:
        raise ValueError("message body is required")

    worker_name = _display_worker_name(worker)
    thread = _get_or_create_thread(
        db,
        worker=worker,
        title=f"행정사 - {worker_name}",
        status="행정사 검토 요청",
        company_id=company_id or worker.get("company_id"),
        source_action_id=f"expert-review:{worker_id}",
        channel="expert",
    )
    duplicate = (
        db.execute(
            select(ContactThreadMessage)
            .where(ContactThreadMessage.thread_id == thread.id)
            .where(ContactThreadMessage.source == "EXPERT_REVIEW")
            .where(ContactThreadMessage.body_ko == body)
            .order_by(ContactThreadMessage.created_at.desc())
        )
        .scalars()
        .first()
    )
    if duplicate is None:
        db.add(
            ContactThreadMessage(
                id=_id("msg"),
                thread_id=thread.id,
                company_id=thread.company_id,
                worker_id=worker_id,
                direction="OUTBOUND",
                source="EXPERT_REVIEW",
                language_code="ko",
                body_original=body,
                body_ko=body,
                status="행정사 검토 요청",
            )
        )
    thread.status = "행정사 검토 요청"
    thread.title = f"행정사 - {worker_name}"
    thread.last_message_at = _now()
    db.commit()
    return _thread_payload(thread, db, include_messages=True)


def update_thread_message(
    *,
    message_id: str,
    body_ko: str,
    body_original: str | None,
    db: Session,
) -> dict[str, Any]:
    ensure_contact_thread_tables(db)
    message = db.get(ContactThreadMessage, message_id)
    if message is None:
        raise ValueError("message not found")
    if not _is_editable_sender(message):
        raise ValueError("only sent messages can be edited")
    target_party = _message_party(message)
    has_reply = db.execute(
        select(ContactThreadMessage)
        .where(ContactThreadMessage.thread_id == message.thread_id)
        .where(ContactThreadMessage.created_at > message.created_at)
        .order_by(ContactThreadMessage.created_at.asc())
    ).scalars().first()
    while has_reply is not None and _message_party(has_reply) == target_party:
        has_reply = (
            db.execute(
                select(ContactThreadMessage)
                .where(ContactThreadMessage.thread_id == message.thread_id)
                .where(ContactThreadMessage.created_at > has_reply.created_at)
                .order_by(ContactThreadMessage.created_at.asc())
            )
            .scalars()
            .first()
        )
    if has_reply is not None:
        raise ValueError("message already has a reply")
    body = body_ko.strip()
    if not body:
        raise ValueError("message body is required")
    message.body_ko = body
    message.body_original = (body_original or body_ko).strip()
    thread = db.get(ContactThread, message.thread_id)
    if thread is not None:
        thread.last_message_at = _now()
    db.commit()
    if thread is None:
        raise ValueError("thread not found")
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
    message_type: str | None = None,
    channel: str = "portal",
) -> ContactThread:
    worker_id = str(worker.get("id"))
    # action_id + title 조합으로 근로자용/행정사용 thread를 별도 구분
    if source_action_id:
        existing = db.execute(
            select(ContactThread)
            .where(ContactThread.source_action_id == source_action_id)
            .where(ContactThread.worker_id == worker_id)
            .where(ContactThread.title == title)
            .where(ContactThread.channel == channel)
            .order_by(ContactThread.created_at.desc())
        ).scalars().first()
        if existing is not None:
            return existing
    else:
        thread = db.execute(
            select(ContactThread)
            .where(ContactThread.worker_id == worker_id)
            .where(ContactThread.title == title)
            .where(ContactThread.channel == channel)
            .order_by(ContactThread.created_at.desc())
        ).scalars().first()
        if thread is not None:
            return thread
    thread = ContactThread(
        id=_id("thr"),
        company_id=company_id or worker.get("company_id"),
        worker_id=worker_id,
        channel=channel,
        status=status,
        title=title,
        source_action_id=source_action_id,
        message_type=message_type,
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
        "channel": thread.channel,
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
            "visa_expires_at": worker.get("visa_expires_at"),
            "contract_starts_at": worker.get("contract_starts_at"),
            "contract_ends_at": worker.get("contract_ends_at"),
        },
        "title": thread.title,
        "status": thread.status,
        "source_action_id": thread.source_action_id,
        "message_type": getattr(thread, "message_type", None),
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
    attachment_payloads = []
    for attachment in attachments:
        doc_type = _doc_type_from_storage_path(attachment.storage_path)
        document_status = _document_status(db, message.worker_id, doc_type)
        attachment_payloads.append(
            {
                "id": attachment.id,
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "size": attachment.size,
                "doc_type": doc_type,
                "doc_status": document_status,
            }
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
        "attachments": attachment_payloads,
    }


def _document_status(db: Session, worker_id: str, doc_type: str | None) -> str | None:
    if not doc_type:
        return None
    document = (
        db.execute(
            select(WorkerDocument)
            .where(WorkerDocument.worker_id == worker_id)
            .where(WorkerDocument.doc_type == doc_type)
            .order_by(WorkerDocument.updated_at.desc())
        )
        .scalars()
        .first()
    )
    return document.status if document is not None else None


def _is_editable_sender(message: ContactThreadMessage) -> bool:
    return message.direction == "OUTBOUND" or message.source == "EXPERT_REPLY"


def _message_party(message: ContactThreadMessage) -> str:
    if message.source == "EXPERT_REPLY":
        return "expert"
    if message.direction == "INBOUND":
        return "worker"
    return "manager"


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
                    "visa_expires_at": row.visa_expires_at,
                    "contract_starts_at": row.contract_starts_at,
                    "contract_ends_at": row.contract_ends_at,
                    "status": row.status,
                    "worker_type": getattr(row, "worker_type", "foreign_worker"),
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


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "attachment.bin"
    return re.sub(r"[^0-9A-Za-z가-힣._ -]+", "_", name)[:120]


def _format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    if size >= 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size}B"


def _build_worker_document_request_ko(
    worker_name: str,
    extra_context: str | None,
) -> str:
    lines = [f"{worker_name}님께,", ""]
    if extra_context:
        lines.append(extra_context)
    lines += [
        "",
        "위 서류를 기한 내에 제출해 주시기 바랍니다.",
        "제출 후 담당자가 확인 연락드립니다.",
        "",
        "감사합니다.",
    ]
    return "\n".join(lines)


def _build_worker_document_request_translated(
    worker_name: str,
    language_code: str,
    extra_context: str | None,
) -> str:
    if language_code == "vi":
        return _build_vi_document_request(worker_name, extra_context)
    if language_code == "id":
        return _build_id_document_request(worker_name, extra_context)
    return _build_worker_document_request_ko(worker_name, extra_context)


def _build_vi_document_request(worker_name: str, extra_context: str | None) -> str:
    lines = [
        f"Kính gửi {worker_name},",
        "",
        "Chúng tôi cần xác nhận một số giấy tờ cần thiết cho quá trình gia hạn visa.",
        "(Danh sách tài liệu cần thiết:)",
        "",
    ]
    if extra_context:
        lines.append(extra_context)
    lines += [
        "",
        "Vui lòng nộp các giấy tờ trên trước hạn chót.",
        "Sau khi nộp, chúng tôi sẽ liên hệ xác nhận.",
        "",
        "Cảm ơn bạn.",
    ]
    return "\n".join(lines)


def _build_id_document_request(worker_name: str, extra_context: str | None) -> str:
    lines = [
        f"Kepada {worker_name},",
        "",
        "Kami perlu mengkonfirmasi beberapa dokumen untuk proses perpanjangan visa.",
        "(Daftar dokumen yang diperlukan:)",
        "",
    ]
    if extra_context:
        lines.append(extra_context)
    lines += [
        "",
        "Harap menyerahkan dokumen-dokumen tersebut sebelum batas waktu.",
        "Setelah pengumpulan, kami akan menghubungi Anda untuk konfirmasi.",
        "",
        "Terima kasih.",
    ]
    return "\n".join(lines)
