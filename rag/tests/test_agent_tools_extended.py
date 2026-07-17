"""search_policy_documents(비자)·search_multilingual_contact_materials 도구 가드레일."""

from __future__ import annotations

import json

import pytest

from oe_rag.agent.tools import search_multilingual_contact_materials, search_policy_documents
from oe_rag.store.base import VectorRecord, flatten_metadata
from oe_rag.store.pgvector_store import PgVectorIndex, read_manifest

pytestmark = pytest.mark.pgvector


@pytest.fixture(autouse=True)
def _require_workforce_official_indexed() -> None:
    if read_manifest("workforce_official") is None:
        pytest.skip("workforce_official not indexed — run `rag index` first")


def test_search_policy_documents_tool_returns_found_result() -> None:
    result = search_policy_documents.invoke(
        {"query": "E-9 체류연장 절차 — 1단계: 신청 가능 기간 확인", "visa_type": "E-9"}
    )

    assert result["found"] is True
    assert result["retrieved_count"] > 0
    assert result["missing_evidence"] is False
    for record in result["records"]:
        assert record["metadata"]["evidence_grade"] not in {"D", "F"}


def test_search_policy_documents_tool_flags_missing_evidence() -> None:
    result = search_policy_documents.invoke(
        {"query": "완전히 무관한 xyz999 질의", "visa_type": "NONEXISTENT-VISA-TYPE"}
    )

    assert result["found"] is False
    assert result["missing_evidence"] is True
    assert "MISSING_EVIDENCE" in result["risk_flags"]


def test_search_policy_documents_event_has_no_raw_query_or_text() -> None:
    result = search_policy_documents.invoke(
        {"query": "체류기간 연장허가 신청 서류 확인해줘", "visa_type": "E-9"}
    )

    event = result["evidence_log"]
    serialized = json.dumps(event, ensure_ascii=False)
    assert "체류기간 연장허가 신청 서류 확인해줘" not in serialized
    assert "query" not in event
    assert "text" not in event


@pytest.fixture()
def _multilingual_index():
    index = PgVectorIndex(
        "multilingual_contact", provider="deterministic", model="deterministic-sha256-64d", dimensions=64
    )
    index.ensure(reset=True)
    index.upsert(
        [
            VectorRecord(
                id="counseling_chunk_0000_toolcheck",
                text="상담센터 대표번호는 1577-0071이다.",
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
            )
        ]
    )
    yield index
    index.close()


def test_search_multilingual_contact_materials_tool_returns_records(_multilingual_index) -> None:
    result = search_multilingual_contact_materials.invoke(
        {"query": "상담센터 전화번호가 뭐예요?", "intent": "counseling"}
    )

    assert result["retrieved_count"] > 0
    assert result["missing_evidence"] is False
    assert result["records"][0]["source_id"] == "counseling_doc"


def test_search_multilingual_contact_materials_event_has_no_pii(_multilingual_index) -> None:
    result = search_multilingual_contact_materials.invoke(
        {"query": "근로자 홍길동 상담 요청", "intent": "counseling"}
    )

    event = result["evidence_log"]
    serialized = json.dumps(event, ensure_ascii=False)
    assert "홍길동" not in serialized
    assert "query" not in event
