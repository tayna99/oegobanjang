from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.services.context_data_service import calculate_candidate_readiness


AGENT_NAME = "candidate_readiness_agent"


class CandidateReadinessRequest(BaseModel):
    candidate_id: str | None = None
    company_id: str | None = None
    requested_role: str | None = None


class CandidateReadinessOutput(BaseModel):
    agent: str = AGENT_NAME
    status: str
    candidate_readiness_table: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    approval_required: bool = False
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class CandidateReadinessAgent:
    """Checks candidate submission readiness without people evaluation."""

    def review_candidates(
        self,
        request: CandidateReadinessRequest,
    ) -> CandidateReadinessOutput:
        rows = calculate_candidate_readiness(
            candidate_id=request.candidate_id,
            company_id=request.company_id,
            requested_role=request.requested_role,
        )
        ready_count = sum(1 for row in rows if bool(row.get("requirements_satisfied")))
        needs_more_info_count = len(rows) - ready_count
        risk_flags = ["CANDIDATE_INFO_MISSING"] if needs_more_info_count else []
        return CandidateReadinessOutput(
            status="SUCCESS",
            candidate_readiness_table=rows,
            summary={
                "total": len(rows),
                "ready_count": ready_count,
                "needs_more_info_count": needs_more_info_count,
            },
            approval_required=False,
            risk_flags=risk_flags,
            evidence_events=[
                _event(
                    "candidate_readiness_calculated",
                    "후보 제출 준비도와 추가 확인 항목을 계산했습니다.",
                    approval_required=False,
                ),
                _event(
                    "final_response_generated",
                    "후보 준비도 검토 결과를 생성했습니다.",
                    approval_required=False,
                ),
            ],
        )


def _event(
    event_type: str,
    summary: str,
    *,
    approval_required: bool,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "agent_name": AGENT_NAME,
        "summary": summary,
        "source_ids": ["candidate_readiness_checklist"],
        "approval_required": approval_required,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
