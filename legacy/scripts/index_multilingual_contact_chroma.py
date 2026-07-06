#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT_DIR / "data-pipeline" / "processed" / "chunks" / "multilingual_contact" / "all_chunks.jsonl"
)
DEFAULT_PERSIST_DIR = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "multilingual_contact"
DEFAULT_COLLECTION_NAME = "multilingual_contact_docs"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_BATCH_SIZE = 100

RAG_DOMAIN = "multilingual_contact"
OWNER_AGENT = "multilingual_contact_agent"
EXCLUDED_KEYWORDS = (
    "worker_replies",
    "synthetic_cases",
    "public_cases",
    "templates",
    "synthetic_worker_reply",
    "public_case_patterns",
    "interview_case_patterns",
)
REQUIRED_TOP_LEVEL_FIELDS = (
    "chunk_id",
    "source_id",
    "text",
    "context",
    "contextual_text",
    "metadata",
)
REQUIRED_METADATA_FIELDS = (
    "source_id",
    "title",
    "publisher",
    "doc_type",
    "evidence_grade",
    "language",
    "raw_path",
    "file_type",
    "rag_domain",
    "owner_agent",
    "ingest_target",
)


def load_dotenv_without_override(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if not path.exists():
        return records, [{"line": 0, "reason": "input_file_missing", "path": str(path)}]

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append({"line": line_no, "reason": "json_parse_error", "error": str(e)})
            continue

        if not isinstance(record, dict):
            errors.append({"line": line_no, "reason": "json_line_not_object"})
            continue

        records.append(record)

    return records, errors


def is_truthy_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def text_contains_excluded_keyword(record: dict[str, Any]) -> bool:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    values = [
        str(metadata.get("raw_path", "")),
        str(record.get("text", "")),
        str(record.get("context", "")),
        str(record.get("contextual_text", "")),
    ]
    combined = "\n".join(values)
    return any(keyword in combined for keyword in EXCLUDED_KEYWORDS)


def validate_chunk(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []

    missing_top = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in record]
    if missing_top:
        reasons.append("missing_top_level_field")
        return reasons

    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        reasons.append("invalid_metadata")
        return reasons

    missing_metadata = [field for field in REQUIRED_METADATA_FIELDS if field not in metadata]
    if missing_metadata:
        reasons.append("invalid_metadata")

    text = record.get("text")
    context = record.get("context")
    contextual_text = record.get("contextual_text")
    if not isinstance(context, str) or not context.strip():
        reasons.append("missing_context")
    if not isinstance(contextual_text, str) or not contextual_text.strip():
        reasons.append("missing_contextual_text")
    if not isinstance(text, str) or not text.strip():
        reasons.append("missing_text")

    if isinstance(contextual_text, str) and isinstance(context, str) and isinstance(text, str):
        if context not in contextual_text or text not in contextual_text:
            reasons.append("contextual_text_invalid")
        if len(contextual_text) <= len(text):
            reasons.append("contextual_text_not_longer_than_text")

    if metadata.get("evidence_grade") == "F":
        reasons.append("excluded_evidence_grade")
    if is_truthy_true(metadata.get("not_for_legal_basis")):
        reasons.append("excluded_not_for_legal_basis")
    if metadata.get("ingest_target") is not True:
        reasons.append("missing_ingest_target")
    if metadata.get("rag_domain") != RAG_DOMAIN:
        reasons.append("wrong_rag_domain")
    if metadata.get("owner_agent") != OWNER_AGENT:
        reasons.append("wrong_owner_agent")
    if text_contains_excluded_keyword(record):
        reasons.append("excluded_path")

    return reasons


def serialize_metadata_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        if all(isinstance(item, (str, int, float, bool)) for item in value):
            return ",".join(str(item) for item in value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def build_chroma_metadata(record: dict[str, Any]) -> dict[str, str | int | float | bool]:
    metadata = record["metadata"]
    output: dict[str, Any] = {
        "chunk_id": record["chunk_id"],
        "source_id": record["source_id"],
        "text": record["text"],
        "context": record["context"],
        "title": metadata.get("title"),
        "publisher": metadata.get("publisher"),
        "doc_type": metadata.get("doc_type"),
        "evidence_grade": metadata.get("evidence_grade"),
        "language": metadata.get("language"),
        "use_case": metadata.get("use_case"),
        "raw_path": metadata.get("raw_path"),
        "file_type": metadata.get("file_type"),
        "page_number": metadata.get("page_number"),
        "rag_domain": metadata.get("rag_domain"),
        "owner_agent": metadata.get("owner_agent"),
        "not_for_legal_basis": metadata.get("not_for_legal_basis", False),
        "ingest_target": metadata.get("ingest_target"),
    }

    # MVP에서는 retriever 구현을 단순하게 하기 위해 text/context를 metadata에 함께 저장한다.
    # 향후 chunk 수나 metadata 크기가 문제가 되면 Chroma metadata에는 chunk_id/source/citation만
    # 저장하고, 원문 text/context는 별도 JSONL 또는 DB에서 chunk_id로 lookup한다.
    return {key: serialize_metadata_value(value) for key, value in output.items()}


def batched(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def create_embeddings(texts: list[str], *, model: str, api_key: str) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def index_chunks(
    chunks: list[dict[str, Any]],
    *,
    persist_dir: Path,
    collection_name: str,
    embedding_model: str,
    batch_size: int,
    reset: bool,
    api_key: str,
) -> int:
    import chromadb

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(name=collection_name)
    indexed = 0

    for batch in batched(chunks, batch_size):
        ids = [str(record["chunk_id"]) for record in batch]
        documents = [str(record["contextual_text"]) for record in batch]
        metadatas = [build_chroma_metadata(record) for record in batch]
        embeddings = create_embeddings(documents, model=embedding_model, api_key=api_key)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        indexed += len(batch)

    return indexed


def print_report(report: dict[str, Any]) -> None:
    print("Multilingual Contact Chroma index report:")
    print(f"  input file: {report['input_file']}")
    print(f"  total chunks read: {report['total_chunks_read']}")
    print(f"  valid chunks: {report['valid_chunks']}")
    print(f"  skipped chunks: {report['skipped_chunks']}")
    print(f"  indexed chunks: {report['indexed_chunks']}")
    print(f"  collection name: {report['collection_name']}")
    print(f"  persist dir: {report['persist_dir']}")
    print(f"  embedding model: {report['embedding_model']}")
    print(f"  dry-run: {report['dry_run']}")
    print(f"  reset: {report['reset']}")
    print(
        "  chunks with not_for_legal_basis=true: "
        f"{report['chunks_with_not_for_legal_basis_true']}"
    )
    print(
        "  skipped_not_for_legal_basis: "
        f"{report['skipped_reason_counts'].get('excluded_not_for_legal_basis', 0)}"
    )
    print("  skipped reason counts:")
    if not report["skipped_reason_counts"]:
        print("    none")
    else:
        for reason, count in sorted(report["skipped_reason_counts"].items()):
            print(f"    {reason}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index multilingual contact RAG chunks into Chroma."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--persist-dir", default=os.getenv("CHROMA_PERSIST_DIR"))
    parser.add_argument(
        "--collection-name",
        default=os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_COLLECTION_NAME),
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("MULTILINGUAL_CONTACT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args()


def main() -> int:
    load_dotenv_without_override(ROOT_DIR / ".env")
    args = parse_args()

    input_path = (ROOT_DIR / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    persist_dir_value = args.persist_dir or os.getenv("CHROMA_PERSIST_DIR")
    persist_dir = (
        (ROOT_DIR / persist_dir_value).resolve()
        if persist_dir_value and not Path(persist_dir_value).is_absolute()
        else Path(persist_dir_value or DEFAULT_PERSIST_DIR)
    )

    records, parse_errors = read_jsonl(input_path)
    skipped_reasons: Counter[str] = Counter()
    valid_chunks: list[dict[str, Any]] = []

    for error in parse_errors:
        skipped_reasons[str(error["reason"])] += 1

    for record in records:
        reasons = validate_chunk(record)
        if reasons:
            for reason in reasons:
                skipped_reasons[reason] += 1
            continue
        valid_chunks.append(record)

    chunks_with_not_for_legal_basis_true = sum(
        1
        for record in records
        if isinstance(record.get("metadata"), dict)
        and is_truthy_true(record["metadata"].get("not_for_legal_basis"))
    )

    report = {
        "input_file": input_path,
        "total_chunks_read": len(records),
        "valid_chunks": len(valid_chunks),
        "skipped_chunks": len(records) - len(valid_chunks) + len(parse_errors),
        "indexed_chunks": 0,
        "collection_name": args.collection_name,
        "persist_dir": persist_dir,
        "embedding_model": args.embedding_model,
        "dry_run": args.dry_run,
        "reset": args.reset,
        "chunks_with_not_for_legal_basis_true": chunks_with_not_for_legal_basis_true,
        "skipped_reason_counts": dict(skipped_reasons),
    }

    if args.dry_run:
        print_report(report)
        print("Dry run completed. No embeddings were created and no Chroma data was written.")
        return 0

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print_report(report)
        print("ERROR: OPENAI_API_KEY is required for actual Chroma indexing. Use --dry-run for validation without API calls.")
        return 1

    if parse_errors:
        print_report(report)
        print("ERROR: Input JSONL has parse errors. Fix the chunk file before indexing.")
        return 1

    indexed = index_chunks(
        valid_chunks,
        persist_dir=persist_dir,
        collection_name=args.collection_name,
        embedding_model=args.embedding_model,
        batch_size=args.batch_size,
        reset=args.reset,
        api_key=api_key,
    )
    report["indexed_chunks"] = indexed
    print_report(report)
    print("Multilingual Contact Chroma indexing completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
