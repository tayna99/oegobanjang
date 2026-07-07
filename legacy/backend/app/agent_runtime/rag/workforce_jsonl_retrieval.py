from __future__ import annotations

from typing import Any

from .retriever import PolicyRetriever

"""
Offline workforce JSONL retriever.

This module is intentionally limited to evals, unit tests, and local debugging
against prepared JSONL chunks. Product runtime must use
workforce_runtime_retriever, which queries Chroma collections and does not
silently fall back to this PolicyRetriever path.
"""


def build_workforce_retrieval_filters(
    *,
    case_type: str,
    sub_agent: str,
    visa_type: str = "E-9",
) -> dict[str, dict[str, str]]:
    base = {
        "mission_agent": "workforce_agent",
        "sub_agent": sub_agent,
        "case_type": case_type,
        "visa_type": visa_type,
    }
    if case_type == "candidate_review":
        return {
            "readiness_checklist": {**base, "output_usage": "readiness_check"},
            "internal_template": {**base, "output_usage": "candidate_readiness_table"},
            "official_procedure": {**base, "output_usage": "requirement_check"},
        }
    return {
        "official_procedure": {**base, "output_usage": "requirement_check"},
        "allowed_industry": {**base, "source_unit_type": "allowed_industry"},
        "internal_template": {**base, "output_usage": "request_form"},
        "handoff_template": {**base, "output_usage": "handoff_question"},
    }


def retrieve_workforce_materials(
    query: str,
    *,
    chunks: list[dict[str, Any]],
    case_type: str,
    sub_agent: str,
    visa_type: str = "E-9",
    top_k: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    retriever = PolicyRetriever(chunks)
    filters_by_bucket = build_workforce_retrieval_filters(
        case_type=case_type,
        sub_agent=sub_agent,
        visa_type=visa_type,
    )
    return {
        bucket: retriever.search(_expanded_query(query, bucket), top_k=top_k, filters=filters, answer_evidence_only=True)
        for bucket, filters in filters_by_bucket.items()
    }


def _expanded_query(query: str, bucket: str) -> str:
    expansions = {
        "official_procedure": "고용허가 내국인 구인노력 신규 고용 절차",
        "allowed_industry": "E-9 허용업종 제조업 허용 범위",
        "internal_template": "신규 인력 요청서 템플릿",
        "handoff_template": "송출회사 행정사 확인 질문",
        "readiness_checklist": "후보 제출 준비도 여권 사진 건강검진 근무 가능일",
    }
    return f"{query} {expansions.get(bucket, '')}".strip()
