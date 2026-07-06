from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from app.agent_runtime.rag.raw_ingest import RawIngestor, build_ingestion_report


ROOT_DIR = Path(__file__).resolve().parents[2]
INGEST_SCRIPT_PATH = ROOT_DIR / "scripts" / "ingest_rag_docs.py"
SPEC = importlib.util.spec_from_file_location("ingest_rag_docs", INGEST_SCRIPT_PATH)
assert SPEC is not None
ingest_rag_docs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ingest_rag_docs)


def test_raw_ingestor_report_counts_processed_and_quarantined_files(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text("체류만료 D-day와 서류 누락을 확인합니다.", encoding="utf-8")
    (tmp_path / "bad.html").write_text("<html><body><script>x</script></body></html>", encoding="utf-8")

    result = RawIngestor(min_chars=10).load_directory(tmp_path)
    report = build_ingestion_report(result)

    assert report["input_files"] == 2
    assert report["processed_files"] == 1
    assert report["quarantined_records"] == 1
    assert report["by_extension"] == {".html": 1, ".md": 1}
    assert report["quarantine"][0]["reason"] in {"empty_text", "html_tag_residue", "text_too_short"}


def test_ingest_script_loads_pdf_and_curated_jsonl_from_raw_dir(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "curated.jsonl").write_text(
        json.dumps(
            {
                "source_id": "curated_001",
                "title": "정제 청크",
                "content": "이미 정제된 JSONL chunk입니다.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    records = ingest_rag_docs.load_raw_text_documents(raw_dir=raw_dir, root_dir=tmp_path)

    assert len(records) == 1
    record, source_path = records[0]
    assert source_path == "raw/curated.jsonl"
    assert record["source_id"] == "curated_001"
    assert record["text"] == "이미 정제된 JSONL chunk입니다."


def test_ingest_chunks_preserve_raw_extraction_metadata() -> None:
    chunks = ingest_rag_docs.make_chunks_from_record(
        {
            "source_id": "pdf_001",
            "title": "PDF 안내",
            "publisher": "official",
            "source_type": "official_pdf",
            "url": "https://example.test/guide.pdf",
            "retrieved_at": "2026-05-09",
            "doc_type": "procedure",
            "evidence_grade": "B",
            "text": "체류기간 만료 전 갱신 서류를 확인합니다.",
            "raw_metadata": {
                "source_hash": "sha256-demo",
                "file_type": "pdf",
                "extraction_method": "pdf_pymupdf_text",
                "page_number": 1,
            },
        },
        source_path="raw/guide.pdf",
    )

    metadata = chunks[0]["metadata"]
    assert metadata["source_hash"] == "sha256-demo"
    assert metadata["file_type"] == "pdf"
    assert metadata["extraction_method"] == "pdf_pymupdf_text"
    assert metadata["page_number"] == 1


def test_ingest_chunks_keep_row_source_id_when_raw_metadata_has_parent_source_id() -> None:
    chunks = ingest_rag_docs.make_chunks_from_record(
        {
            "source_id": "eps_employer_process_procedure_step_0007",
            "title": "EPS 사업주 고용절차 — 외국인고용허가신청",
            "publisher": "EPS/한국산업인력공단",
            "source_type": "official_procedure",
            "url": "https://eps.hrdkorea.or.kr/e9/user/employment/employment.do?method=employProcessCompany",
            "retrieved_at": "2026-05-09",
            "doc_type": "procedure",
            "evidence_grade": "B",
            "text": "외국인고용허가신청 단계에서는 내국인 구인노력 이후 고용허가 신청을 확인한다.",
            "raw_metadata": {
                "source_id": "eps_employer_process",
                "source_hash": "sha256-demo",
                "source_unit_type": "procedure_step",
            },
        },
        source_path="data-pipeline/raw/workforce_official/workforce_official_imported.jsonl",
    )

    assert chunks[0]["source_id"] == "eps_employer_process_procedure_step_0007"
    assert chunks[0]["chunk_id"] == "eps_employer_process_procedure_step_0007_chunk_0000"
    assert chunks[0]["metadata"]["source_id"] == "eps_employer_process_procedure_step_0007"
    assert chunks[0]["metadata"]["parent_source_id"] == "eps_employer_process"


def test_demo_seed_is_excluded_by_default_and_flagged_explicitly() -> None:
    assert ingest_rag_docs.load_seed_documents() == []

    records = ingest_rag_docs.load_seed_documents(include_demo_seed=True)

    assert {record["source_id"] for record in records} >= {
        "seed_eps_procedure_demo_001",
        "seed_visa_extension_demo_001",
    }


def test_ingestion_report_separates_seed_raw_official_and_synthetic_counts() -> None:
    report = ingest_rag_docs.build_source_mix_report(
        source_records=[
            {"source_id": "seed_demo", "source_type": "synthetic_case", "evidence_grade": "F"},
            {"source_id": "document_requirement_demo", "source_type": "internal_checklist", "evidence_grade": "E"},
        ],
        raw_records=[
            (
                {"source_id": "law_001", "source_type": "official_law", "evidence_grade": "A", "text": "법령"},
                "raw/law.jsonl",
            ),
            (
                {"source_id": "procedure_001", "source_type": "official_procedure", "evidence_grade": "B", "text": "절차"},
                "raw/procedure.jsonl",
            ),
        ],
        raw_report={"input_files": 2},
    )

    assert report["seed_records"] == 1
    assert report["internal_records"] == 1
    assert report["raw_records"] == 2
    assert report["official_records"] == 2
    assert report["synthetic_records"] == 1


def test_eval_gate_blocks_low_hit_rate(tmp_path: Path) -> None:
    chunks = [
        {
            "chunk_id": "official_001_chunk_0000",
            "source_id": "official_001",
            "text": "체류기간 연장허가 공통 제출 서류",
            "metadata": {
                "source_id": "official_001",
                "title": "체류기간 연장허가",
                "publisher": "official",
                "source_type": "official_procedure",
                "evidence_grade": "B",
            },
        }
    ]
    dataset_path = tmp_path / "rag_cases.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "miss",
                "input": "사업장변경 제한",
                "expected_source_ids": ["missing_source"],
                "answer_evidence_only": True,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    passed, report = ingest_rag_docs.evaluate_chunk_gate(
        chunks=chunks,
        dataset_path=dataset_path,
        min_hit_rate=0.80,
    )

    assert not passed
    assert report["hits"] == 0
    assert report["total_cases"] == 1
