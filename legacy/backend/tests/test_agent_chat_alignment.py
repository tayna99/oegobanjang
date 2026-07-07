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
            "message": "Nguyen한테 서류 다시 보내달라고 정중하게 써줘",
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
    assert body["contact_preview"]["kind"] == "message_draft"
    assert body["contact_preview"]["sent"] is False
    assert body["contact_subagents"]["contact_onboarding_subagent"]["status"] == "SUCCESS"
    assert "Nguyen Van A" not in str(body)


def test_agent_chat_contact_onboarding_runs_contact_subagent(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Nguyen에게 안전교육 일정 베트남어로 안내문 만들어줘",
            "companyId": "company_001",
            "date": "2026-05-08",
            "sessionId": "alignment_contact_onboarding",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["normalized_intent"] == "contact_onboarding"
    assert body["approval_required"] is True
    assert body["contact_preview"]["kind"] == "message_draft"
    assert body["contact_preview"]["sent"] is False
    assert body["contact_preview"]["language_code"] == "vi"
    assert body["contact_preview"]["message_purpose"] == "safety_training_notice"
    assert body["contact_subagents"]["contact_onboarding_subagent"]["status"] == "SUCCESS"
    assert any(call["name"] == "run_contact_onboarding" for call in body["tool_calls"])
    assert "Nguyen Van A" not in str(body)


def test_agent_chat_worker_reply_interpretation_runs_interpreter_subagent(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    worker_reply = "Tôi có hộ chiếu, ảnh mai gửi."
    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": f"근로자가 '{worker_reply}'라고 답했는데 요약해줘",
            "companyId": "company_001",
            "date": "2026-05-08",
            "sessionId": "alignment_worker_reply",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["normalized_intent"] == "worker_reply_interpretation"
    assert body["approval_required"] is True
    assert body["structured_plan"]["execution_allowed"] is True
    assert body["contact_preview"]["kind"] == "worker_reply_summary"
    assert body["contact_preview"]["status_applied"] is False
    assert body["contact_preview"]["status_update_candidate_count"] >= 1
    interpreter = body["contact_subagents"]["worker_reply_interpreter_subagent"]
    assert interpreter["status"] == "SUCCESS"
    assert interpreter["manager_review_required"] is True
    assert any(call["name"] == "run_worker_reply_interpreter" for call in body["tool_calls"])
    assert worker_reply not in str(body)


def test_agent_chat_worker_reply_interpretation_requires_raw_reply(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "근로자 답변 보고 상태 업데이트까지 해줘",
            "companyId": "company_001",
            "date": "2026-05-08",
            "sessionId": "alignment_worker_reply_missing_raw",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "rag_first_chat"
    assert body["normalized_intent"] == "worker_reply_interpretation"
    assert body["structured_plan"]["execution_allowed"] is False
    assert body["contact_preview"]["kind"] == "worker_reply_summary_required_input"
    assert body["contact_preview"]["status_applied"] is False
    assert body["actions"] == []
    assert "근로자 답변 원문이 필요합니다" in body["answer"]


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
