from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.agent_runtime.tools.safe_draft import build_hiring_request_draft_payload


AGENT_NAME = "workforce_requirement_agent"


class WorkforceRequirementRequest(BaseModel):
    company_id: str
    needed_headcount: int | None = None
    preferred_language: str | None = None
    requested_role: str | None = None
    desired_start_date: str | None = None
    user_request: str = ""


class WorkforceRequirementOutput(BaseModel):
    agent: str = AGENT_NAME
    status: str
    hiring_request_draft: dict[str, Any] = Field(default_factory=dict)
    institutional_checklist: list[dict[str, Any]] = Field(default_factory=list)
    handoff_questions: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    approval_required: bool = True
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    error: str | None = None


class WorkforceRequirementAgent:
    """Creates workforce request drafts and business-condition checklists."""

    def build_hiring_request(
        self,
        request: WorkforceRequirementRequest,
    ) -> WorkforceRequirementOutput:
        payload = build_hiring_request_draft_payload(
            company_id=request.company_id,
            needed_headcount=request.needed_headcount,
            preferred_language=request.preferred_language,
            requested_role=request.requested_role,
            desired_start_date=request.desired_start_date,
            user_request=request.user_request,
        )
        if payload.get("status") != "SUCCESS":
            return WorkforceRequirementOutput(
                status="FAILED",
                approval_required=False,
                risk_flags=list(payload.get("risk_flags", [])),
                error=payload.get("error"),
                evidence_events=[
                    _event(
                        "risk_flagged",
                        "신규 인력 요청서 초안 생성에 필요한 사업장 정보를 찾지 못했습니다.",
                        approval_required=False,
                    )
                ],
            )

        source_ids = [
            str(citation.get("source_id"))
            for citation in payload.get("citations", [])
            if citation.get("source_id")
        ]
        return WorkforceRequirementOutput(
            status="SUCCESS",
            hiring_request_draft=dict(payload.get("hiring_request_draft", {})),
            institutional_checklist=list(payload.get("institutional_checklist", [])),
            handoff_questions=[str(item) for item in payload.get("handoff_questions", [])],
            missing_inputs=[str(item) for item in payload.get("missing_inputs", [])],
            citations=list(payload.get("citations", [])),
            approval_required=True,
            risk_flags=list(payload.get("risk_flags", [])),
            evidence_events=[
                _event(
                    "hiring_request_draft_created",
                    "신규 인력 요청서 초안을 생성했습니다.",
                    source_ids,
                    approval_required=True,
                ),
                _event(
                    "plan_created",
                    "사업장 확인 항목과 외부 확인 질문 초안을 정리했습니다.",
                    source_ids,
                    approval_required=True,
                ),
                _event(
                    "approval_requested",
                    "외부 전달 전 담당자 승인이 필요합니다.",
                    source_ids,
                    approval_required=True,
                ),
            ],
        )


def _event(
    event_type: str,
    summary: str,
    source_ids: list[str] | None = None,
    *,
    approval_required: bool,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "agent_name": AGENT_NAME,
        "summary": summary,
        "source_ids": source_ids or [],
        "approval_required": approval_required,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
