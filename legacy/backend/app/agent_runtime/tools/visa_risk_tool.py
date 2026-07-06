from __future__ import annotations

from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolContractLevel, ToolResult, ToolStatus
from app.services.context_data_service import get_worker_profile_data


VISA_PREPARATION_DAYS: dict[str, int] = {
    "E-9": 120,
    "E-7": 90,
    "E-7-1": 90,
    "F-2": 90,
    "D-10": 90,
}
DEFAULT_PREPARATION_DAYS = 90

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _visa_risk_level(d_day: int, prep_days: int) -> str:
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


def _higher_risk(a: str, b: str) -> str:
    return a if _RISK_ORDER.get(a, 0) >= _RISK_ORDER.get(b, 0) else b


@tool
def assess_visa_risk(
    worker_id: str,
    reference_date: str | None = None,
) -> dict[str, Any]:
    """비자 유형별 준비 기간과 계약 만료를 교차한 종합 위험도 판정."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="assess_visa_risk",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()

    today = _parse_date(reference_date) or date.today()
    visa_expires = _parse_date(str(worker.get("visa_expires_at") or ""))
    if visa_expires is None:
        return ToolResult(
            tool_name="assess_visa_risk",
            tool_grade=ToolContractLevel.SAFE_CALCULATE,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="체류 만료일을 해석할 수 없습니다.",
        ).model_dump()

    visa_type = str(worker.get("visa_type") or "")
    prep_days = VISA_PREPARATION_DAYS.get(visa_type, DEFAULT_PREPARATION_DAYS)
    visa_d_day = (visa_expires - today).days
    visa_risk = _visa_risk_level(visa_d_day, prep_days)

    risk_flags: list[str] = []
    if visa_d_day < 0:
        n = abs(visa_d_day)
        if n <= 30:
            risk_flags.append(f"체류기간 초과 {n}일")
        elif n <= 90:
            risk_flags.append(f"체류기간 초과 {n}일 (장기 초과)")
        else:
            risk_flags.append(f"체류기간 초과 {n}일 (심각)")
    elif visa_d_day < prep_days:
        risk_flags.append(f"체류만료 D-{visa_d_day} ({visa_type} 준비기간 {prep_days}일 기준)")

    contract_ends = _parse_date(str(worker.get("contract_ends_at") or ""))
    contract_d_day: int | None = None
    contract_risk = "LOW"

    if contract_ends is not None:
        contract_d_day = (contract_ends - today).days
        contract_risk = _visa_risk_level(contract_d_day, prep_days)
        if contract_d_day < 0 and visa_d_day >= 0:
            risk_flags.append(f"계약 만료 {abs(contract_d_day)}일 초과 (비자는 유효)")
        elif contract_d_day < visa_d_day:
            risk_flags.append(f"계약 만료(D-{contract_d_day})가 비자 만료(D-{visa_d_day})보다 먼저 도래")

    effective_d_day = min(visa_d_day, contract_d_day) if contract_d_day is not None else visa_d_day
    risk_level = _higher_risk(visa_risk, contract_risk)

    reasons: list[str] = []
    if risk_level == "CRITICAL":
        reasons.append("즉시 조치 필요")
    elif risk_level == "HIGH":
        reasons.append("긴급 확인 필요")
    elif risk_level == "MEDIUM":
        reasons.append("준비 시작 권고")
    combined_risk_reason = " | ".join(reasons + risk_flags) if reasons else " | ".join(risk_flags)

    return ToolResult(
        tool_name="assess_visa_risk",
        tool_grade=ToolContractLevel.SAFE_CALCULATE,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={
            "worker_id": worker_id,
            "visa_type": visa_type,
            "visa_expires_at": worker.get("visa_expires_at"),
            "contract_ends_at": worker.get("contract_ends_at"),
            "visa_d_day": visa_d_day,
            "contract_d_day": contract_d_day,
            "effective_d_day": effective_d_day,
            "prep_days": prep_days,
            "risk_level": risk_level,
            "combined_risk_reason": combined_risk_reason,
            "today": today.isoformat(),
        },
        risk_flags=risk_flags,
    ).model_dump()
