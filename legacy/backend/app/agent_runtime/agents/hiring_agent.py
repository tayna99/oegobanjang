"""Workforce Agent: 채용·고용허가 절차 안내, 후보자 서류 준비 상태 확인."""
from typing import Any

from app.agent_runtime.agents.candidate_readiness_agent import (
    CandidateReadinessAgent,
    CandidateReadinessRequest,
)
from app.agent_runtime.agents.workforce_requirement_agent import (
    WorkforceRequirementAgent,
    WorkforceRequirementRequest,
)
from app.agent_runtime.schemas import ForeignHiringState, EventType
from app.agent_runtime.tools.registry import (
    calculate_candidate_readiness,
    generate_hiring_request_draft,
    get_candidate_profile,
    get_company_profile,
    get_worker_profile,
    search_policy_documents,
    get_document_requirements,
    generate_expert_handoff_package_draft,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event

_TOOLS = [
    get_company_profile,
    get_worker_profile,
    get_candidate_profile,
    calculate_candidate_readiness,
    generate_hiring_request_draft,
    search_policy_documents,
    get_document_requirements,
    generate_expert_handoff_package_draft,
]

_SYSTEM_PROMPT = """당신은 외국인 고용 운영 시스템의 채용·고용허가 전문 에이전트입니다.

역할:
- 외국인 고용허가 절차 안내
- 신규 인력 요청서 초안 생성
- 사업장 요건 확인
- 후보 제출 준비도 확인
- 채용 단계별 필요 서류 안내
- 사업장 등록 절차 안내

제약:
- 국적별 선호 또는 차별적 추천을 하지 않습니다.
- 후보자의 성실도나 이탈 가능성을 판단하지 않습니다.
- 모든 안내에 공식 근거(EPS 절차, 법령)를 명시합니다.

사용 가능한 tools: get_company_profile, get_candidate_profile,
calculate_candidate_readiness, generate_hiring_request_draft,
get_worker_profile, search_policy_documents, get_document_requirements,
generate_expert_handoff_package_draft"""


class WorkforceAgent:
    """Top-level workforce agent that owns the workforce subagents."""

    def __init__(
        self,
        *,
        requirement_agent: WorkforceRequirementAgent | None = None,
        candidate_readiness_agent: CandidateReadinessAgent | None = None,
    ) -> None:
        self.sub_agents = {
            "workforce_requirement_agent": requirement_agent or WorkforceRequirementAgent(),
            "candidate_readiness_agent": (
                candidate_readiness_agent or CandidateReadinessAgent()
            ),
        }

    def run(
        self,
        state: ForeignHiringState,
        *,
        needed_headcount: int | None = None,
        preferred_language: str | None = None,
        requested_role: str | None = None,
        desired_start_date: str | None = None,
    ) -> dict[str, Any]:
        company_id = state.company_id or str(state.company_context.get("id") or "")
        role = (
            requested_role
            or str(state.company_context.get("requested_role") or "")
            or None
        )
        requirement_result = self.sub_agents[
            "workforce_requirement_agent"
        ].build_hiring_request(
            WorkforceRequirementRequest(
                company_id=company_id,
                needed_headcount=needed_headcount,
                preferred_language=preferred_language,
                requested_role=role,
                desired_start_date=desired_start_date,
                user_request=state.user_message,
            )
        )
        draft = requirement_result.hiring_request_draft
        candidate_result = self.sub_agents[
            "candidate_readiness_agent"
        ].review_candidates(
            CandidateReadinessRequest(
                candidate_id=state.candidate_id or None,
                company_id=company_id or None,
                requested_role=role or draft.get("requested_role"),
            )
        )
        sub_agent_results = {
            "workforce_requirement_agent": requirement_result.model_dump(),
            "candidate_readiness_agent": candidate_result.model_dump(),
        }
        risk_flags = _dedupe(
            requirement_result.risk_flags + candidate_result.risk_flags
        )
        evidence_events = (
            requirement_result.evidence_events + candidate_result.evidence_events
        )
        return {
            "agent": "workforce_agent",
            "summary": "인력 확보 서브에이전트 실행 완료",
            "sub_agents": [
                "workforce_requirement_agent",
                "candidate_readiness_agent",
            ],
            "sub_agent_results": sub_agent_results,
            "hiring_request_draft": draft,
            "institutional_checklist": requirement_result.institutional_checklist,
            "candidate_readiness_table": candidate_result.candidate_readiness_table,
            "handoff_questions": requirement_result.handoff_questions,
            "approval_required": requirement_result.approval_required,
            "risk_flags": risk_flags,
            "evidence_events": evidence_events,
            "tool_calls": 0,
        }


def run_hiring_agent(state: ForeignHiringState) -> dict[str, Any]:
    """workforce_agent 실행."""
    allowed, reason = check_llm_limit(state)
    if not allowed:
        return {"error": reason}

    agent_result = WorkforceAgent().run(state)
    risk_flags_new = list(agent_result.get("risk_flags", []))

    state.agent_results.append(agent_result)
    state.risk_flags.extend(risk_flags_new)

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="workforce_agent",
        step_name="hiring_agent",
        summary="workforce_agent 실행. subagent 2건",
    )
    log_event(state, event)

    return agent_result


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
