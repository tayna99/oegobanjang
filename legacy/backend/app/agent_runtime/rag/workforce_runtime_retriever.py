from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb

from app.agent_runtime.rag.embeddings import deterministic_embedding


ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_WORKFORCE_CHROMA_DIR = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "workforce"


def retrieve_workforce_runtime_materials(
    *,
    query: str,
    case_type: str,
    sub_agent: str,
    visa_type: str = "E-9",
    industry: str | None = None,
    top_k: int = 5,
    persist_dir: Path = DEFAULT_WORKFORCE_CHROMA_DIR,
) -> dict[str, list[dict[str, Any]]]:
    _assert_chroma_runtime_backend()
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
            persist_dir=persist_dir,
            collection_name="workforce_official",
            query=_expanded_query(query, "official_procedure"),
            filters=official_filters,
            top_k=top_k,
        ),
        "allowed_industry": _query_collection(
            persist_dir=persist_dir,
            collection_name="workforce_official",
            query=_expanded_query(query, "allowed_industry"),
            filters=allowed_industry_filters,
            top_k=3,
        ),
        "internal_template": _query_collection(
            persist_dir=persist_dir,
            collection_name="workforce_templates",
            query=_expanded_query(query, "internal_template"),
            filters=template_filters,
            top_k=3,
        ),
    }


def _assert_chroma_runtime_backend() -> None:
    backend = os.getenv("WORKFORCE_RAG_RUNTIME_BACKEND", "chroma").strip().lower()
    if backend != "chroma":
        raise RuntimeError(
            "Workforce runtime retrieval supports Chroma only. "
            "JSONL/PolicyRetriever is offline/eval-only and cannot be used as a runtime fallback."
        )


def _query_collection(
    *,
    persist_dir: Path,
    collection_name: str,
    query: str,
    filters: dict[str, str],
    top_k: int,
) -> list[dict[str, Any]]:
    if not (persist_dir / "chroma.sqlite3").exists():
        return []

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    response = collection.query(
        query_embeddings=[_embed_query(query)],
        n_results=max(min(collection.count(), top_k * 20), top_k),
        include=["documents", "metadatas", "distances"],
    )
    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    results: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = dict(metadata or {})
        if not _matches_filters(metadata, filters):
            continue
        source_id = str(metadata.get("source_id") or item_id)
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        results.append({"id": item_id, "text": document, "metadata": metadata, "distance": distance})
    return _rerank_results(query, results)[:top_k]


def _matches_filters(metadata: dict[str, Any], filters: dict[str, str]) -> bool:
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


def _embed_query(query: str) -> list[float]:
    provider = os.getenv("WORKFORCE_RAG_EMBEDDING_PROVIDER", "deterministic").strip().lower()
    if provider == "auto":
        provider = "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "deterministic"
    if provider == "deterministic":
        return deterministic_embedding(query)
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when WORKFORCE_RAG_EMBEDDING_PROVIDER=openai.")
        from openai import OpenAI

        model = os.getenv("WORKFORCE_RAG_EMBEDDING_MODEL", "text-embedding-3-small").strip()
        response = OpenAI(api_key=api_key).embeddings.create(model=model, input=[query])
        return response.data[0].embedding
    raise RuntimeError(f"Unsupported WORKFORCE_RAG_EMBEDDING_PROVIDER: {provider}")


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
