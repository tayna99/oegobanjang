from __future__ import annotations

import json
from pathlib import Path

from app.agent_runtime.rag.chunking import (
    REQUIRED_METADATA_FIELDS,
    build_chunks,
    load_policy_documents,
    write_chunks_jsonl,
)
from app.agent_runtime.rag.citation import can_use_as_answer_evidence
from app.agent_runtime.rag.evaluate import evaluate_retrieval
from app.agent_runtime.rag.retriever import PolicyRetriever, load_chunks


def _sample_document() -> dict[str, object]:
    return {
        "source_id": "seed_eps_procedure_demo_001",
        "title": "E-9 고용허가 절차 데모 문서",
        "publisher": "MVP seed placeholder",
        "source_type": "synthetic_case",
        "url": "",
        "retrieved_at": "2026-05-03",
        "effective_date": None,
        "doc_type": "case",
        "mission_agent": ["workforce_agent"],
        "visa_type": ["E-9"],
        "country": ["ALL"],
        "industry": ["manufacturing"],
        "risk_level": "medium",
        "evidence_grade": "F",
        "content": "내국인 구인노력 후 고용허가 신청을 준비한다.\n\n근로계약 체결 전 제출 서류를 확인한다.",
    }


def test_build_chunks_requires_metadata_and_preserves_source() -> None:
    chunks = build_chunks([_sample_document()])

    assert len(chunks) == 2
    assert chunks[0]["chunk_id"] == "seed_eps_procedure_demo_001__0001"
    assert chunks[0]["source_id"] == "seed_eps_procedure_demo_001"
    assert chunks[0]["text"] == "내국인 구인노력 후 고용허가 신청을 준비한다."

    for field in REQUIRED_METADATA_FIELDS:
        assert field in chunks[0]["metadata"]


def test_missing_metadata_is_blocked_explicitly() -> None:
    document = _sample_document()
    document.pop("publisher")

    try:
        build_chunks([document])
    except ValueError as exc:
        assert "Missing metadata" in str(exc)
        assert "publisher" in str(exc)
    else:
        raise AssertionError("missing metadata must raise a ValueError")


def test_write_and_load_chunks_jsonl(tmp_path: Path) -> None:
    chunk_path = tmp_path / "policy_chunks.jsonl"
    write_chunks_jsonl(build_chunks([_sample_document()]), chunk_path)

    loaded = load_chunks(chunk_path)

    assert len(loaded) == 2
    assert loaded[0]["chunk_id"] == "seed_eps_procedure_demo_001__0001"


def test_retriever_filters_to_answer_eligible_evidence() -> None:
    chunks = build_chunks(
        [
            _sample_document(),
            {
                **_sample_document(),
                "source_id": "message_template_passport_request_ko",
                "title": "여권 사본 요청 메시지",
                "publisher": "외고반장 MVP template",
                "source_type": "message_template",
                "doc_type": "template",
                "evidence_grade": "E",
                "content": "여권 사본과 외국인등록증 사본을 제출해 주세요.",
            },
        ]
    )

    retriever = PolicyRetriever(chunks)
    results = retriever.search(
        "여권 사본 요청 메시지",
        top_k=3,
        answer_evidence_only=True,
    )

    assert results
    assert results[0]["source_id"] == "message_template_passport_request_ko"
    assert results[0]["metadata"]["evidence_grade"] == "E"
    assert can_use_as_answer_evidence(results[0]["metadata"])
    assert all(result["metadata"]["evidence_grade"] in {"A", "B", "E"} for result in results)


def test_retriever_scores_metadata_title_from_ingest_chunks() -> None:
    chunks = [
        {
            "chunk_id": "document_requirement_001_chunk_0000",
            "source_id": "document_requirement_001",
            "text": "required_doc: passport_copy\nnotes: 여권 사본",
            "metadata": {
                "source_id": "document_requirement_001",
                "title": "stay_extension E-9 required document: passport_copy",
                "publisher": "internal",
                "source_type": "internal_checklist",
                "doc_type": "form",
                "evidence_grade": "E",
            },
        },
        {
            "chunk_id": "message_template_passport_request_ko_chunk_0000",
            "source_id": "message_template_passport_request_ko",
            "text": "여권 사본과 외국인등록증 사본을 제출해 주세요.",
            "metadata": {
                "source_id": "message_template_passport_request_ko",
                "title": "여권 사본 요청 메시지",
                "publisher": "외고반장 MVP template",
                "source_type": "message_template",
                "doc_type": "template",
                "evidence_grade": "E",
            },
        },
    ]

    results = PolicyRetriever(chunks).search("여권 사본 요청 메시지", top_k=1)

    assert results[0]["source_id"] == "message_template_passport_request_ko"


def test_load_policy_documents_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "docs.jsonl"
    path.write_text(json.dumps(_sample_document(), ensure_ascii=False) + "\n", encoding="utf-8")

    docs = load_policy_documents(path)

    assert docs[0]["source_id"] == "seed_eps_procedure_demo_001"


def test_evaluate_retrieval_reports_hit_rate(tmp_path: Path) -> None:
    chunk_path = tmp_path / "chunks.jsonl"
    dataset_path = tmp_path / "rag_cases.jsonl"
    write_chunks_jsonl(build_chunks([_sample_document()]), chunk_path)
    dataset_path.write_text(
        json.dumps(
            {
                "id": "rag-test",
                "input": "고용허가 신청",
                "expected_source_ids": ["seed_eps_procedure_demo_001"],
                "answer_evidence_only": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = evaluate_retrieval(dataset_path=dataset_path, chunk_path=chunk_path, top_k=3)

    assert report.hit_rate == 1.0
    assert report.hits == 1
