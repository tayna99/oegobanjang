"""pgvector 인덱스 구현 — langchain-postgres PGVectorStore 기반.

- 전용 PG 스키마 `rag` 사용: 정본 db/schema.sql(앱 상태)과 분리 (RAG=근거 검색 경계)
- 컬렉션당 테이블 1개, id는 TEXT(chunk_id = {source_id}_chunk_{idx}_{hash8})
- rag.index_manifest에 provider/model/dimensions 기록 — 색인과 질의는 같은 provider여야
  한다는 RAG_STRATEGY 계약을 코드로 강제
- 멱등 upsert: 동일 id 선삭제 후 add — 스토어 구현의 conflict 시맨틱에 의존하지 않음
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import Any

import sqlalchemy
from langchain_core.embeddings import Embeddings
from langchain_postgres import Column, PGEngine, PGVectorStore

# Windows 기본 ProactorEventLoop에서는 psycopg 비동기가 동작하지 않는다.
# PGEngine이 백그라운드 이벤트 루프를 만들기 전에 Selector 정책으로 전환한다.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from ..config import pg_url
from ..embeddings import embed_query, embed_texts
from .base import VectorHit, VectorRecord

SCHEMA = "rag"
MANIFEST_TABLE = "index_manifest"


class ProviderEmbeddings(Embeddings):
    """oe_rag.embeddings의 provider 스위치를 LangChain Embeddings 인터페이스로 노출."""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, provider=self.provider)

    def embed_query(self, text: str) -> list[float]:
        return embed_query(text, provider=self.provider)


@dataclass(frozen=True)
class IndexManifest:
    collection: str
    provider: str
    model: str
    dimensions: int


class ManifestMismatchError(RuntimeError):
    pass


def _sync_engine(url: str) -> sqlalchemy.Engine:
    return sqlalchemy.create_engine(url)


def _ensure_schema_and_manifest(engine: sqlalchemy.Engine) -> None:
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        conn.execute(
            sqlalchemy.text(
                f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA}.{MANIFEST_TABLE} (
                    collection TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    dimensions INT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )


def read_manifest(collection: str, *, url: str | None = None) -> IndexManifest | None:
    engine = _sync_engine(url or pg_url())
    try:
        _ensure_schema_and_manifest(engine)
        with engine.connect() as conn:
            row = conn.execute(
                sqlalchemy.text(
                    f"SELECT collection, provider, model, dimensions FROM {SCHEMA}.{MANIFEST_TABLE} WHERE collection = :c"
                ),
                {"c": collection},
            ).fetchone()
        if row is None:
            return None
        return IndexManifest(collection=row[0], provider=row[1], model=row[2], dimensions=row[3])
    finally:
        engine.dispose()


def assert_provider_matches(collection: str, provider: str, *, url: str | None = None) -> IndexManifest:
    manifest = read_manifest(collection, url=url)
    if manifest is None:
        raise ManifestMismatchError(
            f"Collection '{collection}' has no index manifest. Run `rag index` first."
        )
    if manifest.provider != provider:
        raise ManifestMismatchError(
            f"Collection '{collection}' was indexed with provider '{manifest.provider}' "
            f"but query uses '{provider}'. 색인과 질의는 같은 provider여야 합니다 (--reset 후 재색인)."
        )
    return manifest


class PgVectorIndex:
    def __init__(
        self,
        collection: str,
        *,
        provider: str,
        model: str,
        dimensions: int,
        url: str | None = None,
    ) -> None:
        self.collection = collection
        self.provider = provider
        self.model = model
        self.dimensions = dimensions
        self._url = url or pg_url()
        self._pg_engine: PGEngine | None = None
        self._store: PGVectorStore | None = None

    # -- 초기화 ---------------------------------------------------------------

    def ensure(self, *, reset: bool = False) -> None:
        engine = _sync_engine(self._url)
        try:
            _ensure_schema_and_manifest(engine)
            if reset:
                with engine.begin() as conn:
                    conn.execute(
                        sqlalchemy.text(f'DROP TABLE IF EXISTS {SCHEMA}."{self.collection}"')
                    )
                    conn.execute(
                        sqlalchemy.text(
                            f"DELETE FROM {SCHEMA}.{MANIFEST_TABLE} WHERE collection = :c"
                        ),
                        {"c": self.collection},
                    )
            exists = engine.dialect.has_table(
                engine.connect(), self.collection, schema=SCHEMA
            )
            if not exists:
                self._engine().init_vectorstore_table(
                    table_name=self.collection,
                    vector_size=self.dimensions,
                    schema_name=SCHEMA,
                    id_column=Column("langchain_id", "TEXT"),
                )
            with engine.begin() as conn:
                conn.execute(
                    sqlalchemy.text(
                        f"""
                        INSERT INTO {SCHEMA}.{MANIFEST_TABLE} (collection, provider, model, dimensions)
                        VALUES (:c, :p, :m, :d)
                        ON CONFLICT (collection) DO UPDATE
                        SET provider = :p, model = :m, dimensions = :d, updated_at = now()
                        """
                    ),
                    {"c": self.collection, "p": self.provider, "m": self.model, "d": self.dimensions},
                )
        finally:
            engine.dispose()

    def _engine(self) -> PGEngine:
        if self._pg_engine is None:
            self._pg_engine = PGEngine.from_connection_string(url=self._url)
        return self._pg_engine

    def _vector_store(self) -> PGVectorStore:
        if self._store is None:
            self._store = PGVectorStore.create_sync(
                engine=self._engine(),
                embedding_service=ProviderEmbeddings(self.provider),
                table_name=self.collection,
                schema_name=SCHEMA,
            )
        return self._store

    # -- VectorIndex 프로토콜 ---------------------------------------------------

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        ids = [record.id for record in records]
        engine = _sync_engine(self._url)
        try:
            with engine.begin() as conn:
                conn.execute(
                    sqlalchemy.text(
                        f'DELETE FROM {SCHEMA}."{self.collection}" WHERE langchain_id = ANY(:ids)'
                    ),
                    {"ids": ids},
                )
        finally:
            engine.dispose()
        self._vector_store().add_texts(
            texts=[record.text for record in records],
            metadatas=[dict(record.metadata) for record in records],
            ids=ids,
        )
        return len(records)

    def delete_source(self, source_id: str) -> int:
        engine = _sync_engine(self._url)
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    sqlalchemy.text(
                        f'DELETE FROM {SCHEMA}."{self.collection}" '
                        "WHERE langchain_metadata->>'source_id' = :sid"
                    ),
                    {"sid": source_id},
                )
            return int(result.rowcount or 0)
        finally:
            engine.dispose()

    def query(self, embedding: list[float], top_k: int) -> list[VectorHit]:
        if len(embedding) != self.dimensions:
            raise ManifestMismatchError(
                f"Query embedding has {len(embedding)} dims but collection "
                f"'{self.collection}' expects {self.dimensions} ({self.provider})."
            )
        results = self._vector_store().similarity_search_with_score_by_vector(
            embedding=embedding, k=top_k
        )
        hits: list[VectorHit] = []
        for document, score in results:
            metadata = dict(document.metadata or {})
            hits.append(
                VectorHit(
                    id=str(document.id or metadata.get("source_id") or ""),
                    text=document.page_content,
                    metadata=metadata,
                    distance=float(score),
                )
            )
        return hits

    def count(self) -> int:
        engine = _sync_engine(self._url)
        try:
            with engine.connect() as conn:
                value = conn.execute(
                    sqlalchemy.text(f'SELECT COUNT(*) FROM {SCHEMA}."{self.collection}"')
                ).scalar()
            return int(value or 0)
        finally:
            engine.dispose()

    def close(self) -> None:
        """PGEngine 커넥션 풀 정리 — 미정리 시 프로세스가 비정상 종료 코드를 남긴다.

        PGEngine.close()는 코루틴이라 동기 경로에서는 내부 sync 러너로 실행한다.
        """
        if self._pg_engine is not None:
            self._pg_engine._run_as_sync(self._pg_engine._pool.dispose())
            self._pg_engine = None
            self._store = None


def open_index(collection: str, *, provider: str, url: str | None = None) -> PgVectorIndex:
    """질의 경로 진입점 — manifest의 provider 일치를 강제한 뒤 인덱스를 연다."""
    manifest = assert_provider_matches(collection, provider, url=url)
    return PgVectorIndex(
        collection,
        provider=manifest.provider,
        model=manifest.model,
        dimensions=manifest.dimensions,
        url=url,
    )
