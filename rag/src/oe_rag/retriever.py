"""워크포스 런타임 retriever — pgvector 3버킷 검색 + 어휘 재랭킹.

legacy rag/workforce_runtime_retriever.py 이식. 스토어 호출부만 VectorIndex(pgvector)로
교체했고 필터·쿼리 확장·재랭킹·dedup 로직은 동일하다.

런타임 경계(RAG_STRATEGY §8): 런타임 검색은 벡터 스토어만 사용한다.
JSONL/PolicyRetriever는 오프라인·평가 전용이며 런타임 fallback으로 쓸 수 없다.
"""

from __future__ import annotations

import os
from typing import Any

from .embeddings import embed_query, resolve_embedding_provider
from .store.base import matches_filters
from .store.pgvector_store import ManifestMismatchError, PgVectorIndex, open_index, read_manifest

_INDEX_CACHE: dict[tuple[str, str], PgVectorIndex] = {}


def retrieve_workforce_runtime_materials(
    *,
    query: str,
    case_type: str,
    sub_agent: str,
    visa_type: str = "E-9",
    industry: str | None = None,
    top_k: int = 5,
    provider: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    _assert_pgvector_runtime_backend()
    resolved_provider = resolve_embedding_provider(provider)
    filters = {
        "mission_agent": "workforce_agent",
        "visa_type": visa_type,
        "case_type": case_type,
    }
    if industry:
        filters["industry"] = industry
    official_filters = {**filters, "source_unit_type": "procedure_step"}
    allowed_industry_filters = {**filters, "source_unit_type": "allowed_industry"}
    template_filters = {
        "mission_agent": "workforce_agent",
        "case_type": case_type,
        "evidence_grade": "E",
    }
    if sub_agent:
        template_filters["sub_agent"] = sub_agent

    return {
        "official_procedure": _query_collection(
            collection_name="workforce_official",
            query=_expanded_query(query, "official_procedure"),
            filters=official_filters,
            top_k=top_k,
            provider=resolved_provider,
        ),
        "allowed_industry": _query_collection(
            collection_name="workforce_official",
            query=_expanded_query(query, "allowed_industry"),
            filters=allowed_industry_filters,
            top_k=3,
            provider=resolved_provider,
        ),
        "internal_template": _query_collection(
            collection_name="workforce_templates",
            query=_expanded_query(query, "internal_template"),
            filters=template_filters,
            top_k=3,
            provider=resolved_provider,
        ),
    }


def close_indexes() -> None:
    """캐시된 인덱스의 PGEngine 커넥션 풀 정리 (CLI 종료 경로에서 호출)."""
    for index in _INDEX_CACHE.values():
        index.close()
    _INDEX_CACHE.clear()


def _assert_pgvector_runtime_backend() -> None:
    backend = os.getenv("WORKFORCE_RAG_RUNTIME_BACKEND", "pgvector").strip().lower()
    if backend != "pgvector":
        raise RuntimeError(
            "Workforce runtime retrieval supports pgvector only. "
            "JSONL/PolicyRetriever is offline/eval-only and cannot be used as a runtime fallback."
        )


def _open_cached_index(collection_name: str, provider: str) -> PgVectorIndex | None:
    key = (collection_name, provider)
    if key in _INDEX_CACHE:
        return _INDEX_CACHE[key]
    if read_manifest(collection_name) is None:
        # 아직 색인되지 않은 컬렉션 — legacy가 인덱스 부재 시 빈 결과를 돌려주던 계약 유지
        return None
    index = open_index(collection_name, provider=provider)
    _INDEX_CACHE[key] = index
    return index


def _query_collection(
    *,
    collection_name: str,
    query: str,
    filters: dict[str, str],
    top_k: int,
    provider: str,
) -> list[dict[str, Any]]:
    try:
        index = _open_cached_index(collection_name, provider)
    except ManifestMismatchError:
        raise
    if index is None:
        return []

    total = index.count()
    if total == 0:
        return []
    candidate_count = max(min(total, top_k * 20), top_k)
    hits = index.query(embed_query(query, provider=provider), top_k=candidate_count)

    results: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for hit in hits:
        metadata = dict(hit.metadata or {})
        if not matches_filters(metadata, filters):
            continue
        source_id = str(metadata.get("source_id") or hit.id)
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        results.append({"id": hit.id, "text": hit.text, "metadata": metadata, "distance": hit.distance})
    return _rerank_results(query, results)[:top_k]


def _expanded_query(query: str, bucket: str) -> str:
    expansions = {
        "official_procedure": "E-9 신규 고용 절차 사업주 고용절차 내국인 구인노력 고용허가 신청 근로계약 사증발급인정서",
        "allowed_industry": "E-9 허용업종 제조업 농축산업 어업 건설업 서비스업",
        "internal_template": "신규 인력 요청서 송출회사 행정사 확인 질문 후보 준비도 체크리스트",
    }
    return f"{query} {expansions.get(bucket, '')}".strip()


def _rerank_results(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        results,
        key=lambda result: (
            -_lexical_score(query, result),
            float(result.get("distance") or 0.0),
        ),
    )


def _lexical_score(query: str, result: dict[str, Any]) -> int:
    metadata = dict(result.get("metadata") or {})
    source_id = str(metadata.get("source_id") or result.get("id") or "")
    haystack = " ".join(
        [
            source_id,
            str(metadata.get("title", "")),
            str(metadata.get("source_unit_type", "")),
            str(metadata.get("doc_type", "")),
            str(result.get("text", "")),
        ]
    )
    score = 0
    for token in _query_tokens(query):
        if token and token in haystack:
            score += 1
    phrase_boosts = [
        (("더 뽑", "절차"), "E9_NEW_HIRING_OVERVIEW", 8),
        (("신규", "사업주"), "E9_NEW_HIRING_OVERVIEW", 10),
        (("사업주", "먼저"), "E9_NEW_HIRING_OVERVIEW", 10),
        (("신규", "절차"), "E9_NEW_HIRING_OVERVIEW", 4),
        (("확인", "항목"), "workforce_company_requirements", 8),
        (("사업장", "정보"), "workforce_request_company_fields", 10),
        (("필드",), "workforce_request_company_fields", 8),
        (("내국인", "구인노력"), "E9_EMPLOYER_STEP_NATIVE_RECRUITMENT", 30),
        (("고용허가서",), "E9_EMPLOYER_STEP_WORK_PERMIT_APPLICATION", 18),
        (("발급", "신청"), "E9_EMPLOYER_STEP_WORK_PERMIT_APPLICATION", 14),
        (("근로계약",), "E9_EMPLOYER_STEP_LABOR_CONTRACT", 22),
        (("사증발급",), "E9_EMPLOYER_STEP_CCVI_APPLICATION", 30),
        (("요청서", "정보"), "workforce_request_template", 12),
        (("채용", "요청서"), "workforce_request_template", 12),
        (("송출회사", "질문"), "handoff_questions_template", 10),
        (("후보군", "질문"), "handoff_questions_template", 16),
        (("성실",), "candidate_forbidden_policy", 12),
        (("네팔", "베트남"), "candidate_forbidden_policy", 12),
        (("오래", "추천"), "candidate_forbidden_policy", 12),
        (("좋은 사람",), "candidate_forbidden_policy", 12),
        (("이탈",), "candidate_forbidden_policy", 12),
        (("여권",), "candidate_readiness_checklist", 5),
        (("사진",), "candidate_readiness_checklist", 5),
        (("주야 2교대",), "candidate_readiness_checklist", 5),
    ]
    for required_tokens, boosted_source_id, boost in phrase_boosts:
        if all(token in query for token in required_tokens) and source_id == boosted_source_id:
            score += boost
    return score


def _query_tokens(query: str) -> list[str]:
    separators = [" ", "\n", "\t", ",", ".", "?", "!", "/", "·", "-", "_"]
    tokens = [query]
    for separator in separators:
        next_tokens: list[str] = []
        for token in tokens:
            next_tokens.extend(token.split(separator))
        tokens = next_tokens
    return [token.strip() for token in tokens if len(token.strip()) >= 2]
