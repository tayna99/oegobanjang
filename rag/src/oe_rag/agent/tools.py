"""LangChain 1.x @tool — 워크포스 근거 검색 (legacy langchain_v1/tools.py 중 RAG 툴만 발췌 이식)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from ..embeddings import resolve_embedding_provider
from ..events import emit_rag_retrieved
from ..retriever import retrieve_workforce_runtime_materials
from ..store.pgvector_store import read_manifest

RUNTIME_COLLECTIONS = ("workforce_official", "workforce_templates")


class RuntimePreflightError(RuntimeError):
    pass


def preflight_pgvector() -> None:
    """런타임 기동 전 pgvector 컬렉션 존재·비어있지 않음 확인 (legacy preflight_chroma 이식)."""
    from ..store.pgvector_store import PgVectorIndex

    for collection_name in RUNTIME_COLLECTIONS:
        manifest = read_manifest(collection_name)
        if manifest is None:
            raise RuntimePreflightError(f"missing pgvector collection: {collection_name}")
        index = PgVectorIndex(
            collection_name,
            provider=manifest.provider,
            model=manifest.model,
            dimensions=manifest.dimensions,
        )
        try:
            if index.count() <= 0:
                raise RuntimePreflightError(f"empty pgvector collection: {collection_name}")
        finally:
            index.close()


@tool
def retrieve_workforce_materials(
    query: str,
    case_type: str = "new_hiring",
    sub_agent: str = "workforce_requirement_agent",
    visa_type: str = "E-9",
    top_k: int = 5,
) -> dict[str, Any]:
    """워크포스(신규 E-9 인력 확보) 공식 절차·허용업종·내부 템플릿 근거를 pgvector에서 검색합니다.

    근거 검색 전용입니다 — 비자 가부 판정·후보자 평가에 쓰지 마세요.
    """
    provider = resolve_embedding_provider(None)
    buckets = retrieve_workforce_runtime_materials(
        query=query,
        case_type=case_type,
        sub_agent=sub_agent,
        visa_type=visa_type,
        top_k=max(1, min(top_k, 10)),
        provider=provider,
    )
    evidence_log = emit_rag_retrieved(query=query, buckets=buckets)

    records: list[dict[str, Any]] = []
    for bucket_name, results in buckets.items():
        for result in results:
            metadata = dict(result.get("metadata") or {})
            evidence_grade = str(metadata.get("evidence_grade", ""))
            doc_type = str(metadata.get("doc_type", ""))
            source_unit_type = str(metadata.get("source_unit_type", ""))
            # 인덱스 생성 단계에서 이미 제외되지만 이중 방어한다
            if evidence_grade in {"D", "F"} or doc_type == "case" or source_unit_type == "case_record":
                continue
            records.append(
                {
                    "chunk_id": str(result.get("id", "")),
                    "source_id": str(metadata.get("source_id") or result.get("id") or ""),
                    "title": str(metadata.get("title", "")),
                    "doc_type": doc_type,
                    "source_unit_type": source_unit_type,
                    "evidence_grade": evidence_grade,
                    "bucket": bucket_name,
                    "distance": result.get("distance"),
                    "excerpt": str(result.get("text", ""))[:300],
                }
            )

    missing_evidence = not records
    return {
        "records": records,
        "retrieved_count": len(records),
        "missing_evidence": missing_evidence,
        "risk_flags": ["MISSING_EVIDENCE"] if missing_evidence else [],
        "evidence_log": evidence_log,
    }
