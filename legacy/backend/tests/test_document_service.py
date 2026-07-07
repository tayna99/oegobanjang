from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.models.approval import Approval  # noqa: F401
from backend.app.models.company import Company  # noqa: F401
from backend.app.models.contact import ContactAttachment, ContactThread, ContactThreadMessage
from backend.app.models.daily_briefing import DailyBriefingDocumentSource
from backend.app.models.document import DocumentRequirement, WorkerDocument
from backend.app.models.worker import Worker
from backend.app.services.context_data_service import calculate_missing_documents_for_worker
from backend.app.services import document_service
from backend.app.services.document_service import accept_worker_document_request
from backend.app.services.contact_thread_service import create_message_draft


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            Worker.__table__,
            Approval.__table__,
            ContactThread.__table__,
            ContactThreadMessage.__table__,
            ContactAttachment.__table__,
            WorkerDocument.__table__,
            DocumentRequirement.__table__,
        ],
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS daily_briefing_source_documents (
                    id VARCHAR(160) PRIMARY KEY,
                    worker_id VARCHAR(64) NOT NULL,
                    document_type VARCHAR(120) NOT NULL,
                    status VARCHAR(40) NOT NULL,
                    required BOOLEAN NOT NULL DEFAULT 1,
                    due_date VARCHAR(20),
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return session_factory()


def test_accept_worker_document_syncs_daily_briefing_document_source(monkeypatch) -> None:
    monkeypatch.setattr(document_service, "_refresh_daily_briefing_after_document_sync", lambda db, company_id: None)
    db = _session()
    db.add(
        WorkerDocument(
            id="wdoc_passport",
            company_id="company-001",
            worker_id="worker-001",
            doc_type="passport_copy",
            status="SUBMITTED",
        )
    )
    db.add(
        DailyBriefingDocumentSource(
            id="worker-001:passport_copy",
            worker_id="worker-001",
            document_type="passport_copy",
            status="MISSING",
            required=True,
        )
    )
    db.commit()

    request = accept_worker_document_request(
        worker_id="worker-001",
        doc_type="passport_copy",
        db=db,
    )

    source = db.get(DailyBriefingDocumentSource, "worker-001:passport_copy")
    assert request["status"] == "ACCEPTED"
    assert source is not None
    assert source.status == "ACCEPTED"


def test_accepted_worker_document_counts_as_present_for_langchain_tools() -> None:
    db = _session()
    db.add(
        Worker(
            id="worker-001",
            company_id="company-001",
            name="Nguyen Van A",
            visa_type="E-9",
        )
    )
    db.add(
        DocumentRequirement(
            id="req_passport",
            case_type="visa_extension",
            visa_type="E-9",
            required_doc="passport_copy",
            required=True,
        )
    )
    db.add(
        WorkerDocument(
            id="wdoc_passport",
            company_id="company-001",
            worker_id="worker-001",
            doc_type="passport_copy",
            status="ACCEPTED",
        )
    )
    db.commit()

    result = calculate_missing_documents_for_worker(
        "worker-001",
        "visa_extension",
        db=db,
    )

    assert result["present"] == ["passport_copy"]
    assert result["missing"] == []


def test_daily_briefing_submitted_documents_are_used_by_langchain_tools() -> None:
    db = _session()
    db.add(
        Worker(
            id="worker-001",
            company_id="company-001",
            name="Nguyen Van A",
            visa_type="E-9",
        )
    )
    for doc_type in ["passport_copy", "employment_contract", "alien_registration", "work_permit"]:
        db.add(
            DocumentRequirement(
                id=f"req_{doc_type}",
                case_type="stay_extension",
                visa_type="E-9",
                required_doc=doc_type,
                required=True,
            )
        )
    db.add(
        WorkerDocument(
            id="wdoc_passport",
            company_id="company-001",
            worker_id="worker-001",
            doc_type="passport_copy",
            status="ACCEPTED",
        )
    )
    for doc_type in ["employment_contract", "alien_registration", "work_permit"]:
        db.add(
            DailyBriefingDocumentSource(
                id=f"worker-001:{doc_type}",
                worker_id="worker-001",
                document_type=doc_type,
                status="SUBMITTED",
                required=True,
            )
        )
    db.commit()

    result = calculate_missing_documents_for_worker(
        "worker-001",
        "stay_extension",
        db=db,
    )

    assert result["missing"] == []
    assert set(result["present"]) == {
        "passport_copy",
        "employment_contract",
        "alien_registration",
        "work_permit",
    }


def test_handoff_message_draft_uses_expert_channel() -> None:
    db = _session()
    db.add(
        Worker(
            id="worker-001",
            company_id="company-001",
            name="Tran Hoa F",
            nationality="Vietnam",
            preferred_language="vi",
            visa_type="H-2",
        )
    )
    db.commit()

    thread = create_message_draft(
        worker_id="worker-001",
        company_id="company-001",
        message_purpose="handoff_notification",
        due_date=None,
        user_id="manager-001",
        source_action_id="action-handoff-001",
        extra_context="체류만료 D-4 케이스 검토 요청",
        db=db,
    )

    saved = db.get(ContactThread, thread["id"])
    assert saved is not None
    assert saved.channel == "expert"
    assert saved.message_type == "scrivener_handoff"
