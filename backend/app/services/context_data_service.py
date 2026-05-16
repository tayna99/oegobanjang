from __future__ import annotations

import csv
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.session import SessionLocal
from ..models.company import Company
from ..models.daily_briefing import DailyBriefingDocumentSource
from ..models.document import DocumentRequirement, WorkerDocument
from ..models.hiring import Candidate, CandidatePreEntryPackage
from ..models.worker import Worker


SEED_DIR = Path(__file__).resolve().parents[3] / "data-pipeline" / "seed"
READY_DOCUMENT_STATUSES = {"SUBMITTED", "APPROVED", "ACCEPTED"}
DOCUMENT_TYPE_EQUIVALENTS = {
    "employment_contract": {"employment_contract", "labor_contract", "standard_contract", "standard_labor_contract"},
    "labor_contract": {"employment_contract", "labor_contract", "standard_contract", "standard_labor_contract"},
    "standard_contract": {"employment_contract", "labor_contract", "standard_contract", "standard_labor_contract"},
    "standard_labor_contract": {"employment_contract", "labor_contract", "standard_contract", "standard_labor_contract"},
    "alien_registration": {"alien_registration", "arc_copy"},
    "arc_copy": {"alien_registration", "arc_copy"},
    "passport_copy": {"passport_copy", "passport"},
    "passport": {"passport_copy", "passport"},
}
READY_CANDIDATE_FIELDS = {
    "passport": "여권",
    "photo": "증명사진",
    "health_check": "건강검진",
    "available_from": "근무 가능일",
    "desired_role": "희망 직무",
    "understood_housing": "숙소 안내",
    "understood_shift": "근무조건 안내",
}


@contextmanager
def _session_scope(db: Session | None = None) -> Iterator[Session]:
    if db is not None:
        yield db
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_rows(filename: str) -> list[dict[str, str]]:
    path = SEED_DIR / filename
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _seed_jsonl(filename: str) -> list[dict[str, Any]]:
    path = SEED_DIR / filename
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "있음", "완료"}


def _model_dict(model: Any, fields: list[str]) -> dict[str, Any]:
    return {field: getattr(model, field) for field in fields}


def get_company_data(company_id: str, *, db: Session | None = None) -> dict[str, Any] | None:
    with _session_scope(db) as session:
        try:
            company = session.get(Company, company_id)
            if company is not None:
                return _model_dict(
                    company,
                    [
                        "id",
                        "name",
                        "business_number",
                        "industry",
                        "region",
                        "address",
                        "current_foreign_workers",
                        "housing_available",
                        "shift_type",
                        "requested_role",
                        "preferred_start_date",
                    ],
                )
        except SQLAlchemyError:
            pass

    return next((row for row in _seed_rows("companies.csv") if row.get("id") == company_id), None)


def get_candidate_profile_data(candidate_id: str, *, db: Session | None = None) -> dict[str, Any] | None:
    fields = [
        "id",
        "company_id",
        "name",
        "nationality",
        "desired_role",
        "available_from",
        "language",
        "visa_type",
        "arrival_due_date",
        "assigned_workplace",
        "visa_issuance_status",
        "pre_entry_training",
        "passport",
        "photo",
        "health_check",
        "understood_housing",
        "understood_shift",
        "status",
    ]
    with _session_scope(db) as session:
        try:
            candidate = session.get(Candidate, candidate_id)
            if candidate is not None:
                return _model_dict(candidate, fields)
        except SQLAlchemyError:
            pass

    return next((row for row in _seed_rows("candidates.csv") if row.get("id") == candidate_id), None)


def get_worker_profile_data(worker_id: str, *, db: Session | None = None) -> dict[str, Any] | None:
    fields = [
        "id",
        "company_id",
        "name",
        "nationality",
        "preferred_language",
        "email",
        "contact_channel",
        "visa_type",
        "visa_expires_at",
        "contract_starts_at",
        "contract_ends_at",
        "status",
        "worker_type",
    ]
    with _session_scope(db) as session:
        try:
            worker = session.get(Worker, worker_id)
            if worker is not None:
                return _model_dict(worker, fields)
        except SQLAlchemyError:
            pass

    return next((row for row in _seed_rows("workers.csv") if row.get("id") == worker_id), None)


def get_visa_status_data(worker_id: str, *, db: Session | None = None) -> dict[str, Any] | None:
    worker = get_worker_profile_data(worker_id, db=db)
    if worker is not None:
        return {
            "worker_id": worker_id,
            "visa_type": worker.get("visa_type"),
            "visa_expires_at": worker.get("visa_expires_at"),
            "expires_at": worker.get("visa_expires_at"),
            "status": worker.get("status"),
        }
    return next((row for row in _seed_rows("visas.csv") if row.get("worker_id") == worker_id), None)


def get_worker_documents_data(worker_id: str, *, db: Session | None = None) -> list[dict[str, Any]]:
    fields = [
        "id",
        "company_id",
        "worker_id",
        "doc_type",
        "status",
        "file_path",
        "submitted_at",
        "reviewed_at",
        "expires_at",
        "notes",
    ]
    with _session_scope(db) as session:
        try:
            rows = list(
                session.scalars(
                    select(WorkerDocument).where(WorkerDocument.worker_id == worker_id)
                )
            )
            daily_rows = _daily_briefing_document_rows(worker_id, session)
            # DB에 SUBMITTED/APPROVED 상태 레코드가 있으면 DB 데이터 사용
            # REQUESTED/PENDING 레코드만 있으면 실제 제출 상태를 모르므로 CSV seed와 병합
            submitted_rows = [r for r in rows if str(getattr(r, "status", "")).upper() in READY_DOCUMENT_STATUSES]
            if submitted_rows:
                return _merge_document_rows(
                    [_model_dict(row, fields) for row in rows],
                    daily_rows,
                )
            if rows:
                # DB에 레코드는 있지만 모두 비제출 상태 — CSV seed를 추가로 확인해 병합
                db_result = [_model_dict(row, fields) for row in rows]
                seed_result = [r for r in _seed_rows("worker_documents.csv") if r.get("worker_id") == worker_id]
                # CSV SUBMITTED 레코드가 DB 레코드를 override (DB의 REQUESTED 상태 대신 CSV의 SUBMITTED 신뢰)
                seed_submitted_types = {str(r.get("doc_type")) for r in seed_result if str(r.get("status", "")).upper() in READY_DOCUMENT_STATUSES}
                merged = [r for r in db_result if str(r.get("doc_type") or "") not in seed_submitted_types]
                extra = [r for r in seed_result if str(r.get("doc_type")) in seed_submitted_types]
                return _merge_document_rows(merged + extra, daily_rows)
            if daily_rows:
                return daily_rows
        except SQLAlchemyError:
            pass

    return [row for row in _seed_rows("worker_documents.csv") if row.get("worker_id") == worker_id]


def get_document_requirements_data(
    case_type: str,
    visa_type: str,
    *,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    fields = ["id", "case_type", "visa_type", "required_doc", "required", "source_id", "notes"]
    with _session_scope(db) as session:
        try:
            rows = list(
                session.scalars(
                    select(DocumentRequirement).where(
                        DocumentRequirement.case_type == case_type,
                        DocumentRequirement.visa_type == visa_type,
                    )
                )
            )
            if rows:
                return [_model_dict(row, fields) for row in rows]
        except SQLAlchemyError:
            pass

    return [
        row
        for row in _seed_rows("document_requirements.csv")
        if row.get("case_type", "").lower() == case_type.lower()
        and row.get("visa_type", "").upper() == visa_type.upper()
    ]


def calculate_missing_documents_for_worker(
    worker_id: str,
    case_type: str,
    *,
    db: Session | None = None,
) -> dict[str, Any]:
    worker = get_worker_profile_data(worker_id, db=db)
    if worker is None:
        return {"found": False, "worker_id": worker_id, "missing": [], "present": []}

    visa_type = str(worker.get("visa_type") or "")
    requirements = [
        row
        for row in get_document_requirements_data(case_type, visa_type, db=db)
        if _bool(row.get("required", True))
    ]
    documents = get_worker_documents_data(worker_id, db=db)
    submitted_types = _expanded_document_types({
        str(row.get("doc_type"))
        for row in documents
        if str(row.get("status", "")).upper() in READY_DOCUMENT_STATUSES
    })
    missing = [
        {"doc_type": str(row.get("required_doc")), "notes": str(row.get("notes") or "")}
        for row in requirements
        if str(row.get("required_doc")) not in submitted_types
    ]
    present = [
        str(row.get("required_doc"))
        for row in requirements
        if str(row.get("required_doc")) in submitted_types
    ]
    return {
        "found": True,
        "worker_id": worker_id,
        "visa_type": visa_type,
        "case_type": case_type,
        "required_count": len(requirements),
        "present_count": len(present),
        "missing_count": len(missing),
        "missing": missing,
        "present": present,
    }


def _daily_briefing_document_rows(worker_id: str, session: Session) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(DailyBriefingDocumentSource).where(DailyBriefingDocumentSource.worker_id == worker_id)
        )
    )
    return [
        {
            "id": row.id,
            "company_id": None,
            "worker_id": row.worker_id,
            "doc_type": row.document_type,
            "status": row.status,
            "file_path": None,
            "submitted_at": None,
            "reviewed_at": None,
            "expires_at": row.due_date,
            "notes": "daily_briefing_source_documents",
        }
        for row in rows
    ]


def _merge_document_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in groups:
        for row in group:
            doc_type = str(row.get("doc_type") or "")
            if not doc_type:
                continue
            current = merged.get(doc_type)
            if current is None:
                merged[doc_type] = row
                continue
            current_ready = str(current.get("status", "")).upper() in READY_DOCUMENT_STATUSES
            next_ready = str(row.get("status", "")).upper() in READY_DOCUMENT_STATUSES
            if next_ready and not current_ready:
                merged[doc_type] = row
    return list(merged.values())


def _expanded_document_types(doc_types: set[str]) -> set[str]:
    expanded = set(doc_types)
    for doc_type in list(doc_types):
        expanded.update(DOCUMENT_TYPE_EQUIVALENTS.get(doc_type, {doc_type}))
    return expanded


def calculate_candidate_readiness(
    *,
    candidate_id: str | None = None,
    company_id: str | None = None,
    requested_role: str | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    with _session_scope(db) as session:
        try:
            query = select(Candidate)
            if candidate_id:
                query = query.where(Candidate.id == candidate_id)
            if company_id:
                query = query.where(Candidate.company_id == company_id)
            rows = list(session.scalars(query))
            candidates = [
                _model_dict(
                    row,
                    [
                        "id",
                        "company_id",
                        "name",
                        "nationality",
                        "desired_role",
                        "available_from",
                        "language",
                        "visa_type",
                        "arrival_due_date",
                        "assigned_workplace",
                        "visa_issuance_status",
                        "pre_entry_training",
                        "passport",
                        "photo",
                        "health_check",
                        "understood_housing",
                        "understood_shift",
                        "status",
                    ],
                )
                for row in rows
            ]
        except SQLAlchemyError:
            candidates = []

    if not candidates:
        candidates = [
            row
            for row in _seed_rows("candidates.csv")
            if (not candidate_id or row.get("id") == candidate_id)
            and (not company_id or row.get("company_id") == company_id)
        ]

    return [_candidate_readiness(row, requested_role=requested_role) for row in candidates]


def _candidate_readiness(row: dict[str, Any], *, requested_role: str | None) -> dict[str, Any]:
    requirements = _candidate_requirement_results(row, requested_role=requested_role)
    ready_items = [
        key for key, result in requirements.items() if result["satisfied"]
    ]
    missing = [
        key for key, result in requirements.items() if not result["satisfied"]
    ]
    required_missing = [
        key
        for key, result in requirements.items()
        if result["required"] and not result["satisfied"]
    ]
    readiness_status = "ready" if not required_missing else "missing_required_info"
    return {
        "candidate_id": row.get("id"),
        "company_id": row.get("company_id"),
        "name": row.get("name"),
        "nationality": row.get("nationality"),
        "desired_role": row.get("desired_role"),
        "available_from": row.get("available_from"),
        "language": row.get("language"),
        "readiness_status": readiness_status,
        "ready_items": ready_items,
        "missing_or_unconfirmed_items": missing,
        "required_missing_items": required_missing,
        "requirements": requirements,
        "requirements_satisfied": not required_missing,
        "safe_description": _safe_candidate_description(row, missing),
    }


def mark_candidate_hired(
    candidate_id: str,
    *,
    db: Session | None = None,
    delete_after_hire: bool = True,
) -> dict[str, Any]:
    """Mark a candidate as hired; candidate records are temporary pre-hire data."""
    with _session_scope(db) as session:
        try:
            candidate = session.get(Candidate, candidate_id)
            if candidate is None:
                return {"found": False, "candidate_id": candidate_id, "deleted": False}
            snapshot = get_candidate_profile_data(candidate_id, db=session) or {"id": candidate_id}
            if delete_after_hire:
                session.query(CandidatePreEntryPackage).filter(
                    CandidatePreEntryPackage.candidate_id == candidate_id
                ).delete(synchronize_session=False)
                session.delete(candidate)
                session.commit()
                return {
                    "found": True,
                    "candidate_id": candidate_id,
                    "deleted": True,
                    "snapshot": snapshot,
                }
            candidate.status = "HIRED"
            session.commit()
            return {
                "found": True,
                "candidate_id": candidate_id,
                "deleted": False,
                "snapshot": snapshot,
            }
        except SQLAlchemyError:
            session.rollback()
            return {"found": False, "candidate_id": candidate_id, "deleted": False}


def _candidate_requirement_results(
    row: dict[str, Any],
    *,
    requested_role: str | None,
) -> dict[str, dict[str, Any]]:
    checklist = _candidate_checklist()
    checks = {
        "passport": _bool(row.get("passport")),
        "photo": _bool(row.get("photo")),
        "health_check": _bool(row.get("health_check")),
        "available_from": bool(row.get("available_from")),
        "desired_role_match": (
            bool(row.get("desired_role"))
            if not requested_role
            else str(row.get("desired_role") or "") == requested_role
        ),
        "understood_housing": _bool(row.get("understood_housing")),
        "understood_shift": _bool(row.get("understood_shift")),
    }
    output: dict[str, dict[str, Any]] = {}
    for field, satisfied in checks.items():
        spec = checklist.get(field, {})
        output[field] = {
            "label": spec.get("notes") or READY_CANDIDATE_FIELDS.get(field, field),
            "required": _bool(spec.get("required", True)),
            "satisfied": bool(satisfied),
            "source_id": spec.get("source_id", "internal_candidate_readiness_template"),
            "check_method": spec.get("check_method", "boolean"),
        }
    return output


def _candidate_checklist() -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in _seed_rows("candidate_readiness_checklist.csv")
        if row.get("case_type") == "candidate_review"
    ]
    return {row.get("field", ""): row for row in rows}


def _safe_candidate_description(row: dict[str, Any], missing: list[str]) -> str:
    if not missing:
        return f"후보 {row.get('id')}는 현재 필수 제출 준비 항목이 모두 확인되었습니다."
    labels = [READY_CANDIDATE_FIELDS.get(key, key) for key in missing]
    return f"후보 {row.get('id')}는 {', '.join(labels)} 확인이 추가로 필요합니다."


def get_message_template(purpose: str, language: str) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in _seed_jsonl("message_templates.jsonl")
            if row.get("purpose") == purpose and row.get("language") == language
        ),
        None,
    )
