from __future__ import annotations

import copy
import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.daily_briefing import (
    DailyBriefingAction,
    DailyBriefingApproval,
    DailyBriefingCandidateDocumentSource,
    DailyBriefingCandidateSource,
    DailyBriefingCase,
    DailyBriefingCitationSource,
    DailyBriefingCompanySource,
    DailyBriefingDocumentRequestDraft,
    DailyBriefingDocumentSource,
    DailyBriefingEvidenceEvent,
    DailyBriefingExternalDeliveryJob,
    DailyBriefingHandoffExportArtifact,
    DailyBriefingHandoffPreview,
    DailyBriefingReportingEventSource,
    DailyBriefingResultRow,
    DailyBriefingUserCompanyAccess,
    DailyBriefingWorkerSource,
)
from app.config import get_settings


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
RISK_TYPE_ORDER = {
    "reporting_deadline": 0,
    "contract_visa_conflict": 1,
    "visa_expiry": 2,
    "missing_document": 3,
    "quota_review": 4,
    "candidate_readiness": 5,
}

RISK_TYPE_DISPLAY_LABELS = {
    "visa_expiry": "체류기간 연장 준비",
    "missing_document": "누락 서류 점검",
    "contract_visa_conflict": "계약-체류 충돌 점검",
    "reporting_deadline": "고용변동 신고기한 점검",
    "quota_review": "신규 고용 준비/쿼터 검토",
    "candidate_readiness": "후보자 서류 준비상태 점검",
}

DOCUMENT_DISPLAY_LABELS = {
    "passport_copy": "여권 사본",
    "alien_registration_copy": "외국인등록증 사본",
    "alien_registration": "외국인등록증 사본",
    "standard_labor_contract": "표준근로계약서 사본",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _short_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _stable_id(prefix: str, *parts: object) -> str:
    return f"{prefix}_{_short_hash(':'.join(str(part) for part in parts))}"


def _briefing_run_id(company_id: str, target_date: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_]+", company_id):
        return f"brf_{company_id}_{target_date}"
    return f"brf_{_short_hash(f'{company_id}:{target_date}', 16)}"


def _today_for_timezone(timezone_name: str) -> str:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    except Exception:
        return datetime.now(UTC).date().isoformat()


def _risk_timing_label_from_risk(risk: "RiskEvaluation") -> str:
    if risk.expired:
        if risk.days_overdue is not None:
            return f"만료 후 {risk.days_overdue}일 경과"
        return "기한 경과"
    if risk.d_day is not None:
        return f"D-{risk.d_day}"
    return "기한 확인 필요"


def _document_display_list(documents: list[str]) -> str:
    if not documents:
        return "현재 확인된 누락 없음"
    return ", ".join(DOCUMENT_DISPLAY_LABELS.get(document, document) for document in documents)


def _case_title_for_item(risk_type: str, subject_display_name: str) -> str:
    risk_label = RISK_TYPE_DISPLAY_LABELS.get(risk_type, risk_type)
    return f"{subject_display_name} {risk_label}"


def _case_summary_for_item(
    *,
    risk_type: str,
    subject_display_name: str,
    risk: "RiskEvaluation",
    missing_documents: list[str],
) -> str:
    risk_label = RISK_TYPE_DISPLAY_LABELS.get(risk_type, risk_type)
    timing = _risk_timing_label_from_risk(risk)
    documents = _document_display_list(missing_documents)
    return f"{subject_display_name}: {risk_label} ({timing}). 누락 서류: {documents}."


class RiskEvaluation(BaseModel):
    severity: str
    d_day: int | None = None
    expired: bool = False
    days_overdue: int | None = None


class RiskSummary(BaseModel):
    total_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    by_risk_type: dict[str, int] = Field(default_factory=dict)


class DailyBriefingItem(BaseModel):
    item_id: str
    case_id: str
    subject_type: str
    subject_id: str
    subject_display_name: str | None = None
    subject_display_id: str | None = None
    risk_type: str
    severity: str
    d_day: int | None = None
    expired: bool = False
    days_overdue: int | None = None
    risk_timing_label: str | None = None
    case_title: str | None = None
    case_summary: str | None = None
    primary_action: dict[str, Any] | None = None
    source_labels: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    next_action_ids: list[str] = Field(default_factory=list)


class NextAction(BaseModel):
    action_id: str
    case_id: str
    approval_id: str
    action_type: str
    status: str = "pending_approval"
    subject_id: str
    label: str
    approval_required: bool = True
    blocked_until_approved: bool = True
    evidence_required: bool = True
    citation_ids: list[str] = Field(default_factory=list)
    approved_at: str | None = None


class ApprovalRecord(BaseModel):
    approval_id: str
    case_id: str
    action_id: str
    status: str = "pending"
    approver_id: str | None = None
    rejection_reason: str | None = None
    revision_reason: str | None = None
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class CaseRecord(BaseModel):
    case_id: str
    company_id: str
    worker_id: str | None = None
    risk_type: str
    status: str = "approval_pending"
    due_date: str | None = None
    risk_level: str
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class EvidenceEventRecord(BaseModel):
    event_id: str
    event_version: str = "v1"
    trace_id: str
    case_id: str | None = None
    request_id: str | None = None
    event_type: str
    actor_type: str
    node_name: str
    summary: str
    citation_ids: list[str] = Field(default_factory=list)
    redacted_input_hash: str | None = None
    redacted_output_hash: str | None = None
    hash_algorithm: str = "sha256"
    payload_ref: str | None = None
    created_at: str = Field(default_factory=_now_iso)


class CitationSummary(BaseModel):
    citation_id: str
    title: str
    source_type: str
    source: str
    ingest_at: str
    document_id: str | None = None
    chunk_id: str | None = None
    chunk_version: str | None = None
    retrieved_at: str | None = None
    source_url: str | None = None
    validation_status: str = "not_checked"
    missing_evidence: bool = False
    retrieved_source_ids: list[str] = Field(default_factory=list)
    evidence_grade: str | None = None
    validation_reason: str | None = None
    stale_evidence: bool = False
    synthetic_only: bool = False
    policy_update_needed: bool = False


class HandoffPreview(BaseModel):
    preview_id: str
    case_id: str
    action_id: str
    content_redacted: dict[str, Any] | str
    citation_ids: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)


class DocumentRequestDraft(BaseModel):
    draft_id: str
    case_id: str
    action_id: str
    worker_id: str
    status: str = "preview_only"
    approval_required: bool = True
    external_send_performed: bool = False
    missing_documents: list[str] = Field(default_factory=list)
    korean_text: str
    translated_text: str
    language_code: str = "vi"
    citation_ids: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)


class HandoffExportDraft(BaseModel):
    export_id: str
    case_id: str
    action_id: str
    format: str = "markdown"
    approval_status: str
    external_delivery_performed: bool = False
    content_markdown: str
    citation_ids: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    evidence_event_id: str
    created_at: str = Field(default_factory=_now_iso)


class HandoffExportArtifactRecord(BaseModel):
    artifact_id: str
    case_id: str
    action_id: str
    format: str
    content_hash: str
    download_url: str
    external_delivery_performed: bool = False
    evidence_event_id: str
    created_at: str = Field(default_factory=_now_iso)


class ExternalDeliveryJobRecord(BaseModel):
    job_id: str
    case_id: str
    action_id: str
    channel: str
    provider: str = "manual"
    status: str = "pending_manual_dispatch"
    external_send_performed: bool = False
    payload_redacted: dict[str, Any] = Field(default_factory=dict)
    citation_ids: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    evidence_event_id: str
    provider_message_id: str | None = None
    created_at: str = Field(default_factory=_now_iso)


class DailyBriefingResult(BaseModel):
    briefing_run_id: str
    company_id: str
    date: str
    generated_at: str
    timezone: str
    source_snapshot_hash: str
    rerun_count: int = 0
    last_refreshed_at: str
    items: list[DailyBriefingItem] = Field(default_factory=list)
    risk_summary: RiskSummary = Field(default_factory=RiskSummary)
    recommended_actions: list[NextAction] = Field(default_factory=list)
    citation_summaries: list[CitationSummary] = Field(default_factory=list)
    evidence_event_ids: list[str] = Field(default_factory=list)
    approval_required: bool = False


class ApprovalResponse(BaseModel):
    approval_id: str
    action_id: str
    status: str
    approved_at: str
    evidence_event_id: str


class CitationRetriever(Protocol):
    def search(self, query: str, **kwargs: Any) -> Any:
        ...


class CitationValidation(BaseModel):
    citation_id: str
    validation_status: str
    missing_evidence: bool
    retrieved_source_ids: list[str] = Field(default_factory=list)
    evidence_grade: str | None = None
    validation_reason: str | None = None
    stale_evidence: bool = False
    synthetic_only: bool = False
    policy_update_needed: bool = False


class DailyBriefingSourceImport(BaseModel):
    companies: list[dict[str, Any]] = Field(default_factory=list)
    workers: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    candidate_documents: list[dict[str, Any]] = Field(default_factory=list)
    reporting_events: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    user_company_access: list[dict[str, Any]] = Field(default_factory=list)


@dataclass
class CompanyRecord:
    company_id: str
    company_name: str
    timezone: str = "Asia/Seoul"
    quota_limit: int | None = None
    current_foreign_worker_count: int | None = None


@dataclass
class WorkerRecord:
    worker_id: str
    company_id: str
    display_name_masked: str
    raw_name: str
    visa_expiry_date: str | None
    contract_end_date: str | None = None


@dataclass
class DocumentStatusRecord:
    worker_id: str
    document_type: str
    status: str
    required: bool = True
    due_date: str | None = None


@dataclass
class CandidateRecord:
    candidate_id: str
    company_id: str
    display_name_masked: str
    raw_name: str
    status: str = "registered"


@dataclass
class CandidateDocumentStatusRecord:
    candidate_id: str
    document_type: str
    status: str
    required: bool = True
    due_date: str | None = None


@dataclass
class CitationRecord:
    citation_id: str
    title: str
    source_type: str
    source: str
    ingest_at: str
    document_id: str | None = None
    chunk_id: str | None = None
    chunk_version: str | None = None
    retrieved_at: str | None = None
    source_url: str | None = None


@dataclass
class ReportingEventRecord:
    event_id: str
    company_id: str
    worker_id: str | None
    event_type: str
    occurred_at: str
    discovered_at: str
    reporting_due_date: str
    reported_at: str | None = None
    status: str = "open"


def evaluate_visa_expiry_risk(reference_date: str, visa_expiry_date: str) -> RiskEvaluation:
    d_day = (_parse_date(visa_expiry_date) - _parse_date(reference_date)).days
    if d_day < 0:
        return RiskEvaluation(severity="CRITICAL", expired=True, days_overdue=abs(d_day))
    if d_day <= 30:
        return RiskEvaluation(severity="HIGH", d_day=d_day)
    if d_day <= 60:
        return RiskEvaluation(severity="MEDIUM", d_day=d_day)
    if d_day <= 90:
        return RiskEvaluation(severity="LOW", d_day=d_day)
    return RiskEvaluation(severity="LOW", d_day=d_day)


def evaluate_missing_document_risk(
    reference_date: str,
    document: DocumentStatusRecord,
) -> RiskEvaluation:
    if document.status != "missing":
        return RiskEvaluation(severity="LOW")
    if not document.required:
        return RiskEvaluation(severity="LOW", d_day=_document_d_day(reference_date, document))
    if document.due_date is None:
        return RiskEvaluation(severity="MEDIUM")

    d_day = _document_d_day(reference_date, document)
    if d_day is not None and d_day < 0:
        return RiskEvaluation(severity="CRITICAL", expired=True, days_overdue=abs(d_day))
    if d_day is not None and d_day <= 7:
        return RiskEvaluation(severity="HIGH", d_day=d_day)
    return RiskEvaluation(severity="MEDIUM", d_day=d_day)


def evaluate_contract_visa_conflict_risk(
    reference_date: str,
    visa_expiry_date: str,
    contract_end_date: str,
) -> RiskEvaluation | None:
    visa_expiry = _parse_date(visa_expiry_date)
    contract_end = _parse_date(contract_end_date)
    if contract_end <= visa_expiry:
        return None

    d_day = (visa_expiry - _parse_date(reference_date)).days
    if d_day < 0:
        return RiskEvaluation(severity="CRITICAL", expired=True, days_overdue=abs(d_day))
    if d_day <= 30:
        return RiskEvaluation(severity="HIGH", d_day=d_day)
    if d_day <= 60:
        return RiskEvaluation(severity="MEDIUM", d_day=d_day)
    return RiskEvaluation(severity="LOW", d_day=d_day)


def evaluate_reporting_deadline_risk(
    reference_date: str,
    reporting_due_date: str,
    reported_at: str | None,
) -> RiskEvaluation | None:
    if reported_at:
        return None
    d_day = (_parse_date(reporting_due_date) - _parse_date(reference_date)).days
    if d_day < 0:
        return RiskEvaluation(severity="CRITICAL", expired=True, days_overdue=abs(d_day))
    if d_day <= 3:
        return RiskEvaluation(severity="HIGH", d_day=d_day)
    if d_day <= 7:
        return RiskEvaluation(severity="MEDIUM", d_day=d_day)
    return RiskEvaluation(severity="LOW", d_day=d_day)


def evaluate_quota_review_risk(
    quota_limit: int | None,
    current_foreign_worker_count: int | None,
) -> RiskEvaluation | None:
    if quota_limit is None and current_foreign_worker_count is None:
        return None
    if quota_limit is None or current_foreign_worker_count is None:
        return RiskEvaluation(severity="MEDIUM")
    remaining = quota_limit - current_foreign_worker_count
    if remaining <= 0:
        return RiskEvaluation(severity="HIGH")
    if remaining <= 1:
        return RiskEvaluation(severity="MEDIUM")
    return None


def _document_d_day(reference_date: str, document: DocumentStatusRecord) -> int | None:
    if document.due_date is None:
        return None
    return (_parse_date(document.due_date) - _parse_date(reference_date)).days


class InMemoryDailyBriefingRepository:
    def __init__(
        self,
        *,
        companies: list[CompanyRecord],
        workers: list[WorkerRecord],
        documents: list[DocumentStatusRecord],
        citations: list[CitationRecord],
        reporting_events: list[ReportingEventRecord] | None = None,
        candidates: list[CandidateRecord] | None = None,
        candidate_documents: list[CandidateDocumentStatusRecord] | None = None,
        fail_on_save: bool = False,
    ) -> None:
        self.companies = {company.company_id: company for company in companies}
        self.workers = workers
        self.documents = documents
        self.citations = {citation.citation_id: citation for citation in citations}
        self.reporting_events = reporting_events or []
        self.candidates = candidates or []
        self.candidate_documents = candidate_documents or []
        self.fail_on_save = fail_on_save
        self.force_redaction_failure = False
        self.briefings: dict[str, DailyBriefingResult] = {}
        self.cases: dict[str, CaseRecord] = {}
        self.actions: dict[str, NextAction] = {}
        self.approvals: dict[str, ApprovalRecord] = {}
        self.evidence_events: dict[str, EvidenceEventRecord] = {}
        self.handoff_previews: dict[str, HandoffPreview] = {}
        self.document_request_drafts: dict[str, DocumentRequestDraft] = {}
        self.external_delivery_jobs: dict[str, ExternalDeliveryJobRecord] = {}
        self.handoff_export_artifacts: dict[str, HandoffExportArtifactRecord] = {}

    @classmethod
    def fail_on_save_fixture(cls) -> InMemoryDailyBriefingRepository:
        repository = build_seed_repository()
        repository.fail_on_save = True
        return repository

    def save_bundle(
        self,
        *,
        briefing: DailyBriefingResult,
        cases: list[CaseRecord],
        actions: list[NextAction],
        approvals: list[ApprovalRecord],
        evidence_events: list[EvidenceEventRecord],
        handoff_previews: list[HandoffPreview],
        document_request_drafts: list[DocumentRequestDraft] | None = None,
    ) -> None:
        document_request_drafts = document_request_drafts or []
        snapshot = (
            copy.deepcopy(self.briefings),
            copy.deepcopy(self.cases),
            copy.deepcopy(self.actions),
            copy.deepcopy(self.approvals),
            copy.deepcopy(self.evidence_events),
            copy.deepcopy(self.handoff_previews),
            copy.deepcopy(self.document_request_drafts),
            copy.deepcopy(self.external_delivery_jobs),
            copy.deepcopy(self.handoff_export_artifacts),
        )
        try:
            if self.fail_on_save:
                raise RuntimeError("STATE_SAVE_FAILED")
            self.briefings[briefing.briefing_run_id] = briefing
            for case in cases:
                self.cases[case.case_id] = case
            for action in actions:
                self.actions[action.action_id] = action
            for approval in approvals:
                self.approvals[approval.approval_id] = approval
            for event in evidence_events:
                self.evidence_events[event.event_id] = event
            for preview in handoff_previews:
                self.handoff_previews[preview.action_id] = preview
            for draft in document_request_drafts:
                self.document_request_drafts[draft.action_id] = draft
        except Exception:
            (
                self.briefings,
                self.cases,
                self.actions,
                self.approvals,
                self.evidence_events,
                self.handoff_previews,
                self.document_request_drafts,
                self.external_delivery_jobs,
                self.handoff_export_artifacts,
            ) = snapshot
            raise

    def persist_evidence_event(self, event: EvidenceEventRecord) -> None:
        self.evidence_events[event.event_id] = event

    def persist_external_delivery_job(
        self,
        *,
        job: ExternalDeliveryJobRecord,
        event: EvidenceEventRecord,
    ) -> None:
        self.external_delivery_jobs[job.job_id] = job
        self.evidence_events[event.event_id] = event

    def persist_handoff_export_artifact(
        self,
        *,
        artifact: HandoffExportArtifactRecord,
        event: EvidenceEventRecord,
    ) -> None:
        self.handoff_export_artifacts[artifact.artifact_id] = artifact
        self.evidence_events[event.event_id] = event


class SqlAlchemyDailyBriefingRepository(InMemoryDailyBriefingRepository):
    def __init__(
        self,
        db: Session,
        *,
        source_repository: InMemoryDailyBriefingRepository,
    ) -> None:
        self.db = db
        super().__init__(
            companies=list(source_repository.companies.values()),
            workers=list(source_repository.workers),
            documents=list(source_repository.documents),
            citations=list(source_repository.citations.values()),
            reporting_events=list(source_repository.reporting_events),
            candidates=list(source_repository.candidates),
            candidate_documents=list(source_repository.candidate_documents),
            fail_on_save=source_repository.fail_on_save,
        )
        self.force_redaction_failure = source_repository.force_redaction_failure
        self._load_persisted_rows()

    def _load_persisted_rows(self) -> None:
        for row in self.db.query(DailyBriefingResultRow).all():
            self.briefings[row.id] = DailyBriefingResult.model_validate_json(row.payload)
        for row in self.db.query(DailyBriefingCase).all():
            self.cases[row.id] = CaseRecord.model_validate_json(row.payload)
        for row in self.db.query(DailyBriefingAction).all():
            self.actions[row.id] = NextAction.model_validate_json(row.payload)
        for row in self.db.query(DailyBriefingApproval).all():
            self.approvals[row.id] = ApprovalRecord.model_validate_json(row.payload)
        for row in self.db.query(DailyBriefingEvidenceEvent).all():
            try:
                self.evidence_events[row.id] = EvidenceEventRecord.model_validate_json(row.payload)
            except ValidationError:
                payload = json.loads(row.payload)
                legacy_citation_ids = payload.get("citation_ids")
                if legacy_citation_ids is None and payload.get("citation_id"):
                    legacy_citation_ids = [payload["citation_id"]]
                self.evidence_events[row.id] = EvidenceEventRecord(
                    event_id=row.id,
                    trace_id=payload.get("trace_id") or f"trace_legacy_{row.id}",
                    case_id=row.case_id,
                    request_id=payload.get("request_id"),
                    event_type=row.event_type,
                    actor_type=payload.get("actor_type") or "system",
                    node_name=payload.get("node_name") or "legacy_evidence_loader",
                    summary=payload.get("summary") or "Legacy EvidenceEvent payload was normalized during load.",
                    citation_ids=legacy_citation_ids or [],
                    created_at=row.created_at.isoformat(),
                )
        for row in self.db.query(DailyBriefingHandoffPreview).all():
            preview = HandoffPreview.model_validate_json(row.payload)
            self.handoff_previews[preview.action_id] = preview
        for row in self.db.query(DailyBriefingDocumentRequestDraft).all():
            draft = DocumentRequestDraft.model_validate_json(row.payload)
            self.document_request_drafts[draft.action_id] = draft
        for row in self.db.query(DailyBriefingExternalDeliveryJob).all():
            job = ExternalDeliveryJobRecord.model_validate_json(row.payload)
            self.external_delivery_jobs[job.job_id] = job
        for row in self.db.query(DailyBriefingHandoffExportArtifact).all():
            artifact = HandoffExportArtifactRecord.model_validate_json(row.payload)
            self.handoff_export_artifacts[artifact.artifact_id] = artifact

    def save_bundle(
        self,
        *,
        briefing: DailyBriefingResult,
        cases: list[CaseRecord],
        actions: list[NextAction],
        approvals: list[ApprovalRecord],
        evidence_events: list[EvidenceEventRecord],
        handoff_previews: list[HandoffPreview],
        document_request_drafts: list[DocumentRequestDraft] | None = None,
    ) -> None:
        document_request_drafts = document_request_drafts or []
        super().save_bundle(
            briefing=briefing,
            cases=cases,
            actions=actions,
            approvals=approvals,
            evidence_events=evidence_events,
            handoff_previews=handoff_previews,
            document_request_drafts=document_request_drafts,
        )
        try:
            self.db.merge(
                DailyBriefingResultRow(
                    id=briefing.briefing_run_id,
                    company_id=briefing.company_id,
                    date=briefing.date,
                    source_snapshot_hash=briefing.source_snapshot_hash,
                    payload=briefing.model_dump_json(),
                )
            )
            for case in cases:
                self.db.merge(
                    DailyBriefingCase(
                        id=case.case_id,
                        company_id=case.company_id,
                        worker_id=case.worker_id,
                        risk_type=case.risk_type,
                        payload=case.model_dump_json(),
                    )
                )
            for action in actions:
                case = self.cases[action.case_id]
                self.db.merge(
                    DailyBriefingAction(
                        id=action.action_id,
                        case_id=action.case_id,
                        company_id=case.company_id,
                        action_type=action.action_type,
                        payload=action.model_dump_json(),
                    )
                )
            for approval in approvals:
                case = self.cases[approval.case_id]
                self.db.merge(
                    DailyBriefingApproval(
                        id=approval.approval_id,
                        case_id=approval.case_id,
                        action_id=approval.action_id,
                        company_id=case.company_id,
                        status=approval.status,
                        payload=approval.model_dump_json(),
                    )
                )
            for event in evidence_events:
                company_id = self.cases[event.case_id].company_id if event.case_id in self.cases else None
                self.db.merge(
                    DailyBriefingEvidenceEvent(
                        id=event.event_id,
                        case_id=event.case_id,
                        company_id=company_id,
                        event_type=event.event_type,
                        payload=event.model_dump_json(),
                    )
                )
            for preview in handoff_previews:
                case = self.cases[preview.case_id]
                self.db.merge(
                    DailyBriefingHandoffPreview(
                        id=preview.preview_id,
                        case_id=preview.case_id,
                        action_id=preview.action_id,
                        company_id=case.company_id,
                        payload=preview.model_dump_json(),
                    )
                )
            for draft in document_request_drafts:
                case = self.cases[draft.case_id]
                self.db.merge(
                    DailyBriefingDocumentRequestDraft(
                        id=draft.draft_id,
                        case_id=draft.case_id,
                        action_id=draft.action_id,
                        company_id=case.company_id,
                        worker_id=draft.worker_id,
                        status=draft.status,
                        payload=draft.model_dump_json(),
                    )
                )
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc

    def persist_approval_update(
        self,
        *,
        approval: ApprovalRecord,
        action: NextAction,
        event: EvidenceEventRecord,
    ) -> None:
        case = self.cases[approval.case_id]
        try:
            self.db.merge(
                DailyBriefingApproval(
                    id=approval.approval_id,
                    case_id=approval.case_id,
                    action_id=approval.action_id,
                    company_id=case.company_id,
                    status=approval.status,
                    payload=approval.model_dump_json(),
                )
            )
            self.db.merge(
                DailyBriefingAction(
                    id=action.action_id,
                    case_id=action.case_id,
                    company_id=case.company_id,
                    action_type=action.action_type,
                    payload=action.model_dump_json(),
                )
            )
            self.db.merge(
                DailyBriefingEvidenceEvent(
                    id=event.event_id,
                    case_id=event.case_id,
                    company_id=case.company_id,
                    event_type=event.event_type,
                    payload=event.model_dump_json(),
                )
            )
            self._refresh_briefings_for_action(action)
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc

    def _refresh_briefings_for_action(self, action: NextAction) -> None:
        for briefing_id, briefing in list(self.briefings.items()):
            if not any(existing.action_id == action.action_id for existing in briefing.recommended_actions):
                continue
            updated_actions = [
                self.actions.get(existing.action_id, existing)
                for existing in briefing.recommended_actions
            ]
            updated = briefing.model_copy(
                update={
                    "recommended_actions": updated_actions,
                    "last_refreshed_at": _now_iso(),
                }
            )
            self.briefings[briefing_id] = updated
            self.db.merge(
                DailyBriefingResultRow(
                    id=updated.briefing_run_id,
                    company_id=updated.company_id,
                    date=updated.date,
                    source_snapshot_hash=updated.source_snapshot_hash,
                    payload=updated.model_dump_json(),
                )
            )

    def persist_document_request_draft(
        self,
        *,
        draft: DocumentRequestDraft,
        event: EvidenceEventRecord,
    ) -> None:
        case = self.cases[draft.case_id]
        try:
            self.db.merge(
                DailyBriefingDocumentRequestDraft(
                    id=draft.draft_id,
                    case_id=draft.case_id,
                    action_id=draft.action_id,
                    company_id=case.company_id,
                    worker_id=draft.worker_id,
                    status=draft.status,
                    payload=draft.model_dump_json(),
                )
            )
            self.db.merge(
                DailyBriefingEvidenceEvent(
                    id=event.event_id,
                    case_id=event.case_id,
                    company_id=case.company_id,
                    event_type=event.event_type,
                    payload=event.model_dump_json(),
                )
            )
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc

    def persist_evidence_event(self, event: EvidenceEventRecord) -> None:
        company_id = self.cases[event.case_id].company_id if event.case_id in self.cases else None
        try:
            self.evidence_events[event.event_id] = event
            self.db.merge(
                DailyBriefingEvidenceEvent(
                    id=event.event_id,
                    case_id=event.case_id,
                    company_id=company_id,
                    event_type=event.event_type,
                    payload=event.model_dump_json(),
                )
            )
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc

    def persist_external_delivery_job(
        self,
        *,
        job: ExternalDeliveryJobRecord,
        event: EvidenceEventRecord,
    ) -> None:
        case = self.cases[job.case_id]
        try:
            self.external_delivery_jobs[job.job_id] = job
            self.evidence_events[event.event_id] = event
            self.db.merge(
                DailyBriefingExternalDeliveryJob(
                    id=job.job_id,
                    case_id=job.case_id,
                    action_id=job.action_id,
                    company_id=case.company_id,
                    channel=job.channel,
                    provider=job.provider,
                    status=job.status,
                    external_send_performed=job.external_send_performed,
                    payload=job.model_dump_json(),
                )
            )
            self.db.merge(
                DailyBriefingEvidenceEvent(
                    id=event.event_id,
                    case_id=event.case_id,
                    company_id=case.company_id,
                    event_type=event.event_type,
                    payload=event.model_dump_json(),
                )
            )
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc

    def persist_handoff_export_artifact(
        self,
        *,
        artifact: HandoffExportArtifactRecord,
        event: EvidenceEventRecord,
    ) -> None:
        case = self.cases[artifact.case_id]
        try:
            self.handoff_export_artifacts[artifact.artifact_id] = artifact
            self.evidence_events[event.event_id] = event
            self.db.merge(
                DailyBriefingHandoffExportArtifact(
                    id=artifact.artifact_id,
                    case_id=artifact.case_id,
                    action_id=artifact.action_id,
                    company_id=case.company_id,
                    format=artifact.format,
                    content_hash=artifact.content_hash,
                    external_delivery_performed=artifact.external_delivery_performed,
                    payload=artifact.model_dump_json(),
                )
            )
            self.db.merge(
                DailyBriefingEvidenceEvent(
                    id=event.event_id,
                    case_id=event.case_id,
                    company_id=case.company_id,
                    event_type=event.event_type,
                    payload=event.model_dump_json(),
                )
            )
            self.db.flush()
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError("STATE_SAVE_FAILED") from exc


class DailyBriefingService:
    def __init__(
        self,
        repository: InMemoryDailyBriefingRepository | None = None,
        *,
        citation_retriever: CitationRetriever | None = None,
    ) -> None:
        self.repository = repository or build_seed_repository()
        self.citation_retriever = citation_retriever

    def run_daily_briefing(
        self,
        company_id: str,
        date: str | None,
        *,
        user_role: str,
        allowed_company_ids: list[str] | None = None,
    ) -> DailyBriefingResult:
        self._assert_company_scope(company_id, allowed_company_ids)
        company = self.repository.companies.get(company_id)
        if company is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        target_date = date or _today_for_timezone(company.timezone)
        if self.repository.force_redaction_failure:
            raise RuntimeError("PII_REDACTION_FAILED")

        briefing_run_id = _briefing_run_id(company_id, target_date)
        source_hash = self._source_snapshot_hash(company_id, target_date)
        existing = self.repository.briefings.get(briefing_run_id)
        rerun_count = (existing.rerun_count + 1) if existing else 0
        if existing and existing.source_snapshot_hash == source_hash:
            updated = existing.model_copy(
                update={
                    "rerun_count": rerun_count,
                    "last_refreshed_at": _now_iso(),
                }
            )
            updated = self._with_display_fields(updated)
            self.repository.briefings[briefing_run_id] = updated
            return updated

        trace_id = _stable_id("trace", company_id, target_date, source_hash)
        events = [
            self._event(
                trace_id=trace_id,
                case_id=None,
                event_type="input_received",
                actor_type="user",
                node_name="daily_briefing_api",
                summary="Daily briefing run requested for scoped company.",
            ),
            self._event(
                trace_id=trace_id,
                case_id=None,
                event_type="state_loaded",
                actor_type="system",
                node_name="daily_briefing_service",
                summary="Company, worker, document, and citation state loaded.",
            ),
        ]
        cases: list[CaseRecord] = []
        actions: list[NextAction] = []
        approvals: list[ApprovalRecord] = []
        previews: list[HandoffPreview] = []
        document_request_drafts: list[DocumentRequestDraft] = []
        items: list[DailyBriefingItem] = []

        workers = sorted(
            [worker for worker in self.repository.workers if worker.company_id == company_id],
            key=lambda worker: worker.worker_id,
        )
        for worker in workers:
            self._assert_worker_scope(company_id, worker)
            if worker.visa_expiry_date:
                risk = evaluate_visa_expiry_risk(target_date, worker.visa_expiry_date)
                if risk.d_day is not None and risk.d_day > 90 and not risk.expired:
                    continue
                item, generated = self._build_item_bundle(
                    company_id=company_id,
                    worker=worker,
                    risk_type="visa_expiry",
                    risk=risk,
                    due_date=worker.visa_expiry_date,
                    missing_documents=[],
                    citation_ids=["cit_visa_expiry"],
                    trace_id=trace_id,
                )
                items.append(item)
                cases.append(generated["case"])
                actions.extend(generated["actions"])
                approvals.extend(generated["approvals"])
                previews.extend(generated["previews"])
                document_request_drafts.extend(generated["document_request_drafts"])
                events.extend(generated["events"])

            if worker.visa_expiry_date and worker.contract_end_date:
                risk = evaluate_contract_visa_conflict_risk(
                    target_date,
                    worker.visa_expiry_date,
                    worker.contract_end_date,
                )
                if risk is not None:
                    item, generated = self._build_item_bundle(
                        company_id=company_id,
                        worker=worker,
                        risk_type="contract_visa_conflict",
                        risk=risk,
                        due_date=worker.visa_expiry_date,
                        missing_documents=[],
                        citation_ids=["cit_contract_visa_conflict"],
                        trace_id=trace_id,
                    )
                    items.append(item)
                    cases.append(generated["case"])
                    actions.extend(generated["actions"])
                    approvals.extend(generated["approvals"])
                    previews.extend(generated["previews"])
                    document_request_drafts.extend(generated["document_request_drafts"])
                    events.extend(generated["events"])

            for document in self._missing_documents_for_worker(worker.worker_id):
                risk = evaluate_missing_document_risk(target_date, document)
                item, generated = self._build_item_bundle(
                    company_id=company_id,
                    worker=worker,
                    risk_type="missing_document",
                    risk=risk,
                    due_date=document.due_date,
                    missing_documents=[document.document_type],
                    citation_ids=["cit_missing_document"],
                    trace_id=trace_id,
                )
                items.append(item)
                cases.append(generated["case"])
                actions.extend(generated["actions"])
                approvals.extend(generated["approvals"])
                previews.extend(generated["previews"])
                document_request_drafts.extend(generated["document_request_drafts"])
                events.extend(generated["events"])

        for candidate in sorted(
            [
                candidate
                for candidate in self.repository.candidates
                if candidate.company_id == company_id and candidate.status == "registered"
            ],
            key=lambda candidate: candidate.candidate_id,
        ):
            missing_candidate_documents = self._missing_documents_for_candidate(
                candidate.candidate_id
            )
            if not missing_candidate_documents:
                continue
            strongest_risk = self._strongest_document_risk(
                target_date,
                [
                    DocumentStatusRecord(
                        worker_id=candidate.candidate_id,
                        document_type=document.document_type,
                        status=document.status,
                        required=document.required,
                        due_date=document.due_date,
                    )
                    for document in missing_candidate_documents
                ],
            )
            candidate_proxy = WorkerRecord(
                worker_id=candidate.candidate_id,
                company_id=candidate.company_id,
                display_name_masked=candidate.display_name_masked,
                raw_name="[CANDIDATE_REDACTED]",
                visa_expiry_date=None,
            )
            item, generated = self._build_item_bundle(
                company_id=company_id,
                worker=candidate_proxy,
                risk_type="candidate_readiness",
                risk=strongest_risk,
                due_date=self._nearest_due_date(
                    [document.due_date for document in missing_candidate_documents]
                ),
                missing_documents=[
                    document.document_type
                    for document in missing_candidate_documents
                ],
                citation_ids=["cit_candidate_readiness"],
                trace_id=trace_id,
                subject_type="candidate",
                subject_id=candidate.candidate_id,
            )
            items.append(item)
            cases.append(generated["case"])
            actions.extend(generated["actions"])
            approvals.extend(generated["approvals"])
            previews.extend(generated["previews"])
            document_request_drafts.extend(generated["document_request_drafts"])
            events.extend(generated["events"])

        for event_record in self._open_reporting_events_for_company(company_id):
            risk = evaluate_reporting_deadline_risk(
                target_date,
                event_record.reporting_due_date,
                event_record.reported_at,
            )
            if risk is None:
                continue
            worker = self._worker_for_event(company_id, event_record)
            item, generated = self._build_item_bundle(
                company_id=company_id,
                worker=worker,
                risk_type="reporting_deadline",
                risk=risk,
                due_date=event_record.reporting_due_date,
                missing_documents=[],
                citation_ids=["cit_reporting_deadline"],
                trace_id=trace_id,
                subject_type="case",
                subject_id=event_record.event_id,
            )
            items.append(item)
            cases.append(generated["case"])
            actions.extend(generated["actions"])
            approvals.extend(generated["approvals"])
            previews.extend(generated["previews"])
            document_request_drafts.extend(generated["document_request_drafts"])
            events.extend(generated["events"])

        quota_risk = evaluate_quota_review_risk(
            company.quota_limit,
            company.current_foreign_worker_count,
        )
        if quota_risk is not None:
            quota_worker = WorkerRecord(
                worker_id=f"{company_id}:quota",
                company_id=company_id,
                display_name_masked=company.company_name,
                raw_name="[COMPANY_QUOTA]",
                visa_expiry_date=None,
            )
            item, generated = self._build_item_bundle(
                company_id=company_id,
                worker=quota_worker,
                risk_type="quota_review",
                risk=quota_risk,
                due_date=target_date,
                missing_documents=[],
                citation_ids=["cit_quota_review"],
                trace_id=trace_id,
                subject_type="company",
                subject_id=company_id,
            )
            items.append(item)
            cases.append(generated["case"])
            actions.extend(generated["actions"])
            approvals.extend(generated["approvals"])
            previews.extend(generated["previews"])
            document_request_drafts.extend(generated["document_request_drafts"])
            events.extend(generated["events"])

        items.sort(key=lambda item: self._sort_key(item))
        summary = self._risk_summary(items)
        citation_summaries = self._citation_summaries_for_items(
            items,
            target_date=target_date,
        )
        citation_events = self._citation_validation_events(
            trace_id=trace_id,
            citation_summaries=citation_summaries,
        )
        events.extend(citation_events)
        missing_citation_ids = {
            summary.citation_id
            for summary in citation_summaries
            if summary.missing_evidence
        }
        if missing_citation_ids:
            previews = self._add_missing_evidence_warnings(previews, missing_citation_ids)
            document_request_drafts = self._add_missing_evidence_warnings(
                document_request_drafts,
                missing_citation_ids,
            )
        result = DailyBriefingResult(
            briefing_run_id=briefing_run_id,
            company_id=company_id,
            date=target_date,
            generated_at=_now_iso(),
            timezone=company.timezone,
            source_snapshot_hash=source_hash,
            rerun_count=rerun_count,
            last_refreshed_at=_now_iso(),
            items=items,
            risk_summary=summary,
            recommended_actions=actions,
            citation_summaries=citation_summaries,
            evidence_event_ids=[event.event_id for event in events],
            approval_required=bool(actions),
        )
        result = self._with_display_fields(result)
        try:
            self.repository.save_bundle(
                briefing=result,
                cases=cases,
                actions=actions,
                approvals=approvals,
                evidence_events=events,
                handoff_previews=previews,
                document_request_drafts=document_request_drafts,
            )
        except RuntimeError as exc:
            if exc.args and exc.args[0] == "STATE_SAVE_FAILED":
                raise
            raise RuntimeError("STATE_SAVE_FAILED") from exc
        return result

    def approve_action(
        self,
        approval_id: str,
        *,
        approver_id: str,
        user_role: str,
        allowed_company_ids: list[str] | None = None,
    ) -> ApprovalResponse:
        if user_role not in {"manager", "admin"}:
            raise PermissionError("UNAUTHORIZED_ROLE")
        approval = self.repository.approvals.get(approval_id)
        if approval is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        action = self.repository.actions[approval.action_id]
        self._assert_case_scope(action.case_id, allowed_company_ids)
        approved_at = _now_iso()
        approval.status = "approved"
        approval.approver_id = approver_id
        approval.updated_at = approved_at
        action.status = "approved"
        action.approved_at = approved_at
        event = self._event(
            trace_id=_stable_id("trace", approval.case_id, approval.action_id, approved_at),
            case_id=approval.case_id,
            event_type="approval_approved",
            actor_type="approver",
            node_name="approval_api",
            summary="Approval completed for internal draft action. No external execution was performed.",
            citation_ids=action.citation_ids,
        )
        self.repository.evidence_events[event.event_id] = event
        if hasattr(self.repository, "persist_approval_update"):
            self.repository.persist_approval_update(
                approval=approval,
                action=action,
                event=event,
            )
        return ApprovalResponse(
            approval_id=approval_id,
            action_id=action.action_id,
            status="approved",
            approved_at=approved_at,
            evidence_event_id=event.event_id,
        )

    def reject_action(
        self,
        approval_id: str,
        *,
        approver_id: str,
        user_role: str,
        reason: str,
        allowed_company_ids: list[str] | None = None,
    ) -> ApprovalResponse:
        return self._transition_approval(
            approval_id,
            approver_id=approver_id,
            user_role=user_role,
            allowed_company_ids=allowed_company_ids,
            status="rejected",
            action_status="rejected",
            event_type="approval_rejected",
            reason=reason,
        )

    def request_revision(
        self,
        approval_id: str,
        *,
        approver_id: str,
        user_role: str,
        reason: str,
        allowed_company_ids: list[str] | None = None,
    ) -> ApprovalResponse:
        return self._transition_approval(
            approval_id,
            approver_id=approver_id,
            user_role=user_role,
            allowed_company_ids=allowed_company_ids,
            status="revision_requested",
            action_status="revision_requested",
            event_type="approval_revision_requested",
            reason=reason,
        )

    def _transition_approval(
        self,
        approval_id: str,
        *,
        approver_id: str,
        user_role: str,
        allowed_company_ids: list[str] | None,
        status: str,
        action_status: str,
        event_type: str,
        reason: str,
    ) -> ApprovalResponse:
        if user_role not in {"manager", "admin"}:
            raise PermissionError("UNAUTHORIZED_ROLE")
        approval = self.repository.approvals.get(approval_id)
        if approval is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        action = self.repository.actions[approval.action_id]
        self._assert_case_scope(action.case_id, allowed_company_ids)
        transitioned_at = _now_iso()
        approval.status = status
        approval.approver_id = approver_id
        approval.updated_at = transitioned_at
        if status == "rejected":
            approval.rejection_reason = reason
        if status == "revision_requested":
            approval.revision_reason = reason
        action.status = action_status
        action.blocked_until_approved = True
        event = self._event(
            trace_id=_stable_id("trace", approval.case_id, approval.action_id, event_type, transitioned_at),
            case_id=approval.case_id,
            event_type=event_type,
            actor_type="approver",
            node_name="approval_api",
            summary=f"Approval marked as {status}. No external execution was performed.",
            citation_ids=action.citation_ids,
            output_value={"reason": reason, "status": status},
        )
        self.repository.evidence_events[event.event_id] = event
        if hasattr(self.repository, "persist_approval_update"):
            self.repository.persist_approval_update(
                approval=approval,
                action=action,
                event=event,
            )
        return ApprovalResponse(
            approval_id=approval_id,
            action_id=action.action_id,
            status=status,
            approved_at=transitioned_at,
            evidence_event_id=event.event_id,
        )

    def get_handoff_preview(
        self,
        action_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> HandoffPreview:
        preview = self.repository.handoff_previews.get(action_id)
        if preview is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_case_scope(preview.case_id, allowed_company_ids)
        return preview

    def get_document_request_draft(
        self,
        action_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> DocumentRequestDraft:
        draft = self.repository.document_request_drafts.get(action_id)
        if draft is None:
            draft = self._backfill_document_request_draft(action_id)
        self._assert_case_scope(draft.case_id, allowed_company_ids)
        return draft

    def generate_handoff_export_draft(
        self,
        action_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> HandoffExportDraft:
        action = self.repository.actions.get(action_id)
        if action is None or action.action_type != "create_handoff":
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        preview = self.get_handoff_preview(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
        approval = self.repository.approvals.get(action.approval_id)
        approval_status = approval.status if approval is not None else "missing"
        if approval_status != "approved" or action.status != "approved":
            raise PermissionError("APPROVAL_REQUIRED")

        content = preview.content_redacted
        risk_summary = content.get("risk_summary", {}) if isinstance(content, dict) else {}
        worker = content.get("worker", {}) if isinstance(content, dict) else {}
        questions = content.get("recommended_questions", []) if isinstance(content, dict) else []
        markdown_lines = [
            "# Handoff Draft",
            "",
            "> Internal review draft only. No external delivery was performed.",
            "",
            f"- Case ID: {preview.case_id}",
            f"- Action ID: {action.action_id}",
            f"- Subject: {worker.get('display_name_masked', '[REDACTED]')}",
            f"- Risk Type: {risk_summary.get('risk_type', 'unknown')}",
            f"- Severity: {risk_summary.get('severity', 'unknown')}",
            f"- External Delivery Performed: false",
            "",
            "## Recommended Questions",
        ]
        markdown_lines.extend(f"- {question}" for question in questions)
        markdown_lines.extend(
            [
                "",
                "## Citations",
                *[f"- {citation_id}" for citation_id in preview.citation_ids],
            ]
        )
        event = self._event(
            trace_id=_stable_id("trace", preview.case_id, action.action_id, "handoff_export_draft"),
            case_id=preview.case_id,
            event_type="handoff_export_draft_generated",
            actor_type="system",
            node_name="handoff_export_builder",
            summary="Approved handoff export draft generated for internal review only. No external delivery performed.",
            citation_ids=preview.citation_ids,
            output_value={"action_id": action.action_id, "format": "markdown"},
        )
        self.repository.persist_evidence_event(event)
        return HandoffExportDraft(
            export_id=_stable_id("export", action.action_id, "markdown"),
            case_id=preview.case_id,
            action_id=action.action_id,
            approval_status=approval_status,
            content_markdown="\n".join(markdown_lines),
            citation_ids=preview.citation_ids,
            warning_flags=preview.warning_flags,
            evidence_event_id=event.event_id,
        )

    def create_external_delivery_job(
        self,
        action_id: str,
        *,
        channel: str,
        provider: str = "manual",
        allowed_company_ids: list[str] | None = None,
    ) -> ExternalDeliveryJobRecord:
        action = self.repository.actions.get(action_id)
        if action is None or action.action_type not in {"create_handoff", "request_document"}:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_case_scope(action.case_id, allowed_company_ids)
        approval = self.repository.approvals.get(action.approval_id)
        approval_status = approval.status if approval else "missing"
        if approval_status != "approved" or action.status != "approved":
            raise PermissionError("APPROVAL_REQUIRED")

        case = self.repository.cases[action.case_id]
        event = self._event(
            trace_id=_stable_id("trace", case.case_id, action.action_id, "external_delivery_job"),
            case_id=case.case_id,
            event_type="external_delivery_job_created",
            actor_type="system",
            node_name="external_delivery_outbox",
            summary=(
                "Approved external delivery job created as a manual outbox item. "
                "No provider call or external send was performed."
            ),
            citation_ids=action.citation_ids,
            output_value={
                "action_id": action.action_id,
                "channel": channel,
                "provider": provider,
                "status": "pending_manual_dispatch",
                "external_send_performed": False,
            },
        )
        job = ExternalDeliveryJobRecord(
            job_id=_stable_id("delivery", action.action_id, channel, provider),
            case_id=case.case_id,
            action_id=action.action_id,
            channel=channel,
            provider=provider,
            status="pending_manual_dispatch",
            external_send_performed=False,
            payload_redacted={
                "case_id": case.case_id,
                "action_type": action.action_type,
                "subject_id": action.subject_id,
                "label": action.label,
                "delivery_mode": "manual_outbox_only",
            },
            citation_ids=action.citation_ids,
            warning_flags=["manual_dispatch_required", "external_provider_not_called"],
            evidence_event_id=event.event_id,
        )
        self.repository.persist_external_delivery_job(job=job, event=event)
        return job

    def dispatch_external_delivery_job(
        self,
        job_id: str,
        *,
        user_role: str,
        allowed_company_ids: list[str] | None = None,
    ) -> ExternalDeliveryJobRecord:
        if user_role not in {"manager", "admin"}:
            raise PermissionError("UNAUTHORIZED_ROLE")
        job = self.repository.external_delivery_jobs.get(job_id)
        if job is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_case_scope(job.case_id, allowed_company_ids)
        if job.provider != "mock_webhook":
            raise PermissionError("PROVIDER_NOT_CONFIGURED")

        dispatched = job.model_copy(
            update={
                "status": "mock_dispatched",
                "external_send_performed": False,
                "provider_message_id": None,
                "warning_flags": sorted({*job.warning_flags, "mock_provider_only"}),
            }
        )
        event = self._event(
            trace_id=_stable_id("trace", job.case_id, job.action_id, "external_delivery_dispatched"),
            case_id=job.case_id,
            event_type="external_delivery_dispatched",
            actor_type="system",
            node_name="external_delivery_provider",
            summary="Approved mock provider dispatch path was verified. No real network provider was called.",
            citation_ids=job.citation_ids,
            output_value={
                "job_id": job.job_id,
                "provider": job.provider,
                "status": "mock_dispatched",
                "external_send_performed": False,
            },
        )
        self.repository.persist_external_delivery_job(job=dispatched, event=event)
        return dispatched

    def record_handoff_export_artifact(
        self,
        action_id: str,
        *,
        export_format: str,
        content: bytes,
        allowed_company_ids: list[str] | None = None,
    ) -> HandoffExportArtifactRecord:
        action = self.repository.actions.get(action_id)
        if action is None or action.action_type != "create_handoff":
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_case_scope(action.case_id, allowed_company_ids)
        content_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
        artifact = HandoffExportArtifactRecord(
            artifact_id=_stable_id("artifact", action.action_id, export_format, content_hash),
            case_id=action.case_id,
            action_id=action.action_id,
            format=export_format,
            content_hash=content_hash,
            download_url=f"/api/v1/actions/{action.action_id}/handoff-export.{export_format}",
            external_delivery_performed=False,
            evidence_event_id=_stable_id("evt", action.case_id, action.action_id, export_format, content_hash),
        )
        event = self._event(
            trace_id=_stable_id("trace", action.case_id, action.action_id, "handoff_export_artifact"),
            case_id=action.case_id,
            event_type="handoff_export_artifact_generated",
            actor_type="system",
            node_name="handoff_export_artifact_store",
            summary="Approved handoff export artifact recorded for download history.",
            citation_ids=action.citation_ids,
            output_value=artifact.model_dump(),
        )
        artifact = artifact.model_copy(update={"evidence_event_id": event.event_id})
        self.repository.persist_handoff_export_artifact(artifact=artifact, event=event)
        return artifact

    def list_handoff_export_artifacts(
        self,
        action_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> list[HandoffExportArtifactRecord]:
        action = self.repository.actions.get(action_id)
        if action is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_case_scope(action.case_id, allowed_company_ids)
        return sorted(
            [
                artifact
                for artifact in self.repository.handoff_export_artifacts.values()
                if artifact.action_id == action_id
            ],
            key=lambda artifact: artifact.created_at,
        )

    def _backfill_document_request_draft(self, action_id: str) -> DocumentRequestDraft:
        action = self.repository.actions.get(action_id)
        if action is None or action.action_type != "request_document":
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        case = self.repository.cases.get(action.case_id)
        if case is None or case.worker_id is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        worker = next((candidate for candidate in self.repository.workers if candidate.worker_id == case.worker_id), None)
        if worker is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        missing_documents = [
            document.document_type
            for document in self._missing_documents_for_worker(worker.worker_id)
        ]
        item = DailyBriefingItem(
            item_id=_stable_id("item", case.case_id),
            case_id=case.case_id,
            subject_type="worker",
            subject_id=worker.worker_id,
            risk_type=case.risk_type,
            severity=case.risk_level,
            missing_documents=missing_documents,
            citation_ids=action.citation_ids,
            next_action_ids=[action.action_id],
        )
        draft = self._document_request_draft(action, worker, item)
        event = self._event(
            trace_id=_stable_id("trace", case.case_id, action.action_id, "document_request_draft_backfill"),
            case_id=case.case_id,
            event_type="document_request_draft_generated",
            actor_type="system",
            node_name="document_request_draft_builder",
            summary="Preview-only document request draft generated on demand. No external send performed.",
            citation_ids=draft.citation_ids,
            output_value=draft.model_dump(),
        )
        self.repository.document_request_drafts[action.action_id] = draft
        self.repository.evidence_events[event.event_id] = event
        if hasattr(self.repository, "persist_document_request_draft"):
            self.repository.persist_document_request_draft(draft=draft, event=event)
        return draft

    def get_case_evidence_events(
        self,
        case_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> list[EvidenceEventRecord]:
        self._assert_case_scope(case_id, allowed_company_ids)
        return [
            event
            for event in self.repository.evidence_events.values()
            if event.case_id == case_id
        ]

    def get_case_audit_review(
        self,
        case_id: str,
        *,
        allowed_company_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self._assert_case_scope(case_id, allowed_company_ids)
        case = self.repository.cases[case_id]
        related_briefing = self._briefing_for_case(case_id)
        related_item = None
        if related_briefing is not None:
            related_item = next(
                (item for item in related_briefing.items if item.case_id == case_id),
                None,
            )
        actions = [
            action
            for action in self.repository.actions.values()
            if action.case_id == case_id
        ]
        approval_history = [
            approval.model_dump()
            for approval in self.repository.approvals.values()
            if approval.case_id == case_id
        ]
        citation_ids = sorted(
            {
                citation_id
                for action in actions
                for citation_id in action.citation_ids
            }
            | set(related_item.citation_ids if related_item else [])
        )
        citation_details = [
            self.get_citation_detail(citation_id).model_dump()
            for citation_id in citation_ids
            if citation_id in self.repository.citations
        ]
        case_events = [
            event
            for event in self.repository.evidence_events.values()
            if event.case_id == case_id
        ]
        citation_events = [
            event
            for event in self.repository.evidence_events.values()
            if event.case_id is None and set(event.citation_ids).intersection(citation_ids)
        ]
        evidence_events = sorted(
            [*case_events, *citation_events],
            key=lambda event: event.created_at,
        )
        rule_snapshot = {
            "risk_type": case.risk_type,
            "risk_level": case.risk_level,
            "due_date": case.due_date,
            "case_status": case.status,
            "d_day": related_item.d_day if related_item else None,
            "expired": related_item.expired if related_item else False,
            "days_overdue": related_item.days_overdue if related_item else None,
            "missing_documents": related_item.missing_documents if related_item else [],
        }
        db_snapshot = {
            "company_id": case.company_id,
            "worker_id": case.worker_id,
            "subject_type": related_item.subject_type if related_item else None,
            "subject_id": related_item.subject_id if related_item else case.worker_id,
            "raw_pii_included": False,
        }
        return {
            "case": case.model_dump(),
            "rule_snapshot": rule_snapshot,
            "db_snapshot": db_snapshot,
            "source_snapshot_hash": (
                related_briefing.source_snapshot_hash
                if related_briefing is not None
                else None
            ),
            "briefing_run_id": (
                related_briefing.briefing_run_id
                if related_briefing is not None
                else None
            ),
            "actions": [action.model_dump() for action in actions],
            "approval_history": approval_history,
            "citation_details": citation_details,
            "evidence_events": [event.model_dump() for event in evidence_events],
        }

    def _briefing_for_case(self, case_id: str) -> DailyBriefingResult | None:
        for briefing in self.repository.briefings.values():
            if any(item.case_id == case_id for item in briefing.items):
                return briefing
        return None

    def _with_display_fields(self, briefing: DailyBriefingResult) -> DailyBriefingResult:
        workers_by_id = {worker.worker_id: worker for worker in self.repository.workers}
        candidates_by_id = {
            candidate.candidate_id: candidate for candidate in self.repository.candidates
        }
        actions_by_id = {action.action_id: action for action in briefing.recommended_actions}
        citations_by_id = {
            citation.citation_id: citation for citation in briefing.citation_summaries
        }
        companies_by_id = self.repository.companies
        items: list[DailyBriefingItem] = []

        for item in briefing.items:
            subject_display_name = item.subject_display_name or item.subject_id
            if item.subject_type == "worker" and item.subject_id in workers_by_id:
                subject_display_name = workers_by_id[item.subject_id].display_name_masked
            elif item.subject_type == "candidate" and item.subject_id in candidates_by_id:
                subject_display_name = candidates_by_id[item.subject_id].display_name_masked
            elif item.subject_type == "company" and item.subject_id in companies_by_id:
                subject_display_name = companies_by_id[item.subject_id].company_name
            elif item.subject_type == "case":
                case = self.repository.cases.get(item.case_id)
                worker_id = case.worker_id if case is not None else None
                if worker_id and worker_id in workers_by_id:
                    subject_display_name = workers_by_id[worker_id].display_name_masked

            risk = RiskEvaluation(
                severity=item.severity,
                d_day=item.d_day,
                expired=item.expired,
                days_overdue=item.days_overdue,
            )
            primary_action = item.primary_action
            if primary_action is None:
                primary_action_record = next(
                    (
                        actions_by_id[action_id]
                        for action_id in item.next_action_ids
                        if action_id in actions_by_id
                    ),
                    None,
                )
                primary_action = (
                    primary_action_record.model_dump()
                    if primary_action_record is not None
                    else None
                )
            source_labels = item.source_labels or [
                citations_by_id[citation_id].title
                for citation_id in item.citation_ids
                if citation_id in citations_by_id
            ]
            case_title = item.case_title
            if (
                not case_title
                or case_title.startswith("[COMPANY_QUOTA]")
                or case_title.startswith(f"{item.subject_id} ")
            ):
                case_title = _case_title_for_item(item.risk_type, subject_display_name)
            case_summary = item.case_summary
            if (
                not case_summary
                or case_summary.startswith("[COMPANY_QUOTA]")
                or case_summary.startswith(f"{item.subject_id}:")
            ):
                case_summary = _case_summary_for_item(
                    risk_type=item.risk_type,
                    subject_display_name=subject_display_name,
                    risk=risk,
                    missing_documents=item.missing_documents,
                )
            items.append(
                item.model_copy(
                    update={
                        "subject_display_name": subject_display_name,
                        "subject_display_id": item.subject_display_id or item.subject_id,
                        "risk_timing_label": item.risk_timing_label
                        or _risk_timing_label_from_risk(risk),
                        "case_title": case_title,
                        "case_summary": case_summary,
                        "primary_action": primary_action,
                        "source_labels": source_labels,
                    }
                )
            )

        return briefing.model_copy(update={"items": items})

    def _source_snapshot_hash(self, company_id: str, target_date: str) -> str:
        worker_rows = [
            {
                "worker_id": worker.worker_id,
                "visa_expiry_date": worker.visa_expiry_date,
                "contract_end_date": worker.contract_end_date,
            }
            for worker in sorted(self.repository.workers, key=lambda row: row.worker_id)
            if worker.company_id == company_id
        ]
        document_rows = [
            {
                "worker_id": document.worker_id,
                "document_type": document.document_type,
                "status": document.status,
                "required": document.required,
                "due_date": document.due_date,
            }
            for document in sorted(
                self.repository.documents,
                key=lambda row: (row.worker_id, row.document_type),
            )
            if any(worker.worker_id == document.worker_id and worker.company_id == company_id for worker in self.repository.workers)
        ]
        citation_rows = [
            {"citation_id": citation.citation_id, "ingest_at": citation.ingest_at}
            for citation in sorted(self.repository.citations.values(), key=lambda row: row.citation_id)
        ]
        reporting_event_rows = [
            {
                "event_id": event.event_id,
                "worker_id": event.worker_id,
                "event_type": event.event_type,
                "reporting_due_date": event.reporting_due_date,
                "reported_at": event.reported_at,
                "status": event.status,
            }
            for event in sorted(self.repository.reporting_events, key=lambda row: row.event_id)
            if event.company_id == company_id
        ]
        candidate_rows = [
            {
                "candidate_id": candidate.candidate_id,
                "status": candidate.status,
            }
            for candidate in sorted(
                self.repository.candidates,
                key=lambda row: row.candidate_id,
            )
            if candidate.company_id == company_id
        ]
        candidate_document_rows = [
            {
                "candidate_id": document.candidate_id,
                "document_type": document.document_type,
                "status": document.status,
                "required": document.required,
                "due_date": document.due_date,
            }
            for document in sorted(
                self.repository.candidate_documents,
                key=lambda row: (row.candidate_id, row.document_type),
            )
            if any(
                candidate.candidate_id == document.candidate_id
                and candidate.company_id == company_id
                for candidate in self.repository.candidates
            )
        ]
        company = self.repository.companies[company_id]
        snapshot = {
            "company_id": company_id,
            "date": target_date,
            "quota_limit": company.quota_limit,
            "current_foreign_worker_count": company.current_foreign_worker_count,
            "workers": worker_rows,
            "documents": document_rows,
            "candidates": candidate_rows,
            "candidate_documents": candidate_document_rows,
            "reporting_events": reporting_event_rows,
            "citations": citation_rows,
        }
        return hashlib.sha256(repr(snapshot).encode("utf-8")).hexdigest()

    def _build_item_bundle(
        self,
        *,
        company_id: str,
        worker: WorkerRecord,
        risk_type: str,
        risk: RiskEvaluation,
        due_date: str | None,
        missing_documents: list[str],
        citation_ids: list[str],
        trace_id: str,
        subject_type: str = "worker",
        subject_id: str | None = None,
    ) -> tuple[DailyBriefingItem, dict[str, Any]]:
        item_subject_id = subject_id or worker.worker_id
        case_id = _stable_id("case", company_id, item_subject_id, risk_type, due_date)
        case = self.repository.cases.get(
            case_id,
            CaseRecord(
                case_id=case_id,
                company_id=company_id,
                worker_id=worker.worker_id if subject_type != "company" else None,
                risk_type=risk_type,
                due_date=due_date,
                risk_level=risk.severity,
            ),
        )
        case.risk_level = risk.severity
        case.status = "approval_pending"
        case.updated_at = _now_iso()
        item = DailyBriefingItem(
            item_id=_stable_id("item", case_id),
            case_id=case_id,
            subject_type=subject_type,
            subject_id=item_subject_id,
            subject_display_name=worker.display_name_masked,
            subject_display_id=item_subject_id,
            risk_type=risk_type,
            severity=risk.severity,
            d_day=risk.d_day,
            expired=risk.expired,
            days_overdue=risk.days_overdue,
            risk_timing_label=_risk_timing_label_from_risk(risk),
            case_title=_case_title_for_item(risk_type, worker.display_name_masked),
            case_summary=_case_summary_for_item(
                risk_type=risk_type,
                subject_display_name=worker.display_name_masked,
                risk=risk,
                missing_documents=missing_documents,
            ),
            source_labels=[
                self.repository.citations[citation_id].title
                for citation_id in citation_ids
                if citation_id in self.repository.citations
            ],
            missing_documents=missing_documents,
            citation_ids=citation_ids,
        )
        actions = self._actions_for_item(item, worker, citation_ids)
        item.next_action_ids = [action.action_id for action in actions]
        item.primary_action = actions[0].model_dump() if actions else None
        approvals = [
            self.repository.approvals.get(
                action.approval_id,
                ApprovalRecord(
                    approval_id=action.approval_id,
                    case_id=case_id,
                    action_id=action.action_id,
                ),
            )
            for action in actions
        ]
        previews = [
            self._handoff_preview(action, worker, item)
            for action in actions
            if action.action_type == "create_handoff"
        ]
        document_request_drafts = [
            self._document_request_draft(action, worker, item)
            for action in actions
            if action.action_type == "request_document"
        ]
        events = [
            self._event(
                trace_id=trace_id,
                case_id=case_id,
                event_type="risk_flagged",
                actor_type="system",
                node_name="risk_rule_engine",
                summary=f"{risk_type} flagged as {risk.severity} for masked worker {worker.worker_id}.",
                citation_ids=citation_ids,
                output_value=item.model_dump(),
            ),
            self._event(
                trace_id=trace_id,
                case_id=case_id,
                event_type="approval_requested",
                actor_type="system",
                node_name="daily_briefing_service",
                summary="Approval requested for generated internal actions. No external execution performed.",
                citation_ids=citation_ids,
                output_value={"action_ids": item.next_action_ids},
            ),
        ]
        events.extend(
            self._event(
                trace_id=trace_id,
                case_id=preview.case_id,
                event_type="handoff_preview_generated",
                actor_type="system",
                node_name="handoff_preview_builder",
                summary="Redacted handoff preview generated for internal review only.",
                citation_ids=preview.citation_ids,
                output_value=preview.model_dump(),
            )
            for preview in previews
        )
        events.extend(
            self._event(
                trace_id=trace_id,
                case_id=draft.case_id,
                event_type="document_request_draft_generated",
                actor_type="system",
                node_name="document_request_draft_builder",
                summary="Preview-only document request draft generated. No external send performed.",
                citation_ids=draft.citation_ids,
                output_value=draft.model_dump(),
            )
            for draft in document_request_drafts
        )
        return item, {
            "case": case,
            "actions": actions,
            "approvals": approvals,
            "previews": previews,
            "document_request_drafts": document_request_drafts,
            "events": events,
        }

    def _actions_for_item(
        self,
        item: DailyBriefingItem,
        worker: WorkerRecord,
        citation_ids: list[str],
    ) -> list[NextAction]:
        action_types = ["create_handoff"]
        if item.risk_type == "missing_document":
            action_types.insert(0, "request_document")
        actions = []
        for action_type in action_types:
            action_id = _stable_id("action", item.case_id, action_type)
            approval_id = _stable_id("approval", action_id)
            actions.append(
                self.repository.actions.get(
                    action_id,
                    NextAction(
                        action_id=action_id,
                        case_id=item.case_id,
                        approval_id=approval_id,
                        action_type=action_type,
                        subject_id=worker.worker_id,
                        label=self._action_label(action_type, item),
                        citation_ids=citation_ids,
                    ),
                )
            )
        return actions

    def _action_label(self, action_type: str, item: DailyBriefingItem) -> str:
        if action_type == "request_document":
            return "누락서류 요청 초안 생성"
        return "행정사 검토용 Handoff preview 생성"

    def _handoff_preview(
        self,
        action: NextAction,
        worker: WorkerRecord,
        item: DailyBriefingItem,
    ) -> HandoffPreview:
        content = {
            "worker": {
                "worker_id": worker.worker_id,
                "display_name": worker.display_name_masked,
            },
            "risk_summary": {
                "risk_type": item.risk_type,
                "severity": item.severity,
                "d_day": item.d_day,
                "expired": item.expired,
                "days_overdue": item.days_overdue,
            },
            "missing_documents": item.missing_documents,
            "contract_visa_review": self._contract_visa_review(worker, item),
            "reporting_deadline": self._reporting_deadline_review(item),
            "quota_review": self._quota_review(worker.company_id, item),
            "recommended_questions": [
                "검토에 필요한 추가 서류가 있는지 확인해 주세요.",
                "체류/계약 일정 충돌 여부를 전문가가 확인해 주세요.",
            ],
        }
        return HandoffPreview(
            preview_id=_stable_id("preview", action.action_id),
            case_id=action.case_id,
            action_id=action.action_id,
            content_redacted=content,
            citation_ids=action.citation_ids,
        )

    def _contract_visa_review(
        self,
        worker: WorkerRecord,
        item: DailyBriefingItem,
    ) -> dict[str, Any] | None:
        if item.risk_type != "contract_visa_conflict":
            return None
        return {
            "visa_expiry_date": worker.visa_expiry_date,
            "contract_end_date": worker.contract_end_date,
            "expert_review_required": True,
            "note": "계약 종료일이 체류만료일 이후입니다. 고용 가능 여부를 확정하지 않고 전문가 검토 대상으로 표시합니다.",
        }

    def _reporting_deadline_review(self, item: DailyBriefingItem) -> dict[str, Any] | None:
        if item.risk_type != "reporting_deadline":
            return None
        return {
            "event_id": item.subject_id,
            "d_day": item.d_day,
            "expired": item.expired,
            "expert_review_required": True,
            "external_report_submitted": False,
        }

    def _quota_review(self, company_id: str, item: DailyBriefingItem) -> dict[str, Any] | None:
        if item.risk_type != "quota_review":
            return None
        company = self.repository.companies[company_id]
        remaining = (
            None
            if company.quota_limit is None or company.current_foreign_worker_count is None
            else company.quota_limit - company.current_foreign_worker_count
        )
        return {
            "quota_limit": company.quota_limit,
            "current_foreign_worker_count": company.current_foreign_worker_count,
            "remaining_slots": remaining,
            "eligibility_confirmed": False,
            "note": "고용 가능 여부를 확정하지 않고 쿼터 검토 필요 상태만 표시합니다.",
        }

    def _document_request_draft(
        self,
        action: NextAction,
        worker: WorkerRecord,
        item: DailyBriefingItem,
    ) -> DocumentRequestDraft:
        documents = ", ".join(item.missing_documents)
        korean_text = (
            f"{worker.display_name_masked}님, 외국인 고용 업무 확인을 위해 "
            f"다음 서류 제출이 필요합니다: {documents}. "
            "이 메시지는 담당자 승인 전 초안이며, 아직 발송되지 않았습니다."
        )
        translated_text = (
            f"Kinh gui {worker.display_name_masked}, de kiem tra ho so viec lam nguoi nuoc ngoai, "
            f"vui long chuan bi cac tai lieu sau: {documents}. "
            "Day la ban nhap can nguoi phu trach phe duyet, chua duoc gui."
        )
        return DocumentRequestDraft(
            draft_id=_stable_id("docdraft", action.action_id),
            case_id=action.case_id,
            action_id=action.action_id,
            worker_id=worker.worker_id,
            missing_documents=item.missing_documents,
            korean_text=korean_text,
            translated_text=translated_text,
            citation_ids=action.citation_ids,
        )

    def _event(
        self,
        *,
        trace_id: str,
        case_id: str | None,
        event_type: str,
        actor_type: str,
        node_name: str,
        summary: str,
        citation_ids: list[str] | None = None,
        output_value: Any = None,
    ) -> EvidenceEventRecord:
        output_hash = None
        if output_value is not None:
            output_hash = hashlib.sha256(repr(output_value).encode("utf-8")).hexdigest()
        return EvidenceEventRecord(
            event_id=_stable_id("evt", trace_id, case_id, event_type, summary, output_hash),
            trace_id=trace_id,
            case_id=case_id,
            event_type=event_type,
            actor_type=actor_type,
            node_name=node_name,
            summary=summary,
            citation_ids=citation_ids or [],
            redacted_output_hash=output_hash,
        )

    def _missing_documents_for_worker(self, worker_id: str) -> list[DocumentStatusRecord]:
        return [
            document
            for document in self.repository.documents
            if document.worker_id == worker_id and document.status == "missing"
        ]

    def _missing_documents_for_candidate(
        self,
        candidate_id: str,
    ) -> list[CandidateDocumentStatusRecord]:
        return [
            document
            for document in self.repository.candidate_documents
            if document.candidate_id == candidate_id and document.status == "missing"
        ]

    def _strongest_document_risk(
        self,
        target_date: str,
        documents: list[DocumentStatusRecord],
    ) -> RiskEvaluation:
        risks = [evaluate_missing_document_risk(target_date, document) for document in documents]
        risks.sort(key=lambda risk: SEVERITY_ORDER.get(risk.severity, 99))
        return risks[0] if risks else RiskEvaluation(severity="LOW")

    def _nearest_due_date(self, due_dates: list[str | None]) -> str | None:
        present_due_dates = sorted(due_date for due_date in due_dates if due_date)
        return present_due_dates[0] if present_due_dates else None

    def _open_reporting_events_for_company(self, company_id: str) -> list[ReportingEventRecord]:
        return [
            event
            for event in self.repository.reporting_events
            if event.company_id == company_id and event.status == "open"
        ]

    def _worker_for_event(
        self,
        company_id: str,
        event: ReportingEventRecord,
    ) -> WorkerRecord:
        if event.worker_id:
            worker = next(
                (
                    candidate
                    for candidate in self.repository.workers
                    if candidate.worker_id == event.worker_id and candidate.company_id == company_id
                ),
                None,
            )
            if worker is not None:
                return worker
        return WorkerRecord(
            worker_id=f"{event.event_id}:reporting",
            company_id=company_id,
            display_name_masked="[REPORTING_EVENT]",
            raw_name="[REPORTING_EVENT]",
            visa_expiry_date=None,
        )

    def _citation_summaries_for_items(
        self,
        items: list[DailyBriefingItem],
        *,
        target_date: str,
    ) -> list[CitationSummary]:
        citation_ids = sorted({citation_id for item in items for citation_id in item.citation_ids})
        summaries: list[CitationSummary] = []
        for citation_id in citation_ids:
            citation = self.repository.citations.get(citation_id)
            if citation is None:
                continue
            validation = self._validate_citation(citation, target_date=target_date)
            summaries.append(
                CitationSummary(
                    citation_id=citation.citation_id,
                    title=self._citation_title(citation),
                    source_type=citation.source_type,
                    source=citation.source,
                    ingest_at=citation.ingest_at,
                    **self._citation_metadata(citation),
                    validation_status=validation.validation_status,
                    missing_evidence=validation.missing_evidence,
                    retrieved_source_ids=validation.retrieved_source_ids,
                    evidence_grade=validation.evidence_grade,
                    validation_reason=validation.validation_reason,
                    stale_evidence=validation.stale_evidence,
                    synthetic_only=validation.synthetic_only,
                    policy_update_needed=validation.policy_update_needed,
                )
            )
        return summaries

    def _validate_citation(
        self,
        citation: CitationRecord,
        *,
        target_date: str | None = None,
    ) -> CitationValidation:
        if citation.source_type == "synthetic":
            return CitationValidation(
                citation_id=citation.citation_id,
                validation_status="synthetic_only",
                missing_evidence=True,
                validation_reason="synthetic_source_cannot_support_official_conclusion",
                synthetic_only=True,
            )
        stale_evidence = self._is_stale_evidence(citation.ingest_at, target_date)
        if stale_evidence:
            return CitationValidation(
                citation_id=citation.citation_id,
                validation_status="stale_evidence",
                missing_evidence=True,
                validation_reason="official_source_ingest_is_older_than_6_months",
                stale_evidence=True,
                policy_update_needed=True,
            )
        if self.citation_retriever is None:
            return CitationValidation(
                citation_id=citation.citation_id,
                validation_status="not_checked",
                missing_evidence=False,
                validation_reason="citation_retriever_not_configured",
            )

        query = (
            f"{citation.citation_id} {citation.title} {citation.source} "
            f"{citation.source_type} official evidence"
        )
        try:
            result = self.citation_retriever.search(
                query,
                evidence_grade="A",
                k=5,
            )
        except Exception:
            return CitationValidation(
                citation_id=citation.citation_id,
                validation_status="validation_error",
                missing_evidence=True,
                validation_reason="retriever_error",
            )

        retrieved_source_ids: list[str] = []
        evidence_grade: str | None = None
        for retrieved in getattr(result, "citations", []) or []:
            source_id = getattr(retrieved, "source_id", None)
            if source_id:
                retrieved_source_ids.append(str(source_id))
            if evidence_grade is None:
                retrieved_grade = getattr(retrieved, "evidence_grade", None)
                if retrieved_grade is not None:
                    evidence_grade = str(retrieved_grade)

        if citation.citation_id in retrieved_source_ids:
            return CitationValidation(
                citation_id=citation.citation_id,
                validation_status="validated",
                missing_evidence=False,
                retrieved_source_ids=retrieved_source_ids,
                evidence_grade=evidence_grade,
                validation_reason="retrieved_official_source_id_matched",
            )

        return CitationValidation(
            citation_id=citation.citation_id,
            validation_status="missing_evidence",
            missing_evidence=True,
            retrieved_source_ids=retrieved_source_ids,
            evidence_grade=evidence_grade,
            validation_reason="retrieved_sources_did_not_match_citation_id",
        )

    def _is_stale_evidence(self, ingest_at: str, target_date: str | None) -> bool:
        try:
            ingest_date = _parse_date(ingest_at[:10])
            reference_date = _parse_date(target_date) if target_date else date.today()
        except Exception:
            return True
        return (reference_date - ingest_date).days > 183

    def get_citation_detail(self, citation_id: str) -> CitationSummary:
        citation = self.repository.citations.get(citation_id)
        if citation is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        validation = self._validate_citation(citation)
        return CitationSummary(
            citation_id=citation.citation_id,
            title=self._citation_title(citation),
            source_type=citation.source_type,
            source=citation.source,
            ingest_at=citation.ingest_at,
            **self._citation_metadata(citation),
            validation_status=validation.validation_status,
            missing_evidence=validation.missing_evidence,
            retrieved_source_ids=validation.retrieved_source_ids,
            evidence_grade=validation.evidence_grade,
            validation_reason=validation.validation_reason,
            stale_evidence=validation.stale_evidence,
            synthetic_only=validation.synthetic_only,
            policy_update_needed=validation.policy_update_needed,
        )

    def get_citation_chunk_view(self, citation_id: str) -> dict[str, Any]:
        citation = self.repository.citations.get(citation_id)
        if citation is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        metadata = self._citation_metadata(citation)
        return {
            "viewer_kind": "chunk",
            "citation_id": citation.citation_id,
            "document_id": metadata["document_id"],
            "chunk_id": metadata["chunk_id"],
            "chunk_version": metadata["chunk_version"],
            "retrieved_at": metadata["retrieved_at"],
            "source_url": metadata["source_url"],
            "source_type": citation.source_type,
            "chunk_text": citation.source,
            "download_available": False,
        }

    def get_citation_source_document_view(self, citation_id: str) -> dict[str, Any]:
        citation = self.repository.citations.get(citation_id)
        if citation is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        metadata = self._citation_metadata(citation)
        return {
            "viewer_kind": "source_document",
            "citation_id": citation.citation_id,
            "document_id": metadata["document_id"],
            "title": self._citation_title(citation),
            "source_type": citation.source_type,
            "source_url": metadata["source_url"],
            "retrieved_at": metadata["retrieved_at"],
            "chunk_ids": [metadata["chunk_id"]],
            "download_available": False,
            "original_pdf_available": False,
        }

    def _citation_metadata(self, citation: CitationRecord) -> dict[str, str | None]:
        suffix = citation.citation_id.removeprefix("cit_")
        version = citation.chunk_version or citation.ingest_at[:10]
        return {
            "document_id": citation.document_id or f"doc_{suffix}",
            "chunk_id": citation.chunk_id or f"chunk_{suffix}",
            "chunk_version": version,
            "retrieved_at": citation.retrieved_at or citation.ingest_at,
            "source_url": citation.source_url or f"mock://daily-briefing/{citation.citation_id}",
        }

    def _citation_validation_events(
        self,
        *,
        trace_id: str,
        citation_summaries: list[CitationSummary],
    ) -> list[EvidenceEventRecord]:
        events: list[EvidenceEventRecord] = []
        for summary in citation_summaries:
            if summary.validation_status == "not_checked":
                continue
            event_type = (
                "citation_missing_evidence"
                if summary.missing_evidence
                else "citation_validated"
            )
            events.append(
                self._event(
                    trace_id=trace_id,
                    case_id=None,
                    event_type=event_type,
                    actor_type="system",
                    node_name="citation_validator",
                    summary=(
                        f"Citation {summary.citation_id} validation status: "
                        f"{summary.validation_status}."
                    ),
                    citation_ids=[summary.citation_id],
                )
            )
        return events

    def _add_missing_evidence_warnings(
        self,
        previews: list[HandoffPreview] | list[DocumentRequestDraft],
        missing_citation_ids: set[str],
    ) -> list[HandoffPreview] | list[DocumentRequestDraft]:
        updated: list[HandoffPreview] | list[DocumentRequestDraft] = []
        for preview in previews:
            if not set(preview.citation_ids).intersection(missing_citation_ids):
                updated.append(preview)
                continue
            warning_flags = sorted({*preview.warning_flags, "missing_evidence"})
            updated.append(preview.model_copy(update={"warning_flags": warning_flags}))
        return updated

    def _citation_title(self, citation: CitationRecord) -> str:
        return citation.title

    def _risk_summary(self, items: list[DailyBriefingItem]) -> RiskSummary:
        summary = RiskSummary(total_count=len(items))
        for item in items:
            if item.severity == "CRITICAL":
                summary.critical_count += 1
            elif item.severity == "HIGH":
                summary.high_count += 1
            elif item.severity == "MEDIUM":
                summary.medium_count += 1
            elif item.severity == "LOW":
                summary.low_count += 1
            summary.by_risk_type[item.risk_type] = summary.by_risk_type.get(item.risk_type, 0) + 1
        return summary

    def _sort_key(self, item: DailyBriefingItem) -> tuple[int, int, int, str]:
        d_day_sort = -1 if item.expired else (item.d_day if item.d_day is not None else 9999)
        return (
            SEVERITY_ORDER.get(item.severity, 99),
            d_day_sort,
            RISK_TYPE_ORDER.get(item.risk_type, 99),
            item.subject_id,
        )

    def _assert_company_scope(
        self,
        company_id: str,
        allowed_company_ids: list[str] | None,
    ) -> None:
        if allowed_company_ids is not None and company_id not in allowed_company_ids:
            raise PermissionError("TENANT_SCOPE_VIOLATION")

    def _assert_worker_scope(self, company_id: str, worker: WorkerRecord) -> None:
        if worker.company_id != company_id:
            raise PermissionError("TENANT_SCOPE_VIOLATION")

    def _assert_case_scope(
        self,
        case_id: str,
        allowed_company_ids: list[str] | None,
    ) -> None:
        case = self.repository.cases.get(case_id)
        if case is None:
            raise LookupError("MISSING_REQUIRED_CONTEXT")
        self._assert_company_scope(case.company_id, allowed_company_ids)


def build_seed_repository() -> InMemoryDailyBriefingRepository:
    return InMemoryDailyBriefingRepository(
        companies=[
            CompanyRecord(
                company_id="company_001",
                company_name="Demo Manufacturing",
                quota_limit=4,
                current_foreign_worker_count=3,
            ),
            CompanyRecord(company_id="company_no_risks", company_name="No Risk Company"),
        ],
        workers=[
            WorkerRecord(
                worker_id="worker_001",
                company_id="company_001",
                display_name_masked="Nguyen V.",
                raw_name="Nguyen Van A",
                visa_expiry_date="2026-06-07",
                contract_end_date="2026-07-31",
            ),
            WorkerRecord(
                worker_id="worker_002",
                company_id="company_001",
                display_name_masked="Tran T.",
                raw_name="Tran Thi B",
                visa_expiry_date="2026-05-05",
            ),
            WorkerRecord(
                worker_id="worker_003",
                company_id="company_001",
                display_name_masked="Pham V.",
                raw_name="Pham Van C",
                visa_expiry_date="2026-12-31",
            ),
            WorkerRecord(
                worker_id="worker_safe_001",
                company_id="company_no_risks",
                display_name_masked="Safe W.",
                raw_name="Safe Worker",
                visa_expiry_date="2026-12-31",
            ),
        ],
        documents=[
            DocumentStatusRecord(
                worker_id="worker_002",
                document_type="passport_copy",
                status="missing",
                required=True,
                due_date="2026-05-05",
            ),
            DocumentStatusRecord(
                worker_id="worker_001",
                document_type="standard_labor_contract",
                status="verified",
                required=True,
                due_date="2026-05-30",
            ),
        ],
        reporting_events=[
            ReportingEventRecord(
                event_id="change_evt_001",
                company_id="company_001",
                worker_id="worker_002",
                event_type="employment_change",
                occurred_at="2026-04-26",
                discovered_at="2026-04-26",
                reporting_due_date="2026-05-11",
            )
        ],
        citations=[
            CitationRecord(
                citation_id="cit_visa_expiry",
                title="체류기간 만료 전 갱신 준비 안내",
                source_type="official",
                source="HiKorea mock official chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
            CitationRecord(
                citation_id="cit_missing_document",
                title="외국인 고용 서류 완결성 점검 안내",
                source_type="official",
                source="EPS mock official chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
            CitationRecord(
                citation_id="cit_contract_visa_conflict",
                title="계약 종료일과 체류만료일 충돌 검토 안내",
                source_type="official",
                source="Internal operating checklist mock chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
            CitationRecord(
                citation_id="cit_reporting_deadline",
                title="고용변동 신고기한 검토 안내",
                source_type="official",
                source="EPS reporting deadline mock official chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
            CitationRecord(
                citation_id="cit_quota_review",
                title="E-9 고용 쿼터 검토 안내",
                source_type="official",
                source="EPS quota review mock official chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
            CitationRecord(
                citation_id="cit_candidate_readiness",
                title="후보자 서류 준비상태 점검 안내",
                source_type="official",
                source="Candidate document readiness mock official chunk",
                ingest_at="2026-05-01T00:00:00+09:00",
            ),
        ],
        candidates=[],
        candidate_documents=[],
    )


def build_default_citation_retriever() -> CitationRetriever | None:
    try:
        from app.agent_runtime.rag_tayna.retriever import RAGRetriever

        return RAGRetriever()
    except Exception:
        return None


def build_seed_daily_briefing_service(
    *,
    citation_retriever: CitationRetriever | None = None,
) -> DailyBriefingService:
    return DailyBriefingService(
        build_seed_repository(),
        citation_retriever=citation_retriever,
    )


daily_briefing_service = DailyBriefingService(build_seed_repository())


def _ensure_source_company_columns(db: Session) -> None:
    bind = db.get_bind()
    columns = {
        column["name"]
        for column in inspect(bind).get_columns(DailyBriefingCompanySource.__tablename__)
    }
    if "quota_limit" not in columns:
        db.execute(text("ALTER TABLE daily_briefing_source_companies ADD COLUMN quota_limit VARCHAR(20)"))
    if "current_foreign_worker_count" not in columns:
        db.execute(
            text(
                "ALTER TABLE daily_briefing_source_companies "
                "ADD COLUMN current_foreign_worker_count VARCHAR(20)"
            )
        )


def _ensure_source_citation_columns(db: Session) -> None:
    bind = db.get_bind()
    columns = {
        column["name"]
        for column in inspect(bind).get_columns(DailyBriefingCitationSource.__tablename__)
    }
    column_specs = {
        "document_id": "VARCHAR(120)",
        "chunk_id": "VARCHAR(120)",
        "chunk_version": "VARCHAR(80)",
        "retrieved_at": "VARCHAR(40)",
        "source_url": "TEXT",
    }
    for column_name, column_type in column_specs.items():
        if column_name not in columns:
            db.execute(
                text(
                    f"ALTER TABLE daily_briefing_source_citations "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )


def seed_daily_briefing_source_tables_if_empty(
    db: Session,
    source_repository: InMemoryDailyBriefingRepository,
) -> None:
    """Persist packaged demo source data so runtime reads DB source rows.

    This keeps Sprint demo data available on a fresh local SQLite DB, but avoids
    silently serving source state from process memory after the first build.
    """

    if db.query(DailyBriefingCompanySource).count() == 0:
        for company in source_repository.companies.values():
            db.merge(
                DailyBriefingCompanySource(
                    id=company.company_id,
                    company_name=company.company_name,
                    timezone=company.timezone,
                    quota_limit=(
                        str(company.quota_limit)
                        if company.quota_limit is not None
                        else None
                    ),
                    current_foreign_worker_count=(
                        str(company.current_foreign_worker_count)
                        if company.current_foreign_worker_count is not None
                        else None
                    ),
                )
            )
        for worker in source_repository.workers:
            db.merge(
                DailyBriefingWorkerSource(
                    id=worker.worker_id,
                    company_id=worker.company_id,
                    display_name_masked=worker.display_name_masked,
                    raw_name=worker.raw_name,
                    visa_expiry_date=worker.visa_expiry_date,
                    contract_end_date=worker.contract_end_date,
                )
            )
        for candidate in source_repository.candidates:
            db.merge(
                DailyBriefingCandidateSource(
                    id=candidate.candidate_id,
                    company_id=candidate.company_id,
                    display_name_masked=candidate.display_name_masked,
                    raw_name=candidate.raw_name,
                    status=candidate.status,
                )
            )
        for document in source_repository.documents:
            db.merge(
                DailyBriefingDocumentSource(
                    id=f"{document.worker_id}:{document.document_type}",
                    worker_id=document.worker_id,
                    document_type=document.document_type,
                    status=document.status,
                    required=document.required,
                    due_date=document.due_date,
                )
            )
        for document in source_repository.candidate_documents:
            db.merge(
                DailyBriefingCandidateDocumentSource(
                    id=f"{document.candidate_id}:{document.document_type}",
                    candidate_id=document.candidate_id,
                    document_type=document.document_type,
                    status=document.status,
                    required=document.required,
                    due_date=document.due_date,
                )
            )
        for event in source_repository.reporting_events:
            db.merge(
                DailyBriefingReportingEventSource(
                    id=event.event_id,
                    company_id=event.company_id,
                    worker_id=event.worker_id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    discovered_at=event.discovered_at,
                    reporting_due_date=event.reporting_due_date,
                    reported_at=event.reported_at,
                    status=event.status,
                )
            )

    for citation in source_repository.citations.values():
        if db.get(DailyBriefingCitationSource, citation.citation_id) is not None:
            continue
        db.merge(
            DailyBriefingCitationSource(
                id=citation.citation_id,
                title=citation.title,
                source_type=citation.source_type,
                source=citation.source,
                ingest_at=citation.ingest_at,
                document_id=citation.document_id or f"doc_{citation.citation_id.removeprefix('cit_')}",
                chunk_id=citation.chunk_id or f"chunk_{citation.citation_id.removeprefix('cit_')}",
                chunk_version=citation.chunk_version or citation.ingest_at[:10],
                retrieved_at=citation.retrieved_at or citation.ingest_at,
                source_url=citation.source_url or f"mock://daily-briefing/{citation.citation_id}",
            )
        )
    for worker in source_repository.workers:
        row = db.get(DailyBriefingWorkerSource, worker.worker_id)
        if (
            row is not None
            and row.raw_name == worker.raw_name
            and row.display_name_masked.startswith("[WORKER_NAME")
        ):
            row.display_name_masked = worker.display_name_masked
    db.flush()


def import_daily_briefing_sources(
    db: Session,
    payload: DailyBriefingSourceImport,
) -> dict[str, Any]:
    upserted_counts = {
        "companies": 0,
        "workers": 0,
        "documents": 0,
        "candidates": 0,
        "candidate_documents": 0,
        "reporting_events": 0,
        "citations": 0,
        "user_company_access": 0,
    }
    for row in payload.companies:
        company_id = row["company_id"]
        db.merge(
            DailyBriefingCompanySource(
                id=company_id,
                company_name=row["company_name"],
                timezone=row.get("timezone", "Asia/Seoul"),
                quota_limit=(
                    str(row["quota_limit"])
                    if row.get("quota_limit") is not None
                    else None
                ),
                current_foreign_worker_count=(
                    str(row["current_foreign_worker_count"])
                    if row.get("current_foreign_worker_count") is not None
                    else None
                ),
            )
        )
        upserted_counts["companies"] += 1
    for row in payload.workers:
        worker_id = row["worker_id"]
        db.merge(
            DailyBriefingWorkerSource(
                id=worker_id,
                company_id=row["company_id"],
                display_name_masked=row["display_name_masked"],
                raw_name=row.get("raw_name", "[REDACTED]"),
                visa_expiry_date=row.get("visa_expiry_date"),
                contract_end_date=row.get("contract_end_date"),
            )
        )
        upserted_counts["workers"] += 1
    for row in payload.documents:
        worker_id = row["worker_id"]
        document_type = row["document_type"]
        db.merge(
            DailyBriefingDocumentSource(
                id=row.get("id") or f"{worker_id}:{document_type}",
                worker_id=worker_id,
                document_type=document_type,
                status=row["status"],
                required=bool(row.get("required", True)),
                due_date=row.get("due_date"),
            )
        )
        upserted_counts["documents"] += 1
    for row in payload.candidates:
        candidate_id = row["candidate_id"]
        db.merge(
            DailyBriefingCandidateSource(
                id=candidate_id,
                company_id=row["company_id"],
                display_name_masked=row["display_name_masked"],
                raw_name=row.get("raw_name", "[REDACTED]"),
                status=row.get("status", "registered"),
            )
        )
        upserted_counts["candidates"] += 1
    for row in payload.candidate_documents:
        candidate_id = row["candidate_id"]
        document_type = row["document_type"]
        db.merge(
            DailyBriefingCandidateDocumentSource(
                id=row.get("id") or f"{candidate_id}:{document_type}",
                candidate_id=candidate_id,
                document_type=document_type,
                status=row["status"],
                required=bool(row.get("required", True)),
                due_date=row.get("due_date"),
            )
        )
        upserted_counts["candidate_documents"] += 1
    for row in payload.reporting_events:
        event_id = row["event_id"]
        db.merge(
            DailyBriefingReportingEventSource(
                id=event_id,
                company_id=row["company_id"],
                worker_id=row.get("worker_id"),
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                discovered_at=row["discovered_at"],
                reporting_due_date=row["reporting_due_date"],
                reported_at=row.get("reported_at"),
                status=row.get("status", "open"),
            )
        )
        upserted_counts["reporting_events"] += 1
    for row in payload.citations:
        citation_id = row["citation_id"]
        db.merge(
            DailyBriefingCitationSource(
                id=citation_id,
                title=row["title"],
                source_type=row["source_type"],
                source=row["source"],
                ingest_at=row["ingest_at"],
                document_id=row.get("document_id"),
                chunk_id=row.get("chunk_id"),
                chunk_version=row.get("chunk_version"),
                retrieved_at=row.get("retrieved_at"),
                source_url=row.get("source_url"),
            )
        )
        upserted_counts["citations"] += 1
    for row in payload.user_company_access:
        user_id = row["user_id"]
        company_id = row["company_id"]
        db.merge(
            DailyBriefingUserCompanyAccess(
                id=row.get("id") or f"{user_id}:{company_id}",
                user_id=user_id,
                company_id=company_id,
                role=row.get("role", "viewer"),
            )
        )
        upserted_counts["user_company_access"] += 1
    db.flush()
    return {"upserted_counts": upserted_counts}


def resolve_daily_briefing_allowed_company_ids(
    db: Session,
    *,
    user_id: str | None,
    header_company_id: str | None,
    authorization: str | None = None,
) -> list[str] | None:
    token_payload = decode_daily_briefing_bearer_token(authorization)
    if token_payload is not None:
        company_ids = token_payload.get("company_ids")
        if isinstance(company_ids, list):
            return [str(company_id) for company_id in company_ids]
        company_id = token_payload.get("company_id")
        if company_id:
            return [str(company_id)]
    if user_id:
        rows = (
            db.query(DailyBriefingUserCompanyAccess)
            .filter(DailyBriefingUserCompanyAccess.user_id == user_id)
            .order_by(DailyBriefingUserCompanyAccess.company_id)
            .all()
        )
        if rows:
            return [row.company_id for row in rows]
    return [header_company_id] if header_company_id else None


def daily_briefing_role_from_request(
    *,
    header_role: str,
    authorization: str | None = None,
) -> str:
    token_payload = decode_daily_briefing_bearer_token(authorization)
    if token_payload is not None and token_payload.get("role"):
        return str(token_payload["role"])
    return header_role


def daily_briefing_user_id_from_request(
    *,
    header_user_id: str | None,
    authorization: str | None = None,
) -> str | None:
    token_payload = decode_daily_briefing_bearer_token(authorization)
    if token_payload is not None and token_payload.get("sub"):
        return str(token_payload["sub"])
    return header_user_id


def decode_daily_briefing_bearer_token(authorization: str | None) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        header_segment, payload_segment, signature_segment = token.split(".", 2)
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected = hmac.new(
            get_settings().jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual = _b64url_decode(signature_segment)
        if not hmac.compare_digest(expected, actual):
            raise PermissionError("INVALID_TOKEN")
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("INVALID_TOKEN") from exc
    if not isinstance(payload, dict):
        raise PermissionError("INVALID_TOKEN")
    return payload


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def build_repository_from_db_sources(
    db: Session,
    *,
    fallback: InMemoryDailyBriefingRepository | None = None,
) -> InMemoryDailyBriefingRepository:
    fallback_repository = fallback
    source_companies = db.query(DailyBriefingCompanySource).order_by(DailyBriefingCompanySource.id).all()
    if not source_companies:
        if fallback_repository is None:
            raise LookupError("MISSING_SOURCE_DATA")
        return fallback_repository

    source_workers = db.query(DailyBriefingWorkerSource).order_by(DailyBriefingWorkerSource.id).all()
    source_candidates = db.query(DailyBriefingCandidateSource).order_by(DailyBriefingCandidateSource.id).all()
    source_documents = db.query(DailyBriefingDocumentSource).order_by(DailyBriefingDocumentSource.id).all()
    source_candidate_documents = db.query(DailyBriefingCandidateDocumentSource).order_by(DailyBriefingCandidateDocumentSource.id).all()
    source_reporting_events = db.query(DailyBriefingReportingEventSource).order_by(DailyBriefingReportingEventSource.id).all()
    source_citations = db.query(DailyBriefingCitationSource).order_by(DailyBriefingCitationSource.id).all()

    citations = [
        CitationRecord(
            citation_id=row.id,
            title=row.title,
            source_type=row.source_type,
            source=row.source,
            ingest_at=row.ingest_at,
            document_id=row.document_id,
            chunk_id=row.chunk_id,
            chunk_version=row.chunk_version,
            retrieved_at=row.retrieved_at,
            source_url=row.source_url,
        )
        for row in source_citations
    ]
    if not citations and fallback_repository is not None:
        citations = list(fallback_repository.citations.values())

    return InMemoryDailyBriefingRepository(
        companies=[
            CompanyRecord(
                company_id=row.id,
                company_name=row.company_name,
                timezone=row.timezone,
                quota_limit=int(row.quota_limit) if row.quota_limit is not None else None,
                current_foreign_worker_count=(
                    int(row.current_foreign_worker_count)
                    if row.current_foreign_worker_count is not None
                    else None
                ),
            )
            for row in source_companies
        ],
        workers=[
            WorkerRecord(
                worker_id=row.id,
                company_id=row.company_id,
                display_name_masked=row.display_name_masked,
                raw_name=row.raw_name,
                visa_expiry_date=row.visa_expiry_date,
                contract_end_date=row.contract_end_date,
            )
            for row in source_workers
        ],
        candidates=[
            CandidateRecord(
                candidate_id=row.id,
                company_id=row.company_id,
                display_name_masked=row.display_name_masked,
                raw_name=row.raw_name,
                status=row.status,
            )
            for row in source_candidates
        ],
        documents=[
            DocumentStatusRecord(
                worker_id=row.worker_id,
                document_type=row.document_type,
                status=row.status,
                required=row.required,
                due_date=row.due_date,
            )
            for row in source_documents
        ],
        candidate_documents=[
            CandidateDocumentStatusRecord(
                candidate_id=row.candidate_id,
                document_type=row.document_type,
                status=row.status,
                required=row.required,
                due_date=row.due_date,
            )
            for row in source_candidate_documents
        ],
        reporting_events=[
            ReportingEventRecord(
                event_id=row.id,
                company_id=row.company_id,
                worker_id=row.worker_id,
                event_type=row.event_type,
                occurred_at=row.occurred_at,
                discovered_at=row.discovered_at,
                reporting_due_date=row.reporting_due_date,
                reported_at=row.reported_at,
                status=row.status,
            )
            for row in source_reporting_events
        ],
        citations=citations,
    )


def build_sqlalchemy_daily_briefing_service(
    db: Session,
    *,
    citation_retriever: CitationRetriever | None = None,
    allow_seed_source_fallback: bool | None = None,
) -> DailyBriefingService:
    bind = db.get_bind()
    for table in (
        DailyBriefingResultRow.__table__,
        DailyBriefingCase.__table__,
        DailyBriefingAction.__table__,
        DailyBriefingApproval.__table__,
        DailyBriefingEvidenceEvent.__table__,
        DailyBriefingHandoffPreview.__table__,
        DailyBriefingDocumentRequestDraft.__table__,
        DailyBriefingCompanySource.__table__,
        DailyBriefingWorkerSource.__table__,
        DailyBriefingCandidateSource.__table__,
        DailyBriefingDocumentSource.__table__,
        DailyBriefingCandidateDocumentSource.__table__,
        DailyBriefingReportingEventSource.__table__,
        DailyBriefingCitationSource.__table__,
        DailyBriefingExternalDeliveryJob.__table__,
        DailyBriefingHandoffExportArtifact.__table__,
        DailyBriefingUserCompanyAccess.__table__,
    ):
        table.create(bind=bind, checkfirst=True)
    _ensure_source_company_columns(db)
    _ensure_source_citation_columns(db)
    if allow_seed_source_fallback is None:
        allow_seed_source_fallback = get_settings().daily_briefing_allow_seed_source_fallback
    fallback_repository = build_seed_repository() if allow_seed_source_fallback else None
    if allow_seed_source_fallback:
        seed_daily_briefing_source_tables_if_empty(db, build_seed_repository())
    source_repository = build_repository_from_db_sources(db, fallback=fallback_repository)
    return DailyBriefingService(
        SqlAlchemyDailyBriefingRepository(
            db,
            source_repository=source_repository,
        ),
        citation_retriever=citation_retriever or build_default_citation_retriever(),
    )
