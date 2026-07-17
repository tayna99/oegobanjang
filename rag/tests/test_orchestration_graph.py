"""직선 StateGraph — 노드 순서·차단 경로·evidence 흐름 (pgvector 필요, 키 불필요)."""

from __future__ import annotations

import pytest

from oe_rag.orchestration.graph import build_orchestration_graph, new_request_id
from oe_rag.store.pgvector_store import read_manifest

pytestmark = pytest.mark.pgvector


@pytest.fixture(autouse=True)
def _require_workforce_official_indexed() -> None:
    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")


def _run(message: str, snapshot: dict | None = None) -> dict:
    graph = build_orchestration_graph(chat_model=None)
    return graph.invoke(
        {
            "request_id": new_request_id(),
            "thread_id": "test",
            "user_message": message,
            "context_snapshot": snapshot or {},
            "mission_results": [],
            "evidence_events": [],
        }
    )


def test_happy_path_visa_intent_flows_to_final_response() -> None:
    state = _run("Nguyen 체류만료일 확인해줘")

    assert state["blocked"] is False
    assert state["route"]["intent"] == "visa_expiry"
    assert state["route"]["mission"] == "m2_visa"
    # m2_visa는 아직 미등록 — rag_answer 폴백 + 명시 플래그 (조용한 폴백 금지)
    assert state["mission_results"][0]["mission"] == "rag_answer"
    assert "MISSION_NOT_IMPLEMENTED" in state["mission_results"][0]["risk_flags"]
    assert state["structured_response"]["final_response"]
    event_types = [e["event_type"] for e in state["evidence_events"]]
    assert event_types[0] == "intent_classified"  # input_guard
    assert "plan_created" in event_types
    assert "rag_retrieved" in event_types
    assert event_types[-1] == "final_response_generated"


def test_forbidden_input_terms_short_circuit_before_any_retrieval() -> None:
    state = _run("성실한 후보 추천해줘")

    assert state["blocked"] is True
    assert state["structured_response"]["risk_flags"] == ["ORCHESTRATION_BLOCKED"]
    assert state["approval"]["status"] == "PENDING"
    event_types = [e["event_type"] for e in state["evidence_events"]]
    assert "rag_retrieved" not in event_types  # LLM/검색 실행 전 차단
    assert event_types[-1] == "final_response_generated"


def test_forbidden_intent_via_router_blocks() -> None:
    state = _run("하이코리아 제출까지 자동으로 신청해줘")

    assert state["route"]["intent"] == "forbidden"
    assert state["structured_response"]["risk_flags"] == ["ORCHESTRATION_BLOCKED"]
    assert "auto_submit_to_government_portal" in state["approval"]["blocked_actions"]


def test_pii_is_masked_before_downstream_nodes() -> None:
    state = _run("여권 M12345678 근로자 체류만료 확인해줘")

    assert state["pii_masked"] is True
    assert "M12345678" not in state["user_message"]
    serialized_events = str(state["evidence_events"])
    assert "M12345678" not in serialized_events


def test_send_request_creates_pending_approval() -> None:
    state = _run("베트남어 안내 메시지 만들어서 바로 보내줘")

    assert state["blocked"] is False
    assert state["approval"]["required"] is True
    assert state["approval"]["status"] == "PENDING"
    assert "send_message_without_approval" in state["approval"]["blocked_actions"]
    event_types = [e["event_type"] for e in state["evidence_events"]]
    assert "approval_requested" in event_types


def test_rule_findings_from_snapshot_flow_into_key_findings() -> None:
    snapshot = {
        "snapshot_version": "v1",
        "rule_findings": [
            {
                "risk_type": "visa_expiry",
                "severity": "HIGH",
                "worker_id": "wrk_1",
                "d_day": 20,
                "display_label": "체류기간 연장 준비",
            }
        ],
    }
    state = _run("오늘 위험 브리핑 정리해", snapshot)

    assert state["aggregated"]["key_findings"] == ["체류기간 연장 준비: HIGH (D-20)"]
