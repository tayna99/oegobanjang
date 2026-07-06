import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.mark.openai_smoke
def test_agent_chat_openai_smoke_routes_rag_first_with_strict_schema():
    settings = get_settings()
    if not settings.agent_chat_openai_smoke_enabled:
        pytest.skip("Set AGENT_CHAT_OPENAI_SMOKE_ENABLED=true to run real OpenAI smoke test.")
    provider = (settings.agent_chat_llm_provider or "openai").strip().lower()
    if provider not in {"openai", "ollama"}:
        provider = "openai"
    if provider == "openai" and not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY/openai_api_key is not configured.")

    client = TestClient(app)
    examples = {
        "비자 관련해서 어떤 걸 해야돼?": "visa_expiry",
        "인원이 필요해": "quota_review",
        "Tran에게 베트남어로 여권 사본 요청 메시지 만들어줘": "document_request_message",
        "Nguyen 갱신 건 행정사에게 전달할 패키지 만들어줘": "handoff_preview",
    }

    for message, expected_intent in examples.items():
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "message": message,
                "companyId": "company_001",
                "activeTab": "today",
                "sessionId": f"openai_smoke_{expected_intent}",
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
        assert body["llm_used"] is True, message
        assert body["llm_provider"] == provider, message
        assert body["fallback_used"] is False, message
        assert body["orchestration_version"] == "semantic_rag_llm_tools_v2", message
        assert body["normalized_intent"] == expected_intent, message
        assert body["structured_plan"]["intent"] == expected_intent, message
        assert body["rag_hits"], message
        assert body["sources"], message
        assert [call["name"] for call in body["tool_calls"][:4]] == [
            "agent_chat_semantic_retrieve",
            "agent_chat_llm_normalize",
            "agent_chat_tool_execute",
            "agent_chat_llm_grounded_answer",
        ], message
        assert body["executed_tools"], message
        assert "Nguyen Van A" not in body["answer"]
        assert "매칭 점수" not in body["answer"]
        assert "추천 점수" not in body["answer"]
        assert "가능하다고 확정" not in body["answer"]
