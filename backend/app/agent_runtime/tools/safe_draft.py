from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolContractLevel, ToolResult, ToolStatus
from app.services.context_data_service import (
    calculate_missing_documents_for_worker,
    get_company_data,
    get_message_template,
    get_worker_documents_data,
    get_worker_profile_data,
)


SUPPORTED_LANGUAGES = {
    "ko": "한국어",
    "vi": "베트남어",
    "km": "크메르어",
    "uz": "우즈베크어",
    "ne": "네팔어",
    "id": "인도네시아어",
}

WORKFORCE_CHECKS = [
    {
        "check_id": "industry_role_check",
        "label": "업종과 요청 직무 확인",
        "status": "needs_review",
        "source_id": "workforce_company_requirements",
        "evidence_grade": "E",
    },
    {
        "check_id": "local_recruitment_effort",
        "label": "내국인 구인노력 진행 여부 확인",
        "status": "needs_input",
        "source_id": "eps_employer_process",
        "evidence_grade": "B",
    },
    {
        "check_id": "employment_permit_application",
        "label": "고용허가 신청 전 구비서류 확인",
        "status": "needs_review",
        "source_id": "work24_employment_permit_application",
        "evidence_grade": "B",
    },
    {
        "check_id": "standard_contract_preparation",
        "label": "표준근로계약서 준비 여부 확인",
        "status": "needs_input",
        "source_id": "eps_employer_process",
        "evidence_grade": "B",
    },
    {
        "check_id": "housing_shift_notice",
        "label": "숙소와 근무조건 사전 안내 준비",
        "status": "needs_input",
        "source_id": "workforce_company_requirements",
        "evidence_grade": "E",
    },
]


def _masked_worker_id(worker_id: str | None) -> str:
    return "worker_***" if worker_id else "worker_***"


def _approval_object(reason: str = "외부 전달 전 담당자 승인이 필요합니다.") -> dict[str, Any]:
    return {
        "approval_required": True,
        "status": "PENDING",
        "reason": reason,
    }


def build_hiring_request_draft_payload(
    *,
    company_id: str,
    needed_headcount: int | None = None,
    preferred_language: str | None = None,
    requested_role: str | None = None,
    desired_start_date: str | None = None,
    user_request: str = "",
) -> dict[str, Any]:
    company = get_company_data(company_id)
    if company is None:
        return {
            "status": "FAILED",
            "input_snapshot": {"company_id": company_id},
            "error": "사업장 정보를 찾을 수 없습니다.",
            "risk_flags": ["COMPANY_CONTEXT_MISSING"],
        }

    request = {
        "company_id": company.get("id"),
        "company_name": company.get("name"),
        "industry": company.get("industry"),
        "region": company.get("region"),
        "visa_type": "E-9",
        "needed_headcount": needed_headcount,
        "preferred_language": preferred_language,
        "requested_role": requested_role or company.get("requested_role"),
        "housing_provided": _boolish(company.get("housing_available")),
        "shift_type": company.get("shift_type"),
        "current_foreign_workers": _int_or_none(company.get("current_foreign_workers")),
        "desired_start_date": desired_start_date or company.get("preferred_start_date"),
    }
    missing_fields = [
        field
        for field in (
            "industry",
            "region",
            "needed_headcount",
            "requested_role",
            "shift_type",
            "desired_start_date",
        )
        if request.get(field) in (None, "")
    ]
    handoff_questions = [
        "위 사업장 조건으로 후보군 확인이 가능한가요?",
        "후보별 여권, 증명사진, 건강검진 준비 상태는 어떻게 되나요?",
        "후보별 근무 가능 시점은 언제인가요?",
        "숙소 제공 및 근무조건을 사전 안내했나요?",
        "고용허가 신청 전 추가로 확인해야 할 서류가 있나요?",
    ]
    risk_flags = []
    if missing_fields:
        risk_flags.append("MISSING_WORKFORCE_REQUEST_INPUT")
    return {
        "status": "SUCCESS",
        "hiring_request_draft": request,
        "institutional_checklist": WORKFORCE_CHECKS,
        "handoff_questions": handoff_questions,
        "missing_inputs": missing_fields,
        "approval_required": True,
        "approval": _approval_object(
            "신규 인력 요청서 또는 외부 확인 질문 전달 전 담당자 승인이 필요합니다."
        ),
        "risk_flags": risk_flags,
        "citations": [
            {
                "source_id": "eps_employer_process",
                "title": "EPS 사업주 고용절차",
                "evidence_grade": "B",
                "used_for": "institutional_checklist",
            },
            {
                "source_id": "workforce_request_template",
                "title": "신규 인력 요청서 템플릿",
                "evidence_grade": "E",
                "used_for": "hiring_request_draft",
            },
        ],
        "note": (
            "이 초안은 현재 사업장 상태와 내부 템플릿으로 만든 검토용 초안이며 "
            "고용 가능 여부를 확정하지 않습니다."
        ),
        "user_request": user_request,
    }


def _boolish(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "있음", "완료"}


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _base_handoff_package(
    *,
    case_type: str,
    masked_worker_id: str,
    visa_type: str | None = None,
    stay_expires_at: str | None = None,
    contract_ends_at: str | None = None,
    risk_flags: list[str] | None = None,
    citation_ids: list[str] | None = None,
    handoff_ready: bool = True,
    handoff_blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "package_type": "expert_handoff_draft",
        "case_type": case_type,
        "worker_summary": {
            "masked_worker_id": masked_worker_id,
            "visa_type": visa_type,
            "stay_expires_at": stay_expires_at,
            "contract_ends_at": contract_ends_at,
        },
        "risk_flags": risk_flags or [],
        "evidence": {
            "citation_ids": citation_ids or [],
            "not_for_legal_judgment": True,
        },
        "approval_required": True,
        "approval": _approval_object(),
        "not_for_legal_judgment": True,
        "raw_worker_reply_included": False,
        "full_translation_included": False,
        "message_body_included": False,
        "handoff_ready": handoff_ready,
        "handoff_blockers": handoff_blockers or [],
    }


def build_handoff_package_draft_from_aggregated_output(
    aggregated_output: dict[str, Any],
    company_context: dict[str, Any] | None = None,
    worker_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an expert handoff draft only; never send or submit it."""

    del company_context
    worker_context = worker_context or {}
    handoff_blockers = list(aggregated_output.get("handoff_blockers") or [])

    visa_type = worker_context.get("visa_type")
    if not visa_type:
        handoff_blockers.append("worker_context.visa_type 누락")

    findings = aggregated_output.get("key_findings") or aggregated_output.get("summaries") or []
    if not findings:
        handoff_blockers.append("aggregated_output.key_findings 또는 summaries 누락")

    risk_reasons = aggregated_output.get("risk_reasons") or aggregated_output.get("risk_flags") or []
    approval_reasons = aggregated_output.get("approval_reasons") or []
    if not approval_reasons and aggregated_output.get("approval_required"):
        approval_reasons = ["approval_required_action"]

    case_type = str(
        aggregated_output.get("case_type")
        or worker_context.get("case_type")
        or "unknown"
    )
    package = _base_handoff_package(
        case_type=case_type,
        masked_worker_id=_masked_worker_id(worker_context.get("worker_id")),
        visa_type=visa_type,
        stay_expires_at=worker_context.get("stay_expires_at")
        or worker_context.get("visa_expires_at"),
        contract_ends_at=worker_context.get("contract_ends_at"),
        risk_flags=[str(flag) for flag in aggregated_output.get("risk_flags", [])],
        citation_ids=[str(source_id) for source_id in aggregated_output.get("citation_ids", [])],
        handoff_ready=not handoff_blockers,
        handoff_blockers=handoff_blockers,
    )
    package.update(
        {
            "case_summary": {
                "summary": "Aggregator 결과를 바탕으로 전문가 검토용 초안을 생성했습니다.",
                "risk_level": aggregated_output.get("risk_level", "MEDIUM"),
                "risk_reasons": [str(reason) for reason in risk_reasons],
            },
            "key_findings": findings,
            "approval_reasons": [str(reason) for reason in approval_reasons],
        }
    )
    return package


@tool
def generate_multilingual_message_draft(
    purpose: str,
    language: str,
    variables: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a multilingual message draft. Sending requires approval."""

    template = get_message_template(purpose, language)
    if template is None:
        return ToolResult(
            tool_name="generate_multilingual_message_draft",
            tool_grade=ToolContractLevel.SAFE_DRAFT,
            status=ToolStatus.FAILED,
            input_snapshot={"purpose": purpose, "language": language},
            error=f"{purpose} + {language} 템플릿을 찾을 수 없습니다.",
        ).model_dump()

    content = str(template.get("content") or "")
    if variables:
        for key, value in variables.items():
            content = content.replace(f"[{key}]", value)
            content = content.replace(f"[{key.upper()}]", value)

    return ToolResult(
        tool_name="generate_multilingual_message_draft",
        tool_grade=ToolContractLevel.SAFE_DRAFT,
        status=ToolStatus.SUCCESS,
        input_snapshot={"purpose": purpose, "language": language, "variables": variables},
        output={
            "draft": content,
            "language": language,
            "language_name": SUPPORTED_LANGUAGES.get(language, language),
            "purpose": purpose,
            "approval_required": True,
            "note": "이 초안은 담당자 검토와 발송 승인이 필요합니다.",
        },
    ).model_dump()


@tool
def generate_hiring_request_draft(
    company_id: str,
    needed_headcount: int | None = None,
    preferred_language: str | None = None,
    requested_role: str | None = None,
    desired_start_date: str | None = None,
    user_request: str = "",
) -> dict[str, Any]:
    """Generate a workforce request draft. External delivery requires approval."""

    payload = build_hiring_request_draft_payload(
        company_id=company_id,
        needed_headcount=needed_headcount,
        preferred_language=preferred_language,
        requested_role=requested_role,
        desired_start_date=desired_start_date,
        user_request=user_request,
    )
    status = ToolStatus.SUCCESS if payload.get("status") == "SUCCESS" else ToolStatus.FAILED
    return ToolResult(
        tool_name="generate_hiring_request_draft",
        tool_grade=ToolContractLevel.SAFE_DRAFT,
        status=status,
        input_snapshot={
            "company_id": company_id,
            "needed_headcount": needed_headcount,
            "preferred_language": preferred_language,
            "requested_role": requested_role,
            "desired_start_date": desired_start_date,
        },
        output=payload if status == ToolStatus.SUCCESS else None,
        risk_flags=payload.get("risk_flags", []),
        approval_required=bool(payload.get("approval_required", False)),
        error=payload.get("error"),
    ).model_dump()


@tool
def generate_expert_handoff_package_draft(
    worker_id: str,
    case_type: str,
    notes: str = "",
) -> dict[str, Any]:
    """Generate an expert/admin-scrivener handoff package draft. No delivery occurs."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="generate_expert_handoff_package_draft",
            tool_grade=ToolContractLevel.SAFE_DRAFT,
            status=ToolStatus.FAILED,
            input_snapshot={"masked_worker_id": _masked_worker_id(worker_id), "case_type": case_type},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    missing_result = calculate_missing_documents_for_worker(worker_id, case_type)
    submitted_docs = get_worker_documents_data(worker_id)
    missing = [item["doc_type"] for item in missing_result.get("missing", [])]
    risk_flags = []
    if missing:
        risk_flags.append(f"누락 서류 {len(missing)}건 있음: {missing}")

    package = _base_handoff_package(
        case_type=case_type,
        masked_worker_id=_masked_worker_id(worker_id),
        visa_type=worker.get("visa_type"),
        stay_expires_at=worker.get("visa_expires_at"),
        contract_ends_at=worker.get("contract_ends_at"),
        risk_flags=risk_flags,
    )
    package.update(
        {
            "document_summary": {
                "submitted_documents": [str(doc.get("doc_type")) for doc in submitted_docs],
                "missing_documents": missing,
            },
            "notes": notes,
            "note": "이 패키지는 담당자 검토 후 전문가에게 전달 승인해야 합니다.",
        }
    )

    return ToolResult(
        tool_name="generate_expert_handoff_package_draft",
        tool_grade=ToolContractLevel.SAFE_DRAFT,
        status=ToolStatus.SUCCESS,
        input_snapshot={"masked_worker_id": _masked_worker_id(worker_id), "case_type": case_type},
        output=package,
        risk_flags=risk_flags,
        approval_required=True,
    ).model_dump()
