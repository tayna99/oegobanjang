from fastapi.testclient import TestClient

from app.main import create_app


HEADERS = {
    "X-Company-Id": "company_001",
    "X-User-Role": "manager",
    "X-User-Id": "manager_001",
}


def test_agent_chat_uses_same_date_snapshot_and_display_contract(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers=HEADERS,
    ).json()
    visa_item = next(item for item in briefing["items"] if item["risk_type"] == "visa_expiry")

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "비자 관련해서 어떤 걸 해야돼?",
            "companyId": "company_001",
            "date": "2026-05-08",
            "workspaceId": "hwaseong",
            "activeTab": "today",
            "selectedCaseId": visa_item["case_id"],
            "sessionId": "alignment_display_contract",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["daily_briefing"]["date"] == briefing["date"]
    assert body["daily_briefing"]["briefing_run_id"] == briefing["briefing_run_id"]
    assert body["normalized_intent"] == "visa_expiry"
    assert body["subject_display_name"] == visa_item["subject_display_name"]
    assert body["subject_display_id"] == visa_item["subject_display_id"]
    assert body["risk_timing_label"] == visa_item["risk_timing_label"]
    assert body["case_title"] == visa_item["case_title"]
    assert body["case_summary"] == visa_item["case_summary"]
    assert body["primary_action"]["action_id"] in visa_item["next_action_ids"]
    assert body["source_labels"]
    assert visa_item["subject_display_name"] in body["answer"]
    assert "worker_001" not in body["answer"]
    assert "Nguyen Van A" not in str(body)


def test_agent_chat_selected_action_opens_document_request_context(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers=HEADERS,
    ).json()
    doc_item = next(item for item in briefing["items"] if item["risk_type"] == "missing_document")
    doc_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_id"] in doc_item["next_action_ids"]
        and action["action_type"] == "request_document"
    )

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Tran한테 서류 다시 보내달라고 정중하게 써줘",
            "companyId": "company_001",
            "date": "2026-05-08",
            "activeTab": "today",
            "selectedCaseId": doc_item["case_id"],
            "selectedActionId": doc_action["action_id"],
            "sessionId": "alignment_doc_action",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["normalized_intent"] == "document_request_message"
    assert body["approval_required"] is True
    assert [action["action_id"] for action in body["actions"]] == [doc_action["action_id"]]
    assert body["primary_action"]["action_id"] == doc_action["action_id"]
    assert body["primary_action"]["action_type"] == "request_document"
    assert body["subject_display_name"] == doc_item["subject_display_name"]
    assert "Nguyen Van A" not in str(body)


def test_agent_chat_forbidden_contract_is_unified(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "이거 바로 문자 보내줘",
            "companyId": "company_001",
            "date": "2026-05-08",
            "sessionId": "alignment_blocked_send",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "unsupported"
    assert body["structured_plan"]["execution_allowed"] is False
    assert body["actions"] == []
    assert body["approval_required"] is True
