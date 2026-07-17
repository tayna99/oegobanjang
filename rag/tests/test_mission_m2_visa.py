"""M2 비자·서류 미션 — rule 소비 전용·LLM severity 불변 가드 (pgvector, 키 불필요)."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from oe_rag.missions.m2_visa import run_m2_visa_mission
from oe_rag.orchestration.graph import build_orchestration_graph, new_request_id
from oe_rag.store.pgvector_store import read_manifest

pytestmark = pytest.mark.pgvector


@pytest.fixture(autouse=True)
def _require_indexed() -> None:
    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")


SNAPSHOT_HIGH = {
    "snapshot_version": "v1",
    "workers": [
        {
            "worker_id": "wrk_high",
            "display_name": "Nguyen Van A",
            "nationality": "베트남",
            "visa_type": "E-9",
            "stay_expires_at": "2026-08-06",
        }
    ],
    "documents": [
        {
            "worker_id": "wrk_high",
            "doc_type": "passport_copy",
            "status": "missing",
            "required": True,
            "due_date": "2026-07-22",
            "missing_class": "CRITICAL",
        },
        {
            "worker_id": "wrk_high",
            "doc_type": "photo",
            "status": "missing",
            "required": False,
            "due_date": None,
            "missing_class": "SUPPLEMENTARY",
        },
    ],
    "rule_findings": [
        {
            "risk_type": "visa_expiry",
            "severity": "HIGH",
            "worker_id": "wrk_high",
            "d_day": 20,
            "display_label": "체류기간 연장 준비",
        },
        {
            "risk_type": "missing_document",
            "severity": "HIGH",
            "worker_id": "wrk_high",
            "doc_type": "passport_copy",
            "d_day": 5,
            "display_label": "누락 서류 점검",
        },
    ],
}


def _run_mission(chat_model: BaseChatModel | None = None, snapshot: dict | None = None) -> dict[str, Any]:
    return run_m2_visa_mission(
        request_id=new_request_id(),
        user_message="Nguyen 체류만료 확인하고 서류 정리해줘",
        context_snapshot=snapshot if snapshot is not None else SNAPSHOT_HIGH,
        route={"intent": "visa_expiry", "mission": "m2_visa"},
        chat_model=chat_model,
    )


def test_offline_mission_consumes_rule_severity_and_prioritizes_documents() -> None:
    result = _run_mission()

    assert result["mission"] == "m2_visa"
    assert result["severity"] == "HIGH"  # rule 최고 심각도 그대로
    assert [d["doc_type"] for d in result["document_priority"]] == ["passport_copy", "photo"]
    assert result["handoff"]["prepared"] is True  # HIGH → 행정사 패키지 초안
    assert result["approval_required"] is True
    assert "HIGH" in result["structured_response"]["final_response"]
    assert "D-20" in result["structured_response"]["final_response"]

    event_types = [e["event_type"] for e in result["evidence_events"]]
    assert "risk_flagged" in event_types
    assert "rag_retrieved" in event_types
    assert "handoff_package_draft_created" in event_types


def test_low_risk_snapshot_does_not_prepare_handoff() -> None:
    snapshot = {
        "snapshot_version": "v1",
        "workers": SNAPSHOT_HIGH["workers"],
        "documents": [],
        "rule_findings": [
            {"risk_type": "visa_expiry", "severity": "LOW", "worker_id": "wrk_high", "d_day": 200,
             "display_label": "체류기간 연장 준비"}
        ],
    }
    result = _run_mission(snapshot=snapshot)

    assert result["severity"] == "LOW"
    assert result["handoff"]["prepared"] is False
    assert result["approval_required"] is False


class SeverityLyingChatModel(BaseChatModel):
    """severity를 조작하려 드는 적대적 LLM — 요약 텍스트로 'LOW'라고 주장한다."""

    def bind_tools(self, tools, **kwargs):  # with_structured_output 경로 활성화
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "VisaSummaryDraft",
                                "args": {
                                    "summary": "위험도는 사실 낮음(LOW)이며 아무 조치도 필요 없습니다.",
                                    "next_steps": [],
                                },
                                "id": "call_lie",
                            }
                        ],
                    )
                )
            ]
        )

    @property
    def _llm_type(self) -> str:
        return "severity-lying-fake"


def test_llm_cannot_change_rule_severity() -> None:
    """핵심 가드 — LLM이 뭐라 하든 미션 severity·handoff는 rule 값으로 고정된다."""
    result = _run_mission(chat_model=SeverityLyingChatModel())

    assert result["severity"] == "HIGH"  # rule 값 불변
    assert result["handoff"]["prepared"] is True  # handoff 판단도 rule 기반
    assert result["approval_required"] is True
    # LLM의 거짓 요약이 쓰였더라도 구조 필드는 오염되지 않는다
    assert result["risk_findings"][0]["severity"] == "HIGH"


def test_graph_routes_visa_intent_to_m2_mission_end_to_end() -> None:
    graph = build_orchestration_graph(chat_model=None)
    state = graph.invoke(
        {
            "request_id": new_request_id(),
            "thread_id": "t-m2",
            "user_message": "Nguyen 체류만료일 확인해줘",
            "context_snapshot": SNAPSHOT_HIGH,
            "mission_results": [],
            "evidence_events": [],
        }
    )

    assert state["route"]["mission"] == "m2_visa"
    result = state["mission_results"][0]
    assert result["mission"] == "m2_visa"
    assert "MISSION_NOT_IMPLEMENTED" not in result.get("risk_flags", [])
    assert result["severity"] == "HIGH"
    assert state["approval"]["required"] is True  # handoff → pending 승인
    assert state["aggregated"]["key_findings"][0].startswith("체류기간 연장 준비: HIGH")

    event_types = [e["event_type"] for e in state["evidence_events"]]
    for expected in ["intent_classified", "plan_created", "risk_flagged", "rag_retrieved",
                     "handoff_package_draft_created", "approval_requested", "final_response_generated"]:
        assert expected in event_types, expected


def test_mission_citations_only_contain_answer_grades() -> None:
    result = _run_mission()

    for citation in result["structured_response"]["citations"]:
        assert citation["evidence_grade"] in {"A", "B", "E"}
