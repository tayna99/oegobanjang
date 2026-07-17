"""rag 서비스(B1) — FastAPI 엔드포인트. OPENAI_API_KEY 불필요(OfflineEchoChatModel로 의존성 오버라이드)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.pgvector


@pytest.fixture()
def client():
    from oe_rag.api import app
    from oe_rag.store.pgvector_store import read_manifest

    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")

    with TestClient(app) as test_client:
        yield test_client
    from oe_rag.api import get_chat_model

    app.dependency_overrides.pop(get_chat_model, None)


def test_health_returns_ok_when_indexed(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["collections"]) == {"workforce_official", "workforce_templates"}


def test_health_returns_503_when_collection_missing(client: TestClient, monkeypatch) -> None:
    import oe_rag.agent.tools as tools_module

    monkeypatch.setattr(tools_module, "read_manifest", lambda *_a, **_k: None)
    response = client.get("/health")

    assert response.status_code == 503


def test_retrieve_returns_records() -> None:
    from oe_rag.api import app
    from oe_rag.store.pgvector_store import read_manifest

    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")

    with TestClient(app) as test_client:
        response = test_client.post(
            "/retrieve", json={"query": "내국인 구인노력은 언제 확인해야 해?", "case_type": "new_hiring"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_count"] > 0
    for record in body["records"]:
        assert record["evidence_grade"] not in {"D", "F"}


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event_type = next((line.removeprefix("event: ") for line in lines if line.startswith("event: ")), "")
        data_line = next((line.removeprefix("data: ") for line in lines if line.startswith("data: ")), "{}")
        events.append((event_type, json.loads(data_line)))
    return events


def test_agent_run_streams_step_then_structured_then_done() -> None:
    from oe_rag.agent.fake_model import OfflineEchoChatModel
    from oe_rag.api import app, get_chat_model
    from oe_rag.store.pgvector_store import read_manifest

    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")

    query = "내국인 구인노력은 언제 확인해야 해?"
    app.dependency_overrides[get_chat_model] = lambda: OfflineEchoChatModel(
        tool_args={"query": query, "case_type": "new_hiring"}
    )
    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/agent/run", json={"query": query, "case_type": "new_hiring", "thread_id": "test-thread-1"}
            )
    finally:
        app.dependency_overrides.pop(get_chat_model, None)

    assert response.status_code == 200
    events = _parse_sse(response.text)
    event_types = [event_type for event_type, _ in events]

    assert "step" in event_types
    assert event_types[-1] == "done"
    structured_index = event_types.index("structured")
    step_indices = [i for i, t in enumerate(event_types) if t == "step"]
    assert all(i < structured_index for i in step_indices), "step 이벤트는 structured보다 먼저 와야 한다"

    structured_data = next(data for etype, data in events if etype == "structured")
    assert structured_data["missing_evidence"] is False
    assert structured_data["citations"]


def test_agent_run_missing_evidence_reports_guardrail_step() -> None:
    from oe_rag.agent.fake_model import OfflineEchoChatModel
    from oe_rag.api import app, get_chat_model
    from oe_rag.store.pgvector_store import read_manifest

    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")

    query = "완전히 무관한 xyz999 질의"
    app.dependency_overrides[get_chat_model] = lambda: OfflineEchoChatModel(
        tool_args={"query": query, "case_type": "nonexistent_case_type_xyz"}
    )
    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/agent/run", json={"query": query, "case_type": "nonexistent_case_type_xyz", "thread_id": "test-thread-2"}
            )
    finally:
        app.dependency_overrides.pop(get_chat_model, None)

    events = _parse_sse(response.text)
    step_events = [data for etype, data in events if etype == "step"]
    assert any(step["kind"] == "guardrail" for step in step_events)

    structured_data = next(data for etype, data in events if etype == "structured")
    assert structured_data["missing_evidence"] is True
