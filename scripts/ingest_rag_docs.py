#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
DATA_PIPELINE_DIR = ROOT_DIR / "data-pipeline"
RAW_DIR = DATA_PIPELINE_DIR / "raw"
SEED_DIR = DATA_PIPELINE_DIR / "seed"
PROCESSED_DIR = DATA_PIPELINE_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent_runtime.rag.raw_ingest import RawIngestor, build_ingestion_report
from app.agent_runtime.rag.evaluate import evaluate_retrieval
from app.agent_runtime.rag.embeddings import deterministic_embedding
from app.agent_runtime.rag.workforce_metadata import (
    build_workforce_source_inventory,
    is_workforce_relevant_record,
    normalize_workforce_metadata,
)


DEFAULT_MAX_CHARS = 1200
DEFAULT_MIN_HIT_RATE = 0.80


def stable_id(*parts: str) -> str:
    raw = "::".join(part for part in parts if part)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def now_iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple | set):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


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

    metadata = {
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
    raw_metadata = record.get("raw_metadata")
    if isinstance(raw_metadata, dict):
        raw_parent_source_id = raw_metadata.get("source_id")
        if raw_parent_source_id and str(raw_parent_source_id) != source_id:
            metadata["parent_source_id"] = raw_parent_source_id
        for key, value in raw_metadata.items():
            if key in {"source_id", "source_path"}:
                continue
            metadata[key] = value
    workforce_record = {**record, "raw_metadata": metadata}
    if is_workforce_relevant_record(workforce_record, source_path=source_path):
        metadata.update(normalize_workforce_metadata(workforce_record, source_path=source_path))

    return metadata


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


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_seed_documents(include_demo_seed: bool | None = None) -> list[dict[str, Any]]:
    if include_demo_seed is None:
        include_demo_seed = _env_flag("DAILY_BRIEFING_INCLUDE_DEMO_SEED")

    if not include_demo_seed:
        return []

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
                    "source_unit_type": "form_section",
                    "domain_unit_id": f"document_requirement_{stable_id(case_type, visa_type, required_doc)}",
                    "unit_heading": required_doc,
                    "unit_index": 1,
                    "unit_confidence": "high",
                    "splitter_version": "internal_document_requirements_v1",
                    "text": text,
                    "linked_source_id": source_id,
                }
            )

    return records


def load_candidate_readiness_checklist() -> list[dict[str, Any]]:
    path = SEED_DIR / "candidate_readiness_checklist.csv"
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_index, row in enumerate(reader, start=1):
            case_type = row.get("case_type", "")
            field = row.get("field", "")
            sub_agent = "candidate_readiness_agent" if case_type == "candidate_review" else "workforce_requirement_agent"
            workflow_stage = "candidate_readiness" if case_type == "candidate_review" else "pre_hiring"
            output_usage = ["readiness_check"] if case_type == "candidate_review" else ["requirement_check"]
            text = (
                f"case_type: {case_type}\n"
                f"field: {field}\n"
                f"required: {row.get('required', '')}\n"
                f"check_method: {row.get('check_method', '')}\n"
                f"source_id: {row.get('source_id', '')}\n"
                f"notes: {row.get('notes', '')}"
            )
            records.append(
                {
                    "source_id": f"candidate_readiness_{stable_id(case_type, field)}",
                    "title": f"candidate_readiness_checklist: {case_type} {field}",
                    "publisher": "internal",
                    "source_type": "internal_checklist",
                    "doc_type": "form",
                    "evidence_grade": "E",
                    "mission_agent": ["workforce_agent"],
                    "sub_agent": [sub_agent],
                    "case_type": [case_type] if case_type else ["candidate_review"],
                    "workflow_stage": workflow_stage,
                    "output_usage": output_usage,
                    "source_unit_type": "employer_requirement",
                    "domain_unit_id": f"candidate_readiness_checklist::{row_index:04d}",
                    "unit_heading": field,
                    "unit_index": row_index,
                    "unit_confidence": "high",
                    "splitter_version": "candidate_readiness_checklist_v1",
                    "visa_type": ["E-9"],
                    "country": ["ALL"],
                    "industry": ["ALL"],
                    "risk_level": "low",
                    "text": text,
                    "linked_source_id": row.get("source_id", ""),
                }
            )
    return records


def load_raw_text_documents(
    raw_dir: Path = RAW_DIR,
    root_dir: Path = ROOT_DIR,
) -> list[tuple[dict[str, Any], str]]:
    if not raw_dir.exists():
        return []

    result = RawIngestor().load_directory(raw_dir, root_dir=root_dir)
    records: list[tuple[dict[str, Any], str]] = []

    for raw_record in result.records:
        metadata = dict(raw_record.get("metadata") or {})
        relative = str(metadata.get("source_path") or "")

        record = {
            "source_id": raw_record.get("source_id") or stable_id(relative),
            "title": raw_record.get("title", "Untitled"),
            "publisher": _infer_raw_publisher(relative),
            "source_type": _infer_raw_source_type(metadata, relative),
            "url": "",
            "retrieved_at": now_iso_date(),
            "doc_type": _infer_raw_doc_type(raw_record, relative),
            "evidence_grade": _infer_raw_evidence_grade(metadata, relative),
            "text": raw_record.get("text", ""),
            "source_path": relative,
            "raw_metadata": metadata,
        }
        for field in ("publisher", "source_type", "url", "retrieved_at", "doc_type", "evidence_grade"):
            if raw_record.get(field):
                record[field] = raw_record[field]

        records.append((record, relative))

    return records

def load_raw_text_documents_with_report(
    raw_dir: Path = RAW_DIR,
    root_dir: Path = ROOT_DIR,
) -> tuple[list[tuple[dict[str, Any], str]], dict[str, Any]]:
    result = RawIngestor().load_directory(raw_dir, root_dir=root_dir)
    records: list[tuple[dict[str, Any], str]] = []

    for raw_record in result.records:
        metadata = dict(raw_record.get("metadata") or {})
        relative = str(metadata.get("source_path") or "")
        record = {
            "source_id": raw_record.get("source_id") or stable_id(relative),
            "title": raw_record.get("title", "Untitled"),
            "publisher": raw_record.get("publisher") or _infer_raw_publisher(relative),
            "source_type": raw_record.get("source_type")
            or _infer_raw_source_type(metadata, relative),
            "url": raw_record.get("url", ""),
            "retrieved_at": raw_record.get("retrieved_at") or now_iso_date(),
            "doc_type": raw_record.get("doc_type") or _infer_raw_doc_type(raw_record, relative),
            "evidence_grade": raw_record.get("evidence_grade") or _infer_raw_evidence_grade(metadata, relative),
            "text": raw_record.get("text", ""),
            "source_path": relative,
            "raw_metadata": metadata,
        }
        records.append((record, relative))

    return records, build_ingestion_report(result)


def _infer_raw_publisher(relative: str) -> str:
    return "internal" if "/templates/" in relative or "\\templates\\" in relative else "unknown"


def _infer_raw_source_type(metadata: dict[str, Any], relative: str) -> str:
    if "/templates/" in relative or "\\templates\\" in relative:
        return "internal_template"
    return "curated_jsonl" if metadata.get("extraction_method") == "curated_jsonl" else "raw_text"


def _infer_raw_doc_type(raw_record: dict[str, Any], relative: str) -> str:
    if "/templates/" in relative or "\\templates\\" in relative:
        return "template"
    return infer_doc_type(raw_record, relative)


def _infer_raw_evidence_grade(metadata: dict[str, Any], relative: str) -> str:
    if "/templates/" in relative or "\\templates\\" in relative:
        return "E"
    return "D"


def load_raw_source_inventory(
    raw_dir: Path = RAW_DIR,
    root_dir: Path = ROOT_DIR,
) -> dict[str, dict[str, Any]]:
    records = load_raw_text_documents(raw_dir=raw_dir, root_dir=root_dir)
    return {str(record["source_id"]): record for record, _ in records}


def _is_seed_record(record: dict[str, Any]) -> bool:
    return str(record.get("source_id", "")).startswith("seed_") or str(record.get("source_type", "")) in {
        "synthetic_case",
        "message_template",
    }


def _is_official_record(record: dict[str, Any]) -> bool:
    source_type = str(record.get("source_type", ""))
    grade = str(record.get("evidence_grade", "")).upper()
    return source_type.startswith("official_") or grade in {"A", "B"}


def build_source_mix_report(
    *,
    source_records: list[dict[str, Any]],
    raw_records: list[tuple[dict[str, Any], str]],
    raw_report: dict[str, Any],
) -> dict[str, Any]:
    raw_only_records = [record for record, _ in raw_records]
    all_records = [*source_records, *raw_only_records]
    workforce_inventory = build_workforce_source_inventory(all_records)
    source_unit_type_counts: dict[str, int] = {}
    for record in all_records:
        raw_metadata = record.get("raw_metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else record
        unit_type = str(metadata.get("source_unit_type") or "missing")
        source_unit_type_counts[unit_type] = source_unit_type_counts.get(unit_type, 0) + 1

    return {
        **raw_report,
        "seed_records": sum(1 for record in source_records if _is_seed_record(record)),
        "internal_records": sum(
            1 for record in source_records if str(record.get("source_type", "")) == "internal_checklist"
        ),
        "raw_records": len(raw_only_records),
        "official_records": sum(1 for record in all_records if _is_official_record(record)),
        "synthetic_records": sum(1 for record in all_records if str(record.get("evidence_grade", "")).upper() == "F"),
        "source_unit_type_counts": dict(sorted(source_unit_type_counts.items())),
        "workforce_source_count": sum(1 for record in all_records if _is_workforce_record(record)),
        "workforce_metadata_coverage": workforce_inventory["coverage"],
        "workforce_source_gaps": workforce_inventory["missing_categories"],
        "workforce_metadata_gap_count": len(workforce_inventory["metadata_gaps"]),
    }


def _is_workforce_record(record: dict[str, Any]) -> bool:
    if is_workforce_relevant_record(record, source_path=str(record.get("source_path") or "")):
        return True
    metadata = record.get("raw_metadata") if isinstance(record.get("raw_metadata"), dict) else {}
    mission_agent = record.get("mission_agent") or metadata.get("mission_agent") or []
    if isinstance(mission_agent, str):
        mission_agent = [mission_agent]
    if "workforce_agent" in mission_agent:
        return True

    text = " ".join(
        str(value)
        for value in (
            record.get("source_id", ""),
            record.get("title", ""),
            record.get("text", ""),
            record.get("doc_type", ""),
            record.get("source_type", ""),
        )
    )
    return any(
        keyword in text
        for keyword in (
            "고용허가",
            "내국인 구인",
            "구인노력",
            "사업주 고용절차",
            "근로계약",
            "사증발급인정서",
            "취업교육",
            "허용업종",
            "신규 고용",
        )
    )


def build_all_chunks(
    *,
    include_demo_seed: bool = False,
    include_document_requirements: bool = True,
    raw_dir: Path = RAW_DIR,
    root_dir: Path = ROOT_DIR,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_records = load_seed_documents(include_demo_seed=include_demo_seed)

    if include_document_requirements:
        source_records.extend(load_document_requirements())
        source_records.extend(load_candidate_readiness_checklist())

    raw_records, raw_report = load_raw_text_documents_with_report(raw_dir=raw_dir, root_dir=root_dir)

    all_chunks: list[dict[str, Any]] = []

    for record in source_records:
        all_chunks.extend(make_chunks_from_record(record))

    for record, source_path in raw_records:
        all_chunks.extend(make_chunks_from_record(record, source_path=source_path))

    return all_chunks, build_source_mix_report(
        source_records=source_records,
        raw_records=raw_records,
        raw_report=raw_report,
    )


def evaluate_chunk_gate(
    *,
    chunks: list[dict[str, Any]],
    dataset_path: Path,
    min_hit_rate: float = DEFAULT_MIN_HIT_RATE,
) -> tuple[bool, dict[str, Any]]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    try:
        report = evaluate_retrieval(dataset_path=dataset_path, chunk_path=temp_path, top_k=3)
    finally:
        temp_path.unlink(missing_ok=True)

    report_dict = {
        "dataset_path": str(dataset_path),
        "top_k": report.top_k,
        "total_cases": report.total_cases,
        "hits": report.hits,
        "hit_rate": report.hit_rate,
        "min_hit_rate": min_hit_rate,
    }
    return report.hit_rate >= min_hit_rate, report_dict


def classify_chunk_file_name(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    doc_type = metadata.get("doc_type", "general")

    if doc_type == "law":
        return "regulation_chunks.jsonl"
    if doc_type in {"procedure", "allowed_industry", "employer_requirement"}:
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


def build_workforce_collection_records(
    chunks: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    collection_records: dict[str, list[dict[str, Any]]] = {
        "workforce_official": [],
        "workforce_templates": [],
    }
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if "workforce_agent" not in _as_list(metadata.get("mission_agent")):
            continue

        evidence_grade = str(metadata.get("evidence_grade", ""))
        source_type = str(metadata.get("source_type", ""))
        doc_type = str(metadata.get("doc_type", ""))
        source_unit_type = str(metadata.get("source_unit_type", ""))
        output_usage = _as_list(metadata.get("output_usage"))
        if evidence_grade in {"D", "F"} or doc_type == "case" or source_unit_type == "case_record":
            continue
        collection = ""
        if evidence_grade in {"A", "B"}:
            collection = "workforce_official"
        elif evidence_grade == "E" and (
            source_type in {"internal_template", "internal_checklist", "message_template"}
            or "template" in source_type
            or set(output_usage)
            & {
            "request_form",
            "handoff_question",
            "candidate_readiness_table",
            "additional_questions",
            }
        ):
            collection = "workforce_templates"
        if not collection:
            continue

        text = _build_workforce_embedding_text(chunk)
        enriched_metadata = dict(metadata)
        enriched_metadata["collection"] = collection
        collection_records[collection].append(
            {
                "id": chunk["chunk_id"],
                "text": text,
                "metadata": enriched_metadata,
                "embedding": deterministic_embedding(text),
            }
        )
    return collection_records


def _build_workforce_embedding_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    return "\n".join(
        [
            f"제목: {metadata.get('title', '')}",
            "업무: 신규 E-9 인력 확보",
            f"세부 에이전트: {', '.join(_as_list(metadata.get('sub_agent')))}",
            f"비자유형: {', '.join(_as_list(metadata.get('visa_type')))}",
            f"케이스유형: {', '.join(_as_list(metadata.get('case_type')))}",
            f"문서유형: {metadata.get('doc_type', '')}",
            f"사용처: {', '.join(_as_list(metadata.get('output_usage')))}",
            "",
            "내용:",
            str(chunk.get("text", "")),
        ]
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local RAG chunk JSONL files for Oegobanjang."
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when no source records are found.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build chunks and reports without writing processed chunk files.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a JSON ingestion quality report.",
    )
    parser.add_argument(
        "--include-demo-seed",
        action="store_true",
        default=_env_flag("DAILY_BRIEFING_INCLUDE_DEMO_SEED"),
        help="Include sample_policy_docs.jsonl demo seed records.",
    )
    parser.add_argument(
        "--eval-dataset",
        type=Path,
        help="Run retrieval eval gate against a dataset before writing chunks.",
    )
    parser.add_argument(
        "--min-hit-rate",
        type=float,
        default=DEFAULT_MIN_HIT_RATE,
        help="Minimum Hit@3 required when --eval-dataset is provided.",
    )

    args = parser.parse_args()

    if not args.dry_run:
        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks, raw_report = build_all_chunks(include_demo_seed=args.include_demo_seed)

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

    if args.report:
        print(json.dumps(raw_report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.eval_dataset:
        passed, eval_report = evaluate_chunk_gate(
            chunks=all_chunks,
            dataset_path=args.eval_dataset,
            min_hit_rate=args.min_hit_rate,
        )
        print(json.dumps({"eval_gate": eval_report}, ensure_ascii=False, indent=2, sort_keys=True))
        if not passed:
            print("RAG retrieval eval gate failed; processed chunks were not written.")
            return 1

    if args.dry_run:
        print(f"Dry run completed. Built {len(all_chunks)} chunks; no files were written.")
        return 0

    gap_report_path = PROCESSED_DIR / "workforce_source_gap_report.json"
    gap_report_path.write_text(
        json.dumps(
            {
                "workforce_metadata_coverage": raw_report.get("workforce_metadata_coverage", {}),
                "workforce_source_gaps": raw_report.get("workforce_source_gaps", []),
                "workforce_metadata_gap_count": raw_report.get("workforce_metadata_gap_count", 0),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    for file_name in expected_files:
        path = CHUNKS_DIR / file_name

        if file_name == "all_chunks.jsonl":
            count = write_jsonl(path, all_chunks)
        else:
            count = write_jsonl(path, grouped.get(file_name, []))

        print(f"Wrote {count:>4} chunks -> {path}")

    workforce_collections = build_workforce_collection_records(all_chunks)
    collection_file_names = {
        "workforce_official": "workforce_official_chroma_records.jsonl",
        "workforce_templates": "workforce_templates_chroma_records.jsonl",
    }
    for collection, file_name in collection_file_names.items():
        path = CHUNKS_DIR / file_name
        count = write_jsonl(path, workforce_collections.get(collection, []))
        print(f"Wrote {count:>4} records -> {path}")

    print("RAG chunk build completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
