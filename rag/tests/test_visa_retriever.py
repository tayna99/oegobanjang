"""비자서류 검색(search_visa_policy_documents) — legacy rag_hyunwook/retriever.py 이식.

조사 결과(2026-07-17): rag_hyunwook은 별도 코퍼스가 없고 workforce_official 컬렉션을
visa_type/evidence_grade flat 필터로 재조회한다. legacy는 D/F 등급을 런타임에서 자동
차단하지 않는 가드레일 공백이 있었다 — 이식본은 workforce_official이 색인 단계에서
이미 D/F를 배제하므로 구조적으로 D/F가 나올 수 없다(이 테스트로 그 불변식을 고정한다).

주의: workforce_official은 워크포스 에이전트가 공유하는 실 인덱스다(M5 eval 게이트가
의존). 여기서는 절대 reset/upsert하지 않고 읽기 전용으로만 검증한다 — `rag index`로
이미 색인된 실 데이터(E9_STAY_EXT_STEP1~3 등, evals/datasets/rag_retrieval_cases.jsonl과
동일 소스)를 전제로 한다.
"""

from __future__ import annotations

import pytest

from oe_rag.retriever import search_visa_policy_documents
from oe_rag.store.pgvector_store import read_manifest

pytestmark = pytest.mark.pgvector


@pytest.fixture(autouse=True)
def _require_workforce_official_indexed() -> None:
    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")


def test_search_finds_stay_extension_procedure_for_e9() -> None:
    # deterministic 임베딩은 의미가 아니라 토큰 중복 기반 해시라 lexical rerank 없이는
    # 어휘가 겹치는 질의여야 정확히 맞는다 — evals/datasets/rag_retrieval_cases.jsonl의
    # E9_STAY_EXT_STEP1 기준 질의(hit@3=1.0으로 검증된 문구)를 그대로 재사용한다.
    result = search_visa_policy_documents(
        "E-9 체류연장 절차 — 1단계: 신청 가능 기간 확인", visa_type="E-9", top_k=5
    )

    assert result.found is True
    assert result.reason is None
    source_ids = {doc["source_id"] for doc in result.documents}
    assert "E9_STAY_EXT_STEP1" in source_ids


def test_search_filters_by_visa_type() -> None:
    result = search_visa_policy_documents("체류 절차 안내", visa_type="E-9", top_k=10)

    for doc in result.documents:
        visa_types = doc["metadata"].get("visa_type", "")
        values = visa_types.split(",") if isinstance(visa_types, str) else visa_types
        assert "E-9" in values


def test_search_returns_no_results_for_unrelated_visa_type() -> None:
    result = search_visa_policy_documents(
        "완전히 무관한 임의 질의 xyz123", visa_type="F-2-9999-NONEXISTENT", top_k=5
    )

    assert result.found is False
    assert result.reason == "no_results"
    assert result.documents == []


def test_search_never_returns_low_grade_evidence() -> None:
    """workforce_official은 색인 단계에서 D/F를 이미 배제한다 — 구조적 불변식."""
    result = search_visa_policy_documents("체류 절차", top_k=20)

    for doc in result.documents:
        assert doc["metadata"]["evidence_grade"] not in {"D", "F"}


def test_citations_are_built_from_documents() -> None:
    result = search_visa_policy_documents(
        "체류기간 연장허가 신청 시 필요한 서류", visa_type="E-9", top_k=3
    )

    assert result.citations
    assert result.citations[0]["source_id"] == result.documents[0]["source_id"]
    assert result.citations[0]["evidence_grade"] in {"A", "B", "E"}


def test_search_returns_no_results_when_collection_unindexed(monkeypatch) -> None:
    import oe_rag.retriever as retriever_module

    monkeypatch.setattr(retriever_module, "read_manifest", lambda *_a, **_k: None)
    result = search_visa_policy_documents("아무 질의")

    assert result.found is False
    assert result.reason == "no_results"
