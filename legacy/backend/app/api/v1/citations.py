from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from backend.app.db.base import Base
from app.db.session import get_sync_db
from app.models.daily_briefing import (
    DailyBriefingCitationRefreshQueue,
    DailyBriefingCitationSource,
    DailyBriefingEvidenceEvent,
)
from app.services.citation_refresh_worker import OfficialCitationRefreshWorker
from app.services.daily_briefing_service import build_sqlalchemy_daily_briefing_service


router = APIRouter(prefix="/citations", tags=["citations"])


class CitationRefreshQueueRequest(BaseModel):
    citation_id: str
    reason: str
    priority: str = "medium"


class CitationManualRefreshPayload(BaseModel):
    title: str | None = None
    source_type: str | None = None
    source: str | None = None
    ingest_at: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    chunk_version: str | None = None
    retrieved_at: str | None = None
    source_url: str | None = None


class CitationRefreshProcessRequest(BaseModel):
    refresh_mode: str = "manual_source"
    citation: CitationManualRefreshPayload | None = None


def _error(error_code: str, message: str, trace_id: str = "trace_unavailable") -> dict[str, str]:
    return {"error_code": error_code, "message": message, "trace_id": trace_id}


def _matches_filter(actual: bool, expected: bool | None) -> bool:
    return expected is None or actual is expected


def _ensure_refresh_queue_table(db: Session) -> None:
    Base.metadata.create_all(
        bind=db.get_bind(),
        tables=[
            DailyBriefingCitationRefreshQueue.__table__,
            DailyBriefingCitationSource.__table__,
            DailyBriefingEvidenceEvent.__table__,
        ],
        checkfirst=True,
    )


def _official_source_fetch_enabled() -> bool:
    return get_settings().daily_briefing_citation_official_fetch_enabled


def _build_official_source_fetch_worker() -> OfficialCitationRefreshWorker:
    return OfficialCitationRefreshWorker()


def _queue_item_response(row: DailyBriefingCitationRefreshQueue) -> dict:
    payload = json.loads(row.payload)
    return {
        "queue_id": row.id,
        "citation_id": row.citation_id,
        "reason": row.reason,
        "priority": row.priority,
        "status": row.status,
        "failure_reason": payload.get("failure_reason"),
        "external_fetch_performed": bool(payload.get("external_fetch_performed", False)),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _citation_refresh_event_payload(
    *,
    event_id: str,
    event_type: str,
    citation_id: str,
    queue_id: str,
    summary: str,
    extra: dict,
) -> str:
    return json.dumps(
        {
            "event_id": event_id,
            "event_version": "v1",
            "trace_id": f"trace_citation_refresh_{queue_id}",
            "case_id": None,
            "request_id": queue_id,
            "event_type": event_type,
            "actor_type": "system",
            "node_name": "citation_refresh_worker",
            "summary": summary,
            "citation_ids": [citation_id],
            "redacted_input_hash": None,
            "redacted_output_hash": None,
            "hash_algorithm": "sha256",
            "payload_ref": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        },
        ensure_ascii=False,
    )


@router.get("/admin/list")
def list_citations_for_admin(
    missing_evidence: bool | None = None,
    stale_evidence: bool | None = None,
    synthetic_only: bool | None = None,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can list citation validation status."),
        )
    service = build_sqlalchemy_daily_briefing_service(db)
    items = []
    for citation_id in sorted(service.repository.citations):
        detail = service.get_citation_detail(citation_id)
        if not _matches_filter(detail.missing_evidence, missing_evidence):
            continue
        if not _matches_filter(detail.stale_evidence, stale_evidence):
            continue
        if not _matches_filter(detail.synthetic_only, synthetic_only):
            continue
        items.append(detail.model_dump())
    return {
        "total_count": len(items),
        "items": items,
    }


@router.post("/refresh-queue")
def create_citation_refresh_queue_item(
    request: CitationRefreshQueueRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can queue citation refresh work."),
        )
    _ensure_refresh_queue_table(db)
    row = DailyBriefingCitationRefreshQueue(
        id=f"crq_{uuid.uuid4().hex}",
        citation_id=request.citation_id,
        reason=request.reason,
        priority=request.priority,
        status="open",
        payload=json.dumps(
            {
                "citation_id": request.citation_id,
                "reason": request.reason,
                "priority": request.priority,
                "external_fetch_performed": False,
            },
            ensure_ascii=False,
        ),
    )
    db.add(row)
    db.commit()
    return {
        **_queue_item_response(row),
    }


@router.get("/refresh-queue")
def list_citation_refresh_queue(
    status: str | None = None,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can list citation refresh work."),
        )
    _ensure_refresh_queue_table(db)
    query = db.query(DailyBriefingCitationRefreshQueue)
    if status:
        query = query.filter(DailyBriefingCitationRefreshQueue.status == status)
    rows = query.order_by(DailyBriefingCitationRefreshQueue.created_at.desc()).all()
    return {
        "total_count": len(rows),
        "items": [
            _queue_item_response(row)
            for row in rows
        ],
    }


@router.post("/refresh-queue/{queue_id}/process")
def process_citation_refresh_queue_item(
    queue_id: str,
    request: CitationRefreshProcessRequest,
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict:
    if x_user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail=_error("UNAUTHORIZED_ROLE", "Only admin can process citation refresh work."),
        )
    _ensure_refresh_queue_table(db)
    row = db.get(DailyBriefingCitationRefreshQueue, queue_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=_error("MISSING_REQUIRED_CONTEXT", "Citation refresh queue item was not found."),
        )
    payload = json.loads(row.payload)
    row.status = "running"
    payload["status_transition"] = ["open", "running"]
    payload["external_fetch_performed"] = False

    if request.refresh_mode == "official_source_fetch":
        if not _official_source_fetch_enabled():
            row.status = "open"
            payload["status_transition"] = ["open"]
            payload["failure_reason"] = "official_source_fetch_disabled"
            row.payload = json.dumps(payload, ensure_ascii=False)
            db.merge(row)
            db.commit()
            raise HTTPException(
                status_code=409,
                detail=_error(
                    "OFFICIAL_SOURCE_FETCH_DISABLED",
                    "Official source fetch is disabled. Use manual_source refresh or enable the feature flag.",
                ),
            )
        if request.citation is None or not request.citation.source_url:
            row.status = "failed"
            payload["failure_reason"] = "source_url_required"
            payload["status_transition"].append("failed")
            row.payload = json.dumps(payload, ensure_ascii=False)
            db.merge(row)
            event_id = f"evt_citation_refresh_failed_{queue_id}"
            db.add(
                DailyBriefingEvidenceEvent(
                    id=event_id,
                    case_id=None,
                    company_id=None,
                    event_type="citation_refresh_failed",
                    payload=_citation_refresh_event_payload(
                        event_id=event_id,
                        event_type="citation_refresh_failed",
                        citation_id=row.citation_id,
                        queue_id=row.id,
                        summary="Citation refresh failed safely because official source URL was missing.",
                        extra={
                            "failure_reason": "source_url_required",
                            "external_fetch_performed": False,
                        },
                    ),
                )
            )
            db.commit()
            return _queue_item_response(row)

        citation = request.citation
        existing = db.get(DailyBriefingCitationSource, row.citation_id)
        title = citation.title or (existing.title if existing else row.citation_id)
        source_type = citation.source_type or (existing.source_type if existing else "official")
        try:
            refresh_result = _build_official_source_fetch_worker().refresh(
                citation_id=row.citation_id,
                source_url=citation.source_url,
                title=title,
                source_type=source_type,
            )
        except Exception as exc:
            row.status = "failed"
            payload["failure_reason"] = str(exc.args[0]) if exc.args else "official_source_fetch_failed"
            payload["status_transition"].append("failed")
            row.payload = json.dumps(payload, ensure_ascii=False)
            db.merge(row)
            event_id = f"evt_citation_refresh_failed_{queue_id}"
            db.add(
                DailyBriefingEvidenceEvent(
                    id=event_id,
                    case_id=None,
                    company_id=None,
                    event_type="citation_refresh_failed",
                    payload=_citation_refresh_event_payload(
                        event_id=event_id,
                        event_type="citation_refresh_failed",
                        citation_id=row.citation_id,
                        queue_id=row.id,
                        summary="Citation refresh failed safely during official source fetch.",
                        extra={
                            "failure_reason": payload["failure_reason"],
                            "external_fetch_performed": True,
                        },
                    ),
                )
            )
            db.commit()
            return _queue_item_response(row)

        updated = DailyBriefingCitationSource(
            id=row.citation_id,
            title=refresh_result.title,
            source_type=refresh_result.source_type,
            source=refresh_result.extracted_text,
            ingest_at=refresh_result.ingest_at,
            document_id=refresh_result.document_id,
            chunk_id=refresh_result.chunk_id,
            chunk_version=refresh_result.chunk_version,
            retrieved_at=refresh_result.retrieved_at,
            source_url=refresh_result.source_url,
        )
        db.merge(updated)
        row.status = "completed"
        payload.update(
            {
                "status_transition": [*payload["status_transition"], "completed"],
                "refresh_mode": "official_source_fetch",
                "refreshed_citation_id": row.citation_id,
                "document_id": updated.document_id,
                "chunk_id": updated.chunk_id,
                "chunk_version": updated.chunk_version,
                "source_url": updated.source_url,
                "source_hash": refresh_result.source_hash,
                "content_type": refresh_result.content_type,
                "chunk_count": refresh_result.chunk_count,
                "chunks_path": refresh_result.chunks_path,
                "chroma_records_path": refresh_result.chroma_records_path,
                "chroma_persist_dir": refresh_result.chroma_persist_dir,
                "chroma_collection_name": refresh_result.chroma_collection_name,
                "chroma_upsert_count": refresh_result.chroma_upsert_count,
                "external_fetch_performed": True,
            }
        )
        row.payload = json.dumps(payload, ensure_ascii=False)
        db.merge(row)
        event_id = f"evt_citation_refreshed_{queue_id}"
        db.add(
            DailyBriefingEvidenceEvent(
                id=event_id,
                case_id=None,
                company_id=None,
                event_type="citation_refreshed",
                payload=_citation_refresh_event_payload(
                    event_id=event_id,
                    event_type="citation_refreshed",
                    citation_id=row.citation_id,
                    queue_id=row.id,
                    summary="Citation refresh completed from fetched official source content and RAG chunks were reindexed.",
                    extra={
                        "refresh_mode": "official_source_fetch",
                        "document_id": updated.document_id,
                        "chunk_id": updated.chunk_id,
                        "chunk_version": updated.chunk_version,
                        "source_url": updated.source_url,
                        "source_hash": refresh_result.source_hash,
                        "content_type": refresh_result.content_type,
                        "chunk_count": refresh_result.chunk_count,
                        "chunks_path": refresh_result.chunks_path,
                        "chroma_records_path": refresh_result.chroma_records_path,
                        "chroma_persist_dir": refresh_result.chroma_persist_dir,
                        "chroma_collection_name": refresh_result.chroma_collection_name,
                        "chroma_upsert_count": refresh_result.chroma_upsert_count,
                        "external_fetch_performed": True,
                    },
                ),
            )
        )
        db.commit()
        return _queue_item_response(row)

    if request.refresh_mode != "manual_source" or request.citation is None:
        row.status = "failed"
        payload["failure_reason"] = "manual_source_required"
        payload["status_transition"].append("failed")
        row.payload = json.dumps(payload, ensure_ascii=False)
        db.merge(row)
        event_id = f"evt_citation_refresh_failed_{queue_id}"
        db.add(
            DailyBriefingEvidenceEvent(
                id=event_id,
                case_id=None,
                company_id=None,
                event_type="citation_refresh_failed",
                payload=_citation_refresh_event_payload(
                    event_id=event_id,
                    event_type="citation_refresh_failed",
                    citation_id=row.citation_id,
                    queue_id=row.id,
                    summary="Citation refresh failed safely because manual source input was missing.",
                    extra={
                        "failure_reason": "manual_source_required",
                        "external_fetch_performed": False,
                    },
                ),
            )
        )
        db.commit()
        return _queue_item_response(row)

    citation = request.citation
    existing = db.get(DailyBriefingCitationSource, row.citation_id)
    updated = DailyBriefingCitationSource(
        id=row.citation_id,
        title=citation.title or (existing.title if existing else row.citation_id),
        source_type=citation.source_type or (existing.source_type if existing else "official"),
        source=citation.source or (existing.source if existing else "Manual refreshed source text."),
        ingest_at=citation.ingest_at or (existing.ingest_at if existing else ""),
        document_id=citation.document_id or (existing.document_id if existing else None),
        chunk_id=citation.chunk_id or (existing.chunk_id if existing else None),
        chunk_version=citation.chunk_version or (existing.chunk_version if existing else None),
        retrieved_at=citation.retrieved_at or (existing.retrieved_at if existing else None),
        source_url=citation.source_url or (existing.source_url if existing else None),
    )
    db.merge(updated)
    row.status = "completed"
    payload.update(
        {
            "status_transition": [*payload["status_transition"], "completed"],
            "refresh_mode": "manual_source",
            "refreshed_citation_id": row.citation_id,
            "document_id": updated.document_id,
            "chunk_id": updated.chunk_id,
            "chunk_version": updated.chunk_version,
            "external_fetch_performed": False,
        }
    )
    row.payload = json.dumps(payload, ensure_ascii=False)
    db.merge(row)
    event_id = f"evt_citation_refreshed_{queue_id}"
    db.add(
        DailyBriefingEvidenceEvent(
            id=event_id,
            case_id=None,
            company_id=None,
            event_type="citation_refreshed",
            payload=_citation_refresh_event_payload(
                event_id=event_id,
                event_type="citation_refreshed",
                citation_id=row.citation_id,
                queue_id=row.id,
                summary="Citation refresh completed from an operator-reviewed manual source. No external fetch was performed.",
                extra={
                    "refresh_mode": "manual_source",
                    "document_id": updated.document_id,
                    "chunk_id": updated.chunk_id,
                    "chunk_version": updated.chunk_version,
                    "external_fetch_performed": False,
                },
            ),
        )
    )
    db.commit()
    return _queue_item_response(row)


@router.get("/{citation_id}")
def get_citation_detail(
    citation_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        citation = service.get_citation_detail(citation_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Citation was not found."),
        ) from exc
    return citation.model_dump()


@router.get("/{citation_id}/validation")
def get_citation_validation(
    citation_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        citation = service.get_citation_detail(citation_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Citation validation target was not found."),
        ) from exc
    return {
        "citation_id": citation.citation_id,
        "validation_status": citation.validation_status,
        "validation_reason": citation.validation_reason,
        "missing_evidence": citation.missing_evidence,
        "stale_evidence": citation.stale_evidence,
        "synthetic_only": citation.synthetic_only,
        "policy_update_needed": citation.policy_update_needed,
        "source_type": citation.source_type,
        "document_id": citation.document_id,
        "chunk_id": citation.chunk_id,
        "chunk_version": citation.chunk_version,
        "retrieved_at": citation.retrieved_at,
    }


@router.get("/{citation_id}/chunk")
def get_citation_chunk(
    citation_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        return service.get_citation_chunk_view(citation_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Citation chunk was not found."),
        ) from exc


@router.get("/{citation_id}/source-document")
def get_citation_source_document(
    citation_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        return service.get_citation_source_document_view(citation_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Citation source document was not found."),
        ) from exc
