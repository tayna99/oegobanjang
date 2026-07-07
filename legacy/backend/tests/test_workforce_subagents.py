from __future__ import annotations

import json
from importlib import import_module

from app.agent_runtime.schemas import ForeignHiringState
from app.agent_runtime.schemas.tool import ToolContractLevel


FORBIDDEN_MARKERS = (
    "candidate_score",
    "reliability_score",
    "absconding_prediction",
    "nationality_preference",
    "recommendation_rank",
    "recommended_candidate",
    "성실",
    "이탈 가능성",
    "국적별",
    "추천",
)


def _assert_no_forbidden_markers(payload: object) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in FORBIDDEN_MARKERS:
        assert marker not in serialized


def _require_attr(module_name: str, attr_name: str):
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        assert False, f"{module_name} module must exist: {exc}"
    assert hasattr(module, attr_name), f"{module_name}.{attr_name} must exist"
    return getattr(module, attr_name)


def test_workforce_requirement_agent_builds_complete_hiring_request_draft() -> None:
    WorkforceRequirementAgent = _require_attr(
        "app.agent_runtime.agents.workforce_requirement_agent",
        "WorkforceRequirementAgent",
    )
    WorkforceRequirementRequest = _require_attr(
        "app.agent_runtime.agents.workforce_requirement_agent",
        "WorkforceRequirementRequest",
    )
    agent = WorkforceRequirementAgent()

    result = agent.build_hiring_request(
        WorkforceRequirementRequest(
            company_id="550e8400-e29b-41d4-a716-446655440006",
            needed_headcount=3,
            preferred_language="vi",
            user_request="충북 음성 자동차부품 공장 E-9 근로자 3명 신규 인력 요청서 만들어줘.",
        )
    )

    assert result.status == "SUCCESS"
    assert result.agent == "workforce_requirement_agent"
    assert result.hiring_request_draft["company_name"] == "음성오토파트"
    assert result.hiring_request_draft["needed_headcount"] == 3
    assert result.hiring_request_draft["preferred_language"] == "vi"
    assert result.hiring_request_draft["visa_type"] == "E-9"
    assert result.hiring_request_draft["requested_role"] == "assembly"
    assert result.approval_required is True
    assert result.handoff_questions
    assert any(
        check["check_id"] == "local_recruitment_effort"
        for check in result.institutional_checklist
    )
    assert {"hiring_request_draft_created", "approval_requested"}.issubset(
        {event["event_type"] for event in result.evidence_events}
    )
    _assert_no_forbidden_markers(result.model_dump())


def test_candidate_readiness_agent_reports_requirements_without_ranking() -> None:
    CandidateReadinessAgent = _require_attr(
        "app.agent_runtime.agents.candidate_readiness_agent",
        "CandidateReadinessAgent",
    )
    CandidateReadinessRequest = _require_attr(
        "app.agent_runtime.agents.candidate_readiness_agent",
        "CandidateReadinessRequest",
    )
    agent = CandidateReadinessAgent()

    result = agent.review_candidates(
        CandidateReadinessRequest(
            company_id="550e8400-e29b-41d4-a716-446655440001",
            requested_role="assembly",
        )
    )

    assert result.status == "SUCCESS"
    assert result.agent == "candidate_readiness_agent"
    assert result.candidate_readiness_table
    candidate = next(
        row
        for row in result.candidate_readiness_table
        if row["candidate_id"] == "candidate-001"
    )
    assert candidate["readiness_status"] == "missing_required_info"
    assert candidate["requirements"]["passport"]["satisfied"] is True
    assert candidate["requirements"]["photo"]["satisfied"] is False
    assert candidate["requirements"]["health_check"]["satisfied"] is False
    assert candidate["requirements"]["desired_role_match"]["satisfied"] is True
    assert candidate["requirements_satisfied"] is False
    assert "photo" in candidate["missing_or_unconfirmed_items"]
    assert result.approval_required is False
    assert {"candidate_readiness_calculated", "final_response_generated"}.issubset(
        {event["event_type"] for event in result.evidence_events}
    )
    _assert_no_forbidden_markers(result.model_dump())


def test_workforce_agent_owns_and_runs_requirement_and_readiness_subagents() -> None:
    WorkforceAgent = _require_attr(
        "app.agent_runtime.agents.hiring_agent",
        "WorkforceAgent",
    )
    agent = WorkforceAgent()

    assert set(agent.sub_agents) == {
        "workforce_requirement_agent",
        "candidate_readiness_agent",
    }

    result = agent.run(
        ForeignHiringState(
            company_id="550e8400-e29b-41d4-a716-446655440006",
            user_message="충북 음성 자동차부품 공장 E-9 근로자 3명 신규 인력 요청서와 후보 준비도 확인해줘.",
        ),
        needed_headcount=3,
        preferred_language="vi",
    )

    assert result["agent"] == "workforce_agent"
    assert result["sub_agents"] == [
        "workforce_requirement_agent",
        "candidate_readiness_agent",
    ]
    assert set(result["sub_agent_results"]) == {
        "workforce_requirement_agent",
        "candidate_readiness_agent",
    }
    assert result["hiring_request_draft"]["company_name"] == "음성오토파트"
    assert result["candidate_readiness_table"]
    assert result["approval_required"] is True
    _assert_no_forbidden_markers(result)


def test_workforce_tools_are_registered_with_contract_grades() -> None:
    TOOL_REGISTRY = _require_attr("app.agent_runtime.tools.registry", "TOOL_REGISTRY")

    assert TOOL_REGISTRY["get_company_profile"][1] == ToolContractLevel.SAFE_READ
    assert TOOL_REGISTRY["get_candidate_profile"][1] == ToolContractLevel.SAFE_READ
    assert TOOL_REGISTRY["calculate_candidate_readiness"][1] == ToolContractLevel.SAFE_CALCULATE
    assert TOOL_REGISTRY["generate_hiring_request_draft"][1] == ToolContractLevel.SAFE_DRAFT


def test_workforce_tools_return_contract_outputs() -> None:
    get_company_profile = _require_attr(
        "app.agent_runtime.tools.safe_read",
        "get_company_profile",
    )
    get_candidate_profile = _require_attr(
        "app.agent_runtime.tools.safe_read",
        "get_candidate_profile",
    )
    calculate_candidate_readiness = _require_attr(
        "app.agent_runtime.tools.safe_calculate",
        "calculate_candidate_readiness",
    )
    generate_hiring_request_draft = _require_attr(
        "app.agent_runtime.tools.safe_draft",
        "generate_hiring_request_draft",
    )

    company = get_company_profile.invoke(
        {"company_id": "550e8400-e29b-41d4-a716-446655440006"}
    )
    candidate = get_candidate_profile.invoke({"candidate_id": "candidate-001"})
    readiness = calculate_candidate_readiness.invoke(
        {
            "company_id": "550e8400-e29b-41d4-a716-446655440001",
            "requested_role": "assembly",
        }
    )
    draft = generate_hiring_request_draft.invoke(
        {
            "company_id": "550e8400-e29b-41d4-a716-446655440006",
            "needed_headcount": 3,
            "preferred_language": "vi",
        }
    )

    assert company["status"] == "SUCCESS"
    assert candidate["status"] == "SUCCESS"
    assert readiness["status"] == "SUCCESS"
    assert draft["status"] == "SUCCESS"
    assert readiness["output"]["candidate_readiness_table"]
    assert draft["output"]["hiring_request_draft"]["needed_headcount"] == 3
    assert draft["approval_required"] is True
    _assert_no_forbidden_markers(
        {
            "company": company,
            "candidate": candidate,
            "readiness": readiness,
            "draft": draft,
        }
    )
