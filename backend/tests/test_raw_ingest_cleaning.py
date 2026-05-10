from __future__ import annotations

import json
from pathlib import Path

import fitz

from app.agent_runtime.rag.raw_ingest import (
    IngestQualityGate,
    RawIngestor,
    serialize_html_table_rows,
)


def test_html_cleaner_removes_layout_tags_and_preserves_main_body(tmp_path: Path) -> None:
    html_path = tmp_path / "policy.html"
    html_path.write_text(
        """
        <html>
          <head><style>.hide { display: none; }</style></head>
          <body>
            <nav>메뉴 링크</nav>
            <main>
              <h1>E-9 체류만료 안내</h1>
              <script>alert("tracking")</script>
              <div>체류기간 만료 전 갱신 서류를 확인해야 합니다.</div>
            </main>
            <footer>광고 footer</footer>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    result = RawIngestor().load_path(html_path, root_dir=tmp_path)

    assert result.records[0]["text"] == "E-9 체류만료 안내\n\n체류기간 만료 전 갱신 서류를 확인해야 합니다."
    assert "<script" not in result.records[0]["text"]
    assert "<div" not in result.records[0]["text"]
    assert "메뉴 링크" not in result.records[0]["text"]
    assert "광고 footer" not in result.records[0]["text"]
    assert result.records[0]["metadata"]["extraction_method"] == "html_generic"


def test_html_table_rows_keep_header_value_meaning() -> None:
    table_html = """
    <table>
      <tr><th>구분</th><th>기간</th><th>비고</th></tr>
      <tr><td>내국인 구인노력</td><td>7일</td><td>원칙</td></tr>
      <tr><td>고용변동 신고</td><td>15일</td><td>사유 인지일 기준</td></tr>
    </table>
    """

    rows = serialize_html_table_rows(table_html)

    assert rows == [
        "구분: 내국인 구인노력 | 기간: 7일 | 비고: 원칙",
        "구분: 고용변동 신고 | 기간: 15일 | 비고: 사유 인지일 기준",
    ]


def test_pdf_loader_emits_page_records_with_source_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "guide.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "E-9 갱신 안내\n여권 사본을 준비합니다.")
    pdf.save(pdf_path)
    pdf.close()

    result = RawIngestor().load_path(pdf_path, root_dir=tmp_path)

    assert len(result.records) == 1
    record = result.records[0]
    assert "E-9" in record["text"]
    assert record["metadata"]["file_type"] == "pdf"
    assert record["metadata"]["page_number"] == 1
    assert record["metadata"]["source_path"] == "guide.pdf"
    assert record["metadata"]["source_hash"]


def test_jsonl_records_are_loaded_as_curated_chunks_without_html_cleaning(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "laws.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "source_id": "law_001",
                "title": "고용변동 신고",
                "content": "이미 정제된 JSONL chunk입니다.",
                "metadata": {"source_type": "official_law"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = RawIngestor().load_path(jsonl_path, root_dir=tmp_path)

    assert result.records[0]["source_id"] == "law_001"
    assert result.records[0]["text"] == "이미 정제된 JSONL chunk입니다."
    assert result.records[0]["metadata"]["extraction_method"] == "curated_jsonl"


def test_quality_gate_quarantines_tag_residue_and_too_short_text(tmp_path: Path) -> None:
    records = [
        {
            "source_id": "bad_html",
            "text": "본문 <script>alert(1)</script>",
            "metadata": {"source_path": "bad.html", "source_hash": "abc"},
        },
        {
            "source_id": "too_short",
            "text": "짧음",
            "metadata": {"source_path": "short.txt", "source_hash": "def"},
        },
        {
            "source_id": "good",
            "text": "체류기간 만료 전 갱신 서류를 확인해야 합니다.",
            "metadata": {"source_path": "good.txt", "source_hash": "ghi"},
        },
    ]

    accepted, quarantined = IngestQualityGate(min_chars=10).apply(records)

    assert [record["source_id"] for record in accepted] == ["good"]
    assert {item["source_id"]: item["reason"] for item in quarantined} == {
        "bad_html": "html_tag_residue",
        "too_short": "text_too_short",
    }
