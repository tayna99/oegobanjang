from __future__ import annotations

import io
import json


class _FakeHtmlFetcher:
    def fetch(self, source_url: str):
        from app.services.citation_refresh_worker import OfficialSourcePayload

        return OfficialSourcePayload(
            source_url=source_url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=(
                b"<html><head><title>HiKorea Notice</title></head>"
                b"<body><h1>E-9 Visa Extension</h1>"
                b"<script>ignore_me()</script>"
                b"<p>Visa extension applications require official document review.</p>"
                b"</body></html>"
            ),
        )


class _FakePdfFetcher:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def fetch(self, source_url: str):
        from app.services.citation_refresh_worker import OfficialSourcePayload

        return OfficialSourcePayload(
            source_url=source_url,
            status_code=200,
            content_type="application/pdf",
            body=self.body,
        )


def test_official_fetch_worker_extracts_html_and_reindexes_rag_files(tmp_path):
    from app.services.citation_refresh_worker import OfficialCitationRefreshWorker

    chunks_path = tmp_path / "chunks.jsonl"
    chroma_records_path = tmp_path / "chroma_records.jsonl"
    worker = OfficialCitationRefreshWorker(
        fetcher=_FakeHtmlFetcher(),
        chunks_path=chunks_path,
        chroma_records_path=chroma_records_path,
        chroma_persist_dir=tmp_path / "chroma",
        chroma_collection_name="test_daily_briefing_official",
    )

    result = worker.refresh(
        citation_id="cit_hikorea_test",
        source_url="https://www.hikorea.go.kr/test-notice",
        title="HiKorea E-9 Notice",
        source_type="official",
    )

    assert result.external_fetch_performed is True
    assert result.content_type.startswith("text/html")
    assert "E-9 Visa Extension" in result.extracted_text
    assert "ignore_me" not in result.extracted_text
    assert result.chunk_count >= 1
    assert result.chroma_upsert_count == result.chunk_count
    assert result.chroma_collection_name == "test_daily_briefing_official"
    assert result.document_id == "doc_cit_hikorea_test"
    assert result.chunk_id.startswith("cit_hikorea_test__")
    assert chunks_path.exists()
    assert chroma_records_path.exists()

    chunk_rows = [
        json.loads(line)
        for line in chunks_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chroma_rows = [
        json.loads(line)
        for line in chroma_records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert chunk_rows[0]["source_id"] == "cit_hikorea_test"
    assert chunk_rows[0]["metadata"]["url"] == "https://www.hikorea.go.kr/test-notice"
    assert chroma_rows[0]["id"] == chunk_rows[0]["chunk_id"]
    assert chroma_rows[0]["embedding"]

    import chromadb

    collection = chromadb.PersistentClient(path=str(tmp_path / "chroma")).get_collection(
        "test_daily_briefing_official"
    )
    assert collection.count() == result.chunk_count


def test_official_fetch_worker_extracts_pdf_text(tmp_path):
    import fitz

    from app.services.citation_refresh_worker import OfficialCitationRefreshWorker

    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Official PDF visa renewal guidance")
    pdf_bytes = pdf.tobytes()
    pdf.close()

    worker = OfficialCitationRefreshWorker(
        fetcher=_FakePdfFetcher(pdf_bytes),
        chunks_path=tmp_path / "chunks.jsonl",
        chroma_records_path=tmp_path / "chroma_records.jsonl",
        chroma_persist_dir=tmp_path / "chroma",
        chroma_collection_name="test_daily_briefing_pdf",
    )

    result = worker.refresh(
        citation_id="cit_pdf_test",
        source_url="https://www.hikorea.go.kr/test.pdf",
        title="PDF Notice",
        source_type="official",
    )

    assert "Official PDF visa renewal guidance" in result.extracted_text
    assert result.chunk_count >= 1
    assert result.chroma_upsert_count == result.chunk_count
    assert result.source_hash.startswith("sha256:")
