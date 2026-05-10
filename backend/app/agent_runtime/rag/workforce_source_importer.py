from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .domain_splitters import SPLITTER_VERSION, split_domain_units
from .raw_ingest import clean_html_document, normalize_whitespace
from .workforce_metadata import normalize_workforce_metadata


DEFAULT_ALLOWED_DOMAINS = {
    "eps.go.kr",
    "www.eps.go.kr",
    "eps.hrdkorea.or.kr",
    "hrdkorea.or.kr",
    "www.hrdkorea.or.kr",
    "work24.go.kr",
    "www.work24.go.kr",
    "moel.go.kr",
    "www.moel.go.kr",
}
DEFAULT_OUTPUT_FILE_NAME = "workforce_official_imported.jsonl"
IMPORTER_VERSION = "workforce_source_importer_v1"
MIN_MEANINGFUL_UNIT_CHARS = 40
WORKFORCE_CORE_TERMS = (
    "내국인",
    "구인노력",
    "외국인고용허가",
    "고용허가 신청",
    "고용허가서",
    "근로계약",
    "사증발급",
    "취업교육",
    "입국",
    "사업장 배치",
    "허용업종",
)


class SourceDomainNotAllowed(ValueError):
    pass


class SourceFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResponse:
    url: str
    content_type: str
    body: bytes


FetchFn = Callable[[str, int, int], FetchResponse]


def import_workforce_sources(
    *,
    manifest_path: Path,
    output_dir: Path,
    fetch_enabled: bool,
    fetcher: FetchFn | None = None,
    allowed_domains: set[str] | None = None,
    timeout_seconds: int = 20,
    max_bytes: int = 5_000_000,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    manifest = _read_manifest(manifest_path)
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("manifest.sources must be a list")

    if not fetch_enabled:
        return {
            "status": "disabled",
            "manifest_path": str(manifest_path),
            "skipped_sources": len(sources),
            "fetched_sources": 0,
            "written_records": 0,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / DEFAULT_OUTPUT_FILE_NAME
    allowed = allowed_domains or DEFAULT_ALLOWED_DOMAINS
    fetch = fetcher or _urllib_fetch
    timestamp = fetched_at or datetime.now(timezone.utc).isoformat()

    all_records: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []
    for spec in sources:
        if not isinstance(spec, dict):
            raise ValueError("each source spec must be an object")
        url = str(spec.get("url") or "")
        _assert_allowed_domain(url, allowed)
        response = fetch(url, timeout_seconds, max_bytes)
        text = _extract_text(response)
        records = _records_from_source_spec(spec, response, text, fetched_at=timestamp)
        if not records and spec.get("fallback_text"):
            records = _records_from_source_spec(
                {**spec, "_source_fetch_method": "official_source_url_with_manifest_fallback"},
                response,
                normalize_whitespace(str(spec["fallback_text"])),
                fetched_at=timestamp,
            )
        all_records.extend(records)
        source_reports.append(
            {
                "source_id": spec.get("source_id"),
                "url": url,
                "content_type": response.content_type,
                "records": len(records),
                "source_hash": _hash_bytes(response.body),
            }
        )

    _write_jsonl(output_path, all_records)
    return {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "output_path": str(output_path),
        "fetched_sources": len(source_reports),
        "written_records": len(all_records),
        "sources": source_reports,
    }


def env_fetch_enabled() -> bool:
    return str(os.getenv("WORKFORCE_OFFICIAL_SOURCE_FETCH_ENABLED", "")).lower() in {"1", "true", "yes", "on"}


def _records_from_source_spec(
    spec: dict[str, Any],
    response: FetchResponse,
    text: str,
    *,
    fetched_at: str,
) -> list[dict[str, Any]]:
    source_id = str(spec.get("source_id") or _stable_id(response.url))
    title = str(spec.get("title") or source_id)
    metadata_base = _metadata_from_spec(spec, response, fetched_at=fetched_at)
    units = split_domain_units(
        text,
        doc_type=str(spec.get("doc_type") or spec.get("source_unit_type") or ""),
        source_id=source_id,
        source_path=response.url,
        title=title,
    )

    records: list[dict[str, Any]] = []
    for unit in units:
        if _should_skip_unit(unit.text):
            continue
        metadata = {
            **metadata_base,
            "source_unit_type": unit.source_unit_type,
            "domain_unit_id": unit.domain_unit_id,
            "unit_heading": unit.unit_heading,
            "unit_index": unit.unit_index,
            "unit_confidence": unit.unit_confidence,
            "splitter_version": unit.splitter_version or SPLITTER_VERSION,
        }
        normalized = normalize_workforce_metadata(
            {
                **spec,
                "title": f"{title} — {unit.unit_heading}" if unit.unit_heading else title,
                "text": unit.text,
                "raw_metadata": metadata,
            },
            source_path=response.url,
        )
        metadata.update(normalized)
        records.append(
            {
                "source_id": f"{source_id}_{unit.source_unit_type}_{unit.unit_index:04d}",
                "title": f"{title} — {unit.unit_heading}" if unit.unit_heading else title,
                "content": unit.text,
                "metadata": metadata,
            }
        )
    return records


def _should_skip_unit(text: str) -> bool:
    cleaned = normalize_whitespace(text)
    if len(cleaned) < MIN_MEANINGFUL_UNIT_CHARS:
        return True
    if not any(term in cleaned for term in WORKFORCE_CORE_TERMS):
        return True

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    sentence_like_lines = sum(1 for line in lines if line.endswith(("다.", "요.", "함.", "됨.", ".")))
    if sentence_like_lines == 0 and len(cleaned) < 300:
        return True
    if len(lines) >= 6:
        short_lines = sum(1 for line in lines if len(line) <= 18)
        if short_lines / len(lines) >= 0.65 and sentence_like_lines <= 1:
            return True

    navigation_terms = ("채용정보", "구직자정보", "자주 쓰는 외국어DB", "영상자료", "홍보자료")
    if sum(1 for term in navigation_terms if term in cleaned) >= 2:
        return True
    footer_terms = ("개인정보 처리방침", "이용약관", "이메일 무단수집거부", "Copyright", "담당자 연락처")
    if sum(1 for term in footer_terms if term in cleaned) >= 2:
        return True

    return False


def _metadata_from_spec(spec: dict[str, Any], response: FetchResponse, *, fetched_at: str) -> dict[str, Any]:
    metadata = {
        "source_id": spec.get("source_id"),
        "title": spec.get("title"),
        "publisher": spec.get("publisher"),
        "source_type": spec.get("source_type", "official_procedure"),
        "url": response.url,
        "retrieved_at": fetched_at[:10],
        "effective_date": spec.get("effective_date"),
        "doc_type": spec.get("doc_type", "procedure"),
        "mission_agent": spec.get("mission_agent", ["workforce_agent"]),
        "sub_agent": spec.get("sub_agent", ["workforce_requirement_agent"]),
        "visa_type": spec.get("visa_type", ["E-9"]),
        "country": spec.get("country", ["ALL"]),
        "industry": spec.get("industry", ["ALL"]),
        "case_type": spec.get("case_type", ["new_hiring"]),
        "workflow_stage": spec.get("workflow_stage", "pre_hiring"),
        "output_usage": spec.get("output_usage", ["requirement_check"]),
        "risk_level": spec.get("risk_level", "medium"),
        "evidence_grade": spec.get("evidence_grade", "B"),
        "source_hash": _hash_bytes(response.body),
        "source_url": response.url,
        "source_content_type": response.content_type,
        "source_fetch_method": spec.get("_source_fetch_method", "official_source_url"),
        "source_importer_version": IMPORTER_VERSION,
        "fetched_at": fetched_at,
    }
    if spec.get("source_unit_type"):
        metadata["source_unit_type"] = spec["source_unit_type"]
    return metadata


def _extract_text(response: FetchResponse) -> str:
    content_type = response.content_type.lower()
    if "pdf" in content_type or urlparse(response.url).path.lower().endswith(".pdf"):
        return _prune_boilerplate_lines(_extract_pdf_text(response.body))
    decoded = _decode_body(response.body, response.content_type)
    if "html" in content_type or re.search(r"<\s*(html|body|main|article)\b", decoded, re.IGNORECASE):
        return _prune_boilerplate_lines(clean_html_document(decoded))
    return _prune_boilerplate_lines(normalize_whitespace(decoded))


def _prune_boilerplate_lines(text: str) -> str:
    blocked_exact = {
        "주요메뉴 돌아가기",
        "본문건너뛰기",
        "개인정보 처리방침",
        "이용약관",
        "이메일 무단수집거부",
        "담당자 연락처",
    }
    kept: list[str] = []
    for line in normalize_whitespace(text).splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if stripped in blocked_exact:
            continue
        if re.match(r"^\(?우\)?\s*\d{5}\b", stripped):
            continue
        if stripped.startswith("> 고용허가제 안내"):
            continue
        if stripped.startswith("Copyright"):
            continue
        kept.append(stripped)
    return normalize_whitespace("\n".join(kept))


def _extract_pdf_text(body: bytes) -> str:
    import fitz

    doc = fitz.open(stream=body, filetype="pdf")
    try:
        pages = [page.get_text("text") for page in doc]
    finally:
        doc.close()
    return normalize_whitespace("\n\n".join(pages))


def _decode_body(body: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    encodings = [match.group(1)] if match else []
    encodings.extend(["utf-8", "cp949", "euc-kr"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="ignore")


def _urllib_fetch(url: str, timeout_seconds: int, max_bytes: int) -> FetchResponse:
    request = urllib.request.Request(url, headers={"User-Agent": "WorkBridge-RAG-Importer/1.0"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise SourceFetchError(f"source too large: {url}")
        return FetchResponse(
            url=response.geturl(),
            content_type=response.headers.get("Content-Type", "application/octet-stream"),
            body=body,
        )


def _assert_allowed_domain(url: str, allowed_domains: set[str]) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"https", "http"} or not hostname:
        raise SourceDomainNotAllowed(f"Invalid source URL: {url}")
    if hostname in allowed_domains:
        return
    if any(hostname.endswith(f".{domain}") for domain in allowed_domains):
        return
    raise SourceDomainNotAllowed(f"Source domain is not allowlisted: {hostname}")


def _read_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _hash_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
