"""/intent·/graph/run API — SSE 계약(step*→evidence*→structured→done) (pgvector, 키 불필요)."""

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


def test_intent_endpoint_returns_route_plan(client: TestClient) -> None:
    response = client.post("/intent", json={"message": "Nguyen 체류만료일 확인해줘"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "visa_expiry"
    assert body["mission"] == "m2_visa"
    assert body["required_context"] == ["company", "workers", "documents", "citations"]
    assert body["approval_required"] is True


def test_intent_endpoint_flags_forbidden(client: TestClient) -> None:
    response = client.post("/intent", json={"message": "국적별로 성실할 사람 추천해줘"})

    body = response.json()
    assert body["should_run"] is False
    assert body["intent"] == "forbidden"


def test_graph_run_streams_steps_evidence_structured_done(client: TestClient) -> None:
    response = client.post(
        "/graph/run",
        json={
            "message": "Nguyen 체류만료일 확인해줘",
            "thread_id": "t1",
            "context_snapshot": {
                "snapshot_version": "v1",
                "rule_findings": [
                    {"risk_type": "visa_expiry", "severity": "HIGH", "d_day": 20, "display_label": "체류기간 연장 준비"}
                ],
            },
        },
    )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    types = [t for t, _ in events]

    assert types[-1] == "done"
    assert types[-2] == "structured"
    assert "step" in types and "evidence" in types
    # step·evidence는 전부 structured보다 앞
    structured_idx = types.index("structured")
    assert all(i < structured_idx for i, t in enumerate(types) if t in {"step", "evidence"})

    step_labels = [d["label"] for t, d in events if t == "step"]
    assert step_labels[0].startswith("입력 검증")
    assert "의도 분류" in step_labels
    assert "미션 실행" in step_labels
    assert "승인 게이트" in step_labels

    structured_data = next(d for t, d in events if t == "structured")
    assert structured_data["answer"]["final_response"]
    assert structured_data["approval"] is not None
    assert structured_data["request_id"]

    evidence_types = [d["event_type"] for t, d in events if t == "evidence"]
    assert evidence_types[0] == "intent_classified"
    assert "final_response_generated" in evidence_types


def test_graph_run_blocked_input_emits_guardrail_step(client: TestClient) -> None:
    response = client.post("/graph/run", json={"message": "성실한 후보 추천해줘"})

    events = _parse_sse(response.text)
    steps = [d for t, d in events if t == "step"]
    assert any(s["kind"] == "guardrail" for s in steps)

    structured_data = next(d for t, d in events if t == "structured")
    assert structured_data["answer"]["risk_flags"] == ["ORCHESTRATION_BLOCKED"]
    assert structured_data["approval"]["status"] == "PENDING"


def test_graph_run_masks_pii_in_all_frames(client: TestClient) -> None:
    response = client.post(
        "/graph/run", json={"message": "여권 M12345678 근로자 체류만료 확인해줘"}
    )

    assert "M12345678" not in response.text
