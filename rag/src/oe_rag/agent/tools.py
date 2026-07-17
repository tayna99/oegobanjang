"""LangChain 1.x @tool — 워크포스 근거 검색 (legacy langchain_v1/tools.py 중 RAG 툴만 발췌 이식)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from ..embeddings import resolve_embedding_provider
from ..events import emit_rag_retrieved
from ..multilingual import search_multilingual_contact_docs
from ..retriever import retrieve_workforce_runtime_materials, search_visa_policy_documents
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


@tool
def search_policy_documents(
    query: str,
    visa_type: str = "",
    evidence_grade: str = "",
    top_k: int = 5,
) -> dict[str, Any]:
    """비자·체류 절차(체류연장·사업장변경·법령 등) 근거를 pgvector에서 검색합니다.

    근거 검색 전용입니다 — 비자 가능/불가능 여부를 확정하지 마세요.
    evidence_grade가 D/F인 근거는 구조적으로 반환되지 않습니다.
    """
    provider = resolve_embedding_provider(None)
    result = search_visa_policy_documents(
        query,
        visa_type=visa_type or None,
        evidence_grade=evidence_grade or None,
        top_k=max(1, min(top_k, 10)),
        provider=provider,
    )
    buckets = {"official_procedure": result.documents}
    evidence_log = emit_rag_retrieved(query=query, buckets=buckets)

    return {
        "found": result.found,
        "records": result.documents,
        "citations": result.citations,
        "retrieved_count": len(result.documents),
        "missing_evidence": not result.found,
        "risk_flags": ["MISSING_EVIDENCE"] if not result.found else [],
        "reason": result.reason,
        "evidence_log": evidence_log,
    }


@tool
def search_multilingual_contact_materials(
    query: str,
    intent: str = "",
    language_code: str = "",
    top_k: int = 5,
) -> dict[str, Any]:
    """다국어 근로자 컨택용 공식 안내(상담센터·안전교육·생활안내·공지) 근거를 검색합니다.

    intent는 counseling|safety|life|notice 중 하나(생략 시 질의에서 추론),
    language_code는 vi|id(생략 시 질의에서 추론). 번역·발송은 이 툴의 역할이 아닙니다 —
    근거 검색 전용입니다.
    """
    results = search_multilingual_contact_docs(
        query,
        top_k=max(1, min(top_k, 10)),
        language_code=language_code or None,
        intent=intent or None,
    )
    buckets = {"multilingual_contact": results}
    evidence_log = emit_rag_retrieved(query=query, buckets=buckets)

    records = [
        {
            "chunk_id": str(result.get("id", "")),
            "source_id": str(result["metadata"].get("source_id", "")),
            "title": str(result["metadata"].get("title", "")),
            "doc_type": str(result["metadata"].get("doc_type", "")),
            "evidence_grade": str(result["metadata"].get("evidence_grade", "")),
            "matched_intent": result.get("matched_intent"),
            "matched_language": result.get("matched_language"),
            "score": result.get("score"),
            "excerpt": str(result.get("text", ""))[:300],
        }
        for result in results
    ]
    missing_evidence = not records
    return {
        "records": records,
        "retrieved_count": len(records),
        "missing_evidence": missing_evidence,
        "risk_flags": ["MISSING_EVIDENCE"] if missing_evidence else [],
        "evidence_log": evidence_log,
    }
