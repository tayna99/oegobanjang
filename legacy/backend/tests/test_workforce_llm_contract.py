import json

import pytest
from pydantic import ValidationError

from app.agent_runtime.llm.workforce_contract import (
    WorkforceAgentPromptInput,
    WorkforceAgentResponse,
    build_workforce_task_prompt,
    build_workforce_system_prompt,
    build_workforce_response_from_runtime_output,
    parse_workforce_agent_response,
)


def _sample_prompt_input() -> WorkforceAgentPromptInput:
    return WorkforceAgentPromptInput(
        user_request="충북 음성 자동차부품 공장인데 베트남 E-9 근로자 3명 추가 채용 준비해줘.",
        company_context={
            "company_id": "C001",
            "name": "샘플테크",
            "industry": "자동차부품 제조",
            "region": "충북 음성",
            "housing": True,
            "shift_type": "주야 2교대",
            "current_foreign_workers": 35,
        },
        candidate_context=[
            {
                "candidate_id": "CAN001",
                "nationality": "VN",
                "desired_role": "assembly",
                "available_from": "2026-06-01",
                "language": "vi",
                "passport": True,
                "photo": False,
                "health_check": False,
                "understood_housing": True,
                "understood_shift": False,
            }
        ],
        rag_results=[
            {
                "source_id": "eps_employer_process",
                "title": "사업주 고용절차",
                "doc_type": "procedure_step",
                "evidence_grade": "B",
                "summary": "E-9 고용허가 신청 전 사업주는 고용 절차와 필요 확인 항목을 점검해야 한다.",
            }
        ],
        rule_results={
            "missing_company_fields": [],
            "missing_candidate_fields": ["photo", "health_check", "understood_shift"],
            "forbidden_judgment_detected": False,
            "requires_human_approval": True,
        },
    )


def _valid_response_dict() -> dict:
    return {
        "agent": "workforce_agent",
        "intent": "new_hiring",
        "status": "draft_ready",
        "summary": "신규 인력 요청서 초안과 확인 질문을 생성했습니다.",
        "workforce_request": {
            "company_name": "샘플테크",
            "industry": "자동차부품 제조",
            "region": "충북 음성",
            "visa_type": "E-9",
            "needed_headcount": 3,
            "preferred_language": "vi",
            "requested_role": "assembly",
            "housing_provided": True,
            "shift_type": "주야 2교대",
            "current_foreign_workers": 35,
            "desired_start_date": None,
        },
        "missing_inputs": [
            {
                "field": "desired_start_date",
                "label": "희망 입사 시점",
                "severity": "medium",
                "reason": "신규 인력 요청서 작성에는 희망 입사 시점이 필요합니다.",
            }
        ],
        "required_checks": [
            {
                "check_id": "local_recruitment_check",
                "label": "내국인 구인노력 여부 확인",
                "status": "needs_input",
                "source_id": "eps_employer_process",
                "evidence_grade": "B",
            }
        ],
        "candidate_readiness": [
            {
                "candidate_id": "CAN001",
                "nationality": "VN",
                "desired_role": "assembly",
                "available_from": "2026-06-01",
                "readiness_status": "additional_check_needed",
                "ready_items": ["passport", "understood_housing"],
                "missing_or_unconfirmed_items": ["photo", "health_check", "understood_shift"],
                "safe_description": "후보 CAN001은 여권과 숙소 안내는 확인되었지만, 사진과 건강검진 확인이 필요합니다.",
                "forbidden_judgment_used": False,
            }
        ],
        "handoff_questions": [
            {
                "target": "sending_agency",
                "question": "후보별 여권, 증명사진, 건강검진 준비 상태는 어떻게 되나요?",
            }
        ],
        "risk_flags": [
            {
                "risk_type": "legal_or_administrative_review",
                "level": "medium",
                "message": "AI가 최종 판정하지 않으며 행정사 검토가 필요합니다.",
            }
        ],
        "approval": {
            "requires_human_approval": True,
            "approval_reason": "송출회사 또는 행정사에게 전달하기 전 담당자 승인이 필요합니다.",
            "blocked_actions": [
                "auto_send_to_candidate",
                "auto_submit_to_government_portal",
                "final_visa_eligibility_decision",
            ],
        },
        "evidence": [
            {
                "source_id": "eps_employer_process",
                "title": "사업주 고용절차",
                "doc_type": "procedure_step",
                "evidence_grade": "B",
                "used_for": "required_checks",
            }
        ],
        "next_actions": [
            {
                "action_id": "review_workforce_request",
                "label": "신규 인력 요청서 담당자 검토",
                "requires_approval": True,
            }
        ],
    }


def test_workforce_system_prompt_contains_safety_and_json_only_rules() -> None:
    prompt = build_workforce_system_prompt()

    assert "후보자의 성격, 성실도, 장기근속 가능성, 이탈 가능성을 판단하지 않는다" in prompt
    assert "국적별 선호" in prompt
    assert "비자 가능/불가능을 최종 판정하지 않는다" in prompt
    assert "JSON 밖에 설명 문장을 쓰지 않는다" in prompt
    assert "지정된 JSON 구조" in prompt


def test_workforce_task_prompt_serializes_db_rag_and_rule_inputs() -> None:
    prompt = build_workforce_task_prompt(_sample_prompt_input())

    assert "[사용자 요청]" in prompt
    assert "[회사 DB 정보]" in prompt
    assert "[후보자 DB 정보]" in prompt
    assert "[RAG 검색 결과]" in prompt
    assert "[Rule Base 결과]" in prompt
    assert "eps_employer_process" in prompt
    assert "missing_candidate_fields" in prompt


def test_workforce_agent_response_schema_accepts_valid_json_contract() -> None:
    response = WorkforceAgentResponse.model_validate(_valid_response_dict())

    assert response.agent == "workforce_agent"
    assert response.intent == "new_hiring"
    assert response.approval.requires_human_approval is True
    assert response.candidate_readiness[0].forbidden_judgment_used is False


def test_workforce_agent_response_rejects_missing_required_top_level_key() -> None:
    payload = _valid_response_dict()
    payload.pop("approval")

    with pytest.raises(ValidationError):
        WorkforceAgentResponse.model_validate(payload)


def test_workforce_agent_response_rejects_forbidden_candidate_judgment() -> None:
    payload = _valid_response_dict()
    payload["candidate_readiness"][0]["safe_description"] = "후보 CAN001은 성실해 보이고 오래 일할 사람입니다."

    with pytest.raises(ValidationError):
        WorkforceAgentResponse.model_validate(payload)


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "후보 CAN001은 더 좋은 사람입니다.",
        "후보 CAN001은 성실해 보입니다.",
        "후보 CAN001은 오래 일할 사람입니다.",
        "후보 CAN001은 이탈 가능성 낮음으로 판단됩니다.",
        "베트남 후보가 네팔 후보보다 낫습니다.",
        "후보 CAN001은 성격이 좋아 보임.",
    ],
)
def test_workforce_agent_response_rejects_forbidden_candidate_phrases(forbidden_text: str) -> None:
    payload = _valid_response_dict()
    payload["candidate_readiness"][0]["safe_description"] = forbidden_text

    with pytest.raises(ValidationError):
        WorkforceAgentResponse.model_validate(payload)


def test_parse_workforce_agent_response_accepts_json_only_and_rejects_extra_text() -> None:
    parsed = parse_workforce_agent_response(json.dumps(_valid_response_dict(), ensure_ascii=False))

    assert parsed.status == "draft_ready"

    with pytest.raises(ValueError, match="JSON only"):
        parse_workforce_agent_response("요약입니다.\n" + json.dumps(_valid_response_dict(), ensure_ascii=False))


def test_workforce_agent_response_accepts_checklist_enum_aliases() -> None:
    payload = _valid_response_dict()
    payload["candidate_readiness"][0]["readiness_status"] = "missing_required_items"
    payload["handoff_questions"][0]["target"] = "company_manager"
    payload["risk_flags"][0]["risk_type"] = "missing_official_evidence"
    payload["approval"]["blocked_actions"].extend(
        ["candidate_personality_judgment", "nationality_preference_ranking"]
    )

    response = WorkforceAgentResponse.model_validate(payload)

    assert response.candidate_readiness[0].readiness_status == "missing_required_items"
    assert response.handoff_questions[0].target == "company_manager"
    assert response.risk_flags[0].risk_type == "missing_official_evidence"


def test_workforce_agent_response_rejects_final_visa_judgment_text() -> None:
    payload = _valid_response_dict()
    payload["summary"] = "이 후보는 비자 발급 가능으로 최종 판정됩니다."

    with pytest.raises(ValidationError):
        WorkforceAgentResponse.model_validate(payload)


def test_build_workforce_response_from_runtime_output_converts_current_agent_shape() -> None:
    runtime_output = {
        "status": "SUCCESS",
        "case_type": "new_hiring",
        "requested_headcount": 3,
        "visa_type": "E-9",
        "industry": "자동차부품 제조",
        "hiring_request_draft": {
            "company_name": "샘플테크",
            "industry": "자동차부품 제조",
            "region": "충북 음성",
            "requested_headcount": 3,
            "preferred_language": "vi",
            "shift_type": "주야 2교대",
            "housing": True,
            "current_foreign_workers": 35,
            "requested_role": "assembly",
            "preferred_start_date": None,
        },
        "institutional_checklist": [
            {"item": "내국인 구인노력 여부 확인", "status": "needs_confirmation"},
        ],
        "candidate_readiness_table": {
            "rows": [
                {
                    "candidate_id": "CAN001",
                    "nationality": "VN",
                    "desired_role": "assembly",
                    "available_from": "2026-06-01",
                    "passport": True,
                    "photo": False,
                    "health_check": "unconfirmed",
                    "understood_housing": True,
                    "understood_shift": False,
                    "missing_required_fields": ["photo", "understood_shift"],
                    "status": "missing_required_info",
                }
            ]
        },
        "handoff_questions": ["후보별 여권, 사진, 건강검진 준비 상태는 어떤가요?"],
        "missing_context": ["desired_start_date"],
        "risk_flags": ["EXPERT_REVIEW_RECOMMENDED"],
        "citations": [
            {
                "source_id": "eps_employer_process",
                "title": "사업주 고용절차",
                "evidence_grade": "B",
                "source_unit_type": "procedure_step",
            }
        ],
        "next_actions": [
            {
                "type": "generate_hiring_request_draft",
                "label": "신규 인력 요청서 초안 생성",
                "approval_required": True,
            }
        ],
        "approval_required": True,
    }

    response = build_workforce_response_from_runtime_output(runtime_output)

    assert response.agent == "workforce_agent"
    assert response.status == "draft_ready"
    assert response.workforce_request.company_name == "샘플테크"
    assert response.workforce_request.needed_headcount == 3
    assert response.required_checks[0].check_id == "check_001"
    assert response.candidate_readiness[0].readiness_status == "missing_required_info"
    assert response.handoff_questions[0].target == "sending_agency"
    assert response.approval.requires_human_approval is True


@pytest.mark.parametrize(
    "user_request",
    [
        "베트남 E-9 근로자 3명 추가 채용 준비해줘.",
        "충북 음성 자동차부품 공장에서 외국인 5명 더 뽑고 싶어.",
        "숙소 제공하고 주야 2교대인데 신규 인력 요청서 만들어줘.",
        "송출회사에 후보군 확인 요청할 질문 만들어줘.",
    ],
)
def test_task_prompt_normal_request_examples_keep_json_contract(user_request: str) -> None:
    prompt_input = _sample_prompt_input()
    prompt_input.user_request = user_request

    prompt = build_workforce_task_prompt(prompt_input)

    assert user_request in prompt
    assert "[출력 요구]" in prompt
    assert "JSON 밖에 설명 문장을 쓰지 마라" in prompt


@pytest.mark.parametrize(
    "user_request",
    [
        "후보자 준비도 비교해줘.",
        "여권 있는 후보와 사진 없는 후보를 정리해줘.",
        "근무 가능일이 빠진 후보를 알려줘.",
    ],
)
def test_task_prompt_candidate_readiness_examples_keep_readiness_boundary(user_request: str) -> None:
    prompt_input = _sample_prompt_input()
    prompt_input.user_request = user_request

    prompt = build_workforce_task_prompt(prompt_input)

    assert user_request in prompt
    assert "[후보자 DB 정보]" in prompt
    assert "후보 준비도" in prompt
