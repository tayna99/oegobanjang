#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PIPELINE_DIR = ROOT_DIR / "data-pipeline"
SOURCE_REGISTRY_PATH = (
    DATA_PIPELINE_DIR / "metadata" / "multilingual_source_registry.jsonl"
)
OUTPUT_DIR = DATA_PIPELINE_DIR / "processed" / "chunks" / "multilingual_contact"

DEFAULT_MAX_CHARS = 1200
SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".pdf"}
PDF_EXTENSION = ".pdf"
RAG_DOMAIN = "multilingual_contact"
OWNER_AGENT = "multilingual_contact_agent"
EXCLUDED_RAG_PATH_PREFIXES = (
    "data-pipeline/raw/templates/",
    "data-pipeline/raw/synthetic_cases/",
    "data-pipeline/raw/public_cases/",
)
EXCLUDED_RAG_PATH_PARTS = {"worker_replies"}
ALLOWED_DOC_TYPES = {"counseling", "life", "notice", "safety"}
NON_LEGAL_BASIS_SOURCE_TYPES = {
    "message_template",
    "public_case_reference",
    "synthetic_case",
    "interview_case_pattern",
}


def stable_id(*parts: str) -> str:
    raw = "::".join(part for part in parts if part)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def now_iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL: {path}:{line_no} - {e}") from e

            if not isinstance(record, dict):
                raise ValueError(f"JSONL line must be object: {path}:{line_no}")

            records.append(record)

    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            count += 1

    return count


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        if len(current) + 2 + len(paragraph) <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
            continue

        for i in range(0, len(chunk), max_chars):
            final_chunks.append(chunk[i : i + max_chars].strip())

    return [chunk for chunk in final_chunks if chunk]


def path_is_excluded(relative_path: str) -> bool:
    path = Path(relative_path)

    if any(relative_path.startswith(prefix) for prefix in EXCLUDED_RAG_PATH_PREFIXES):
        return True

    return any(part in EXCLUDED_RAG_PATH_PARTS for part in path.parts)


def is_multilingual_contact_candidate(record: dict[str, Any]) -> bool:
    if record.get("rag_domain", RAG_DOMAIN) != RAG_DOMAIN:
        return False

    if record.get("owner_agent", OWNER_AGENT) != OWNER_AGENT:
        return False

    if record.get("doc_type") not in ALLOWED_DOC_TYPES:
        return False

    if record.get("evidence_grade") == "F":
        return False

    if record.get("source_type") in NON_LEGAL_BASIS_SOURCE_TYPES:
        return False

    return True


def should_skip_not_for_legal_basis(record: dict[str, Any]) -> bool:
    return record.get("not_for_legal_basis") is True


def normalize_not_for_legal_basis(record: dict[str, Any]) -> bool:
    is_official_rag_record = (
        record.get("ingest_target") is True
        and record.get("evidence_grade") != "F"
        and record.get("source_type") not in NON_LEGAL_BASIS_SOURCE_TYPES
    )

    if is_official_rag_record:
        return False

    return bool(record.get("not_for_legal_basis"))


def format_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)

    if value:
        return str(value)

    return "unspecified"


def build_context_prefix(metadata: dict[str, Any]) -> str:
    """Build metadata-only context for contextual retrieval.

    Embedding should use contextual_text. User-facing citations should use the
    original text plus metadata, so generated context never replaces source text.
    """

    publisher = metadata.get("publisher") or "unknown publisher"
    title = metadata.get("title") or "untitled document"
    doc_type = metadata.get("doc_type") or "general"
    language = format_list(metadata.get("language"))
    use_case = format_list(metadata.get("use_case"))
    file_type = metadata.get("file_type") or "unknown"
    rag_domain = metadata.get("rag_domain") or RAG_DOMAIN
    page_number = metadata.get("page_number")

    if file_type == "pdf" and page_number is not None:
        source_description = (
            f"이 chunk는 {publisher}의 '{title}' PDF {page_number}페이지에서 "
            "추출되었다."
        )
    else:
        source_description = (
            f"이 chunk는 {publisher}의 '{title}' {file_type} 문서에서 추출되었다."
        )

    return (
        f"{source_description} 문서 유형은 {doc_type}이고, 언어는 {language}이며, "
        f"{rag_domain} RAG에서 {use_case} 용도로 참고할 수 있다."
    )


def normalize_metadata(
    record: dict[str, Any],
    source_path: str,
    *,
    file_type: str,
    page_number: int | None = None,
) -> dict[str, Any]:
    metadata = {
        "source_id": record.get("source_id") or stable_id(source_path),
        "title": record.get("title", "Untitled"),
        "publisher": record.get("publisher", "unknown"),
        "source_type": record.get("source_type", "unknown"),
        "url": record.get("url", ""),
        "retrieved_at": record.get("retrieved_at", now_iso_date()),
        "doc_type": record.get("doc_type", "general"),
        "evidence_grade": record.get("evidence_grade", "D"),
        "use_case": record.get("use_case", []),
        "language": record.get("language", []),
        "raw_path": record.get("raw_path", source_path),
        "file_type": file_type,
        "rag_domain": record.get("rag_domain", RAG_DOMAIN),
        "owner_agent": record.get("owner_agent", OWNER_AGENT),
        "ingest_target": record.get("ingest_target"),
        "not_for_legal_basis": normalize_not_for_legal_basis(record),
        "contains_personal_data": record.get("contains_personal_data"),
        "source_path": source_path,
    }

    if page_number is not None:
        metadata["page_number"] = page_number

    return metadata


def make_chunks(
    record: dict[str, Any],
    source_path: str,
    text: str,
    *,
    file_type: str,
    page_number: int | None = None,
) -> list[dict[str, Any]]:
    chunks = split_text(text)
    if not chunks:
        return []

    metadata = normalize_metadata(
        record,
        source_path,
        file_type=file_type,
        page_number=page_number,
    )

    output: list[dict[str, Any]] = []
    for index, chunk_text in enumerate(chunks):
        if page_number is None:
            chunk_id = f"{metadata['source_id']}_chunk_{index:04d}"
        else:
            chunk_id = f"{metadata['source_id']}_page_{page_number:04d}_chunk_{index:04d}"

        context = build_context_prefix(metadata)
        contextual_text = f"{context}\n\n{chunk_text}"

        output.append(
            {
                "chunk_id": chunk_id,
                "source_id": metadata["source_id"],
                "text": chunk_text,
                "context": context,
                "contextual_text": contextual_text,
                "metadata": {
                    **metadata,
                    "chunk_index": index,
                    "chunk_char_length": len(chunk_text),
                },
            }
        )

    return output


def extract_pdf_chunks(
    record: dict[str, Any],
    path: Path,
    relative_path: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats: dict[str, Any] = {
        "pdf_pages_extracted": 0,
        "pdf_pages_empty": 0,
        "pdf_failed": None,
        "empty_pdf_text": False,
    }

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as e:
        stats["pdf_failed"] = {
            "source_id": record.get("source_id", ""),
            "raw_path": relative_path,
            "reason": "pymupdf_not_installed",
            "error": str(e),
        }
        return [], stats

    output: list[dict[str, Any]] = []

    try:
        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                text = normalize_text(page.get_text("text"))
                if not text:
                    stats["pdf_pages_empty"] += 1
                    continue

                page_chunks = make_chunks(
                    record,
                    relative_path,
                    text,
                    file_type="pdf",
                    page_number=page_index,
                )
                if page_chunks:
                    stats["pdf_pages_extracted"] += 1
                    output.extend(page_chunks)
                else:
                    stats["pdf_pages_empty"] += 1
    except Exception as e:
        stats["pdf_failed"] = {
            "source_id": record.get("source_id", ""),
            "raw_path": relative_path,
            "reason": "pdf_extract_failed",
            "error": str(e),
        }
        return [], stats

    if not output:
        stats["empty_pdf_text"] = True

    return output, stats


def classify_chunk_file_name(chunk: dict[str, Any]) -> str:
    doc_type = chunk.get("metadata", {}).get("doc_type", "general")

    if doc_type == "safety":
        return "safety_chunks.jsonl"
    if doc_type == "life":
        return "life_chunks.jsonl"
    if doc_type == "counseling":
        return "counseling_chunks.jsonl"
    if doc_type == "notice":
        return "notice_chunks.jsonl"

    return "general_chunks.jsonl"


def build_chunks() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    registry_records = read_jsonl(SOURCE_REGISTRY_PATH)
    report: dict[str, Any] = {
        "total_registry_rows": len(registry_records),
        "multilingual_ingest_target_rows": 0,
        "ingested_files": [],
        "ingested_pdf_files": [],
        "pdf_pages_extracted": 0,
        "pdf_pages_empty": 0,
        "pdf_files_failed": [],
        "skipped_missing_raw_path": [],
        "skipped_missing_files": [],
        "skipped_unsupported_files": [],
        "skipped_excluded_paths": [],
        "skipped_ingest_target_false": 0,
        "skipped_non_multilingual_contact": [],
        "skipped_not_for_legal_basis": [],
        "skipped_empty_pdf_text": [],
        "contextual_chunks_generated": 0,
        "chunks_missing_context": 0,
        "chunks_missing_contextual_text": 0,
        "chunks_with_not_for_legal_basis_true": 0,
        "short_chunks_under_50_chars": 0,
    }
    all_chunks: list[dict[str, Any]] = []

    for record in registry_records:
        source_id = str(record.get("source_id", ""))

        if record.get("ingest_target") is not True:
            report["skipped_ingest_target_false"] += 1
            continue

        if not is_multilingual_contact_candidate(record):
            report["skipped_non_multilingual_contact"].append(source_id)
            continue

        if should_skip_not_for_legal_basis(record):
            report["skipped_not_for_legal_basis"].append(source_id)
            continue

        report["multilingual_ingest_target_rows"] += 1

        raw_path = record.get("raw_path")
        if not raw_path:
            report["skipped_missing_raw_path"].append(source_id)
            continue

        path = (ROOT_DIR / str(raw_path)).resolve()
        relative_path = path.relative_to(ROOT_DIR).as_posix()

        if path_is_excluded(relative_path):
            report["skipped_excluded_paths"].append(relative_path)
            continue

        if not path.exists() or not path.is_file():
            report["skipped_missing_files"].append(relative_path)
            continue

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            report["skipped_unsupported_files"].append(
                {
                    "source_id": source_id,
                    "raw_path": relative_path,
                    "extension": suffix,
                    "reason": "unsupported_extension",
                }
            )
            continue

        if suffix == PDF_EXTENSION:
            chunks, pdf_stats = extract_pdf_chunks(record, path, relative_path)
            report["pdf_pages_extracted"] += int(pdf_stats["pdf_pages_extracted"])
            report["pdf_pages_empty"] += int(pdf_stats["pdf_pages_empty"])

            if pdf_stats["pdf_failed"]:
                report["pdf_files_failed"].append(pdf_stats["pdf_failed"])
                continue

            if pdf_stats["empty_pdf_text"]:
                report["skipped_empty_pdf_text"].append(
                    {
                        "source_id": source_id,
                        "raw_path": relative_path,
                        "reason": "needs_ocr",
                    }
                )
                continue

            all_chunks.extend(chunks)
            report["ingested_files"].append(relative_path)
            report["ingested_pdf_files"].append(relative_path)
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        file_type = suffix.lstrip(".")
        chunks = make_chunks(
            record,
            relative_path,
            text,
            file_type=file_type,
        )

        if chunks:
            all_chunks.extend(chunks)
            report["ingested_files"].append(relative_path)

    report["contextual_chunks_generated"] = sum(
        1 for chunk in all_chunks if chunk.get("context") and chunk.get("contextual_text")
    )
    report["chunks_missing_context"] = sum(
        1 for chunk in all_chunks if not chunk.get("context")
    )
    report["chunks_missing_contextual_text"] = sum(
        1 for chunk in all_chunks if not chunk.get("contextual_text")
    )
    report["chunks_with_not_for_legal_basis_true"] = sum(
        1
        for chunk in all_chunks
        if chunk.get("metadata", {}).get("not_for_legal_basis") is True
    )
    report["short_chunks_under_50_chars"] = sum(
        1 for chunk in all_chunks if len(str(chunk.get("text", "")).strip()) < 50
    )

    return all_chunks, report


def write_chunk_files(chunks: list[dict[str, Any]]) -> dict[str, int]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        grouped.setdefault(classify_chunk_file_name(chunk), []).append(chunk)

    expected_files = [
        "all_chunks.jsonl",
        "safety_chunks.jsonl",
        "life_chunks.jsonl",
        "counseling_chunks.jsonl",
        "notice_chunks.jsonl",
        "general_chunks.jsonl",
    ]

    counts: dict[str, int] = {}
    for file_name in expected_files:
        path = OUTPUT_DIR / file_name
        if file_name == "all_chunks.jsonl":
            counts[file_name] = write_jsonl(path, chunks)
        else:
            counts[file_name] = write_jsonl(path, grouped.get(file_name, []))

    return counts


def print_report(report: dict[str, Any], output_counts: dict[str, int] | None) -> None:
    print("Multilingual Contact RAG ingest report:")
    print(f"  total registry rows: {report['total_registry_rows']}")
    print(
        "  multilingual ingest_target rows: "
        f"{report['multilingual_ingest_target_rows']}"
    )
    print(f"  ingested files: {len(report['ingested_files'])}")
    print(f"  ingested pdf files: {len(report['ingested_pdf_files'])}")
    print(f"  pdf pages extracted: {report['pdf_pages_extracted']}")
    print(f"  pdf pages empty: {report['pdf_pages_empty']}")
    print(f"  pdf files failed: {len(report['pdf_files_failed'])}")
    print(f"  skipped missing raw_path: {len(report['skipped_missing_raw_path'])}")
    print(f"  skipped missing files: {len(report['skipped_missing_files'])}")
    print(f"  skipped unsupported files: {len(report['skipped_unsupported_files'])}")
    print(f"  skipped excluded paths: {len(report['skipped_excluded_paths'])}")
    print(f"  skipped ingest_target=false: {report['skipped_ingest_target_false']}")
    print(
        "  skipped non multilingual_contact: "
        f"{len(report['skipped_non_multilingual_contact'])}"
    )
    print(
        "  skipped not_for_legal_basis=true: "
        f"{len(report['skipped_not_for_legal_basis'])}"
    )
    print(f"  skipped empty pdf text: {len(report['skipped_empty_pdf_text'])}")
    print(
        "  contextual chunks generated: "
        f"{report['contextual_chunks_generated']}"
    )
    print(f"  chunks missing context: {report['chunks_missing_context']}")
    print(
        "  chunks missing contextual_text: "
        f"{report['chunks_missing_contextual_text']}"
    )
    print(
        "  chunks with not_for_legal_basis=true: "
        f"{report['chunks_with_not_for_legal_basis_true']}"
    )
    print(f"  short chunks under 50 chars: {report['short_chunks_under_50_chars']}")
    print("  output chunk files:")

    expected_files = [
        "all_chunks.jsonl",
        "safety_chunks.jsonl",
        "life_chunks.jsonl",
        "counseling_chunks.jsonl",
        "notice_chunks.jsonl",
        "general_chunks.jsonl",
    ]
    for file_name in expected_files:
        suffix = ""
        if output_counts is not None:
            suffix = f" ({output_counts.get(file_name, 0)} chunks)"
        print(f"    {OUTPUT_DIR / file_name}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build multilingual contact RAG chunk JSONL files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate ingest selection and extraction without writing chunk files.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when no chunks are generated.",
    )
    args = parser.parse_args()

    chunks, report = build_chunks()

    if not chunks:
        print("No multilingual contact RAG chunks generated.")
        if args.strict:
            print_report(report, output_counts=None)
            return 1

    output_counts = None
    if not args.dry_run:
        output_counts = write_chunk_files(chunks)

    print_report(report, output_counts=output_counts)
    print(f"  total chunks: {len(chunks)}")

    if args.dry_run:
        print("Dry run completed. No chunk files were written.")
    else:
        print("Multilingual Contact RAG chunk build completed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
