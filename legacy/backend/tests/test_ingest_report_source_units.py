from pathlib import Path

from app.agent_runtime.rag.raw_ingest import RawIngestor, build_ingestion_report


def test_ingestion_report_includes_source_unit_counts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    eps_dir = raw_dir / "eps"
    eps_dir.mkdir(parents=True)
    (eps_dir / "employer_process.md").write_text(
        "고용허가 신청\n고용허가 신청 절차를 확인한다.",
        encoding="utf-8",
    )

    result = RawIngestor().load_directory(raw_dir, root_dir=tmp_path)
    report = build_ingestion_report(result)

    assert report["source_unit_type_counts"] == {"procedure_step": 1}
    assert report["low_confidence_unit_count"] == 0
    assert "domain_splitter_warnings" in report
