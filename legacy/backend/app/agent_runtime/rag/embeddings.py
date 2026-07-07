from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np
from langchain_openai import OpenAIEmbeddings

try:
    from app.config import get_settings
except ModuleNotFoundError:
    from backend.app.config import get_settings


def deterministic_embedding(text: str, *, dimensions: int = 64) -> list[float]:
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


@lru_cache(maxsize=1)
def get_embedding_model() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )
