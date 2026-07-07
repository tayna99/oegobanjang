from fastapi.testclient import TestClient

from app.main import create_app
from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_service_blocks_company_outside_allowed_scope() -> None:
    service = DailyBriefingService(build_seed_repository())

    try:
        service.run_daily_briefing(
            company_id="company_001",
            date="2026-05-08",
            user_role="manager",
            allowed_company_ids=["company_no_risks"],
        )
    except PermissionError as exc:
        assert exc.args[0] == "TENANT_SCOPE_VIOLATION"
    else:
        raise AssertionError("expected tenant scope violation")


def test_api_blocks_company_outside_header_scope() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_no_risks", "X-User-Role": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_api_blocks_approval_outside_header_scope() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    ).json()
    approval_id = briefing["recommended_actions"][0]["approval_id"]

    response = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers={"X-Company-Id": "company_no_risks", "X-User-Role": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_api_blocks_handoff_preview_outside_header_scope() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )

    response = client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-preview",
        headers={"X-Company-Id": "company_no_risks"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_api_blocks_evidence_events_outside_header_scope() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    ).json()
    case_id = briefing["items"][0]["case_id"]

    response = client.get(
        f"/api/v1/cases/{case_id}/evidence-events",
        headers={"X-Company-Id": "company_no_risks"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_api_blocks_daily_briefing_detail_outside_header_scope() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    ).json()

    response = client.get(
        f"/api/v1/daily-briefings/{briefing['briefing_run_id']}",
        headers={"X-Company-Id": "company_no_risks"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"
