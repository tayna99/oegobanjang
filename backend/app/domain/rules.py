"""Risk Rule Engine — 순수 함수 (발표 수정본 p.16: "severity는 deterministic, LLM은 초안만").

legacy 이식(읽기 전용 소스, 함수 발췌):
- 룰 5함수·RiskEvaluation·정렬/라벨 상수: legacy/backend/app/services/daily_briefing_service.py
- 비자유형별 준비기간 임계표·위험도 산정: legacy/backend/app/agent_runtime/tools/visa_risk_tool.py
- 누락 서류 CRITICAL/SUPPLEMENTARY 분류: legacy/backend/app/agent_runtime/tools/document_check_tool.py

이 모듈은 DB·LLM·네트워크에 일절 의존하지 않는다 — 입력은 ISO 날짜 문자열과 dataclass뿐.
rag 서비스(py3.13)가 아니라 backend(py3.14)에 두는 이유: severity 계산이 상태(DB) 옆에서
끝나고 ContextSnapshot에 실려 가므로, rag의 LLM이 severity를 만질 방법이 프로세스 경계로
차단된다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel

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

# 비자 유형별 연장 준비 기간(일) — visa_risk_tool.py 이식.
VISA_PREPARATION_DAYS: dict[str, int] = {
    "E-9": 120,
    "E-7": 90,
    "E-7-1": 90,
    "F-2": 90,
    "D-10": 90,
}
DEFAULT_PREPARATION_DAYS = 90

# 누락 서류 분류 키워드 — document_check_tool.py 이식.
CRITICAL_DOC_KEYWORDS = {
    "여권", "passport",
    "고용허가", "work_permit",
    "고용계약", "employment_contract", "labor_contract",
    "외국인등록", "alien_registration",
    "건강검진", "health_certificate",
    "범죄경력", "criminal_record",
    "표준근로계약", "standard_contract",
}

SUPPLEMENTARY_DOC_KEYWORDS = {
    "사진", "photo", "증명사진",
    "학력", "education",
    "기술자격", "technical_cert",
    "가족관계", "family_relation",
    "선서", "affidavit",
}


class RiskEvaluation(BaseModel):
    severity: str
    d_day: int | None = None
    expired: bool = False
    days_overdue: int | None = None


@dataclass
class DocumentStatusRecord:
    worker_id: str
    document_type: str
    status: str
    required: bool = True
    due_date: str | None = None


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_flexible_date(value: str | None) -> date | None:
    """visa_risk_tool의 관대한 날짜 파서 — YYYY-MM-DD / YYYY/MM/DD."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def short_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: object) -> str:
    return f"{prefix}_{short_hash(':'.join(str(part) for part in parts))}"


def canonical_document_type(document_type: str) -> str:
    normalized = str(document_type).strip().lower()
    if normalized in {"labor_contract", "standard_contract", "standard_labor_contract"}:
        return "employment_contract"
    if normalized == "arc_copy":
        return "alien_registration"
    if normalized == "passport":
        return "passport_copy"
    return normalized


# --- 룰 5함수 (daily_briefing_service.py:452-534 이식) ---------------------------------


def evaluate_visa_expiry_risk(reference_date: str, visa_expiry_date: str) -> RiskEvaluation:
    d_day = (parse_iso_date(visa_expiry_date) - parse_iso_date(reference_date)).days
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
    visa_expiry = parse_iso_date(visa_expiry_date)
    contract_end = parse_iso_date(contract_end_date)
    if contract_end <= visa_expiry:
        return None

    d_day = (visa_expiry - parse_iso_date(reference_date)).days
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
    d_day = (parse_iso_date(reporting_due_date) - parse_iso_date(reference_date)).days
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
    return (parse_iso_date(document.due_date) - parse_iso_date(reference_date)).days


# --- 비자유형별 준비기간 위험도 (visa_risk_tool.py 이식) --------------------------------


def visa_risk_level(d_day: int, prep_days: int) -> str:
    """준비기간 대비 잔여일 비율로 위험도 산정 — 비자유형 준비기간을 반영한 심화 룰."""
    if d_day < 0:
        if d_day >= -30:
            return "CRITICAL"
        return "HIGH"
    if d_day < prep_days * 0.25:
        return "CRITICAL"
    if d_day < prep_days * 0.5:
        return "HIGH"
    if d_day < prep_days:
        return "MEDIUM"
    return "LOW"


def preparation_days_for(visa_type: str | None) -> int:
    if not visa_type:
        return DEFAULT_PREPARATION_DAYS
    return VISA_PREPARATION_DAYS.get(visa_type.strip().upper(), DEFAULT_PREPARATION_DAYS)


def higher_risk(a: str, b: str) -> str:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def classify_missing_document(document_type: str) -> str:
    """누락 서류를 CRITICAL/SUPPLEMENTARY로 분류 — document_check_tool.py 이식."""
    lower = str(document_type).strip().lower()
    for keyword in CRITICAL_DOC_KEYWORDS:
        if keyword in lower:
            return "CRITICAL"
    return "SUPPLEMENTARY"
