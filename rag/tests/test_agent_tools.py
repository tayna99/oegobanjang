"""워크포스 RAG 도구 가드레일 — 실행 중인 pgvector + 색인된 데이터 필요."""

from __future__ import annotations

import json

import pytest

from oe_rag.agent.tools import RuntimePreflightError, preflight_pgvector, retrieve_workforce_materials

pytestmark = pytest.mark.pgvector


def test_retrieve_workforce_materials_excludes_low_grade_evidence() -> None:
    result = retrieve_workforce_materials.invoke(
        {"query": "내국인 구인노력은 언제 확인해야 해?", "case_type": "new_hiring"}
    )

    assert result["retrieved_count"] > 0
    for record in result["records"]:
        assert record["evidence_grade"] not in {"D", "F"}
        assert record["doc_type"] != "case"
        assert record["source_unit_type"] != "case_record"


def test_retrieve_workforce_materials_flags_missing_evidence_for_unmatched_case() -> None:
    result = retrieve_workforce_materials.invoke(
        {
            "query": "완전히 존재하지 않는 케이스에 대한 질의입니다",
            "case_type": "nonexistent_case_type_xyz",
        }
    )

    assert result["retrieved_count"] == 0
    assert result["missing_evidence"] is True
    assert "MISSING_EVIDENCE" in result["risk_flags"]


def test_retrieve_workforce_materials_emits_rag_retrieved_event_without_raw_text() -> None:
    result = retrieve_workforce_materials.invoke(
        {"query": "고용허가서 발급 절차 문의", "case_type": "new_hiring"}
    )

    event = result["evidence_log"]
    assert event["event_type"] == "rag_retrieved"
    serialized = json.dumps(event, ensure_ascii=False)
    assert "고용허가서 발급 절차 문의" not in serialized
    assert "query" not in event
    assert "text" not in event
    assert "excerpt" not in event


def test_preflight_pgvector_passes_when_collections_indexed() -> None:
    preflight_pgvector()  # 예외 없이 통과해야 한다 (색인된 상태 전제)


def test_preflight_pgvector_rejects_unindexed_collection(monkeypatch) -> None:
    import oe_rag.agent.tools as tools_module

    monkeypatch.setattr(tools_module, "read_manifest", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimePreflightError, match="missing pgvector collection"):
        preflight_pgvector()
