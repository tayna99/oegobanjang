from fastapi.testclient import TestClient

from app.main import app
from app.services.daily_briefing_planner import plan_daily_briefing_from_message


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
