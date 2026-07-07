from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


REQUIRED_METADATA_FIELDS = (
    "source_id",
    "title",
    "publisher",
    "source_type",
    "url",
    "retrieved_at",
    "effective_date",
    "doc_type",
    "mission_agent",
    "visa_type",
    "country",
    "industry",
    "risk_level",
    "evidence_grade",
)


def load_policy_documents(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)
    records: list[dict[str, Any]] = []

    with source_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {source_path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Invalid JSONL at {source_path}:{line_no}: row must be an object")
            records.append(record)

    return records


def validate_document(document: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_METADATA_FIELDS if field not in document]
    if missing:
        source_id = document.get("source_id", "<unknown>")
        raise ValueError(
            f"Missing metadata for source_id={source_id}: {', '.join(sorted(missing))}"
        )

    content = document.get("content")
    if not isinstance(content, str) or not content.strip():
        source_id = document.get("source_id", "<unknown>")
        raise ValueError(f"Missing content for source_id={source_id}")


def split_text(text: str) -> list[str]:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if blocks:
        return blocks
    return [line.strip() for line in text.splitlines() if line.strip()]


def build_chunks(documents: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for document in documents:
        validate_document(document)
        source_id = str(document["source_id"])
        metadata = {field: document[field] for field in REQUIRED_METADATA_FIELDS}

        for index, text in enumerate(split_text(str(document["content"])), start=1):
            chunks.append(
                {
                    "chunk_id": f"{source_id}__{index:04d}",
                    "source_id": source_id,
                    "title": document["title"],
                    "text": text,
                    "metadata": metadata,
                }
            )

    return chunks


def write_chunks_jsonl(chunks: Iterable[dict[str, Any]], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    return output_path
