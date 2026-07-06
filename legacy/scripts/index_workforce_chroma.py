#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_CHUNKS_DIR = ROOT_DIR / "data-pipeline" / "processed" / "chunks"
DEFAULT_PERSIST_DIR = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "workforce"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent_runtime.rag.embeddings import deterministic_embedding


COLLECTION_FILES = {
    "workforce_official": "workforce_official_chroma_records.jsonl",
    "workforce_templates": "workforce_templates_chroma_records.jsonl",
}


@dataclass(frozen=True)
class EmbeddingProvider:
    name: str
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.name == "deterministic":
            return [deterministic_embedding(text) for text in texts]
        if self.name == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
            response = client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        raise RuntimeError(f"Unsupported embedding provider: {self.name}")


def select_embedding_provider(*, provider_name: str = "auto", model: str = "text-embedding-3-small") -> EmbeddingProvider:
    requested = provider_name.strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if requested == "auto":
        return EmbeddingProvider(name="openai" if api_key else "deterministic", model=model)
    if requested == "deterministic":
        return EmbeddingProvider(name="deterministic", model=model)
    if requested == "openai":
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when --embedding-provider openai is used.")
        return EmbeddingProvider(name="openai", model=model)
    raise RuntimeError(f"Unsupported embedding provider: {provider_name}")


def load_workforce_collection_records(chunks_dir: Path) -> dict[str, list[dict[str, Any]]]:
    collections: dict[str, list[dict[str, Any]]] = {}
    for collection_name, file_name in COLLECTION_FILES.items():
        path = chunks_dir / file_name
        records: list[dict[str, Any]] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    raw = line.strip()
                    if not raw:
                        continue
                    record = json.loads(raw)
                    _validate_record(record, path=path, line_no=line_no, collection_name=collection_name)
                    records.append(record)
        collections[collection_name] = records
    return collections


def index_workforce_collections(
    *,
    chunks_dir: Path,
    persist_dir: Path,
    reset: bool = False,
    embedding_provider: EmbeddingProvider | None = None,
) -> dict[str, Any]:
    import chromadb

    collections = load_workforce_collection_records(chunks_dir)
    provider = embedding_provider or select_embedding_provider(provider_name="deterministic")
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    report: dict[str, Any] = {
        "chunks_dir": str(chunks_dir),
        "persist_dir": str(persist_dir),
        "embedding_provider": provider.name,
        "embedding_model": provider.model,
        "collections": {},
        "reset": reset,
    }

    for collection_name, records in collections.items():
        if reset:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass
        collection = client.get_or_create_collection(name=collection_name)
        if records:
            documents = [str(record["text"]) for record in records]
            collection.upsert(
                ids=[str(record["id"]) for record in records],
                documents=documents,
                embeddings=provider.embed(documents) if provider.name != "deterministic" else [record["embedding"] for record in records],
                metadatas=[_chroma_metadata(record.get("metadata", {})) for record in records],
            )
        report["collections"][collection_name] = {
            "input_records": len(records),
            "indexed_records": collection.count(),
        }
    return report


def query_workforce_collection(
    *,
    persist_dir: Path,
    collection_name: str,
    query: str,
    filters: dict[str, str] | None = None,
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[dict[str, Any]]:
    import chromadb

    provider = embedding_provider or select_embedding_provider(provider_name="deterministic")
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_collection(name=collection_name)
    candidate_count = max(top_k * 5, top_k)
    response = collection.query(
        query_embeddings=[provider.embed([query])[0]],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]
    results: list[dict[str, Any]] = []
    for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = dict(metadata or {})
        if filters and not _matches_filter_metadata(metadata, filters):
            continue
        results.append(
            {
                "id": item_id,
                "text": document,
                "metadata": metadata,
                "distance": distance,
            }
        )
        if len(results) >= top_k:
            break
    return results


def _validate_record(record: dict[str, Any], *, path: Path, line_no: int, collection_name: str) -> None:
    missing = [field for field in ("id", "text", "embedding", "metadata") if field not in record]
    if missing:
        raise ValueError(f"{path}:{line_no} missing fields: {', '.join(missing)}")
    if record.get("metadata", {}).get("collection") != collection_name:
        raise ValueError(f"{path}:{line_no} collection mismatch")
    if not isinstance(record["embedding"], list) or not record["embedding"]:
        raise ValueError(f"{path}:{line_no} embedding must be non-empty list")


def _chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    output: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool | int | float | str):
            output[key] = value
        elif isinstance(value, list):
            output[key] = ",".join(str(item) for item in value)
        else:
            output[key] = json.dumps(value, ensure_ascii=False)
    return output


def _matches_filter_metadata(metadata: dict[str, Any], filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual == expected:
            continue
        if isinstance(actual, str):
            values = [item.strip() for item in actual.split(",") if item.strip()]
            if expected in values or "ALL" in values:
                continue
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Index workforce RAG collections into local Chroma.")
    parser.add_argument("--chunks-dir", type=Path, default=DEFAULT_CHUNKS_DIR)
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--embedding-provider",
        choices=["auto", "deterministic", "openai"],
        default="deterministic",
        help="deterministic is the offline default; openai requires OPENAI_API_KEY.",
    )
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    args = parser.parse_args()

    collections = load_workforce_collection_records(args.chunks_dir)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "chunks_dir": str(args.chunks_dir),
                    "persist_dir": str(args.persist_dir),
                    "collections": {name: len(records) for name, records in collections.items()},
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    provider = select_embedding_provider(provider_name=args.embedding_provider, model=args.embedding_model)
    report = index_workforce_collections(
        chunks_dir=args.chunks_dir,
        persist_dir=args.persist_dir,
        reset=args.reset,
        embedding_provider=provider,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
