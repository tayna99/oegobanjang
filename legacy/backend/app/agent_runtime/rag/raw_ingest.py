from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from .domain_splitters import SPLITTER_VERSION, infer_source_unit_type, split_domain_units
from .workforce_metadata import is_workforce_relevant_record, normalize_workforce_metadata


SUPPORTED_RAW_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".pdf", ".jsonl"}
HTML_TAG_RESIDUE_RE = re.compile(
    r"<\s*/?\s*(script|style|div|span|table|td|tr|html|body|head|nav|footer|header|aside|form)\b",
    re.IGNORECASE,
)
TABLE_RE = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)


def normalize_whitespace(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_source_id(path: Path, root_dir: Path | None = None) -> str:
    try:
        source_path = path.relative_to(root_dir or path.parent).as_posix()
    except ValueError:
        source_path = path.as_posix()
    return hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:16]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._current_row = []
        elif tag.lower() in {"th", "td"}:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            cleaned = normalize_whitespace(data)
            if cleaned:
                self._current_cell.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"th", "td"} and self._current_cell is not None:
            cell = normalize_whitespace(" ".join(self._current_cell))
            if self._current_row is not None:
                self._current_row.append(cell)
            self._current_cell = None
        elif normalized == "tr" and self._current_row is not None:
            row = [cell for cell in self._current_row if cell]
            if row:
                self.rows.append(row)
            self._current_row = None


def serialize_html_table_rows(table_html: str) -> list[str]:
    parser = _TableParser()
    parser.feed(table_html)

    if not parser.rows:
        return []

    headers = parser.rows[0]
    data_rows = parser.rows[1:] if len(parser.rows) > 1 else parser.rows
    output: list[str] = []

    for row in data_rows:
        if len(headers) == len(row) and row is not headers:
            output.append(" | ".join(f"{header}: {value}" for header, value in zip(headers, row)))
        else:
            output.append(" | ".join(row))

    return output


class _HTMLBodyParser(HTMLParser):
    block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "li", "section", "article", "main", "br"}
    ignored_tags = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}

    def __init__(self, prefer_main: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.prefer_main = prefer_main
        self.parts: list[str] = []
        self._ignored_depth = 0
        self._main_depth = 0
        self._body_depth = 0

    def _is_capturing(self) -> bool:
        if self._ignored_depth:
            return False
        if self.prefer_main:
            return self._main_depth > 0
        return self._body_depth > 0

    def _newline(self) -> None:
        if self.parts and self.parts[-1] != "\n\n":
            self.parts.append("\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self.ignored_tags:
            self._ignored_depth += 1
            return
        if normalized in {"main", "article"}:
            self._main_depth += 1
        if normalized == "body":
            self._body_depth += 1
        if normalized in self.block_tags and self._is_capturing():
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if normalized in self.block_tags and self._is_capturing():
            self._newline()
        if normalized in {"main", "article"} and self._main_depth:
            self._main_depth -= 1
        if normalized == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._is_capturing():
            return
        cleaned = normalize_whitespace(data)
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return normalize_whitespace("".join(self.parts))


def clean_html_document(raw_html: str) -> str:
    html_with_tables = TABLE_RE.sub(
        lambda match: "\n" + "\n".join(serialize_html_table_rows(match.group(0))) + "\n",
        raw_html,
    )
    prefer_main = bool(re.search(r"<\s*(main|article)\b", html_with_tables, flags=re.IGNORECASE))
    parser = _HTMLBodyParser(prefer_main=prefer_main)
    parser.feed(html_with_tables)
    return parser.text()


@dataclass
class RawIngestResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    quarantine: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_summaries: list[dict[str, Any]] = field(default_factory=list)


class IngestQualityGate:
    def __init__(self, min_chars: int = 10) -> None:
        self.min_chars = min_chars

    def apply(self, records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        accepted: list[dict[str, Any]] = []
        quarantined: list[dict[str, Any]] = []

        for record in records:
            reason = self._rejection_reason(record)
            if reason:
                quarantined.append(
                    {
                        "source_id": record.get("source_id", "<unknown>"),
                        "source_path": record.get("metadata", {}).get("source_path"),
                        "reason": reason,
                    }
                )
                continue
            accepted.append(record)

        return accepted, quarantined

    def _rejection_reason(self, record: dict[str, Any]) -> str | None:
        text = str(record.get("text", "")).strip()
        metadata = record.get("metadata", {})

        if not text:
            return "empty_text"
        if HTML_TAG_RESIDUE_RE.search(text):
            return "html_tag_residue"
        if len(text) < self.min_chars:
            return "text_too_short"
        if not metadata.get("source_path") or not metadata.get("source_hash"):
            return "missing_source_metadata"

        return None


class RawIngestor:
    def __init__(
        self,
        min_chars: int = 10,
        supported_extensions: set[str] | None = None,
    ) -> None:
        self.supported_extensions = supported_extensions or SUPPORTED_RAW_EXTENSIONS
        self.quality_gate = IngestQualityGate(min_chars=min_chars)

    def load_directory(self, raw_dir: Path, root_dir: Path | None = None) -> RawIngestResult:
        result = RawIngestResult()

        if not raw_dir.exists():
            return result

        for path in sorted(raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.supported_extensions:
                result.file_summaries.append(
                    {
                        "path": self._relative_path(path, root_dir or raw_dir),
                        "extension": path.suffix.lower(),
                        "status": "skipped",
                    }
                )
                continue

            partial = self.load_path(path, root_dir=root_dir or raw_dir)
            result.records.extend(partial.records)
            result.quarantine.extend(partial.quarantine)
            result.warnings.extend(partial.warnings)
            result.file_summaries.extend(partial.file_summaries)

        return result

    def load_path(self, path: Path, root_dir: Path | None = None) -> RawIngestResult:
        extension = path.suffix.lower()
        relative = self._relative_path(path, root_dir or path.parent)
        summary = {"path": relative, "extension": extension, "status": "processed"}

        try:
            records = self._load_supported_path(path, root_dir=root_dir or path.parent)
        except Exception as exc:
            return RawIngestResult(
                quarantine=[
                    {
                        "source_id": stable_source_id(path, root_dir),
                        "source_path": relative,
                        "reason": f"parser_error:{type(exc).__name__}",
                    }
                ],
                warnings=[f"{relative}: {exc}"],
                file_summaries=[{**summary, "status": "quarantined"}],
            )

        accepted, quarantined = self.quality_gate.apply(records)
        if not records:
            quarantined.append(
                {
                    "source_id": stable_source_id(path, root_dir),
                    "source_path": relative,
                    "reason": "empty_text",
                }
            )
        status = "processed" if accepted else "quarantined"
        return RawIngestResult(
            records=accepted,
            quarantine=quarantined,
            file_summaries=[{**summary, "status": status}],
        )

    def _load_supported_path(self, path: Path, root_dir: Path) -> list[dict[str, Any]]:
        extension = path.suffix.lower()

        if extension in {".html", ".htm"}:
            text = clean_html_document(path.read_text(encoding="utf-8", errors="ignore"))
            return self._records_from_text(path, root_dir, text, "html_generic")
        if extension in {".txt", ".md"}:
            text = normalize_whitespace(path.read_text(encoding="utf-8", errors="ignore"))
            return self._records_from_text(path, root_dir, text, "plain_text")
        if extension == ".pdf":
            return self._load_pdf(path, root_dir)
        if extension == ".jsonl":
            return self._load_curated_jsonl(path, root_dir)

        return []

    def _records_from_text(
        self,
        path: Path,
        root_dir: Path,
        text: str,
        extraction_method: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        relative = self._relative_path(path, root_dir)
        page_number = (extra_metadata or {}).get("page_number")
        base_source_id = stable_source_id(path, root_dir)
        if page_number:
            base_source_id = f"{base_source_id}_p{int(page_number):04d}"

        units = split_domain_units(
            normalize_whitespace(text),
            doc_type=None,
            source_id=base_source_id,
            source_path=relative,
            title=path.stem,
        )
        records: list[dict[str, Any]] = []
        for unit in units:
            metadata = {
                "source_path": relative,
                "source_hash": source_hash(path),
                "file_type": path.suffix.lower().lstrip("."),
                "extraction_method": extraction_method,
                "source_unit_type": unit.source_unit_type,
                "domain_unit_id": unit.domain_unit_id,
                "unit_heading": unit.unit_heading,
                "unit_index": unit.unit_index,
                "unit_confidence": unit.unit_confidence,
                "splitter_version": unit.splitter_version,
                **(extra_metadata or {}),
            }
            workforce_record = {
                "title": path.stem,
                "text": unit.text,
                "raw_metadata": metadata,
            }
            if is_workforce_relevant_record(workforce_record, source_path=relative):
                metadata.update(normalize_workforce_metadata(workforce_record, source_path=relative))
            records.append(
                {
                    "source_id": unit.domain_unit_id.replace("::", "_"),
                    "title": f"{path.stem} — {unit.unit_heading}" if unit.unit_heading else path.stem,
                    "text": unit.text,
                    "metadata": metadata,
                }
            )
        return records

    def _load_curated_jsonl(self, path: Path, root_dir: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        relative = self._relative_path(path, root_dir)
        digest = source_hash(path)

        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                row = json.loads(raw)
                text = normalize_whitespace(
                    str(row.get("text") or row.get("content") or row.get("body") or row.get("summary") or "")
                )
                metadata = {
                    **dict(row.get("metadata") or {}),
                    "source_path": relative,
                    "source_hash": digest,
                    "file_type": "jsonl",
                    "extraction_method": "curated_jsonl",
                    "line_number": line_no,
                }
                publisher = row.get("publisher") or metadata.get("publisher")
                source_type = row.get("source_type") or metadata.get("source_type")
                url = row.get("url") or metadata.get("url", "")
                retrieved_at = row.get("retrieved_at") or metadata.get("retrieved_at")
                doc_type = row.get("doc_type") or metadata.get("doc_type")
                evidence_grade = row.get("evidence_grade") or metadata.get("evidence_grade")
                source_id = str(row.get("source_id") or f"{stable_source_id(path, root_dir)}_{line_no:04d}")
                source_unit_type = metadata.get("source_unit_type") or infer_source_unit_type(
                    doc_type=str(doc_type) if doc_type else None,
                    source_path=relative,
                    text=text,
                    title=str(row.get("title", path.stem)),
                )
                metadata.update(
                    {
                        "source_unit_type": source_unit_type,
                        "domain_unit_id": metadata.get("domain_unit_id") or source_id,
                        "unit_heading": metadata.get("unit_heading") or row.get("title", path.stem),
                        "unit_index": metadata.get("unit_index") or line_no,
                        "unit_confidence": metadata.get("unit_confidence") or "high",
                        "splitter_version": metadata.get("splitter_version") or SPLITTER_VERSION,
                    }
                )
                workforce_record = {
                    **row,
                    "text": text,
                    "raw_metadata": metadata,
                }
                if is_workforce_relevant_record(workforce_record, source_path=relative):
                    metadata.update(normalize_workforce_metadata(workforce_record, source_path=relative))
                records.append(
                    {
                        "source_id": source_id,
                        "title": row.get("title", path.stem),
                        "publisher": publisher,
                        "source_type": source_type,
                        "url": url,
                        "retrieved_at": retrieved_at,
                        "doc_type": doc_type,
                        "evidence_grade": evidence_grade,
                        "text": text,
                        "metadata": metadata,
                    }
                )

        return records

    def _load_pdf(self, path: Path, root_dir: Path) -> list[dict[str, Any]]:
        import fitz

        records: list[dict[str, Any]] = []
        pdf = fitz.open(path)
        try:
            for page_index, page in enumerate(pdf, start=1):
                text = normalize_whitespace(page.get_text("text"))
                if not text:
                    continue
                records.extend(
                    self._records_from_text(
                        path,
                        root_dir,
                        text,
                        "pdf_pymupdf_text",
                        extra_metadata={"page_number": page_index},
                    )
                )
        finally:
            pdf.close()

        return records

    def _relative_path(self, path: Path, root_dir: Path) -> str:
        try:
            return path.relative_to(root_dir).as_posix()
        except ValueError:
            return path.as_posix()


def build_ingestion_report(result: RawIngestResult) -> dict[str, Any]:
    by_extension: dict[str, int] = {}
    by_source_unit_type: dict[str, int] = {}
    low_confidence = 0
    splitter_warnings: list[str] = []
    for summary in result.file_summaries:
        extension = str(summary.get("extension", ""))
        by_extension[extension] = by_extension.get(extension, 0) + 1
    for record in result.records:
        metadata = record.get("metadata", {})
        unit_type = str(metadata.get("source_unit_type") or "missing")
        by_source_unit_type[unit_type] = by_source_unit_type.get(unit_type, 0) + 1
        if metadata.get("unit_confidence") == "low":
            low_confidence += 1
            splitter_warnings.append(
                f"{metadata.get('source_path', '<unknown>')}:{record.get('source_id', '<unknown>')} low confidence domain unit"
            )

    return {
        "input_files": len(result.file_summaries),
        "processed_files": sum(1 for summary in result.file_summaries if summary.get("status") == "processed"),
        "skipped_files": sum(1 for summary in result.file_summaries if summary.get("status") == "skipped"),
        "quarantined_files": sum(1 for summary in result.file_summaries if summary.get("status") == "quarantined"),
        "emitted_records": len(result.records),
        "quarantined_records": len(result.quarantine),
        "warnings": result.warnings,
        "by_extension": dict(sorted(by_extension.items())),
        "source_unit_type_counts": dict(sorted(by_source_unit_type.items())),
        "low_confidence_unit_count": low_confidence,
        "domain_splitter_warnings": splitter_warnings,
        "quarantine": result.quarantine,
    }
