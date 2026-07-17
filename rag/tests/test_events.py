"""rag_retrieved 이벤트 계약 — AGENTS.md §9(Evidence Log) 가드레일."""

from __future__ import annotations

import json
from pathlib import Path

from oe_rag.events import FORBIDDEN_PAYLOAD_KEYS, build_rag_retrieved_payload, emit_rag_retrieved


def _sample_buckets() -> dict[str, list[dict]]:
    return {
        "official_procedure": [
            {
                "id": "chunk_1",
                "text": "내국인 구인노력 절차 원문 전체가 여기 있다고 가정한다.",
                "metadata": {"source_id": "E9_STEP1", "evidence_grade": "B", "title": "1단계"},
            }
        ],
        "internal_template": [],
        "allowed_industry": [],
    }


def test_payload_excludes_query_text_and_chunk_content() -> None:
    payload = build_rag_retrieved_payload(query="후보자 여권번호 123456 확인해줘", buckets=_sample_buckets())

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "여권번호" not in serialized
    assert "123456" not in serialized
    assert "내국인 구인노력 절차 원문" not in serialized
    assert not (set(payload) & FORBIDDEN_PAYLOAD_KEYS)


def test_payload_contains_query_hash_not_raw_query() -> None:
    payload = build_rag_retrieved_payload(query="여권 사본 요청", buckets=_sample_buckets())

    assert "query_sha256" in payload
    assert len(payload["query_sha256"]) == 64
    assert "query" not in payload


def test_payload_reports_source_ids_and_grades_and_counts() -> None:
    payload = build_rag_retrieved_payload(query="내국인 구인노력", buckets=_sample_buckets())

    assert payload["source_ids"] == ["E9_STEP1"]
    assert payload["evidence_grades"] == ["B"]
    assert payload["retrieved_count"] == 1
    assert payload["missing_evidence"] is False
    assert payload["bucket_counts"] == {
        "official_procedure": 1,
        "internal_template": 0,
        "allowed_industry": 0,
    }


def test_empty_buckets_set_missing_evidence_flag() -> None:
    payload = build_rag_retrieved_payload(
        query="아무 결과도 없는 질의",
        buckets={"official_procedure": [], "internal_template": [], "allowed_industry": []},
    )

    assert payload["missing_evidence"] is True
    assert payload["retrieved_count"] == 0


def test_emit_rag_retrieved_appends_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "events" / "rag_retrieved.jsonl"

    emit_rag_retrieved(query="질의 1", buckets=_sample_buckets(), log_path=log_path)
    emit_rag_retrieved(query="질의 2", buckets=_sample_buckets(), log_path=log_path)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert record["event_type"] == "rag_retrieved"
        assert not (set(record) & FORBIDDEN_PAYLOAD_KEYS)
