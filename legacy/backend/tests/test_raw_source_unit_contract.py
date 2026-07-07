from pathlib import Path

from app.agent_runtime.rag.raw_ingest import RawIngestor


def test_raw_ingest_adds_domain_unit_metadata_to_plain_text(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    laws_dir = raw_dir / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "law.txt").write_text(
        "제1조(목적) 조문 내용입니다.\n\n제2조(정의) 정의 내용입니다.",
        encoding="utf-8",
    )

    result = RawIngestor().load_directory(raw_dir, root_dir=tmp_path)

    assert len(result.records) == 2
    metadata = result.records[0]["metadata"]
    assert metadata["source_unit_type"] == "law_article"
    assert metadata["domain_unit_id"].endswith("::law_article::0001")
    assert metadata["splitter_version"]


def test_curated_jsonl_preserves_record_and_infers_unit_metadata(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    law_dir = raw_dir / "laws"
    law_dir.mkdir(parents=True)
    (law_dir / "law.jsonl").write_text(
        '{"source_id":"act_제1조","title":"제1조(목적)","content":"제1조(목적) 내용",'
        '"metadata":{"doc_type":"law","evidence_grade":"A"}}\n',
        encoding="utf-8",
    )

    result = RawIngestor().load_directory(raw_dir, root_dir=tmp_path)

    assert len(result.records) == 1
    assert result.records[0]["source_id"] == "act_제1조"
    assert result.records[0]["metadata"]["source_unit_type"] == "law_article"
    assert result.records[0]["metadata"]["domain_unit_id"] == "act_제1조"
