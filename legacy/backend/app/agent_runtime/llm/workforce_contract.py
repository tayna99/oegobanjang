from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


FORBIDDEN_CANDIDATE_JUDGMENT_TERMS = (
    "성실",
    "성격",
    "오래 일할",
    "장기근속",
    "이탈 가능성",
    "도망",
    "좋은 사람",
    "더 나은 후보",
    "국적별",
    "우대",
    "추천",
    "보다 낫",
    "더 낫",
    "비자 발급 가능",
    "비자 가능",
    "비자 불가능",
    "최종 판정",
)

WORKFORCE_SYSTEM_PROMPT_VERSION = "workforce_system_prompt_v1"
WORKFORCE_TASK_PROMPT_VERSION = "workforce_task_prompt_v1"


class WorkforceAgentPromptInput(BaseModel):
    user_request: str
    company_context: dict[str, Any] = Field(default_factory=dict)
    candidate_context: list[dict[str, Any]] = Field(default_factory=list)
    rag_results: list[dict[str, Any]] = Field(default_factory=list)
    rule_results: dict[str, Any] = Field(default_factory=dict)


class MissingInput(BaseModel):
    field: str
    label: str
    severity: Literal["low", "medium", "high"] = "medium"
    reason: str = ""


class RequiredCheck(BaseModel):
    check_id: str
    label: str
    status: Literal["confirmed", "needs_input", "needs_review", "expert_review_recommended", "not_applicable"]
    source_id: str | None = None
    evidence_grade: Literal["A", "B", "C", "D", "E", "F"] | None = None


class WorkforceRequestDraft(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    region: str | None = None
    visa_type: str | None = None
    needed_headcount: int | None = None
    preferred_language: str | None = None
    requested_role: str | None = None
    housing_provided: bool | None = None
    shift_type: str | None = None
    current_foreign_workers: int | None = None
    desired_start_date: str | None = None


class CandidateReadinessItem(BaseModel):
    candidate_id: str
    nationality: str | None = None
    desired_role: str | None = None
    available_from: str | None = None
    readiness_status: Literal[
        "ready",
        "additional_check_needed",
        "missing_required_info",
        "missing_required_items",
        "needs_confirmation",
        "needs_onboarding_info",
        "blocked_due_to_forbidden_judgment",
        "not_applicable",
    ]
    ready_items: list[str] = Field(default_factory=list)
    missing_or_unconfirmed_items: list[str] = Field(default_factory=list)
    safe_description: str
    forbidden_judgment_used: bool = False

    @model_validator(mode="after")
    def reject_forbidden_candidate_judgment(self) -> "CandidateReadinessItem":
        if self.forbidden_judgment_used:
            raise ValueError("candidate readiness cannot include forbidden judgment")
        _raise_if_forbidden_text(self.safe_description)
        return self


class HandoffQuestion(BaseModel):
    target: Literal["sending_agency", "admin_scrivener", "manager", "company_manager", "candidate"]
    question: str


class RiskFlag(BaseModel):
    risk_type: Literal[
        "legal_or_administrative_review",
        "missing_required_input",
        "missing_evidence",
        "missing_official_evidence",
        "human_approval_required",
        "forbidden_judgment_blocked",
        "forbidden_candidate_judgment",
    ]
    level: Literal["low", "medium", "high", "critical"] = "medium"
    message: str


class ApprovalBlock(BaseModel):
    requires_human_approval: bool = True
    approval_reason: str
    blocked_actions: list[
        Literal[
            "auto_send_to_candidate",
            "auto_send_to_sending_agency",
            "auto_send_to_admin_scrivener",
            "auto_submit_to_government_portal",
            "final_visa_eligibility_decision",
            "candidate_scoring_or_ranking",
            "candidate_personality_judgment",
            "nationality_preference_ranking",
        ]
    ] = Field(default_factory=list)

    @field_validator("requires_human_approval")
    @classmethod
    def require_human_approval(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("workforce LLM output must require human approval")
        return value


class EvidenceReference(BaseModel):
    source_id: str
    title: str = ""
    doc_type: str = ""
    evidence_grade: Literal["A", "B", "C", "D", "E", "F"]
    used_for: str


class NextAction(BaseModel):
    action_id: str
    label: str
    requires_approval: bool = False


class WorkforceAgentResponse(BaseModel):
    agent: Literal["workforce_agent"]
    intent: Literal[
        "new_hiring",
        "candidate_review",
        "workforce_request_update",
        "handoff_question_generation",
        "unsupported_candidate_judgment",
    ]
    status: Literal["draft_ready", "needs_more_input", "needs_human_review", "blocked"]
    summary: str
    workforce_request: WorkforceRequestDraft
    missing_inputs: list[MissingInput]
    required_checks: list[RequiredCheck]
    candidate_readiness: list[CandidateReadinessItem]
    handoff_questions: list[HandoffQuestion]
    risk_flags: list[RiskFlag]
    approval: ApprovalBlock
    evidence: list[EvidenceReference]
    next_actions: list[NextAction]

    @model_validator(mode="after")
    def reject_forbidden_summary(self) -> "WorkforceAgentResponse":
        _raise_if_forbidden_text(self.summary)
        return self


def build_workforce_system_prompt() -> str:
    return """너는 외국인 고용 운영 시스템의 인력 확보 에이전트다.

너의 역할은 외국인 근로자를 추천하거나 평가하는 것이 아니다.
너의 역할은 사업장의 신규 인력 요청을 구조화하고, E-9 고용 절차상 확인해야 할 항목을 정리하고, 후보자의 제출 준비도와 추가 확인 항목을 업무적으로 정리하는 것이다.

반드시 지켜야 할 원칙:
1. 후보자의 성격, 성실도, 장기근속 가능성, 이탈 가능성을 판단하지 않는다.
2. 국적별 선호나 우열을 말하지 않는다.
3. 특정 후보를 "좋은 사람"이라고 표현하지 않는다.
4. 후보 비교는 오직 제출 준비도, 입력값 충족 여부, 추가 확인 필요 항목 기준으로만 한다.
5. 비자 가능/불가능을 최종 판정하지 않는다.
6. 공식 근거가 부족하면 "행정사 검토 필요"로 표시한다.
7. 송출회사나 행정사에게 전달하기 전에는 사람 승인이 필요하다고 표시한다.
8. 출력은 반드시 지정된 JSON 구조로만 한다.
9. JSON 밖에 설명 문장을 쓰지 않는다.

지정된 JSON 구조의 top-level key:
agent, intent, status, summary, workforce_request, missing_inputs, required_checks, candidate_readiness, handoff_questions, risk_flags, approval, evidence, next_actions
"""


def build_workforce_task_prompt(prompt_input: WorkforceAgentPromptInput) -> str:
    return "\n\n".join(
        [
            "다음 사용자 요청을 인력 확보 업무로 구조화하라.",
            "[사용자 요청]\n" + prompt_input.user_request,
            "[회사 DB 정보]\n" + _json_dumps(prompt_input.company_context),
            "[후보자 DB 정보]\n" + _json_dumps(prompt_input.candidate_context),
            "[RAG 검색 결과]\n" + _json_dumps(prompt_input.rag_results),
            "[Rule Base 결과]\n" + _json_dumps(prompt_input.rule_results),
            "[출력 요구]\n정해진 JSON 구조에 맞춰 신규 인력 요청서, 확인 필요 항목, 후보 준비도, 송출회사/행정사 질문, 승인 필요 여부를 생성하라. JSON 밖에 설명 문장을 쓰지 마라.",
        ]
    )


def parse_workforce_agent_response(raw_text: str) -> WorkforceAgentResponse:
    stripped = raw_text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        raise ValueError("JSON only response is required")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON response: {exc}") from exc
    try:
        return WorkforceAgentResponse.model_validate(payload)
    except ValidationError:
        raise


def build_workforce_response_from_runtime_output(output: dict[str, Any]) -> WorkforceAgentResponse:
    draft = dict(output.get("hiring_request_draft") or {})
    candidate_block = output.get("candidate_readiness_table") or {}
    candidate_rows = candidate_block if isinstance(candidate_block, list) else candidate_block.get("rows", [])
    payload = {
        "agent": "workforce_agent",
        "intent": _intent_from_runtime(output),
        "status": _status_from_runtime(output),
        "summary": _summary_from_runtime(output),
        "workforce_request": {
            "company_name": draft.get("company_name"),
            "industry": draft.get("industry") or output.get("industry"),
            "region": draft.get("region"),
            "visa_type": output.get("visa_type") or draft.get("visa_type") or "E-9",
            "needed_headcount": draft.get("requested_headcount") or output.get("requested_headcount"),
            "preferred_language": draft.get("preferred_language") or output.get("country"),
            "requested_role": draft.get("requested_role"),
            "housing_provided": draft.get("housing"),
            "shift_type": draft.get("shift_type"),
            "current_foreign_workers": draft.get("current_foreign_workers"),
            "desired_start_date": draft.get("preferred_start_date") or draft.get("desired_start_date"),
        },
        "missing_inputs": [
            {
                "field": field,
                "label": _field_label(field),
                "severity": "medium",
                "reason": f"{_field_label(field)} 입력이 필요합니다.",
            }
            for field in output.get("missing_context", [])
        ],
        "required_checks": _required_checks_from_runtime(output),
        "candidate_readiness": _candidate_readiness_from_runtime(candidate_rows),
        "handoff_questions": _handoff_questions_from_runtime(output),
        "risk_flags": _risk_flags_from_runtime(output),
        "approval": {
            "requires_human_approval": bool(output.get("approval_required", True)),
            "approval_reason": "송출회사 또는 행정사에게 요청서/질문을 전달하기 전 담당자 승인이 필요합니다.",
            "blocked_actions": [
                "auto_send_to_candidate",
                "auto_send_to_sending_agency",
                "auto_send_to_admin_scrivener",
                "auto_submit_to_government_portal",
                "final_visa_eligibility_decision",
                "candidate_scoring_or_ranking",
            ],
        },
        "evidence": _evidence_from_runtime(output),
        "next_actions": _next_actions_from_runtime(output),
    }
    return WorkforceAgentResponse.model_validate(payload)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _raise_if_forbidden_text(text: str) -> None:
    if any(term in text for term in FORBIDDEN_CANDIDATE_JUDGMENT_TERMS):
        raise ValueError("workforce response contains forbidden candidate judgment")


def _intent_from_runtime(output: dict[str, Any]) -> str:
    case_type = str(output.get("case_type") or "")
    if case_type == "candidate_review":
        return "candidate_review"
    return "new_hiring"


def _status_from_runtime(output: dict[str, Any]) -> str:
    if output.get("status") == "FORBIDDEN":
        return "blocked"
    if output.get("approval_required"):
        return "draft_ready"
    if output.get("missing_context"):
        return "needs_more_input"
    return "needs_human_review"


def _summary_from_runtime(output: dict[str, Any]) -> str:
    if output.get("status") == "FORBIDDEN":
        return str(output.get("blocked_reason") or "금지된 후보 판단 요청입니다.")
    headcount = output.get("requested_headcount")
    visa_type = output.get("visa_type") or "E-9"
    industry = output.get("industry") or "사업장"
    if headcount:
        return f"{industry} {visa_type} 근로자 {headcount}명 신규 채용 준비 요청을 구조화했습니다."
    return f"{industry} {visa_type} 신규 채용 준비 요청을 구조화했습니다."


def _required_checks_from_runtime(output: dict[str, Any]) -> list[dict[str, Any]]:
    citations = output.get("citations") or []
    default_source = citations[0]["source_id"] if citations else None
    default_grade = citations[0]["evidence_grade"] if citations else None
    checks = []
    for index, item in enumerate(output.get("institutional_checklist") or [], start=1):
        label = str(item.get("item") or item.get("label") or f"확인 항목 {index}")
        checks.append(
            {
                "check_id": f"check_{index:03d}",
                "label": label,
                "status": _normalize_check_status(str(item.get("status") or "needs_review")),
                "source_id": item.get("source_id") or default_source,
                "evidence_grade": item.get("evidence_grade") or default_grade,
            }
        )
    return checks


def _normalize_check_status(value: str) -> str:
    mapping = {
        "provided": "confirmed",
        "confirmed": "confirmed",
        "needs_confirmation": "needs_input",
        "needs_input": "needs_input",
        "needs_rule_check": "needs_review",
        "needs_review": "needs_review",
        "expert_review_recommended": "expert_review_recommended",
        "not_applicable": "not_applicable",
    }
    return mapping.get(value, "needs_review")


def _candidate_readiness_from_runtime(candidate_rows: Any) -> list[dict[str, Any]]:
    rows = candidate_rows if isinstance(candidate_rows, list) else []
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        missing = list(row.get("missing_required_fields") or row.get("missing_or_unconfirmed_items") or [])
        ready_items = [
            field
            for field in ("passport", "photo", "understood_housing", "understood_shift")
            if row.get(field) is True
        ]
        output.append(
            {
                "candidate_id": str(row.get("candidate_id") or f"candidate_{index:03d}"),
                "nationality": row.get("nationality"),
                "desired_role": row.get("desired_role"),
                "available_from": row.get("available_from"),
                "readiness_status": _normalize_readiness_status(str(row.get("status") or "needs_confirmation")),
                "ready_items": ready_items,
                "missing_or_unconfirmed_items": missing,
                "safe_description": _candidate_safe_description(row, missing),
                "forbidden_judgment_used": False,
            }
        )
    return output


def _normalize_readiness_status(value: str) -> str:
    mapping = {
        "ready": "ready",
        "missing_required_info": "missing_required_info",
        "needs_confirmation": "needs_confirmation",
        "needs_onboarding_info": "needs_onboarding_info",
        "missing_required_items": "missing_required_items",
        "blocked_due_to_forbidden_judgment": "blocked_due_to_forbidden_judgment",
        "not_applicable": "not_applicable",
        "additional_check_needed": "additional_check_needed",
    }
    return mapping.get(value, "needs_confirmation")


def _candidate_safe_description(row: dict[str, Any], missing: list[str]) -> str:
    candidate_id = row.get("candidate_id") or "후보"
    if missing:
        return f"후보 {candidate_id}는 {', '.join(missing)} 항목 확인이 추가로 필요합니다."
    return f"후보 {candidate_id}는 현재 입력된 제출 준비도 항목이 확인되었습니다."


def _handoff_questions_from_runtime(output: dict[str, Any]) -> list[dict[str, str]]:
    questions = []
    for question in output.get("handoff_questions") or []:
        if isinstance(question, dict):
            questions.append(
                {
                    "target": question.get("target") or "sending_agency",
                    "question": question.get("question") or "",
                }
            )
        else:
            questions.append({"target": "sending_agency", "question": str(question)})
    return questions


def _risk_flags_from_runtime(output: dict[str, Any]) -> list[dict[str, str]]:
    flags = []
    for raw in output.get("risk_flags") or []:
        if isinstance(raw, dict):
            flags.append(raw)
        elif str(raw) == "MISSING_EVIDENCE":
            flags.append(
                {
                    "risk_type": "missing_official_evidence",
                    "level": "medium",
                    "message": "인력확보 Chroma RAG에서 공식 절차 근거를 찾지 못했습니다. 행정사 또는 담당자 검토가 필요합니다.",
                }
            )
        else:
            flags.append(
                {
                    "risk_type": "legal_or_administrative_review",
                    "level": "medium",
                    "message": "AI가 최종 판정하지 않으며 담당자 또는 행정사 검토가 필요합니다.",
                }
            )
    if not flags:
        flags.append(
            {
                "risk_type": "human_approval_required",
                "level": "medium",
                "message": "외부 전달 전 담당자 승인이 필요합니다.",
            }
        )
    return flags


def _evidence_from_runtime(output: dict[str, Any]) -> list[dict[str, str]]:
    evidence = []
    for citation in output.get("citations") or []:
        evidence.append(
            {
                "source_id": citation.get("source_id", ""),
                "title": citation.get("title", ""),
                "doc_type": citation.get("doc_type") or citation.get("source_unit_type", ""),
                "evidence_grade": citation.get("evidence_grade", "E"),
                "used_for": citation.get("used_for", "required_checks"),
            }
        )
    return evidence


def _next_actions_from_runtime(output: dict[str, Any]) -> list[dict[str, Any]]:
    actions = []
    for index, action in enumerate(output.get("next_actions") or [], start=1):
        actions.append(
            {
                "action_id": action.get("action_id") or action.get("type") or f"next_action_{index:03d}",
                "label": action.get("label") or "다음 조치",
                "requires_approval": bool(action.get("requires_approval", action.get("approval_required", False))),
            }
        )
    return actions


def _field_label(field: str) -> str:
    labels = {
        "desired_start_date": "희망 입사 시점",
        "industry": "업종",
        "requested_headcount": "필요 인원",
        "region": "지역",
        "housing": "숙소 제공 여부",
        "shift_type": "근무 형태",
    }
    return labels.get(field, field)
