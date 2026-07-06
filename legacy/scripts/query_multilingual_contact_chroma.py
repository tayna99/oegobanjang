#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PERSIST_DIR = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "multilingual_contact"
DEFAULT_COLLECTION_NAME = "multilingual_contact_docs"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TOP_K = 5

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


def is_truthy_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def is_truthy_false(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "false"
    return False


def metadata_text(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key, "")
    if value is None:
        return ""
    return str(value)


def contains_excluded_keyword(*values: str) -> bool:
    combined = "\n".join(values)
    return any(keyword in combined for keyword in EXCLUDED_KEYWORDS)


def is_unsafe_result(metadata: dict[str, Any], document: str) -> bool:
    raw_path = metadata_text(metadata, "raw_path")
    text = metadata_text(metadata, "text")
    context = metadata_text(metadata, "context")

    if contains_excluded_keyword(raw_path, text, context, document):
        return True

    if is_truthy_true(metadata.get("not_for_legal_basis")):
        return True

    if metadata.get("evidence_grade") == "F":
        return True

    if metadata.get("rag_domain") != RAG_DOMAIN:
        return True

    if metadata.get("owner_agent") != OWNER_AGENT:
        return True

    if metadata.get("ingest_target") is not True:
        return True

    return False


def create_query_embedding(query: str, *, model: str, api_key: str) -> list[float]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=query)
    return response.data[0].embedding


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query multilingual contact Chroma collection."
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--persist-dir", default=os.getenv("CHROMA_PERSIST_DIR"))
    parser.add_argument(
        "--collection-name",
        default=os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_COLLECTION_NAME),
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("MULTILINGUAL_CONTACT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )
    return parser.parse_args()


def resolve_persist_dir(value: str | None) -> Path:
    if not value:
        return DEFAULT_PERSIST_DIR

    path = Path(value)
    if path.is_absolute():
        return path

    return (ROOT_DIR / path).resolve()


def print_result(
    *,
    rank: int,
    distance: float | None,
    document: str,
    metadata: dict[str, Any],
) -> None:
    # Chroma document is contextual_text for retrieval. User-facing evidence uses
    # metadata.text and citation/source fields from metadata.
    print(f"[{rank}]")
    print(f"distance: {distance if distance is not None else ''}")
    print(f"chunk_id: {metadata_text(metadata, 'chunk_id')}")
    print(f"source_id: {metadata_text(metadata, 'source_id')}")
    print(f"title: {metadata_text(metadata, 'title')}")
    print(f"publisher: {metadata_text(metadata, 'publisher')}")
    print(f"doc_type: {metadata_text(metadata, 'doc_type')}")
    print(f"evidence_grade: {metadata_text(metadata, 'evidence_grade')}")
    print(f"language: {metadata_text(metadata, 'language')}")
    print(f"raw_path: {metadata_text(metadata, 'raw_path')}")
    print(f"page_number: {metadata_text(metadata, 'page_number')}")
    print("context:")
    print(metadata_text(metadata, "context"))
    print("text:")
    print(metadata_text(metadata, "text"))
    print()


def main() -> int:
    load_dotenv_without_override(ROOT_DIR / ".env")
    args = parse_args()

    query = args.query.strip()
    if not query:
        print("ERROR: --query is required.")
        return 1

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for Chroma query embedding.")
        return 1

    persist_dir = resolve_persist_dir(args.persist_dir)

    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb is not installed. Run uv sync first.")
        return 1

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        collection = client.get_collection(args.collection_name)
    except Exception:
        print(
            "ERROR: Chroma collection not found. "
            "Run scripts/index_multilingual_contact_chroma.py first."
        )
        return 1

    collection_count = collection.count()
    if collection_count == 0:
        print("ERROR: Chroma collection is empty. Run the index script first.")
        return 1

    query_embedding = create_query_embedding(
        query,
        model=args.embedding_model,
        api_key=api_key,
    )

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(args.top_k, 1),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    if not documents:
        print("ERROR: No search results found.")
        print("returned results: 0")
        print("filtered unsafe results: 0")
        print(f"collection count: {collection_count}")
        return 1

    returned = 0
    filtered = 0
    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        if is_unsafe_result(metadata, document or ""):
            filtered += 1
            continue

        returned += 1
        print_result(
            rank=returned,
            distance=distance,
            document=document or "",
            metadata=metadata,
        )

    if returned == 0:
        print("ERROR: No safe search results found.")

    print(f"returned results: {returned}")
    print(f"filtered unsafe results: {filtered}")
    print(f"collection count: {collection_count}")

    return 0 if returned > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
