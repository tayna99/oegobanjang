"""워크포스 벡터 레코드 계약 — legacy test_workforce_vector_index.py의 스토어 중립 부분 이식.

(Chroma 전용 인덱서/질의 테스트는 tests/test_pgvector_index.py의 pgvector 계약 테스트로 대체)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oe_rag.cli import load_collection_records
from oe_rag.embeddings import resolve_embedding_provider
from oe_rag.pipeline import build_workforce_collection_records


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(content + "\n" if content else "", encoding="utf-8")


def test_workforce_collection_records_are_loaded_by_collection(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "workforce_official_vector_records.jsonl",
        [
            {
                "id": "official_001",
                "text": "제목: 사업주 고용절차\n내용: 내국인 구인노력 이후 고용허가 신청",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"collection": "workforce_official", "source_id": "official_001"},
            }
        ],
    )
    _write_jsonl(
        tmp_path / "workforce_templates_vector_records.jsonl",
        [
            {
                "id": "template_001",
                "text": "제목: 신규 인력 요청서 템플릿\n내용: 송출회사 확인 질문",
                "embedding": [0.4, 0.5, 0.6],
                "metadata": {"collection": "workforce_templates", "source_id": "template_001"},
            }
        ],
    )

    records = load_collection_records(tmp_path)

    assert set(records) == {"workforce_official", "workforce_templates"}
    assert records["workforce_official"][0]["id"] == "official_001"
    assert records["workforce_templates"][0]["id"] == "template_001"


def test_collection_mismatch_is_rejected(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "workforce_official_vector_records.jsonl",
        [
            {
                "id": "official_001",
                "text": "본문",
                "embedding": [0.1],
                "metadata": {"collection": "workforce_templates", "source_id": "official_001"},
            }
        ],
    )

    with pytest.raises(ValueError, match="collection mismatch"):
        load_collection_records(tmp_path)


def test_workforce_collection_records_exclude_case_and_low_grade_materials() -> None:
    collections = build_workforce_collection_records(
        [
            {
                "chunk_id": "case_demo_chunk_0000",
                "text": "합성 케이스. 공식 근거가 아니다.",
                "metadata": {
                    "source_id": "case_demo",
                    "title": "합성 케이스",
                    "source_type": "raw_text",
                    "doc_type": "case",
                    "mission_agent": ["workforce_agent"],
                    "case_type": ["new_hiring"],
                    "output_usage": ["request_form"],
                    "evidence_grade": "D",
                },
            },
            {
                "chunk_id": "template_safe_chunk_0000",
                "text": "신규 인력 요청서 템플릿",
                "metadata": {
                    "source_id": "template_safe",
                    "title": "신규 인력 요청서 템플릿",
                    "source_type": "internal_template",
                    "doc_type": "template",
                    "mission_agent": ["workforce_agent"],
                    "case_type": ["new_hiring"],
                    "output_usage": ["request_form"],
                    "evidence_grade": "E",
                },
            },
        ]
    )

    assert collections["workforce_official"] == []
    assert [record["id"] for record in collections["workforce_templates"]] == ["template_safe_chunk_0000"]


def test_resolve_embedding_provider_defaults_to_deterministic_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("WORKFORCE_RAG_EMBEDDING_PROVIDER", raising=False)

    assert resolve_embedding_provider("auto") == "deterministic"
    assert resolve_embedding_provider() == "deterministic"


def test_resolve_embedding_provider_requires_api_key_for_openai(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        resolve_embedding_provider("openai")
