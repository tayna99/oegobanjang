from __future__ import annotations

from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolContractLevel, ToolResult, ToolStatus
from app.services.context_data_service import (
    calculate_candidate_readiness as calculate_candidate_readiness_rows,
    calculate_missing_documents_for_worker,
    get_worker_profile_data,
)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


@tool
def calculate_visa_d_day(worker_id: str) -> dict[str, Any]:
    """Calculate D-day to visa expiration from DB-backed worker context."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="calculate_visa_d_day",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    expires_at = _parse_date(str(worker.get("visa_expires_at") or ""))
    if expires_at is None:
        return ToolResult(
            tool_name="calculate_visa_d_day",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="체류 만료일을 해석할 수 없습니다.",
        ).model_dump()

    today = date.today()
    d_day = (expires_at - today).days
    risk_level = "LOW"
    if d_day <= 30:
        risk_level = "HIGH"
    elif d_day <= 90:
        risk_level = "MEDIUM"

    risk_flags = []
    if d_day < 0:
        risk_flags.append(f"체류기간 초과 ({abs(d_day)}일 경과)")
    elif d_day <= 30:
        risk_flags.append(f"체류만료 D-{d_day} 긴급 구간")
    elif d_day <= 90:
        risk_flags.append(f"체류만료 D-{d_day} 주의 구간")

    return ToolResult(
        tool_name="calculate_visa_d_day",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={
            "worker_id": worker_id,
            "visa_type": worker.get("visa_type"),
            "visa_expires_at": worker.get("visa_expires_at"),
            "d_day": d_day,
            "risk_level": risk_level,
            "today": today.isoformat(),
        },
        risk_flags=risk_flags,
    ).model_dump()


@tool
def calculate_missing_documents(worker_id: str, case_type: str) -> dict[str, Any]:
    """Calculate missing required documents from DB-backed rule/context data."""

    result = calculate_missing_documents_for_worker(worker_id, case_type)
    if not result.get("found"):
        return ToolResult(
            tool_name="calculate_missing_documents",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id, "case_type": case_type},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    risk_flags = []
    if result["missing_count"]:
        risk_flags.append(
            f"누락 서류 {result['missing_count']}건: "
            f"{[item['doc_type'] for item in result['missing']]}"
        )

    return ToolResult(
        tool_name="calculate_missing_documents",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id, "case_type": case_type},
        output=result,
        risk_flags=risk_flags,
    ).model_dump()


@tool
def calculate_candidate_readiness(
    candidate_id: str | None = None,
    company_id: str | None = None,
    requested_role: str | None = None,
) -> dict[str, Any]:
    """Calculate candidate requirement readiness without scoring or ranking."""

    rows = calculate_candidate_readiness_rows(
        candidate_id=candidate_id,
        company_id=company_id,
        requested_role=requested_role,
    )
    missing_count = sum(
        1 for row in rows if not bool(row.get("requirements_satisfied"))
    )
    return ToolResult(
        tool_name="calculate_candidate_readiness",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={
            "candidate_id": candidate_id,
            "company_id": company_id,
            "requested_role": requested_role,
        },
        output={
            "candidate_readiness_table": rows,
            "total": len(rows),
            "ready_count": len(rows) - missing_count,
            "needs_more_info_count": missing_count,
            "policy": "결과는 제출 준비도와 추가 확인 항목만 표시합니다.",
        },
        risk_flags=["CANDIDATE_INFO_MISSING"] if missing_count else [],
    ).model_dump()


@tool
def calculate_contract_gap(worker_id: str) -> dict[str, Any]:
    """Calculate the gap between employment contract end and visa expiration."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="calculate_contract_gap",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    visa_expires = _parse_date(str(worker.get("visa_expires_at") or ""))
    contract_ends = _parse_date(str(worker.get("contract_ends_at") or ""))
    if visa_expires is None or contract_ends is None:
        return ToolResult(
            tool_name="calculate_contract_gap",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="계약일 또는 체류만료일을 해석할 수 없습니다.",
        ).model_dump()

    gap_days = (contract_ends - visa_expires).days
    risk_flags = []
    if gap_days > 30:
        risk_flags.append(f"계약기간이 체류기간보다 {gap_days}일 초과되어 체류연장 검토가 필요합니다.")
    elif gap_days < -30:
        risk_flags.append(f"체류기간이 계약기간보다 {abs(gap_days)}일 초과되어 계약 갱신 확인이 필요합니다.")

    return ToolResult(
        tool_name="calculate_contract_gap",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={
            "worker_id": worker_id,
            "visa_expires_at": worker.get("visa_expires_at"),
            "contract_ends_at": worker.get("contract_ends_at"),
            "gap_days": gap_days,
            "note": "양수는 계약이 비자보다 길고, 음수는 비자가 계약보다 긴 상태입니다.",
        },
        risk_flags=risk_flags,
    ).model_dump()
