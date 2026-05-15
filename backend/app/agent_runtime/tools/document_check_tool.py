from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolContractLevel, ToolResult, ToolStatus
from app.services.context_data_service import (
    calculate_missing_documents_for_worker,
    get_worker_profile_data,
)


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

_DOC_CODE_TO_KO: dict[str, str] = {
    "work_permit": "고용허가서 사본",
    "alien_registration": "외국인등록증 사본",
    "employment_contract": "표준근로계약서",
    "labor_contract": "표준근로계약서",
    "passport_copy": "여권 사본",
    "passport": "여권 사본",
    "health_certificate": "건강검진 결과서",
    "criminal_record": "범죄경력 조회서",
    "standard_contract": "표준근로계약서",
    "company_approval": "사업장 변경 승인서",
    "education_cert": "학력 증명서",
}


def _doc_code_to_ko(code: str) -> str:
    return _DOC_CODE_TO_KO.get(code.lower(), code)


def _classify_doc(doc_type: str) -> str:
    lower = doc_type.lower()
    for kw in CRITICAL_DOC_KEYWORDS:
        if kw in lower:
            return "CRITICAL"
    return "SUPPLEMENTARY"


@tool
def assess_document_priority(
    worker_id: str,
    case_type: str,
) -> dict[str, Any]:
    """누락 서류를 CRITICAL/SUPPLEMENTARY로 분류해 우선순위 위험도 반환."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="assess_document_priority",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id, "case_type": case_type},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    result = calculate_missing_documents_for_worker(worker_id, case_type)
    if not result.get("found"):
        return ToolResult(
            tool_name="assess_document_priority",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id, "case_type": case_type},
            error="서류 요건을 찾을 수 없습니다.",
        ).model_dump()

    critical_missing: list[dict[str, str]] = []
    supplementary_missing: list[dict[str, str]] = []

    for item in result.get("missing", []):
        doc_type = str(item.get("doc_type") or "")
        notes = str(item.get("notes") or "")
        entry = {"doc_type": doc_type, "notes": notes}
        if _classify_doc(doc_type) == "CRITICAL":
            critical_missing.append(entry)
        else:
            supplementary_missing.append(entry)

    critical_count = len(critical_missing)
    supplementary_count = len(supplementary_missing)

    if critical_count > 0:
        priority_risk_level = "CRITICAL"
        submission_readiness = "신청 불가"
    elif supplementary_count > 0:
        priority_risk_level = "MEDIUM"
        submission_readiness = "부분 준비"
    else:
        priority_risk_level = "LOW"
        submission_readiness = "신청 가능"

    risk_flags: list[str] = []
    if critical_count > 0:
        names = list(dict.fromkeys(_doc_code_to_ko(item["doc_type"]) for item in critical_missing))
        risk_flags.append(f"필수 서류 누락 {critical_count}건: {', '.join(names)}")
    if supplementary_count > 0:
        names = list(dict.fromkeys(_doc_code_to_ko(item["doc_type"]) for item in supplementary_missing))
        risk_flags.append(f"보조 서류 누락 {supplementary_count}건: {', '.join(names)}")

    return ToolResult(
        tool_name="assess_document_priority",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id, "case_type": case_type},
        output={
            "worker_id": worker_id,
            "case_type": case_type,
            "visa_type": worker.get("visa_type"),
            "critical_missing": critical_missing,
            "critical_missing_count": critical_count,
            "supplementary_missing": supplementary_missing,
            "supplementary_missing_count": supplementary_count,
            "total_missing": critical_count + supplementary_count,
            "present_count": result.get("present_count", 0),
            "priority_risk_level": priority_risk_level,
            "submission_readiness": submission_readiness,
        },
        risk_flags=risk_flags,
    ).model_dump()
