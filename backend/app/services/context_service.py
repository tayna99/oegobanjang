"""ContextSnapshot 빌더 — backend가 rag 그래프에 주입할 상태 스냅샷을 조립한다.

plans/BACKEND_CONNECT.md·M7 설계의 "상태 소스 = 스냅샷 주입"(2-phase) 구현:
backend(상태의 주인)가 tenant scope를 강제해 회사 데이터를 조회하고, Risk Rule
Engine(app/domain/rules.py — 순수 함수)을 여기서 실행해 severity가 확정된 스냅샷을
만든다. rag 서비스는 이 스냅샷을 소비만 하므로 LLM이 severity를 바꿀 수 없다.

PII 경계: 스키마 자체가 마스킹 컬럼만 노출한다(workers.registration_no_masked).
스냅샷 직렬화본에 여권/외국인등록번호/전화 패턴이 없음을 assert_snapshot_has_no_pii()로
이중 확인한다(발표 p.15 "입력 검증 및 필터링 계층").
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import rules
from app.models.company import Company
from app.models.document import DocumentRequirement, WorkerDocument
from app.models.worker import Worker

# rag/src/oe_rag/orchestration/guard.py의 PII_PATTERNS와 동일 계약 (프로세스가 달라 상수 중복 —
# 계약 테스트가 양쪽 드리프트를 잡는다).
_PII_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}[0-9]{7,9}(?![A-Za-z0-9])"),
    re.compile(r"(?<!\d)\d{6}-\d{7}(?!\d)"),
    re.compile(r"(?<!\d)010-\d{3,4}-\d{4}(?!\d)"),
)


class SnapshotPIIError(ValueError):
    pass


class CompanySnapshot(BaseModel):
    company_id: str
    name: str
    timezone: str = "Asia/Seoul"
    quota_limit: int | None = None
    current_foreign_worker_count: int | None = None


class RuleFinding(BaseModel):
    """Risk Rule Engine 산출 — rag 미션은 이 severity를 소비만 한다."""

    risk_type: str
    severity: str
    worker_id: str | None = None
    doc_type: str | None = None
    d_day: int | None = None
    expired: bool = False
    days_overdue: int | None = None
    display_label: str = ""


class WorkerSnapshot(BaseModel):
    worker_id: str
    display_name: str
    nationality: str
    visa_type: str
    stay_expires_at: str
    contract_ends_at: str | None = None
    preferred_language: str | None = None


class WorkerDocumentSnapshot(BaseModel):
    worker_id: str
    doc_type: str
    status: str
    required: bool = True
    due_date: str | None = None
    missing_class: str | None = None  # CRITICAL/SUPPLEMENTARY (rules.classify_missing_document)


class ContextSnapshot(BaseModel):
    """rag `/graph/run`에 주입되는 상태 스냅샷 — golden fixture로 rag와 계약 고정."""

    snapshot_version: str = "v1"
    company: CompanySnapshot
    reference_date: str
    required_context: list[str] = Field(default_factory=list)
    workers: list[WorkerSnapshot] = Field(default_factory=list)
    documents: list[WorkerDocumentSnapshot] = Field(default_factory=list)
    document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    rule_findings: list[RuleFinding] = Field(default_factory=list)


def build_context_snapshot(
    db: Session,
    *,
    company_id: str,
    required_context: list[str],
    reference_date: str | None = None,
) -> ContextSnapshot:
    """tenant-scoped 상태 조회 + 룰 실행 → 스냅샷. required_context는
    oe_rag.orchestration.planner.REQUIRED_CONTEXT_BY_INTENT 값을 그대로 받는다."""
    company_row = db.execute(select(Company).where(Company.id == company_id)).scalar_one()
    reference = reference_date or dt.date.today().isoformat()

    workers = _load_workers(db, company_id) if _needs(required_context, "workers") else []
    documents = (
        _load_documents(db, company_id) if _needs(required_context, "documents") else []
    )
    requirements = (
        _load_document_requirements(db) if _needs(required_context, "documents") else []
    )

    company = CompanySnapshot(
        company_id=company_row.id,
        name=company_row.name,
        timezone=company_row.timezone,
        quota_limit=None,
        current_foreign_worker_count=len(workers) if workers else None,
    )

    findings = _run_rules(
        reference_date=reference,
        workers=workers,
        documents=documents,
        quota_requested=_needs(required_context, "quota"),
        company=company,
    )

    snapshot = ContextSnapshot(
        company=company,
        reference_date=reference,
        required_context=list(required_context),
        workers=workers,
        documents=documents,
        document_requirements=requirements,
        rule_findings=findings,
    )
    assert_snapshot_has_no_pii(snapshot)
    return snapshot


def _needs(required_context: list[str], kind: str) -> bool:
    if not required_context:
        return True  # 명시 없으면 전체 컨텍스트 (daily_briefing 수준)
    if kind == "workers":
        return bool({"workers", "contracts", "documents"} & set(required_context))
    if kind == "documents":
        return "documents" in required_context
    return kind in required_context


def _load_workers(db: Session, company_id: str) -> list[WorkerSnapshot]:
    rows = (
        db.execute(
            select(Worker).where(Worker.company_id == company_id, Worker.status == "active")
        )
        .scalars()
        .all()
    )
    return [
        WorkerSnapshot(
            worker_id=row.id,
            display_name=row.display_name,
            nationality=row.nationality,
            visa_type=row.visa_type,
            stay_expires_at=row.stay_expires_at.isoformat(),
            contract_ends_at=row.contract_ends_at.isoformat() if row.contract_ends_at else None,
            preferred_language=row.preferred_language,
        )
        for row in rows
    ]


def _load_documents(db: Session, company_id: str) -> list[WorkerDocumentSnapshot]:
    rows = (
        db.execute(select(WorkerDocument).where(WorkerDocument.company_id == company_id))
        .scalars()
        .all()
    )
    snapshots: list[WorkerDocumentSnapshot] = []
    for row in rows:
        missing_class = (
            rules.classify_missing_document(row.doc_type) if row.status == "missing" else None
        )
        snapshots.append(
            WorkerDocumentSnapshot(
                worker_id=row.worker_id,
                doc_type=row.doc_type,
                status=row.status,
                due_date=row.due_date.isoformat() if row.due_date else None,
                missing_class=missing_class,
            )
        )
    return snapshots


def _load_document_requirements(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(DocumentRequirement)).scalars().all()
    return [
        {
            "case_type": row.case_type,
            "visa_type": row.visa_type,
            "required_doc": row.required_doc,
            "required": row.required,
            "citation_id": row.citation_id,
        }
        for row in rows
    ]


def _run_rules(
    *,
    reference_date: str,
    workers: list[WorkerSnapshot],
    documents: list[WorkerDocumentSnapshot],
    quota_requested: bool,
    company: CompanySnapshot,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for worker in workers:
        visa_eval = rules.evaluate_visa_expiry_risk(reference_date, worker.stay_expires_at)
        findings.append(
            RuleFinding(
                risk_type="visa_expiry",
                severity=visa_eval.severity,
                worker_id=worker.worker_id,
                d_day=visa_eval.d_day,
                expired=visa_eval.expired,
                days_overdue=visa_eval.days_overdue,
                display_label=rules.RISK_TYPE_DISPLAY_LABELS["visa_expiry"],
            )
        )
        if worker.contract_ends_at:
            conflict = rules.evaluate_contract_visa_conflict_risk(
                reference_date, worker.stay_expires_at, worker.contract_ends_at
            )
            if conflict is not None:
                findings.append(
                    RuleFinding(
                        risk_type="contract_visa_conflict",
                        severity=conflict.severity,
                        worker_id=worker.worker_id,
                        d_day=conflict.d_day,
                        expired=conflict.expired,
                        days_overdue=conflict.days_overdue,
                        display_label=rules.RISK_TYPE_DISPLAY_LABELS["contract_visa_conflict"],
                    )
                )

    for document in documents:
        if document.status != "missing":
            continue
        doc_eval = rules.evaluate_missing_document_risk(
            reference_date,
            rules.DocumentStatusRecord(
                worker_id=document.worker_id,
                document_type=document.doc_type,
                status=document.status,
                required=document.required,
                due_date=document.due_date,
            ),
        )
        findings.append(
            RuleFinding(
                risk_type="missing_document",
                severity=doc_eval.severity,
                worker_id=document.worker_id,
                doc_type=document.doc_type,
                d_day=doc_eval.d_day,
                expired=doc_eval.expired,
                days_overdue=doc_eval.days_overdue,
                display_label=rules.RISK_TYPE_DISPLAY_LABELS["missing_document"],
            )
        )

    if quota_requested:
        quota_eval = rules.evaluate_quota_review_risk(
            company.quota_limit, company.current_foreign_worker_count
        )
        if quota_eval is not None:
            findings.append(
                RuleFinding(
                    risk_type="quota_review",
                    severity=quota_eval.severity,
                    display_label=rules.RISK_TYPE_DISPLAY_LABELS["quota_review"],
                )
            )

    findings.sort(
        key=lambda f: (
            rules.SEVERITY_ORDER.get(f.severity, 9),
            rules.RISK_TYPE_ORDER.get(f.risk_type, 9),
            f.worker_id or "",
        )
    )
    return findings


def assert_snapshot_has_no_pii(snapshot: ContextSnapshot) -> None:
    serialized = snapshot.model_dump_json()
    for pattern in _PII_PATTERNS:
        match = pattern.search(serialized)
        if match:
            raise SnapshotPIIError(f"snapshot contains PII-like value: {match.group(0)[:4]}***")
