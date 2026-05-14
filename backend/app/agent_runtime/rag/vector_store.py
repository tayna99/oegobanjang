from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma

try:
    from app.config import get_settings
except ModuleNotFoundError:
    from backend.app.config import get_settings

from .chunking import write_chunks_jsonl
from .embeddings import deterministic_embedding, get_embedding_model


CHROMA_COLLECTION_NAME = "foreign_hiring"


def build_chroma_ready_records(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        records.append(
            {
                "id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": deterministic_embedding(chunk["text"]),
            }
        )
    return records


def write_chroma_jsonl(chunks: list[dict[str, Any]], path: str | Path) -> Path:
    return write_chunks_jsonl(build_chroma_ready_records(chunks), path)


@lru_cache(maxsize=1)
def get_chroma_store() -> Chroma:
    settings = get_settings()
    persist_directory = os.path.abspath(settings.normalized_chroma_persist_directory)
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=persist_directory,
    )
