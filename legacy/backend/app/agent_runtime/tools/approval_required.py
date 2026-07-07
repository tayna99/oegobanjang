"""APPROVAL_REQUIRED: 관리자 승인 없이 실행 불가. 항상 NEEDS_APPROVAL 반환."""
from typing import Any
from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolResult, ToolContractLevel, ToolStatus

_APPROVAL_REASON = "담당자 승인 후 실행 가능한 작업입니다."


@tool
def send_worker_message(worker_id: str, message: str, channel: str = "sms") -> dict[str, Any]:
    """근로자에게 메시지를 발송합니다. (승인 필요)

    Args:
        worker_id: 근로자 ID
        message: 발송할 메시지 내용
        channel: 발송 채널 (sms, kakao)
    """
    return ToolResult(
        tool_name="send_worker_message",
        tool_grade=ToolContractLevel.APPROVAL_REQUIRED,
        status=ToolStatus.NEEDS_APPROVAL,
        input_snapshot={"worker_id": worker_id, "channel": channel},
        approval_required=True,
        error=_APPROVAL_REASON,
    ).model_dump()


@tool
def send_expert_package(
    worker_id: str,
    expert_type: str = "admin_officer",
    package_summary: str = "",
) -> dict[str, Any]:
    """행정사/노무사에게 케이스 패키지를 전달합니다. (승인 필요)

    Args:
        worker_id: 근로자 ID
        expert_type: 전문가 유형 (admin_officer, labor_attorney)
        package_summary: 패키지 요약
    """
    return ToolResult(
        tool_name="send_expert_package",
        tool_grade=ToolContractLevel.APPROVAL_REQUIRED,
        status=ToolStatus.NEEDS_APPROVAL,
        input_snapshot={"worker_id": worker_id, "expert_type": expert_type},
        approval_required=True,
        error=_APPROVAL_REASON,
    ).model_dump()


@tool
def update_case_status_completed(case_id: str, notes: str = "") -> dict[str, Any]:
    """케이스 상태를 완료로 변경합니다. (승인 필요)

    Args:
        case_id: 케이스 ID
        notes: 완료 메모
    """
    return ToolResult(
        tool_name="update_case_status_completed",
        tool_grade=ToolContractLevel.APPROVAL_REQUIRED,
        status=ToolStatus.NEEDS_APPROVAL,
        input_snapshot={"case_id": case_id},
        approval_required=True,
        error=_APPROVAL_REASON,
    ).model_dump()
