from __future__ import annotations

import json
import sys
from pathlib import Path

from app.agent_runtime.rag.embeddings import deterministic_embedding

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.ingest_rag_docs import build_workforce_collection_records
from scripts.index_workforce_chroma import (
    EmbeddingProvider,
    index_workforce_collections,
    load_workforce_collection_records,
    query_workforce_collection,
    select_embedding_provider,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_workforce_collection_records_are_loaded_by_collection(tmp_path: Path) -> None:
    official_path = tmp_path / "workforce_official_chroma_records.jsonl"
    template_path = tmp_path / "workforce_templates_chroma_records.jsonl"
    _write_jsonl(
        official_path,
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
        template_path,
        [
            {
                "id": "template_001",
                "text": "제목: 신규 인력 요청서 템플릿\n내용: 송출회사 확인 질문",
                "embedding": [0.4, 0.5, 0.6],
                "metadata": {"collection": "workforce_templates", "source_id": "template_001"},
            }
        ],
    )

    records = load_workforce_collection_records(tmp_path)

    assert set(records) == {"workforce_official", "workforce_templates"}
    assert records["workforce_official"][0]["id"] == "official_001"
    assert records["workforce_templates"][0]["id"] == "template_001"


def test_workforce_chroma_indexer_upserts_two_collections(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    _write_jsonl(
        chunks_dir / "workforce_official_chroma_records.jsonl",
        [
            {
                "id": "official_001",
                "text": "제목: 사업주 고용절차\n내용: 내국인 구인노력 이후 고용허가 신청",
                "embedding": deterministic_embedding("제목: E-9 신규 고용 절차\n내용: 내국인 구인노력 이후 고용허가 신청"),
                "metadata": {
                    "collection": "workforce_official",
                    "source_id": "official_001",
                    "mission_agent": ["workforce_agent"],
                    "case_type": ["new_hiring"],
                    "evidence_grade": "B",
                },
            }
        ],
    )
    _write_jsonl(
        chunks_dir / "workforce_templates_chroma_records.jsonl",
        [
            {
                "id": "template_001",
                "text": "제목: 신규 인력 요청서 템플릿\n내용: 송출회사 확인 질문",
                "embedding": [0.2] * 16,
                "metadata": {
                    "collection": "workforce_templates",
                    "source_id": "template_001",
                    "mission_agent": ["workforce_agent"],
                    "case_type": ["new_hiring"],
                    "evidence_grade": "E",
                },
            }
        ],
    )

    report = index_workforce_collections(chunks_dir=chunks_dir, persist_dir=tmp_path / "chroma", reset=True)

    assert report["collections"]["workforce_official"]["indexed_records"] == 1
    assert report["collections"]["workforce_templates"]["indexed_records"] == 1
    assert report["persist_dir"] == str(tmp_path / "chroma")


def test_workforce_chroma_query_applies_metadata_filters(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    new_hiring_text = "제목: E-9 신규 고용 절차\n내용: 내국인 구인노력 이후 고용허가 신청"
    other_case_text = "제목: 다른 케이스\n내용: 체류만료 확인"
    _write_jsonl(
        chunks_dir / "workforce_official_chroma_records.jsonl",
        [
            {
                "id": "official_new_hiring",
                "text": new_hiring_text,
                "embedding": deterministic_embedding(new_hiring_text),
                "metadata": {
                    "collection": "workforce_official",
                    "source_id": "official_new_hiring",
                    "mission_agent": ["workforce_agent"],
                    "visa_type": ["E-9"],
                    "case_type": ["new_hiring"],
                    "evidence_grade": "B",
                },
            },
            {
                "id": "official_other_case",
                "text": other_case_text,
                "embedding": deterministic_embedding(other_case_text),
                "metadata": {
                    "collection": "workforce_official",
                    "source_id": "official_other_case",
                    "mission_agent": ["workforce_agent"],
                    "visa_type": ["E-9"],
                    "case_type": ["visa_expiry"],
                    "evidence_grade": "B",
                },
            },
        ],
    )
    _write_jsonl(chunks_dir / "workforce_templates_chroma_records.jsonl", [])
    persist_dir = tmp_path / "chroma"
    index_workforce_collections(chunks_dir=chunks_dir, persist_dir=persist_dir, reset=True)

    results = query_workforce_collection(
        persist_dir=persist_dir,
        collection_name="workforce_official",
        query="E-9 신규 고용 절차",
        filters={"mission_agent": "workforce_agent", "visa_type": "E-9", "case_type": "new_hiring"},
        top_k=5,
    )

    assert [result["id"] for result in results] == ["official_new_hiring"]


class _TinyEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        super().__init__(name="tiny_test", model="tiny-test-model")

    def embed(self, texts: list[str]) -> list[list[float]]:
        output: list[list[float]] = []
        for text in texts:
            if "needle" in text:
                output.append([1.0, 0.0, 0.0])
            else:
                output.append([0.0, 1.0, 0.0])
        return output


def test_workforce_chroma_query_uses_same_embedding_provider_as_index(tmp_path: Path) -> None:
    provider = _TinyEmbeddingProvider()
    chunks_dir = tmp_path / "chunks"
    target_text = "제목: needle official\n내용: provider-specific query target"
    other_text = "제목: other official\n내용: unrelated"
    _write_jsonl(
        chunks_dir / "workforce_official_chroma_records.jsonl",
        [
            {
                "id": "official_needle",
                "text": target_text,
                "embedding": [9.9, 9.9, 9.9],
                "metadata": {
                    "collection": "workforce_official",
                    "source_id": "official_needle",
                    "mission_agent": ["workforce_agent"],
                    "visa_type": ["E-9"],
                    "case_type": ["new_hiring"],
                    "evidence_grade": "B",
                },
            },
            {
                "id": "official_other",
                "text": other_text,
                "embedding": [9.9, 9.9, 9.9],
                "metadata": {
                    "collection": "workforce_official",
                    "source_id": "official_other",
                    "mission_agent": ["workforce_agent"],
                    "visa_type": ["E-9"],
                    "case_type": ["new_hiring"],
                    "evidence_grade": "B",
                },
            },
        ],
    )
    _write_jsonl(chunks_dir / "workforce_templates_chroma_records.jsonl", [])
    persist_dir = tmp_path / "chroma"
    index_workforce_collections(
        chunks_dir=chunks_dir,
        persist_dir=persist_dir,
        reset=True,
        embedding_provider=provider,
    )

    results = query_workforce_collection(
        persist_dir=persist_dir,
        collection_name="workforce_official",
        query="needle",
        filters={"mission_agent": "workforce_agent", "visa_type": "E-9", "case_type": "new_hiring"},
        top_k=1,
        embedding_provider=provider,
    )

    assert [result["id"] for result in results] == ["official_needle"]


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


def test_select_embedding_provider_defaults_to_deterministic_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = select_embedding_provider(provider_name="auto", model="text-embedding-3-small")

    assert provider.name == "deterministic"
    assert provider.embed(["E-9 신규 고용 절차"])[0]


def test_select_embedding_provider_requires_api_key_for_openai(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        select_embedding_provider(provider_name="openai", model="text-embedding-3-small")
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("openai embedding provider must require OPENAI_API_KEY")
