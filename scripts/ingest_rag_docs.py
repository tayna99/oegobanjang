#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PIPELINE_DIR = ROOT_DIR / "data-pipeline"
RAW_DIR = DATA_PIPELINE_DIR / "raw"
SEED_DIR = DATA_PIPELINE_DIR / "seed"
PROCESSED_DIR = DATA_PIPELINE_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"


DEFAULT_MAX_CHARS = 1200


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
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
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


def infer_doc_type(record: dict[str, Any], source_path: str | None = None) -> str:
    explicit = record.get("doc_type")
    if explicit:
        return str(explicit)

    source_type = str(record.get("source_type", "")).lower()
    title = str(record.get("title", "")).lower()
    path = (source_path or "").lower()

    value = f"{source_type} {title} {path}"

    if any(token in value for token in ["law", "act", "법", "시행령", "시행규칙"]):
        return "law"
    if any(token in value for token in ["procedure", "process", "절차", "고용허가"]):
        return "procedure"
    if any(token in value for token in ["form", "서식", "신고서"]):
        return "form"
    if any(token in value for token in ["safety", "안전", "kosha"]):
        return "safety"
    if any(token in value for token in ["template", "message", "메시지", "템플릿"]):
        return "template"
    if any(token in value for token in ["case", "synthetic", "케이스"]):
        return "case"

    return "general"


def infer_evidence_grade(record: dict[str, Any]) -> str:
    explicit = record.get("evidence_grade")
    if explicit:
        return str(explicit)

    source_type = str(record.get("source_type", "")).lower()
    publisher = str(record.get("publisher", "")).lower()

    if "official_law" in source_type or "법령" in publisher:
        return "A"
    if "official" in source_type:
        return "B"
    if "statistics" in source_type:
        return "C"
    if "case" in source_type:
        return "F"
    if "template" in source_type:
        return "E"

    return "D"


def normalize_metadata(
    record: dict[str, Any],
    source_path: str | None = None,
) -> dict[str, Any]:
    doc_type = infer_doc_type(record, source_path)
    evidence_grade = infer_evidence_grade(record)

    source_id = str(
        record.get("source_id")
        or stable_id(
            str(record.get("title", "")),
            str(record.get("url", "")),
            source_path or "",
        )
    )

    return {
        "source_id": source_id,
        "title": record.get("title", "Untitled"),
        "publisher": record.get("publisher", "unknown"),
        "source_type": record.get("source_type", "unknown"),
        "url": record.get("url", ""),
        "retrieved_at": record.get("retrieved_at", now_iso_date()),
        "effective_date": record.get("effective_date"),
        "doc_type": doc_type,
        "mission_agent": record.get("mission_agent", []),
        "visa_type": record.get("visa_type", []),
        "country": record.get("country", ["ALL"]),
        "industry": record.get("industry", []),
        "risk_level": record.get("risk_level", "medium"),
        "evidence_grade": evidence_grade,
        "source_path": source_path,
    }


def make_chunks_from_record(record: dict[str, Any], source_path: str | None = None) -> list[dict[str, Any]]:
    text = (
        record.get("text")
        or record.get("content")
        or record.get("body")
        or record.get("summary")
        or ""
    )

    text = normalize_text(str(text))
    metadata = normalize_metadata(record, source_path)

    if not text:
        return []

    chunks = split_text(text)

    output: list[dict[str, Any]] = []

    for index, chunk_text in enumerate(chunks):
        chunk_id = f"{metadata['source_id']}_chunk_{index:04d}"

        output.append(
            {
                "chunk_id": chunk_id,
                "source_id": metadata["source_id"],
                "text": chunk_text,
                "metadata": {
                    **metadata,
                    "chunk_index": index,
                    "chunk_char_length": len(chunk_text),
                },
            }
        )

    return output


def load_seed_documents() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for filename in ("sample_policy_docs.jsonl", "sample_required_docs.jsonl"):
        path = SEED_DIR / filename
        records.extend(read_jsonl(path))

    return records


def load_document_requirements() -> list[dict[str, Any]]:
    path = SEED_DIR / "document_requirements.csv"

    if not path.exists():
        return []

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            case_type = row.get("case_type", "")
            visa_type = row.get("visa_type", "")
            required_doc = row.get("required_doc", "")
            source_id = row.get("source_id", "")

            title = f"{case_type} {visa_type} required document: {required_doc}"

            text = (
                f"case_type: {case_type}\n"
                f"visa_type: {visa_type}\n"
                f"required_doc: {required_doc}\n"
                f"required: {row.get('required', '')}\n"
                f"source_id: {source_id}\n"
                f"notes: {row.get('notes', '')}"
            )

            records.append(
                {
                    "source_id": f"document_requirement_{stable_id(case_type, visa_type, required_doc)}",
                    "title": title,
                    "publisher": "internal",
                    "source_type": "internal_checklist",
                    "doc_type": "form",
                    "evidence_grade": "E",
                    "mission_agent": ["visa_document_agent"],
                    "visa_type": [visa_type] if visa_type else [],
                    "country": ["ALL"],
                    "industry": [],
                    "risk_level": "medium",
                    "text": text,
                    "linked_source_id": source_id,
                }
            )

    return records


def load_raw_text_documents() -> list[tuple[dict[str, Any], str]]:
    if not RAW_DIR.exists():
        return []

    supported_extensions = {".txt", ".md", ".html", ".htm"}

    results: list[tuple[dict[str, Any], str]] = []

    for path in sorted(RAW_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in supported_extensions:
            continue

        relative = path.relative_to(ROOT_DIR).as_posix()

        text = path.read_text(encoding="utf-8", errors="ignore")

        record = {
            "source_id": stable_id(relative),
            "title": path.stem,
            "publisher": "unknown",
            "source_type": "raw_text",
            "url": "",
            "retrieved_at": now_iso_date(),
            "doc_type": infer_doc_type({}, relative),
            "evidence_grade": "D",
            "text": text,
        }

        results.append((record, relative))

    return results


def classify_chunk_file_name(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    doc_type = metadata.get("doc_type", "general")

    if doc_type == "law":
        return "regulation_chunks.jsonl"
    if doc_type == "procedure":
        return "procedure_chunks.jsonl"
    if doc_type == "form":
        return "form_chunks.jsonl"
    if doc_type == "safety":
        return "safety_chunks.jsonl"
    if doc_type == "template":
        return "template_chunks.jsonl"
    if doc_type == "case":
        return "case_chunks.jsonl"

    return "general_chunks.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local RAG chunk JSONL files for Oegobanjang."
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when no source records are found.",
    )

    args = parser.parse_args()

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    source_records = load_seed_documents()
    source_records.extend(load_document_requirements())

    raw_records = load_raw_text_documents()

    all_chunks: list[dict[str, Any]] = []

    for record in source_records:
        all_chunks.extend(make_chunks_from_record(record))

    for record, source_path in raw_records:
        all_chunks.extend(make_chunks_from_record(record, source_path=source_path))

    if not all_chunks:
        message = (
            "No source records found. Created empty chunk files. "
            "Add data under data-pipeline/seed or data-pipeline/raw."
        )
        print(message)

        if args.strict:
            return 1

    grouped: dict[str, list[dict[str, Any]]] = {}

    for chunk in all_chunks:
        file_name = classify_chunk_file_name(chunk)
        grouped.setdefault(file_name, []).append(chunk)

    expected_files = [
        "all_chunks.jsonl",
        "regulation_chunks.jsonl",
        "procedure_chunks.jsonl",
        "form_chunks.jsonl",
        "safety_chunks.jsonl",
        "template_chunks.jsonl",
        "case_chunks.jsonl",
        "general_chunks.jsonl",
    ]

    for file_name in expected_files:
        path = CHUNKS_DIR / file_name

        if file_name == "all_chunks.jsonl":
            count = write_jsonl(path, all_chunks)
        else:
            count = write_jsonl(path, grouped.get(file_name, []))

        print(f"Wrote {count:>4} chunks -> {path}")

    print("RAG chunk build completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())