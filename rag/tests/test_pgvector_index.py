"""PgVectorIndex 통합 테스트 — 실행 중인 pgvector PostgreSQL 필요 (marker: pgvector)."""

from __future__ import annotations

import pytest

from oe_rag.chunking import chunk_hash
from oe_rag.embeddings import DETERMINISTIC_DIMENSIONS, embed_query
from oe_rag.store.base import VectorRecord, flatten_metadata
from oe_rag.store.pgvector_store import (
    ManifestMismatchError,
    PgVectorIndex,
    open_index,
)

pytestmark = pytest.mark.pgvector

COLLECTION = "test_vectors_unit"


def _record(source_id: str, index: int, text: str, **metadata: object) -> VectorRecord:
    return VectorRecord(
        id=f"{source_id}_chunk_{index:04d}_{chunk_hash(text)}",
        text=text,
        metadata=flatten_metadata({"source_id": source_id, "title": source_id, **metadata}),
    )


@pytest.fixture()
def index() -> PgVectorIndex:
    idx = PgVectorIndex(
        COLLECTION,
        provider="deterministic",
        model=f"deterministic-sha256-{DETERMINISTIC_DIMENSIONS}d",
        dimensions=DETERMINISTIC_DIMENSIONS,
    )
    idx.ensure(reset=True)
    return idx


def _sample_records() -> list[VectorRecord]:
    return [
        _record("passport_doc", 0, "여권 사본 요청 및 증명사진 제출 안내", visa_type=["E-9"]),
        _record("safety_doc", 0, "안전교육 이수 및 안전표지 안내", visa_type=["E-9"]),
        _record("contract_doc", 0, "표준근로계약서 체결 절차", visa_type=["ALL"]),
    ]


def test_upsert_is_idempotent(index: PgVectorIndex) -> None:
    records = _sample_records()
    assert index.upsert(records) == 3
    assert index.count() == 3
    assert index.upsert(records) == 3
    assert index.count() == 3, "같은 id 재적재 시 개수가 늘면 안 된다 (멱등 upsert)"


def test_query_returns_nearest_by_token_overlap(index: PgVectorIndex) -> None:
    index.upsert(_sample_records())
    hits = index.query(embed_query("여권 사본 요청", provider="deterministic"), top_k=3)
    assert hits, "질의 결과가 비어 있으면 안 된다"
    assert hits[0].metadata["source_id"] == "passport_doc"
    assert hits[0].distance <= hits[-1].distance


def test_delete_source_removes_only_that_source(index: PgVectorIndex) -> None:
    index.upsert(_sample_records())
    deleted = index.delete_source("safety_doc")
    assert deleted == 1
    assert index.count() == 2
    remaining = {hit.metadata["source_id"] for hit in index.query([0.0] * DETERMINISTIC_DIMENSIONS, top_k=10)}
    assert "safety_doc" not in remaining


def test_query_dimension_mismatch_raises(index: PgVectorIndex) -> None:
    index.upsert(_sample_records())
    with pytest.raises(ManifestMismatchError):
        index.query([0.0] * 10, top_k=3)


def test_open_index_enforces_provider_manifest(index: PgVectorIndex) -> None:
    index.upsert(_sample_records())
    reopened = open_index(COLLECTION, provider="deterministic")
    assert reopened.count() == 3
    with pytest.raises(ManifestMismatchError):
        open_index(COLLECTION, provider="openai")
