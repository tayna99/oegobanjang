from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np

DETERMINISTIC_DIMENSIONS = 64
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_DIMENSIONS = 1536

# legacy와 동일한 환경변수 계약: deterministic | openai | auto
EMBEDDING_PROVIDER_ENV = "WORKFORCE_RAG_EMBEDDING_PROVIDER"


def deterministic_embedding(text: str, *, dimensions: int = DETERMINISTIC_DIMENSIONS) -> list[float]:
    """Local deterministic embedding for tests and offline MVP indexing."""
    vector = np.zeros(dimensions, dtype=float)
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % dimensions
        vector[index] += 1.0

    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector.tolist()
    return (vector / norm).tolist()


def resolve_embedding_provider(explicit: str | None = None) -> str:
    provider = (explicit or os.getenv(EMBEDDING_PROVIDER_ENV, "deterministic")).strip().lower()
    if provider == "auto":
        return "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "deterministic"
    if provider == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is required when embedding provider is 'openai'.")
    if provider not in {"deterministic", "openai"}:
        raise ValueError(f"Unknown embedding provider: {provider}")
    return provider


def embedding_dimensions(provider: str) -> int:
    return OPENAI_DIMENSIONS if provider == "openai" else DETERMINISTIC_DIMENSIONS


@lru_cache(maxsize=1)
def get_embedding_model():
    from langchain_openai import OpenAIEmbeddings

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the openai embedding provider")
    return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=api_key)


def embed_texts(texts: list[str], *, provider: str) -> list[list[float]]:
    if provider == "openai":
        return get_embedding_model().embed_documents(texts)
    return [deterministic_embedding(text) for text in texts]


def embed_query(text: str, *, provider: str) -> list[float]:
    if provider == "openai":
        return get_embedding_model().embed_query(text)
    return deterministic_embedding(text)
