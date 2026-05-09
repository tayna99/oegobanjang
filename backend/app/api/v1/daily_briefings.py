from __future__ import annotations

import csv
import json
import re
import uuid
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from app.services.daily_briefing_service import (
    DailyBriefingSourceImport,
    build_sqlalchemy_daily_briefing_service,
    daily_briefing_role_from_request,
    import_daily_briefing_sources,
    resolve_daily_briefing_allowed_company_ids,
)
from app.services.daily_briefing_scheduler import run_scheduled_daily_briefings
from app.db.session import get_sync_db
from app.config import get_settings
from app.models.daily_briefing import (
    DailyBriefingCandidateDocumentSource,
    DailyBriefingCandidateSource,
    DailyBriefingCitationRefreshQueue,
    DailyBriefingCitationSource,
    DailyBriefingCompanySource,
    DailyBriefingDocumentSource,
    DailyBriefingApproval,
    DailyBriefingExternalDeliveryJob,
    DailyBriefingHandoffExportArtifact,
    DailyBriefingMetricsSnapshot,
    DailyBriefingPilotFeedback,
    DailyBriefingResultRow,
    DailyBriefingReportingEventSource,
    DailyBriefingSchedulerRunHistory,
    DailyBriefingUserCompanyAccess,
    DailyBriefingWorkerSource,
)


router = APIRouter(prefix="/daily-briefings", tags=["daily-briefings"])


class DailyBriefingRunRequest(BaseModel):
    company_id: str
    date: str | None = None


class ScheduledDailyBriefingRunRequest(BaseModel):
    company_ids: list[str] | None = None
    date: str | None = None


class DailyBriefingSourceImportRequest(BaseModel):
    companies: list[dict] = Field(default_factory=list)
    workers: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)
    candidates: list[dict] = Field(default_factory=list)
    candidate_documents: list[dict] = Field(default_factory=list)
    reporting_events: list[dict] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    user_company_access: list[dict] = Field(default_factory=list)


class DailyBriefingCsvImportRequest(BaseModel):
    companies_csv: str | None = None
    workers_csv: str | None = None
    documents_csv: str | None = None
    candidates_csv: str | None = None
    candidate_documents_csv: str | None = None
    reporting_events_csv: str | None = None
    citations_csv: str | None = None
    user_company_access_csv: str | None = None


class DailyBriefingMetricsSnapshotRequest(BaseModel):
    company_id: str | None = None
    date: str | None = None


class DailyBriefingPilotFeedbackRequest(BaseModel):
    company_id: str
    case_id: str | None = None
    feedback_type: str
    message: str


def _error(error_code: str, message: str, trace_id: str = "trace_unavailable") -> dict[str, str]:
    return {"error_code": error_code, "message": message, "trace_id": trace_id}


def _ensure_v4_tables(db: Session) -> None:
    Base.metadata.create_all(
        bind=db.get_bind(),
        tables=[
            DailyBriefingSchedulerRunHistory.__table__,
            DailyBriefingMetricsSnapshot.__table__,
            DailyBriefingPilotFeedback.__table__,
            DailyBriefingCitationRefreshQueue.__table__,
        ],
        checkfirst=True,
    )


def _csv_rows(raw_csv: str | None) -> list[dict]:
    if not raw_csv or not raw_csv.strip():
        return []
    rows: list[dict] = []
    for row in csv.DictReader(StringIO(raw_csv.strip())):
        cleaned = {
            key: _csv_value(value)
            for key, value in row.items()
            if key is not None and key.strip()
        }
        rows.append(cleaned)
    return rows


def _csv_value(value: str | None) -> object:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    return stripped


def _source_csv_fields(request: DailyBriefingCsvImportRequest) -> dict[str, str | None]:
    return {
        "companies": request.companies_csv,
        "workers": request.workers_csv,
        "documents": request.documents_csv,
        "candidates": request.candidates_csv,
        "candidate_documents": request.candidate_documents_csv,
        "reporting_events": request.reporting_events_csv,
        "citations": request.citations_csv,
        "user_company_access": request.user_company_access_csv,
    }


def _source_import_from_csv_request(request: DailyBriefingCsvImportRequest) -> DailyBriefingSourceImport:
    return DailyBriefingSourceImport(
        companies=_csv_rows(request.companies_csv),
        workers=_csv_rows(request.workers_csv),
        documents=_csv_rows(request.documents_csv),
        candidates=_csv_rows(request.candidates_csv),
        candidate_documents=_csv_rows(request.candidate_documents_csv),
        reporting_events=_csv_rows(request.reporting_events_csv),
        citations=_csv_rows(request.citations_csv),
        user_company_access=_csv_rows(request.user_company_access_csv),
    )


def _validate_date(value: object) -> bool:
    if value is None:
        return True
    text = str(value)
    if not re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _csv_validation_report(request: DailyBriefingCsvImportRequest, db: Session) -> dict:
    required_columns = {
        "companies": {"company_id", "company_name", "timezone"},
        "workers": {"worker_id", "company_id", "display_name_masked"},
        "documents": {"worker_id", "document_type", "status"},
        "candidates": {"candidate_id", "company_id", "display_name_masked"},
        "candidate_documents": {"candidate_id", "document_type", "status"},
        "reporting_events": {"event_id", "company_id", "event_type", "occurred_at", "discovered_at", "reporting_due_date"},
        "citations": {"citation_id", "title", "source_type", "source", "ingest_at"},
        "user_company_access": {"user_id", "company_id"},
    }
    id_fields = {
        "companies": ["company_id"],
        "workers": ["worker_id"],
        "documents": ["worker_id", "document_type"],
        "candidates": ["candidate_id"],
        "candidate_documents": ["candidate_id", "document_type"],
        "reporting_events": ["event_id"],
        "citations": ["citation_id"],
        "user_company_access": ["user_id", "company_id"],
    }
    date_fields = {
        "workers": ["visa_expiry_date", "contract_end_date"],
        "documents": ["due_date"],
        "candidate_documents": ["due_date"],
        "reporting_events": ["occurred_at", "discovered_at", "reporting_due_date", "reported_at"],
        "citations": ["ingest_at", "retrieved_at"],
    }
    issues: list[dict] = []
    warnings: list[dict] = []
    row_counts: dict[str, int] = {}
    parsed_rows: dict[str, list[dict]] = {}

    for source_type, raw_csv in _source_csv_fields(request).items():
        rows = _csv_rows(raw_csv)
        parsed_rows[source_type] = rows
        row_counts[source_type] = len(rows)
        if not raw_csv or not raw_csv.strip():
            continue
        reader = csv.DictReader(StringIO(raw_csv.strip()))
        headers = {header.strip() for header in (reader.fieldnames or []) if header}
        missing = sorted(required_columns[source_type] - headers)
        for column in missing:
            issues.append(
                {
                    "source_type": source_type,
                    "row_number": 1,
                    "issue_type": "missing_required_column",
                    "message": f"Required column is missing: {column}",
                }
            )
        seen: set[tuple] = set()
        for index, row in enumerate(rows, start=2):
            key = tuple(row.get(field) for field in id_fields[source_type])
            if all(key):
                if key in seen:
                    issues.append(
                        {
                            "source_type": source_type,
                            "row_number": index,
                            "issue_type": "duplicate_row",
                            "message": "Duplicate source row key.",
                        }
                    )
                seen.add(key)
            for field in date_fields.get(source_type, []):
                if field in row and not _validate_date(row.get(field)):
                    issues.append(
                        {
                            "source_type": source_type,
                            "row_number": index,
                            "issue_type": "invalid_date",
                            "message": f"Invalid date value in {field}.",
                        }
                    )

    known_worker_ids = {row.id for row in db.query(DailyBriefingWorkerSource).all()}
    known_worker_ids.update(
        str(row.get("worker_id"))
        for row in parsed_rows.get("workers", [])
        if row.get("worker_id")
    )
    for index, row in enumerate(parsed_rows.get("documents", []), start=2):
        worker_id = row.get("worker_id")
        if worker_id and worker_id not in known_worker_ids:
            issues.append(
                {
                    "source_type": "documents",
                    "row_number": index,
                    "issue_type": "unknown_worker_id",
                    "message": "Document row references an unknown worker_id.",
                }
            )

    return {
        "status": "invalid" if issues else "valid",
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "row_counts": row_counts,
        "issues": issues,
        "warnings": warnings,
        "pii_policy": "Validation reports never echo raw source values.",
    }


def _briefing_row_summary(row: DailyBriefingResultRow) -> dict:
    payload = json.loads(row.payload)
    risk_summary = payload.get("risk_summary", {})
    citation_summaries = payload.get("citation_summaries", [])
    recommended_actions = payload.get("recommended_actions", [])
    return {
        "briefing_run_id": row.id,
        "company_id": row.company_id,
        "date": row.date,
        "total_count": risk_summary.get("total_count", 0),
        "critical_count": risk_summary.get("critical_count", 0),
        "high_count": risk_summary.get("high_count", 0),
        "medium_count": risk_summary.get("medium_count", 0),
        "low_count": risk_summary.get("low_count", 0),
        "approval_pending_count": sum(
            1 for action in recommended_actions if action.get("status") == "pending_approval"
        ),
        "missing_evidence_count": sum(
            1 for citation in citation_summaries if citation.get("missing_evidence")
        ),
        "source_snapshot_hash": row.source_snapshot_hash,
        "updated_at": row.updated_at.isoformat(),
    }


def _metrics_summary(
    db: Session,
    *,
    company_id: str | None,
    allowed_company_ids: list[str] | None,
) -> dict:
    def scoped(query, model):
        if company_id:
            return query.filter(model.company_id == company_id)
        if allowed_company_ids is not None:
            return query.filter(model.company_id.in_(allowed_company_ids))
        return query

    briefing_rows = scoped(db.query(DailyBriefingResultRow), DailyBriefingResultRow).all()
    approval_rows = scoped(db.query(DailyBriefingApproval), DailyBriefingApproval).all()
    export_count = scoped(db.query(DailyBriefingHandoffExportArtifact), DailyBriefingHandoffExportArtifact).count()
    mock_dispatch_count = scoped(
        db.query(DailyBriefingExternalDeliveryJob).filter(
            DailyBriefingExternalDeliveryJob.status == "mock_dispatched"
        ),
        DailyBriefingExternalDeliveryJob,
    ).count()

    approved_count = sum(1 for row in approval_rows if row.status == "approved")
    revision_count = sum(1 for row in approval_rows if row.status == "revision_requested")
    rejected_count = sum(1 for row in approval_rows if row.status == "rejected")
    missing_evidence_count = 0
    high_or_critical_count = 0
    for row in briefing_rows:
        payload = json.loads(row.payload)
        missing_evidence_count += sum(
            1 for citation in payload.get("citation_summaries", []) if citation.get("missing_evidence")
        )
        risk_summary = payload.get("risk_summary", {})
        high_or_critical_count += int(risk_summary.get("critical_count", 0)) + int(
            risk_summary.get("high_count", 0)
        )

    total_approvals = len(approval_rows)
    approval_rate = approved_count / total_approvals if total_approvals else 0.0
    revision_rate = revision_count / total_approvals if total_approvals else 0.0
    rejection_rate = rejected_count / total_approvals if total_approvals else 0.0
    return {
        "company_id": company_id,
        "briefing_run_count": len(briefing_rows),
        "approval_count": total_approvals,
        "approved_count": approved_count,
        "revision_requested_count": revision_count,
        "rejected_count": rejected_count,
        "approval_rate": approval_rate,
        "revision_rate": revision_rate,
        "rejection_rate": rejection_rate,
        "handoff_export_count": export_count,
        "mock_dispatch_count": mock_dispatch_count,
        "missing_evidence_count": missing_evidence_count,
        "high_or_critical_risk_count": high_or_critical_count,
    }


def _check_company_scope(db: Session, company_id: str | None, x_company_id: str | None, x_user_id: str | None, authorization: str | None) -> list[str] | None:
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    if company_id and allowed_company_ids is not None and company_id not in allowed_company_ids:
        raise HTTPException(
            status_code=403,
            detail=_error("TENANT_SCOPE_VIOLATION", "Requested resource is outside the allowed company scope."),
        )
    return allowed_company_ids


@router.post("/run")
def run_daily_briefing(
    request: DailyBriefingRunRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
            db,
            user_id=x_user_id,
            header_company_id=x_company_id,
            authorization=authorization,
        )
        user_role = daily_briefing_role_from_request(
            header_role=x_user_role,
            authorization=authorization,
        )
        result = service.run_daily_briefing(
            company_id=request.company_id,
            date=request.date,
            user_role=user_role,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=_error(str(exc.args[0]), "Requested company is outside the allowed company scope."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error(str(exc.args[0]), "Required company or worker context is missing."),
        ) from exc
    except RuntimeError as exc:
        code = str(exc.args[0])
        status_code = 500 if code == "STATE_SAVE_FAILED" else 400
        raise HTTPException(status_code=status_code, detail=_error(code, "Daily briefing failed safely.")) from exc
    return result.model_dump()


@router.post("/scheduled-run")
def run_scheduled_daily_briefings_api(
    request: ScheduledDailyBriefingRunRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role not in {"admin", "system"}:
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin or system can run scheduled briefings."),
        )
    result = run_scheduled_daily_briefings(
        db,
        company_ids=request.company_ids,
        run_date=request.date,
    )
    _ensure_v4_tables(db)
    row = DailyBriefingSchedulerRunHistory(
        id=f"sch_{uuid.uuid4().hex}",
        run_date=result.run_date,
        status="completed" if result.failed_count == 0 else "partial_failure",
        company_ids=json.dumps(list(request.company_ids or []), ensure_ascii=False),
        total_companies=str(result.total_companies),
        succeeded_count=str(result.succeeded_count),
        failed_count=str(result.failed_count),
        payload=json.dumps(result.model_dump(), ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    return result.model_dump()


@router.post("/sources/import")
def import_daily_briefing_source_rows(
    request: DailyBriefingSourceImportRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can import Daily Briefing source rows."),
        )
    try:
        result = import_daily_briefing_sources(
            db,
            DailyBriefingSourceImport(**request.model_dump()),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=_error("SOURCE_IMPORT_FAILED", str(exc)),
        ) from exc
    return result


@router.post("/sources/import-csv")
def import_daily_briefing_source_csv_rows(
    request: DailyBriefingCsvImportRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can import Daily Briefing source CSV rows."),
        )
    payload = _source_import_from_csv_request(request)
    try:
        result = import_daily_briefing_sources(db, payload)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=_error("SOURCE_IMPORT_FAILED", str(exc)),
        ) from exc
    return result


@router.post("/sources/validate-csv")
def validate_daily_briefing_source_csv_rows(
    request: DailyBriefingCsvImportRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can validate Daily Briefing source CSV rows."),
        )
    return _csv_validation_report(request, db)


@router.post("/sources/upload-csv")
def upload_daily_briefing_source_csv(
    source_type: str = Form(...),
    file: UploadFile = File(...),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can upload Daily Briefing source CSV rows."),
        )
    field_by_source_type = {
        "companies": "companies_csv",
        "workers": "workers_csv",
        "documents": "documents_csv",
        "candidates": "candidates_csv",
        "candidate_documents": "candidate_documents_csv",
        "reporting_events": "reporting_events_csv",
        "citations": "citations_csv",
        "user_company_access": "user_company_access_csv",
    }
    if source_type not in field_by_source_type:
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_SOURCE_TYPE", "Unsupported Daily Briefing source_type."),
        )
    raw = file.file.read().decode("utf-8-sig")
    request = DailyBriefingCsvImportRequest(**{field_by_source_type[source_type]: raw})
    report = _csv_validation_report(request, db)
    if report["status"] == "invalid":
        raise HTTPException(
            status_code=400,
            detail={
                **_error("CSV_VALIDATION_FAILED", "CSV validation failed."),
                "validation_report": report,
            },
        )
    try:
        result = import_daily_briefing_sources(db, _source_import_from_csv_request(request))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=_error("SOURCE_IMPORT_FAILED", str(exc)),
        ) from exc
    return result


@router.get("/sources/summary")
def get_daily_briefing_source_summary(
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can view Daily Briefing source summaries."),
        )
    source_counts = {
        "companies": db.query(DailyBriefingCompanySource).count(),
        "workers": db.query(DailyBriefingWorkerSource).count(),
        "documents": db.query(DailyBriefingDocumentSource).count(),
        "candidates": db.query(DailyBriefingCandidateSource).count(),
        "candidate_documents": db.query(DailyBriefingCandidateDocumentSource).count(),
        "reporting_events": db.query(DailyBriefingReportingEventSource).count(),
        "citations": db.query(DailyBriefingCitationSource).count(),
        "user_company_access": db.query(DailyBriefingUserCompanyAccess).count(),
    }
    return {
        "status": "ready",
        "source_counts": source_counts,
        "pii_policy": "Raw source PII is never returned by this summary endpoint.",
    }


@router.get("/scheduler/status")
def get_daily_briefing_scheduler_status(
    request: Request,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
) -> dict:
    if x_user_role not in {"admin", "system"}:
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin or system can view scheduler status."),
        )
    settings = get_settings()
    scheduler = getattr(request.app.state, "daily_briefing_scheduler", None)
    last_run = getattr(scheduler, "last_run", None)
    return {
        "enabled": settings.daily_briefing_scheduler_enabled,
        "run_on_startup": settings.daily_briefing_scheduler_run_on_startup,
        "interval_seconds": settings.daily_briefing_scheduler_interval_seconds,
        "timezone": settings.daily_briefing_scheduler_timezone,
        "configured_company_ids": settings.daily_briefing_scheduler_company_id_list,
        "running": bool(getattr(getattr(scheduler, "_thread", None), "is_alive", lambda: False)()),
        "last_run": last_run.model_dump() if last_run is not None else None,
    }


@router.get("/scheduler/history")
def list_daily_briefing_scheduler_history(
    company_id: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    _ensure_v4_tables(db)
    allowed_company_ids = _check_company_scope(db, company_id, x_company_id, x_user_id, authorization)
    rows = db.query(DailyBriefingSchedulerRunHistory).order_by(
        DailyBriefingSchedulerRunHistory.created_at.desc()
    ).all()
    runs = []
    for row in rows:
        company_ids = json.loads(row.company_ids)
        if company_id and company_id not in company_ids:
            continue
        if allowed_company_ids is not None and not any(cid in allowed_company_ids for cid in company_ids):
            continue
        runs.append(
            {
                "run_id": row.id,
                "date": row.run_date,
                "status": row.status,
                "company_ids": company_ids,
                "total_companies": int(row.total_companies),
                "succeeded_count": int(row.succeeded_count),
                "failed_count": int(row.failed_count),
                "created_at": row.created_at.isoformat(),
            }
        )
    return {"total_count": len(runs), "runs": runs}


@router.get("/quality/summary")
def get_daily_briefing_data_quality_summary(
    company_id: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    allowed_company_ids = _check_company_scope(db, company_id, x_company_id, x_user_id, authorization)
    worker_query = db.query(DailyBriefingWorkerSource)
    if company_id:
        worker_query = worker_query.filter(DailyBriefingWorkerSource.company_id == company_id)
    elif allowed_company_ids is not None:
        worker_query = worker_query.filter(DailyBriefingWorkerSource.company_id.in_(allowed_company_ids))
    workers = worker_query.all()
    worker_ids = {worker.id for worker in workers}
    documents = db.query(DailyBriefingDocumentSource).all()
    citations = {citation.id for citation in db.query(DailyBriefingCitationSource).all()}
    canonical_citations = {
        "cit_visa_expiry",
        "cit_missing_document",
        "cit_contract_visa_conflict",
        "cit_reporting_deadline",
        "cit_quota_review",
    }
    orphan_documents = [
        document
        for document in documents
        if document.worker_id not in worker_ids and (company_id is None or document.worker_id not in worker_ids)
    ]
    missing_visa_expiry_count = sum(1 for worker in workers if not worker.visa_expiry_date)
    missing_contract_end_count = sum(1 for worker in workers if not worker.contract_end_date)
    citation_gap_count = len(canonical_citations - citations)
    issues = []
    if missing_visa_expiry_count:
        issues.append({"issue_type": "missing_visa_expiry", "severity": "high", "count": missing_visa_expiry_count})
    if missing_contract_end_count:
        issues.append({"issue_type": "missing_contract_end", "severity": "medium", "count": missing_contract_end_count})
    if orphan_documents:
        issues.append({"issue_type": "orphan_document", "severity": "high", "count": len(orphan_documents)})
    if citation_gap_count:
        issues.append({"issue_type": "citation_gap", "severity": "medium", "count": citation_gap_count})
    return {
        "company_id": company_id,
        "worker_count": len(workers),
        "missing_visa_expiry_count": missing_visa_expiry_count,
        "missing_contract_end_count": missing_contract_end_count,
        "orphan_document_count": len(orphan_documents),
        "citation_gap_count": citation_gap_count,
        "issues": issues,
        "pii_policy": "Data quality summaries use IDs and counts only.",
    }


@router.get("/history/list")
def list_daily_briefing_history(
    company_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    if company_id and allowed_company_ids is not None and company_id not in allowed_company_ids:
        raise HTTPException(
            status_code=403,
            detail=_error("TENANT_SCOPE_VIOLATION", "Requested history is outside the allowed company scope."),
        )
    query = db.query(DailyBriefingResultRow)
    if company_id:
        query = query.filter(DailyBriefingResultRow.company_id == company_id)
    elif allowed_company_ids is not None:
        query = query.filter(DailyBriefingResultRow.company_id.in_(allowed_company_ids))
    if date_from:
        query = query.filter(DailyBriefingResultRow.date >= date_from)
    if date_to:
        query = query.filter(DailyBriefingResultRow.date <= date_to)
    rows = query.order_by(DailyBriefingResultRow.date.desc(), DailyBriefingResultRow.updated_at.desc()).all()
    return {
        "total_count": len(rows),
        "runs": [_briefing_row_summary(row) for row in rows],
    }


@router.get("/metrics/summary")
def get_daily_briefing_pilot_metrics(
    company_id: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    if company_id and allowed_company_ids is not None and company_id not in allowed_company_ids:
        raise HTTPException(
            status_code=403,
            detail=_error("TENANT_SCOPE_VIOLATION", "Requested metrics are outside the allowed company scope."),
        )
    return _metrics_summary(db, company_id=company_id, allowed_company_ids=allowed_company_ids)


@router.post("/metrics/snapshot")
def create_daily_briefing_metrics_snapshot(
    request: DailyBriefingMetricsSnapshotRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role not in {"admin", "system"}:
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin or system can snapshot Daily Briefing metrics."),
        )
    _ensure_v4_tables(db)
    allowed_company_ids = _check_company_scope(db, request.company_id, x_company_id, x_user_id, authorization)
    metrics = _metrics_summary(db, company_id=request.company_id, allowed_company_ids=allowed_company_ids)
    snapshot_date = request.date or datetime.now().date().isoformat()
    snapshot_id = f"met_{request.company_id or 'all'}_{snapshot_date}"
    row = DailyBriefingMetricsSnapshot(
        id=snapshot_id,
        company_id=request.company_id,
        snapshot_date=snapshot_date,
        payload=json.dumps(metrics, ensure_ascii=False),
    )
    merged = db.merge(row)
    db.commit()
    return {
        "snapshot_id": merged.id,
        "company_id": merged.company_id,
        "snapshot_date": merged.snapshot_date,
        "metrics": metrics,
        "created_at": merged.created_at.isoformat(),
    }


@router.get("/metrics/snapshots")
def list_daily_briefing_metrics_snapshots(
    company_id: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    _ensure_v4_tables(db)
    _check_company_scope(db, company_id, x_company_id, x_user_id, authorization)
    query = db.query(DailyBriefingMetricsSnapshot)
    if company_id:
        query = query.filter(DailyBriefingMetricsSnapshot.company_id == company_id)
    rows = query.order_by(DailyBriefingMetricsSnapshot.created_at.desc()).all()
    return {
        "total_count": len(rows),
        "snapshots": [
            {
                "snapshot_id": row.id,
                "company_id": row.company_id,
                "snapshot_date": row.snapshot_date,
                "metrics": json.loads(row.payload),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/feedback")
def create_daily_briefing_pilot_feedback(
    request: DailyBriefingPilotFeedbackRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    _ensure_v4_tables(db)
    _check_company_scope(db, request.company_id, x_company_id, x_user_id, authorization)
    row = DailyBriefingPilotFeedback(
        id=f"fb_{uuid.uuid4().hex}",
        company_id=request.company_id,
        case_id=request.case_id,
        feedback_type=request.feedback_type,
        payload=json.dumps(
            {
                "summary": request.message[:400],
                "redaction_policy": "operator feedback is stored as summary text only",
            },
            ensure_ascii=False,
        ),
    )
    db.add(row)
    db.commit()
    return {
        "feedback_id": row.id,
        "company_id": row.company_id,
        "case_id": row.case_id,
        "feedback_type": row.feedback_type,
        "summary": json.loads(row.payload)["summary"],
        "created_at": row.created_at.isoformat(),
    }


@router.get("/feedback")
def list_daily_briefing_pilot_feedback(
    company_id: str | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    _ensure_v4_tables(db)
    _check_company_scope(db, company_id, x_company_id, x_user_id, authorization)
    query = db.query(DailyBriefingPilotFeedback)
    if company_id:
        query = query.filter(DailyBriefingPilotFeedback.company_id == company_id)
    rows = query.order_by(DailyBriefingPilotFeedback.created_at.desc()).all()
    return {
        "total_count": len(rows),
        "items": [
            {
                "feedback_id": row.id,
                "company_id": row.company_id,
                "case_id": row.case_id,
                "feedback_type": row.feedback_type,
                "summary": json.loads(row.payload).get("summary"),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/{briefing_run_id}")
def get_daily_briefing(
    briefing_run_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    result = service.repository.briefings.get(briefing_run_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=_error("MISSING_REQUIRED_CONTEXT", "Daily briefing result was not found."),
        )
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    if allowed_company_ids is not None and result.company_id not in allowed_company_ids:
        raise HTTPException(
            status_code=403,
            detail=_error("TENANT_SCOPE_VIOLATION", "Requested briefing is outside the allowed company scope."),
        )
    return result.model_dump()
