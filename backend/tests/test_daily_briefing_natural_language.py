import pytest
from fastapi.testclient import TestClient

from app.agent_runtime.schemas import ForeignHiringState, Intent
from app.main import app
from app.services.daily_briefing_planner import DailyBriefingPlan, plan_daily_briefing_from_message


@pytest.fixture(autouse=True)
def disable_openai_smoke_for_deterministic_natural_language_tests(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )


def test_agent_run_routes_daily_briefing_natural_language_request():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "이번 달 외국인 직원 중 급한 케이스만 정리해줘",
            "user_id": "manager_001",
            "company_id": "company_001",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "daily_briefing" in body
    assert body["daily_briefing"]["company_id"] == "company_001"
    assert body["daily_briefing"]["risk_summary"]["total_count"] >= 1
    assert "daily_briefing" in body["detected_intents"]
    assert body["approval_required"] is True
    assert body["evidence_event_count"] >= 1
    plan = body["structured_plan"]
    assert plan["intent"] == "daily_briefing"
    assert plan["approval_required"] is True
    assert plan["execution_allowed"] is True
    assert plan["target_service"] == "daily_briefing"
    assert "company" in plan["required_context"]
    assert "workers" in plan["required_context"]
    assert "create_pending_next_actions" in plan["plan_steps"]
    assert plan["blocked_actions"] == []


def test_agent_run_daily_briefing_respects_tenant_scope():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "이번 달 외국인 직원 중 급한 케이스만 정리해줘",
            "user_id": "manager_001",
            "company_id": "company_001",
        },
        headers={
            "X-Company-Id": "other_company",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_agent_run_structured_planner_blocks_external_sending_requests():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "이번 달 외국인 직원 중 급한 케이스 정리하고 카톡으로 바로 보내줘",
            "user_id": "manager_001",
            "company_id": "company_001",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    plan = body["structured_plan"]
    assert plan["intent"] == "daily_briefing"
    assert plan["approval_required"] is True
    assert plan["execution_allowed"] is True
    assert "send_message_without_approval" in plan["blocked_actions"]
    assert body["daily_briefing"]["approval_required"] is True


def test_structured_planner_classifies_specific_natural_language_intents():
    examples = {
        "Nguyen 체류만료일 확인하고 필요한 조치 알려줘": "visa_expiry",
        "외국인 직원들 갱신 서류 빠진 거 점검해줘": "document_gap",
        "계약 종료일과 체류만료일이 겹치는 사람 있어?": "contract_visa_conflict",
        "고용변동 신고 기한 놓친 건 없는지 봐줘": "reporting_deadline",
        "신규 E-9 3명 고용 가능한지 쿼터 검토해줘": "quota_review",
        "Nguyen 갱신 건 행정사 검토 패키지 만들어줘": "handoff_preview",
        "비자 관련 업무가 뭐뭐있어?": "visa_expiry",
        "채용하고 싶은데 인원있나?": "quota_review",
        "인원이 필요해": "quota_review",
        "채용 하고 싶어": "quota_review",
        "Nguyen 현황 알려줘": "daily_briefing",
        "이번 주 기한 임박 건?": "daily_briefing",
    }

    for message, expected_intent in examples.items():
        plan = plan_daily_briefing_from_message(message)

        assert plan.should_run is True
        assert plan.intent == expected_intent
        assert plan.target_service == "daily_briefing"
        assert plan.approval_required is True
        assert "company" in plan.required_context
        assert plan.plan_steps


def test_structured_planner_marks_forbidden_government_submission_requests():
    plan = plan_daily_briefing_from_message("Nguyen 비자 갱신을 정부 포털에 바로 제출해줘")

    assert plan.should_run is False
    assert plan.intent == "forbidden"
    assert plan.execution_allowed is False
    assert "government_portal_submission" in plan.blocked_actions


def test_structured_planner_marks_discriminatory_recommendation_requests_forbidden():
    plan = plan_daily_briefing_from_message("국적별로 성실할 사람 추천해줘")

    assert plan.should_run is False
    assert plan.intent == "forbidden"
    assert plan.execution_allowed is False
    assert "discriminatory_recommendation" in plan.blocked_actions


def test_structured_planner_extracts_shortcut_entities_from_chat_prompts():
    worker_plan = plan_daily_briefing_from_message("Nguyen 현황 알려줘")
    weekly_plan = plan_daily_briefing_from_message("이번 주 기한 임박 건?")

    assert worker_plan.entities["worker_ref"] == "Nguyen"
    assert weekly_plan.entities["date_range"] == "this_week"


def test_agent_run_exposes_specific_structured_plan_intent():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "Nguyen 체류만료일 확인하고 필요한 조치 알려줘",
            "user_id": "manager_001",
            "company_id": "company_001",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["structured_plan"]["intent"] == "visa_expiry"
    assert "visa_expiry" in body["detected_intents"]
    assert body["daily_briefing"]["approval_required"] is True


def test_agent_run_returns_operational_summary_for_visa_question():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/run",
        json={
            "user_message": "비자 관련 업무가 뭐였어?",
            "user_id": "manager_001",
            "company_id": "company_001",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    answer = body["final_response"]
    assert "비자 관련 업무" in answer
    assert "체류기간" in answer
    assert "누락 서류" in answer
    assert "여권 사본" in answer
    assert "다음 처리" in answer
    assert "담당자 승인" in answer
    assert "담당자 확인이 필요한 내용입니다" not in answer
    assert "Nguyen Van A" not in answer


def test_agent_chat_adapter_returns_answer_actions_and_sources():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "비자 관련 업무가 뭐였어?",
            "companyId": "company_001",
            "workspaceId": "hwaseong",
            "activeTab": "today",
            "selectedCaseId": "case_nguyen_visa",
            "sessionId": "session_001",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == body["final_response"]
    assert "비자 관련 업무" in body["answer"]
    assert body["actions"]
    assert body["sources"]
    assert body["structured_plan"]["intent"] == "visa_expiry"


def test_agent_chat_exposes_fast_operational_route_and_tool_trace():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "위험 케이스 우선순위 브리핑",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_route_trace",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["fallback_used"] is False
    assert body["llm_used"] is False
    assert body["latency_mode"] == "rag_first_fast"
    assert body["tool_calls"]
    assert body["tool_calls"][0]["name"] == "agent_chat_rag_search"
    assert body["tool_calls"][0]["result_count"] >= 1
    assert body["rag_hits"]
    assert "operational_case" in body["retrieval_source_types"]


def test_agent_chat_uses_rag_first_route_for_daily_briefing_questions():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "비자 관련해서 어떤 걸 해야돼?",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_rag_first",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["fallback_used"] is False
    assert body["structured_plan"]["intent"] == "visa_expiry"
    assert body["rag_hits"]
    assert body["rag_hits"][0]["source_type"] in {
        "operational_case",
        "official_policy",
        "action_draft",
        "evidence_event",
    }
    assert "operational_case" in body["retrieval_source_types"]
    assert body["tool_calls"][0]["name"] == "agent_chat_rag_search"
    assert body["sources"]


def test_agent_chat_tool_trace_uses_rag_then_llm_then_rule_lookup_order():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "비자 뭐 해야 해?",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_rag_llm_rule_order",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["structured_plan"]["intent"] == "visa_expiry"
    assert [call["name"] for call in body["tool_calls"][:3]] == [
        "agent_chat_rag_search",
        "agent_chat_llm_plan",
        "daily_briefing_lookup",
    ]
    assert body["structured_plan"]["plan_steps"][:3] == [
        "retrieve_rag_intent_chunks",
        "plan_with_llm_from_rag_context",
        "load_rule_db_state_for_selected_intent",
    ]


def test_agent_chat_rag_first_does_not_depend_on_keyword_planner_for_routing(monkeypatch):
    def unknown_planner(message: str) -> DailyBriefingPlan:
        return DailyBriefingPlan(
            should_run=False,
            intent="unknown",
            approval_required=True,
            execution_allowed=False,
        )

    monkeypatch.setattr("app.api.v1.agent.plan_daily_briefing_from_message", unknown_planner)
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(app)
    variants = {
        "사람 좀 더 뽑아야 할 것 같아": "quota_review",
        "비자 쪽에서 오늘 손볼 거 있어?": "visa_expiry",
        "체류랑 계약 날짜 안 맞는 사람 보여줘": "contract_visa_conflict",
        "갱신할 때 빠진 서류만 체크해줘": "document_gap",
        "여권 사본 요청 문구 베트남어로 만들어줘": "document_request_message",
        "행정사한테 넘길 검토 자료 준비해줘": "handoff_preview",
        "오늘 위험한 외국인 고용 건만 먼저 보여줘": "daily_briefing",
        "후보자 입국 전 준비 안 된 것만 확인해줘": "candidate_readiness",
        "그 판단 근거랑 기록 다시 보여줘": "evidence_audit_review",
        "인력이 모자라서 충원해야 해": "quota_review",
        "체류기간 만료 가까운 순서로 알려줘": "visa_expiry",
        "계약 종료랑 비자 만료가 엇갈린 건 있어?": "contract_visa_conflict",
        "외국인 직원 서류 빈칸 있는지 봐줘": "document_gap",
        "베트남어로 서류 보완 요청 초안 잡아줘": "document_request_message",
        "노무사 검토용 자료 묶어줘": "handoff_preview",
        "이번 달 급한 케이스 브리핑해줘": "daily_briefing",
        "후보자 서류 준비상태만 봐줘": "candidate_readiness",
        "왜 그렇게 판단했는지 evidence 보여줘": "evidence_audit_review",
        "추가 채용 준비할 수 있어?": "quota_review",
        "비자 갱신 관련 다음 일 알려줘": "visa_expiry",
    }

    for message, expected_intent in variants.items():
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"rag_variant_{expected_intent}",
            },
            headers={
                "X-Company-Id": "company_001",
                "X-User-Role": "manager",
                "X-User-Id": "manager_001",
            },
        )

        assert response.status_code == 200, message
        body = response.json()
        assert body["route"] == "rag_first_chat", message
        assert body["structured_plan"]["intent"] == expected_intent, message
        assert body["rag_hits"], message
        assert "담당자 확인이 필요한 내용입니다" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]


def test_agent_chat_falls_back_to_daily_briefing_service_when_rag_first_fails(monkeypatch):
    def fail_rag_first(*args, **kwargs):
        raise RuntimeError("rag unavailable")

    monkeypatch.setattr("app.api.v1.agent.run_agent_chat_rag_first", fail_rag_first)
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "비자 관련해서 어떤 걸 해야돼?",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_rag_fallback",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "daily_briefing_service"
    assert body["fallback_used"] is True
    assert body["fallback_reason"] == "rag_first_failed"


def test_agent_chat_rag_first_returns_grounded_not_found_when_rag_has_no_hits():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "화성 기지 조명 색깔을 정해줘",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_rag_not_found",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["structured_plan"]["intent"] == "unsupported"
    assert body["fallback_used"] is False
    assert body["rag_hits"] == []
    assert body["tool_calls"][0]["result_count"] == 0
    assert "RAG 검색에서 관련 업무나 공식 근거를 찾지 못했습니다" in body["answer"]
    assert "담당자 확인이 필요한 내용입니다" not in body["answer"]


def test_agent_chat_blocks_external_submit_requests_before_tool_execution():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Nguyen 비자 갱신을 정부 포털에 바로 제출해줘",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_forbidden_submit",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "unsupported"
    assert body["answer"] == body["final_response"]
    assert body["structured_plan"]["execution_allowed"] is False
    assert body["tool_calls"] == []
    assert body["rag_hits"] == []


def test_agent_chat_falls_back_to_llm_agent_runtime_for_non_daily_briefing_prompt(monkeypatch):
    async def fake_run_workflow(
        user_message: str,
        user_id: str,
        company_id: str,
        thread_id: str | None = None,
    ) -> ForeignHiringState:
        return ForeignHiringState(
            request_id="req_llm_chat",
            user_id=user_id,
            company_id=company_id,
            user_message=user_message,
            detected_intents=[Intent.HIRING],
            agent_results=[
                {
                    "agent": "workforce_agent",
                    "summary": "고용허가 절차 근거를 확인했습니다.",
                    "tool_calls": 1,
                }
            ],
            tool_results=[],
            rag_contexts=[{"source_id": "eps_procedure", "title": "EPS 절차"}],
            final_response="고용허가 절차는 공식 근거 확인 후 담당자 승인 흐름으로 진행합니다.",
        )

    def unknown_planner(message: str) -> DailyBriefingPlan:
        return DailyBriefingPlan(
            should_run=False,
            intent="unknown",
            approval_required=True,
            execution_allowed=False,
        )

    def fail_rag_first(*args, **kwargs):
        raise RuntimeError("rag unavailable")

    monkeypatch.setattr("app.api.v1.agent.plan_daily_briefing_from_message", unknown_planner)
    monkeypatch.setattr("app.api.v1.agent.run_agent_chat_rag_first", fail_rag_first)
    monkeypatch.setattr("app.api.v1.agent.run_workflow", fake_run_workflow)
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "공식 근거 중심으로 고용허가 절차를 설명해줘",
            "companyId": "company_001",
            "sessionId": "session_llm_fallback",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "agent_runtime_workflow"
    assert body["fallback_used"] is True
    assert body["fallback_reason"] == "rag_first_failed"
    assert body["llm_used"] is True
    assert body["tool_calls"][0]["name"] == "workforce_agent"
    assert body["tool_calls"][0]["result_count"] == 1
    assert body["answer"] == "고용허가 절차는 공식 근거 확인 후 담당자 승인 흐름으로 진행합니다."


def test_agent_chat_covers_core_demo_cases_without_matching_scores_or_generic_fallback():
    client = TestClient(app)
    examples = [
        (
            "신규 외국인 근로자 채용 준비",
            "quota_review",
            "신규 인력/쿼터 검토",
        ),
        (
            "기존 직원 체류만료 확인",
            "visa_expiry",
            "체류기간 연장 준비",
        ),
        (
            "계약 종료일과 체류만료일 충돌 탐지",
            "contract_visa_conflict",
            "계약-체류기간 충돌 검토",
        ),
        (
            "서류 누락 일괄 점검",
            "document_gap",
            "체류/고용 서류 누락 확인",
        ),
        (
            "다국어 서류 요청 메시지 생성",
            "document_request_message",
            "누락서류 요청 초안 보기",
        ),
        (
            "행정사 전달 패키지 생성",
            "handoff_preview",
            "전문가 검토 패키지 초안 보기",
        ),
        (
            "위험 케이스 우선순위 브리핑",
            "daily_briefing",
            "오늘 확인할 외국인 고용 업무",
        ),
        (
            "신규 후보자 요건 매칭",
            "candidate_readiness",
            "후보자 서류 준비상태 확인",
        ),
        (
            "감사 로그/근거 재현 케이스",
            "evidence_audit_review",
            "근거/감사 재현",
        ),
    ]

    for message, expected_intent, expected_text in examples:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"session_{expected_intent}",
            },
            headers={
                "X-Company-Id": "company_001",
                "X-User-Role": "manager",
                "X-User-Id": "manager_001",
            },
        )

        assert response.status_code == 200, message
        body = response.json()
        assert body["structured_plan"]["intent"] == expected_intent
        assert body["route"] == "rag_first_chat"
        assert body["fallback_used"] is False
        assert body["rag_hits"], message
        assert body["tool_calls"], message
        assert expected_text in body["answer"]
        assert "담당자 확인이 필요한 내용입니다" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]
        assert "Nguyen Van A" not in body["answer"]


def test_agent_chat_covers_natural_language_variants_for_core_situation_cases():
    client = TestClient(app)
    variants = [
        (
            "요즘 일이 늘어서 외국인 인원이 필요해",
            "quota_review",
            "신규 인력/쿼터 검토",
        ),
        (
            "채용 하고 싶어. 지금 준비할 수 있는 인원 있어?",
            "quota_review",
            "신규 인력/쿼터 검토",
        ),
        (
            "비자 관련해서 어떤 걸 해야돼?",
            "visa_expiry",
            "비자 관련 업무",
        ),
        (
            "기존 직원들 체류 만료 다가오는 사람부터 알려줘",
            "visa_expiry",
            "체류기간 연장 준비",
        ),
        (
            "계약 끝나는 날이랑 체류만료일 안 맞는 케이스 있어?",
            "contract_visa_conflict",
            "계약-체류기간 충돌 검토",
        ),
        (
            "외국인 직원들 갱신 서류 빠진 거 한번 점검해줘.",
            "document_gap",
            "서류 누락 업무",
        ),
        (
            "Tran에게 베트남어로 여권 사본이랑 표준근로계약서 요청 메시지 만들어줘.",
            "document_request_message",
            "다국어 서류 요청 메시지 업무",
        ),
        (
            "Nguyen 갱신 건 행정사에게 전달할 패키지 만들어줘.",
            "handoff_preview",
            "전문가 검토 패키지 업무",
        ),
        (
            "이번 달 외국인 직원 중 급한 케이스만 정리해줘.",
            "daily_briefing",
            "오늘 확인할 외국인 고용 업무",
        ),
        (
            "후보자들 입국 전에 준비 안 된 서류만 봐줘. 점수는 빼고.",
            "candidate_readiness",
            "후보자 서류 준비상태 확인",
        ),
        (
            "이 판단 근거랑 감사 로그 다시 재현해서 보여줘.",
            "evidence_audit_review",
            "근거/감사 재현",
        ),
    ]

    for message, expected_intent, expected_text in variants:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"variant_{expected_intent}",
            },
            headers={
                "X-Company-Id": "company_001",
                "X-User-Role": "manager",
                "X-User-Id": "manager_001",
            },
        )

        assert response.status_code == 200, message
        body = response.json()
        assert body["structured_plan"]["intent"] == expected_intent
        assert body["route"] == "rag_first_chat"
        assert body["fallback_used"] is False
        assert body["latency_mode"] == "rag_first_fast"
        assert body["rag_hits"], message
        assert expected_text in body["answer"]
        assert "담당자 확인이 필요한 내용입니다" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]
        assert "Nguyen Van A" not in body["answer"]


def test_agent_chat_rag_first_handles_broad_paraphrases_without_keyword_planner(monkeypatch):
    def unknown_planner(message: str) -> DailyBriefingPlan:
        return DailyBriefingPlan(
            should_run=False,
            intent="unknown",
            approval_required=True,
            execution_allowed=False,
        )

    monkeypatch.setattr("app.api.v1.agent.plan_daily_briefing_from_message", unknown_planner)
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(app)
    variants = {
        "이번 라인에 사람 더 필요해": "quota_review",
        "외국인 근로자 추가로 뽑을 수 있어?": "quota_review",
        "채용 하고 싶은데 어떻게 하면 돼?": "quota_review",
        "E-9 새로 받을 준비 됐나?": "quota_review",
        "충원 가능 인원 확인해줘": "quota_review",
        "생산팀 인력 부족해 외국인 채용 준비 알려줘": "quota_review",
        "만료 임박한 체류 건 있어?": "visa_expiry",
        "비자 갱신 먼저 챙길 사람 누구야?": "visa_expiry",
        "체류기간 얼마 안 남은 직원 정리해줘": "visa_expiry",
        "E-9 만료 리스크 알려줘": "visa_expiry",
        "이번 주 갱신해야 할 체류 건 보여줘": "visa_expiry",
        "근로계약 끝나는 날이 비자랑 안 맞는 케이스 있어?": "contract_visa_conflict",
        "계약기간이랑 체류기간 안 맞는 사람 찾아줘": "contract_visa_conflict",
        "계약 만료랑 체류 만료 비교해줘": "contract_visa_conflict",
        "비자는 남았는데 계약은 끝나는 경우 있어?": "contract_visa_conflict",
        "계약서 날짜 충돌 확인해줘": "contract_visa_conflict",
        "누락된 서류만 모아줘": "document_gap",
        "여권 사본 빠진 사람 있어?": "document_gap",
        "외국인등록증 사본 없는 직원 확인해줘": "document_gap",
        "갱신 패키지 서류 완성됐는지 봐줘": "document_gap",
        "제출 준비 안 된 서류 점검해줘": "document_gap",
        "서류 보완 요청 문자 초안 만들어줘": "document_request_message",
        "베트남어로 누락서류 알려주는 문구 써줘": "document_request_message",
        "Tran한테 서류 다시 달라고 말해줘": "document_request_message",
        "여권이랑 외국인등록증 보내달라고 베트남어로 작성해줘": "document_request_message",
        "근로계약서 사본 요청 메시지 만들어줘": "document_request_message",
        "네팔 직원에게 내일 2시에 교육장으로 오라고 네팔어 안내문 만들어줘": "document_request_message",
        "고용변동 신고 기한 지난 케이스 있어?": "reporting_deadline",
        "행정사 검토자료 묶어줘": "handoff_preview",
        "노무사에게 넘길 초안 만들기": "handoff_preview",
        "전문가 전달용 패키지 준비해줘": "handoff_preview",
        "갱신 건 검토 패키지 초안 보여줘": "handoff_preview",
        "승인 전에 볼 handoff draft 만들어줘": "handoff_preview",
        "오늘 급한 순서대로만 정리해줘": "daily_briefing",
        "이번 달 리스크 높은 건만 보여줘": "daily_briefing",
        "우선순위 브리핑 해줘": "daily_briefing",
        "제일 먼저 처리할 건 뭐야?": "daily_briefing",
        "오늘 반장이 봐야 할 것 정리": "daily_briefing",
        "후보자 입국 전 서류 상태 확인해줘": "candidate_readiness",
        "신규 후보 준비 안 된 항목만 봐줘": "candidate_readiness",
        "추천 점수 없이 후보 서류만 확인": "candidate_readiness",
        "후보별 제출 준비 확인해줘": "candidate_readiness",
        "입국 예정자 서류 누락 알려줘": "candidate_readiness",
        "왜 이 케이스가 위험한지 근거 보여줘": "evidence_audit_review",
        "방금 판단 로그 보여줘": "evidence_audit_review",
        "감사용으로 근거 재현해줘": "evidence_audit_review",
        "evidence 기록 확인해줘": "evidence_audit_review",
        "어떤 출처 보고 말한 거야?": "evidence_audit_review",
    }

    for message, expected_intent in variants.items():
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"broad_variant_{expected_intent}",
            },
            headers={
                "X-Company-Id": "company_001",
                "X-User-Role": "manager",
                "X-User-Id": "manager_001",
            },
        )

        assert response.status_code == 200, message
        body = response.json()
        assert body["route"] == "rag_first_chat", message
        assert body["structured_plan"]["intent"] == expected_intent, message
        assert body["rag_hits"], message
        assert body["fallback_used"] is False, message
        assert body["tool_calls"][0]["name"] == "agent_chat_rag_search", message
        assert "담당자 확인이 필요한 내용입니다" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]


def test_agent_chat_rag_first_handles_beginner_level_questions_without_keyword_planner(monkeypatch):
    def unknown_planner(message: str) -> DailyBriefingPlan:
        return DailyBriefingPlan(
            should_run=False,
            intent="unknown",
            approval_required=True,
            execution_allowed=False,
        )

    monkeypatch.setattr("app.api.v1.agent.plan_daily_briefing_from_message", unknown_planner)
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(app)
    variants = {
        "사람 더 필요해": "quota_review",
        "사람이 부족해": "quota_review",
        "직원 더 뽑아야 해": "quota_review",
        "일할 사람 없어": "quota_review",
        "채용 좀 해야 할 것 같아": "quota_review",
        "비자 뭐 해야 해?": "visa_expiry",
        "비자 괜찮아?": "visa_expiry",
        "기간 얼마 남았어?": "visa_expiry",
        "끝나는 사람 있어?": "visa_expiry",
        "만료되는 사람 있어?": "visa_expiry",
        "날짜 안 맞는 거 있어?": "contract_visa_conflict",
        "계약이랑 비자 안 맞아?": "contract_visa_conflict",
        "둘이 날짜 겹쳐?": "contract_visa_conflict",
        "계약 끝나는 거랑 비자 끝나는 거 봐줘": "contract_visa_conflict",
        "고용변동 신고 봐줘": "reporting_deadline",
        "신고기한 놓친 건 있어?": "reporting_deadline",
        "뭐 빠졌어?": "document_gap",
        "서류 빠진 거 있어?": "document_gap",
        "안 낸 서류 있어?": "document_gap",
        "여권 사본 받았어?": "document_gap",
        "서류 다 됐어?": "document_gap",
        "서류 달라고 해줘": "document_request_message",
        "베트남어로 말해줘": "document_request_message",
        "네팔어로 말해줘": "document_request_message",
        "여권 보내달라고 써줘": "document_request_message",
        "다시 보내달라고 문구 만들어줘": "document_request_message",
        "직원한테 뭐라고 보내?": "document_request_message",
        "행정사한테 뭐 보내야 해?": "handoff_preview",
        "전문가한테 보낼 거 만들어줘": "handoff_preview",
        "검토자료 만들어줘": "handoff_preview",
        "누구한테 넘기면 돼?": "handoff_preview",
        "보낼 묶음 만들어줘": "handoff_preview",
        "오늘 뭐부터 해?": "daily_briefing",
        "급한 거 뭐야?": "daily_briefing",
        "뭐가 제일 위험해?": "daily_briefing",
        "먼저 볼 것만 알려줘": "daily_briefing",
        "오늘 할 일 알려줘": "daily_briefing",
        "후보자 준비됐어?": "candidate_readiness",
        "새 사람 서류 됐어?": "candidate_readiness",
        "들어올 사람 문제 있어?": "candidate_readiness",
        "입국할 사람 뭐 빠졌어?": "candidate_readiness",
        "새로 올 사람 확인해줘": "candidate_readiness",
        "왜 그렇게 봤어?": "evidence_audit_review",
        "근거 있어?": "evidence_audit_review",
        "로그 보여줘": "evidence_audit_review",
        "기록 남아 있어?": "evidence_audit_review",
        "어디 보고 말한 거야?": "evidence_audit_review",
    }

    for message, expected_intent in variants.items():
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"beginner_variant_{expected_intent}",
            },
            headers={
                "X-Company-Id": "company_001",
                "X-User-Role": "manager",
                "X-User-Id": "manager_001",
            },
        )

        assert response.status_code == 200, message
        body = response.json()
        assert body["route"] == "rag_first_chat", message
        assert body["structured_plan"]["intent"] == expected_intent, message
        assert body["rag_hits"], message
        assert body["fallback_used"] is False, message
        assert "담당자 확인이 필요한 내용입니다" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]


def test_agent_chat_blocks_discriminatory_nationality_recommendation_requests():
    client = TestClient(app)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "국적별로 성실할 사람 추천해줘",
            "companyId": "company_001",
            "activeTab": "today",
            "sessionId": "session_forbidden_discriminatory_recommendation",
        },
        headers={
            "X-Company-Id": "company_001",
            "X-User-Role": "manager",
            "X-User-Id": "manager_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "unsupported"
    assert body["structured_plan"]["execution_allowed"] is False
    assert body["tool_calls"] == []
    assert body["rag_hits"] == []
