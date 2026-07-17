"""M1 인력확보·M3 다국어컨택 미션 — 승인 필수·점수 금지·PII 미노출 가드 (pgvector, 키 불필요)."""

from __future__ import annotations

import json

import pytest

from oe_rag.missions.m1_workforce import run_m1_workforce_mission
from oe_rag.missions.m3_contact import UNSAFE_RESULT_KEYS, run_m3_contact_mission
from oe_rag.orchestration.graph import MISSION_REGISTRY, build_orchestration_graph, new_request_id
from oe_rag.store.pgvector_store import read_manifest

pytestmark = pytest.mark.pgvector


@pytest.fixture(autouse=True)
def _require_indexed() -> None:
    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")


SNAPSHOT = {
    "snapshot_version": "v1",
    "company": {"company_id": "cmp_1", "name": "화성정밀"},
    "workers": [
        {
            "worker_id": "wrk_1",
            "display_name": "Nguyen Van A",
            "nationality": "베트남",
            "visa_type": "E-9",
            "stay_expires_at": "2026-08-06",
            "preferred_language": "vi",
        }
    ],
    "rule_findings": [{"risk_type": "quota_review", "severity": "MEDIUM", "display_label": "신규 고용 준비/쿼터 검토"}],
    "candidates": [
        {"candidate_id": "cand_1", "display_name": "후보 A"},
        {"candidate_id": "cand_2", "display_name": "후보 B"},
    ],
    "candidate_documents": [
        {"candidate_id": "cand_1", "document_type": "passport_copy", "status": "submitted"},
        {"candidate_id": "cand_1", "document_type": "health_certificate", "status": "missing"},
        {"candidate_id": "cand_2", "document_type": "passport_copy", "status": "missing"},
    ],
}


def test_m1_quota_review_creates_request_form_draft_pending_approval() -> None:
    result = run_m1_workforce_mission(
        request_id=new_request_id(),
        user_message="E-9 추가 채용 가능한지 확인하고 요청서 준비해줘",
        context_snapshot=SNAPSHOT,
        route={"intent": "quota_review", "mission": "m1_workforce"},
        chat_model=None,
    )

    assert result["mission"] == "m1_workforce"
    assert result["request_form_draft"] is not None
    assert result["request_form_draft"]["approval_required"] is True
    assert result["approval_required"] is True
    event_types = [e["event_type"] for e in result["evidence_events"]]
    assert "risk_flagged" in event_types  # 쿼터 rule 소비
    assert "handoff_package_draft_created" in event_types


def test_m1_candidate_readiness_has_no_score_or_ranking_fields() -> None:
    """발표 원칙 구조 강제 — 충족/누락만, 점수·순위·추천 필드가 존재하지 않아야 한다."""
    result = run_m1_workforce_mission(
        request_id=new_request_id(),
        user_message="후보자들 입국 전 서류 준비 상태 정리해줘",
        context_snapshot=SNAPSHOT,
        route={"intent": "candidate_readiness", "mission": "m1_workforce"},
        chat_model=None,
    )

    readiness = result["candidate_readiness"]
    assert readiness is not None
    assert len(readiness["rows"]) == 2
    for row in readiness["rows"]:
        # 핵심 가드: 이 dict의 키 집합 자체에 점수·순위·추천 필드가 구조적으로 없다
        # ("순위 없음"이라고 설명하는 텍스트는 허용 — 실제 순위/점수 필드가 없는지만 본다).
        assert set(row) == {"candidate_id", "display_name", "satisfied", "missing"}
        for value in row.values():
            assert not isinstance(value, (int, float))  # 점수화된 숫자 필드 부재

    serialized = json.dumps(result, ensure_ascii=False, default=str)
    for banned in ["score", "ranking", "recommendation", "성실", "이탈"]:
        assert banned not in serialized, banned


def test_m1_candidate_readiness_without_candidates_reports_gap() -> None:
    result = run_m1_workforce_mission(
        request_id=new_request_id(),
        user_message="후보자들 서류 준비 상태",
        context_snapshot={"snapshot_version": "v1"},
        route={"intent": "candidate_readiness", "mission": "m1_workforce"},
        chat_model=None,
    )

    assert "후보자 데이터가 스냅샷에 없습니다" in result["candidate_readiness"]["summary"]


def test_m3_message_draft_is_always_pending_approval() -> None:
    result = run_m3_contact_mission(
        request_id=new_request_id(),
        user_message="안전교육 안내 메시지 준비해줘",
        context_snapshot=SNAPSHOT,
        route={"intent": "contact_onboarding", "mission": "m3_contact"},
        chat_model=None,
    )

    assert result["approval_required"] is True
    artifact = result["artifact"]
    assert artifact["kind"] == "contact_message_draft"
    assert artifact["approval_required"] is True
    assert artifact["language"] == "vi"  # 근로자 preferred_language 반영
    assert "발송되지 않았습니다" in result["structured_response"]["final_response"]
    assert not (UNSAFE_RESULT_KEYS & set(artifact))


def test_m3_reply_interpretation_creates_candidates_only_no_auto_apply() -> None:
    result = run_m3_contact_mission(
        request_id=new_request_id(),
        user_message="근로자 답변 요약해줘: 여권 010-1234-5678로 사진 보냈어요",
        context_snapshot=SNAPSHOT,
        route={"intent": "worker_reply_interpretation", "mission": "m3_contact"},
        chat_model=None,
    )

    artifact = result["artifact"]
    assert artifact["kind"] == "worker_reply_interpretation"
    assert artifact["manager_review_required"] is True
    for candidate in artifact["status_update_candidates"]:
        assert candidate["auto_apply"] is False

    serialized = json.dumps(result, ensure_ascii=False, default=str)
    assert "010-1234-5678" not in serialized  # PII 미노출


def test_graph_registry_covers_all_three_missions() -> None:
    assert {"m1_workforce", "m2_visa", "m3_contact", "rag_answer"} <= set(MISSION_REGISTRY)


def test_graph_routes_contact_intent_to_m3_end_to_end() -> None:
    graph = build_orchestration_graph(chat_model=None)
    state = graph.invoke(
        {
            "request_id": new_request_id(),
            "thread_id": "t-m3",
            "user_message": "베트남어 서류 요청 메시지 초안 만들어줘",
            "context_snapshot": SNAPSHOT,
            "mission_results": [],
            "evidence_events": [],
        }
    )

    assert state["route"]["mission"] == "m3_contact"
    assert state["mission_results"][0]["mission"] == "m3_contact"
    assert state["approval"]["required"] is True
    assert state["approval"]["status"] == "PENDING"
