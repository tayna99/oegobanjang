"""다국어 컨택 retriever — 순수 함수(intent/언어 추론·부스팅) + pgvector 통합."""

from __future__ import annotations

import pytest

from oe_rag.multilingual import (
    MULTILINGUAL_COLLECTION,
    compute_boosted_score,
    infer_intent,
    infer_language_code,
    search_multilingual_contact_docs,
)
from oe_rag.store.base import VectorRecord, flatten_metadata
from oe_rag.store.pgvector_store import PgVectorIndex


def test_infer_intent_from_explicit_value() -> None:
    assert infer_intent("아무 질문", intent="safety") == "safety"


def test_infer_intent_from_keyword() -> None:
    assert infer_intent("상담센터 전화번호가 뭐예요?") == "counseling"
    assert infer_intent("안전교육은 언제 받나요?") == "safety"
    assert infer_intent("숙소 관련 문의입니다") == "life"
    assert infer_intent("아무 관련 없는 문장") is None


def test_infer_language_code_from_keyword() -> None:
    assert infer_language_code("tiếng việt로 안내해주세요") == "vi"
    assert infer_language_code("bahasa indonesia 안내") == "id"
    assert infer_language_code("한국어로만") is None


def test_compute_boosted_score_rewards_matching_doc_type_and_language() -> None:
    base_metadata = {"doc_type": "counseling", "language": "ko,vi", "title": "", "publisher": ""}
    baseline = compute_boosted_score(1.0, base_metadata, intent=None, language_code=None)
    with_intent = compute_boosted_score(1.0, base_metadata, intent="counseling", language_code=None)
    with_language = compute_boosted_score(1.0, base_metadata, intent=None, language_code="vi")

    assert with_intent < baseline
    assert with_language < baseline


def test_compute_boosted_score_counseling_keyword_boost() -> None:
    metadata = {"doc_type": "counseling", "language": "ko", "title": "상담센터 1577-0071", "publisher": "HRDK"}
    boosted = compute_boosted_score(1.0, metadata, intent="counseling", language_code=None)
    plain = compute_boosted_score(1.0, {**metadata, "title": "", "publisher": ""}, intent="counseling", language_code=None)
    assert boosted < plain


@pytest.mark.pgvector
class TestMultilingualRetrievalIntegration:
    COLLECTION = MULTILINGUAL_COLLECTION

    @pytest.fixture(autouse=True)
    def _seed_index(self, monkeypatch):
        monkeypatch.setenv("WORKFORCE_RAG_EMBEDDING_PROVIDER", "deterministic")
        index = PgVectorIndex(self.COLLECTION, provider="deterministic", model="deterministic-sha256-64d", dimensions=64)
        index.ensure(reset=True)
        records = [
            VectorRecord(
                id="counseling_chunk_0000_aaaa1111",
                text="상담센터 대표번호는 1577-0071이다. 다국어 상담이 가능하다.",
                metadata=flatten_metadata(
                    {
                        "source_id": "counseling_doc",
                        "title": "상담센터 안내",
                        "doc_type": "counseling",
                        "evidence_grade": "B",
                        "language": ["ko", "vi"],
                        "rag_domain": "multilingual_contact",
                        "owner_agent": "multilingual_contact_agent",
                        "ingest_target": True,
                        "not_for_legal_basis": False,
                    }
                ),
            ),
            VectorRecord(
                id="safety_chunk_0000_bbbb2222",
                text="안전교육은 작업 전 필수로 이수해야 한다.",
                metadata=flatten_metadata(
                    {
                        "source_id": "safety_doc",
                        "title": "안전교육 안내",
                        "doc_type": "safety",
                        "evidence_grade": "C",
                        "language": ["ko", "id"],
                        "rag_domain": "multilingual_contact",
                        "owner_agent": "multilingual_contact_agent",
                        "ingest_target": True,
                        "not_for_legal_basis": False,
                    }
                ),
            ),
            VectorRecord(
                id="excluded_chunk_0000_cccc3333",
                text="상담 관련 합성 예시 데이터입니다.",
                metadata=flatten_metadata(
                    {
                        "source_id": "excluded_doc",
                        "title": "제외 대상",
                        "doc_type": "counseling",
                        "evidence_grade": "F",
                        "language": ["ko"],
                        "rag_domain": "multilingual_contact",
                        "owner_agent": "multilingual_contact_agent",
                        "ingest_target": True,
                        "not_for_legal_basis": False,
                    }
                ),
            ),
        ]
        index.upsert(records)
        yield
        index.close()

    def test_search_excludes_evidence_grade_f(self) -> None:
        results = search_multilingual_contact_docs("상담센터 전화번호", top_k=5)
        source_ids = {r["metadata"]["source_id"] for r in results}
        assert "excluded_doc" not in source_ids

    def test_search_intent_prioritizes_matching_doc_type(self) -> None:
        results = search_multilingual_contact_docs("문의 사항", intent="safety", top_k=5)
        assert results
        assert results[0]["metadata"]["doc_type"] == "safety"

    def test_search_returns_empty_list_when_collection_missing(self, monkeypatch) -> None:
        import oe_rag.store.pgvector_store as store_module

        monkeypatch.setattr(store_module, "read_manifest", lambda *_a, **_k: None)
        assert search_multilingual_contact_docs("아무 질의") == []
