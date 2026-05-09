from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.agent_runtime.rag.chunking import build_chunks
from app.agent_runtime.rag.vector_store import build_chroma_ready_records
from app.config import get_settings


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PUBLISHER = "official_source"
DEFAULT_MISSION_AGENTS = ["visa_document_agent", "workforce_agent"]


class OfficialSourcePayload(BaseModel):
    source_url: str
    status_code: int
    content_type: str = ""
    body: bytes


class OfficialCitationRefreshResult(BaseModel):
    citation_id: str
    source_url: str
    title: str
    source_type: str
    content_type: str
    source_hash: str
    extracted_text: str
    document_id: str
    chunk_id: str
    chunk_version: str
    retrieved_at: str
    ingest_at: str
    chunk_count: int
    chunks_path: str
    chroma_records_path: str
    chroma_persist_dir: str
    chroma_collection_name: str
    chroma_upsert_count: int
    external_fetch_performed: bool = True
    warning_flags: list[str] = Field(default_factory=list)


class OfficialSourceFetcher(Protocol):
    def fetch(self, source_url: str) -> OfficialSourcePayload:
        ...


@dataclass
class UrlOfficialSourceFetcher:
    timeout_seconds: int = 20
    max_bytes: int = 5_000_000

    def fetch(self, source_url: str) -> OfficialSourcePayload:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https", "file"}:
            raise ValueError("UNSUPPORTED_SOURCE_URL_SCHEME")

        if parsed.scheme == "file":
            path = Path(urllib.request.url2pathname(parsed.path))
            body = path.read_bytes()
            if len(body) > self.max_bytes:
                raise ValueError("SOURCE_TOO_LARGE")
            return OfficialSourcePayload(
                source_url=source_url,
                status_code=200,
                content_type=_guess_content_type(source_url, body),
                body=body,
            )

        request = urllib.request.Request(
            source_url,
            headers={
                "User-Agent": "Oegobanjang-DailyBriefingCitationRefresh/1.0",
                "Accept": "text/html,application/pdf,*/*;q=0.8",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read(self.max_bytes + 1)
            if len(body) > self.max_bytes:
                raise ValueError("SOURCE_TOO_LARGE")
            return OfficialSourcePayload(
                source_url=source_url,
                status_code=int(getattr(response, "status", 200)),
                content_type=response.headers.get("content-type", ""),
                body=body,
            )


class OfficialCitationRefreshWorker:
    def __init__(
        self,
        *,
        fetcher: OfficialSourceFetcher | None = None,
        chunks_path: str | Path | None = None,
        chroma_records_path: str | Path | None = None,
        chroma_persist_dir: str | Path | None = None,
        chroma_collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self.fetcher = fetcher or UrlOfficialSourceFetcher(
            timeout_seconds=settings.daily_briefing_official_fetch_timeout_seconds,
            max_bytes=settings.daily_briefing_official_fetch_max_bytes,
        )
        self.chunks_path = _resolve_repo_path(
            chunks_path or settings.daily_briefing_rag_refresh_chunks_path
        )
        self.chroma_records_path = _resolve_repo_path(
            chroma_records_path or settings.daily_briefing_rag_refresh_chroma_records_path
        )
        self.chroma_persist_dir = _resolve_repo_path(
            chroma_persist_dir or settings.daily_briefing_rag_refresh_chroma_persist_dir
        )
        self.chroma_collection_name = (
            chroma_collection_name or settings.daily_briefing_rag_refresh_chroma_collection
        )

    def refresh(
        self,
        *,
        citation_id: str,
        source_url: str,
        title: str,
        source_type: str = "official",
        publisher: str = DEFAULT_PUBLISHER,
        doc_type: str = "policy",
        evidence_grade: str = "B",
    ) -> OfficialCitationRefreshResult:
        payload = self.fetcher.fetch(source_url)
        if payload.status_code >= 400:
            raise ValueError("SOURCE_FETCH_FAILED")

        content_type = payload.content_type or _guess_content_type(source_url, payload.body)
        extracted_text = extract_official_source_text(
            payload.body,
            content_type=content_type,
            source_url=source_url,
        )
        if not extracted_text.strip():
            raise ValueError("EMPTY_SOURCE_TEXT")

        source_hash = f"sha256:{hashlib.sha256(payload.body).hexdigest()}"
        retrieved_at = datetime.now(timezone.utc).isoformat()
        chunk_version = source_hash.removeprefix("sha256:")[:12]
        document_id = f"doc_{citation_id}"
        document = {
            "source_id": citation_id,
            "title": title,
            "publisher": publisher,
            "source_type": source_type,
            "url": source_url,
            "retrieved_at": retrieved_at,
            "effective_date": retrieved_at[:10],
            "doc_type": doc_type,
            "mission_agent": DEFAULT_MISSION_AGENTS,
            "visa_type": ["E-9"],
            "country": ["ALL"],
            "industry": ["ALL"],
            "risk_level": "medium",
            "evidence_grade": evidence_grade,
            "content": extracted_text,
        }
        chunks = build_chunks([document])
        for chunk in chunks:
            metadata = dict(chunk.get("metadata", {}))
            metadata.update(
                {
                    "document_id": document_id,
                    "chunk_version": chunk_version,
                    "source_hash": source_hash,
                    "content_type": content_type,
                    "reindex_worker": "official_source_fetch",
                }
            )
            chunk["metadata"] = metadata

        _upsert_jsonl_records(self.chunks_path, chunks, source_id=citation_id)
        chroma_records = build_chroma_ready_records(chunks)
        _upsert_jsonl_records(
            self.chroma_records_path,
            chroma_records,
            source_id=citation_id,
        )
        chroma_upsert_count = _upsert_chroma_records(
            chroma_records,
            persist_dir=self.chroma_persist_dir,
            collection_name=self.chroma_collection_name,
            source_id=citation_id,
        )

        first_chunk_id = str(chunks[0]["chunk_id"])
        return OfficialCitationRefreshResult(
            citation_id=citation_id,
            source_url=source_url,
            title=title,
            source_type=source_type,
            content_type=content_type,
            source_hash=source_hash,
            extracted_text=extracted_text,
            document_id=document_id,
            chunk_id=first_chunk_id,
            chunk_version=chunk_version,
            retrieved_at=retrieved_at,
            ingest_at=retrieved_at,
            chunk_count=len(chunks),
            chunks_path=str(self.chunks_path),
            chroma_records_path=str(self.chroma_records_path),
            chroma_persist_dir=str(self.chroma_persist_dir),
            chroma_collection_name=self.chroma_collection_name,
            chroma_upsert_count=chroma_upsert_count,
            external_fetch_performed=True,
        )


def extract_official_source_text(body: bytes, *, content_type: str, source_url: str) -> str:
    normalized_type = content_type.casefold()
    if "pdf" in normalized_type or source_url.casefold().endswith(".pdf") or body.startswith(b"%PDF"):
        return _extract_pdf_text(body)
    return _extract_html_or_text(body, content_type=content_type)


def _extract_pdf_text(body: bytes) -> str:
    import fitz

    with fitz.open(stream=body, filetype="pdf") as document:
        pages = [page.get_text("text").strip() for page in document]
    return _normalize_text("\n\n".join(page for page in pages if page))


def _extract_html_or_text(body: bytes, *, content_type: str) -> str:
    charset = _charset_from_content_type(content_type)
    decoded = body.decode(charset, errors="replace")
    if "<" not in decoded or ">" not in decoded:
        return _normalize_text(decoded)
    parser = _VisibleTextHTMLParser()
    parser.feed(decoded)
    return _normalize_text(parser.text())


class _VisibleTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(html.unescape(data))

    def text(self) -> str:
        return "\n".join(self._parts)


def _upsert_jsonl_records(path: Path, new_records: list[dict[str, Any]], *, source_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_jsonl_records(path)
    kept = [record for record in existing if _record_source_id(record) != source_id]
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in [*kept, *new_records]:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def _upsert_chroma_records(
    records: list[dict[str, Any]],
    *,
    persist_dir: Path,
    collection_name: str,
    source_id: str,
) -> int:
    import chromadb

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(collection_name)
    ids = [str(record["id"]) for record in records]
    try:
        collection.delete(where={"source_id": source_id})
    except Exception:
        if ids:
            try:
                collection.delete(ids=ids)
            except Exception:
                pass
    if not records:
        return 0
    collection.add(
        ids=ids,
        documents=[str(record["text"]) for record in records],
        metadatas=[
            _chroma_metadata(record.get("metadata", {}), source_id=source_id)
            for record in records
        ],
        embeddings=[record["embedding"] for record in records],
    )
    return len(records)


def _chroma_metadata(metadata: dict[str, Any], *, source_id: str) -> dict[str, str | int | float | bool]:
    normalized: dict[str, str | int | float | bool] = {"source_id": source_id}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        else:
            normalized[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return normalized


def _load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                records.append(json.loads(raw))
    return records


def _record_source_id(record: dict[str, Any]) -> str | None:
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get("source_id")
    return record.get("source_id")


def _normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def _charset_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([A-Za-z0-9_\-]+)", content_type)
    return match.group(1) if match else "utf-8"


def _guess_content_type(source_url: str, body: bytes) -> str:
    if source_url.casefold().endswith(".pdf") or body.startswith(b"%PDF"):
        return "application/pdf"
    if body.lstrip().startswith(b"<"):
        return "text/html; charset=utf-8"
    return "text/plain; charset=utf-8"


def _resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value
