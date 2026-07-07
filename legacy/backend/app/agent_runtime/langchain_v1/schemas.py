from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FORBIDDEN_RESPONSE_KEYS = {
    "candidate_score",
    "nationality_preference",
    "reliability_score",
    "absconding_prediction",
    "final_eligibility_decision",
}

DISALLOWED_OFFICIAL_EVIDENCE_GRADES = {"D", "F"}
DISALLOWED_OFFICIAL_DOC_TYPES = {"case", "case_record"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def assert_no_forbidden_response_keys(payload: Any, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_RESPONSE_KEYS:
                raise ValueError(f"forbidden response key at {path}.{key}: {key}")
            assert_no_forbidden_response_keys(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for idx, value in enumerate(payload):
            assert_no_forbidden_response_keys(value, f"{path}[{idx}]")


def _is_disallowed_official_record(record: dict[str, Any]) -> bool:
    evidence_grade = str(record.get("evidence_grade", ""))
    doc_type = str(record.get("doc_type", ""))
    return (
        evidence_grade in DISALLOWED_OFFICIAL_EVIDENCE_GRADES
        or doc_type in DISALLOWED_OFFICIAL_DOC_TYPES
    )


IntentValue = Literal[
    "HIRING",
    "VISA_CHECK",
    "DOCUMENT_CHECK",
    "CONTACT",
    "BRIEFING",
    "UNSUPPORTED_VALUE_JUDGMENT",
    "UNSUPPORTED_LEGAL_JUDGMENT",
    "UNSUPPORTED_AUTO_SUBMISSION",
]


class AgentRuntimeInput(StrictModel):
    request_id: str
    user_message: str
    user_id: str = ""
    company_id: str = ""
    worker_id: str = ""
    candidate_id: str = ""
    thread_id: str | None = None
    persist_result: bool = False
    created_by: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalBlock(StrictModel):
    required: bool = False
    status: Literal["NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED"] = "NOT_REQUIRED"
    reason: str = ""
    blocked_actions: list[str] = Field(default_factory=list)


class HandoffDraft(StrictModel):
    available: bool = False
    package_type: str | None = None
    approval_required: bool = False
    approval_status: str | None = None
    not_for_legal_judgment: bool = True
    handoff_ready: bool = False
    handoff_blockers: list[str] = Field(default_factory=list)
    raw_worker_reply_included: bool = False
    full_translation_included: bool = False
    message_body_included: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceReference(StrictModel):
    event_type: str = ""
    source_id: str | None = None
    title: str = ""
    doc_type: str = ""
    evidence_grade: str = ""
    used_for: str = ""
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkforceAgentResponse(StrictModel):
    case_type: str = "new_hiring"
    hiring_request_draft: dict[str, Any] = Field(default_factory=dict)
    institutional_checklist: list[dict[str, Any]] = Field(default_factory=list)
    candidate_readiness_table: list[dict[str, Any]] = Field(default_factory=list)
    handoff_questions: list[dict[str, Any]] = Field(default_factory=list)


class VisaAgentResponse(StrictModel):
    visa_summary: str = ""
    missing_documents: list[str] = Field(default_factory=list)
    review_required: bool = True


class ContactAgentResponse(StrictModel):
    draft_summary: str = ""
    target_language: str | None = None
    approval_required: bool = True
    safe_delivery_note: str = "외부 발송 전 담당자 승인이 필요합니다."


class FinalResponseDraft(StrictModel):
    answer: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    risk_notices: list[str] = Field(default_factory=list)
    approval_notice: str = ""
    missing_evidence_notice: str = ""


class WorkBridgeAgentResponse(StrictModel):
    final_response: str
    detected_intents: list[IntentValue] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    approval: ApprovalBlock = Field(default_factory=ApprovalBlock)
    handoff: HandoffDraft = Field(default_factory=HandoffDraft)
    evidence_events: list[EvidenceReference] = Field(default_factory=list)
    rag_contexts: list[dict[str, Any]] = Field(default_factory=list)
    domain_payload: dict[str, Any] = Field(default_factory=dict)
    blocked_reason: str = ""

    @model_validator(mode="after")
    def _validate_response_contract(self) -> "WorkBridgeAgentResponse":
        if self.approval.required and self.approval.status == "NOT_REQUIRED":
            self.approval.status = "PENDING"
        for idx, context in enumerate(self.rag_contexts):
            if _is_disallowed_official_record(context):
                raise ValueError(
                    f"rag_contexts[{idx}] cannot use D/F/case evidence as runtime grounding"
                )
        for idx, event in enumerate(self.evidence_events):
            if event.evidence_grade in DISALLOWED_OFFICIAL_EVIDENCE_GRADES:
                raise ValueError(
                    f"evidence_events[{idx}] cannot use evidence_grade={event.evidence_grade}"
                )
            if event.doc_type in DISALLOWED_OFFICIAL_DOC_TYPES:
                raise ValueError(
                    f"evidence_events[{idx}] cannot use doc_type={event.doc_type}"
                )
        return self


class RuntimeContext(StrictModel):
    request_id: str
    user_message: str
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    rag_contexts: list[dict[str, Any]] = Field(default_factory=list)
    contact_artifacts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    interrupt_metadata: dict[str, Any] = Field(default_factory=dict)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    approval_metadata: dict[str, Any] = Field(default_factory=dict)


class LangChainRuntimeState(StrictModel):
    request_id: str
    input: AgentRuntimeInput
    raw_input_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)
    structured_response: WorkBridgeAgentResponse
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    approval: ApprovalBlock = Field(default_factory=ApprovalBlock)
    interrupt_metadata: dict[str, Any] = Field(default_factory=dict)
    checkpoint_metadata: dict[str, Any] = Field(default_factory=dict)
