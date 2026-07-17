import pytest

from oe_rag import retriever


def test_workforce_runtime_retriever_rejects_jsonl_backend(monkeypatch) -> None:
    monkeypatch.setenv("WORKFORCE_RAG_RUNTIME_BACKEND", "jsonl")

    with pytest.raises(RuntimeError, match="pgvector"):
        retriever.retrieve_workforce_runtime_materials(
            query="E-9 신규 고용 절차",
            case_type="new_hiring",
            sub_agent="workforce_requirement_agent",
        )


def test_workforce_runtime_retriever_rejects_chroma_backend(monkeypatch) -> None:
    monkeypatch.setenv("WORKFORCE_RAG_RUNTIME_BACKEND", "chroma")

    with pytest.raises(RuntimeError, match="pgvector"):
        retriever.retrieve_workforce_runtime_materials(
            query="E-9 신규 고용 절차",
            case_type="new_hiring",
            sub_agent="workforce_requirement_agent",
        )


@pytest.mark.pgvector
def test_runtime_retrieval_returns_three_buckets_with_filters(monkeypatch) -> None:
    monkeypatch.delenv("WORKFORCE_RAG_RUNTIME_BACKEND", raising=False)
    monkeypatch.setenv("WORKFORCE_RAG_EMBEDDING_PROVIDER", "deterministic")

    buckets = retriever.retrieve_workforce_runtime_materials(
        query="내국인 구인노력은 언제 확인해야 해?",
        case_type="new_hiring",
        sub_agent="workforce_requirement_agent",
        visa_type="E-9",
        top_k=5,
    )

    assert set(buckets) == {"official_procedure", "allowed_industry", "internal_template"}
    for result in buckets["official_procedure"]:
        assert result["metadata"]["source_unit_type"] == "procedure_step"
        assert result["metadata"]["evidence_grade"] in {"A", "B"}
    for result in buckets["internal_template"]:
        assert result["metadata"]["evidence_grade"] == "E"
    # D/F 등급은 어떤 버킷에도 나타나면 안 된다 (인덱스 생성 단계에서 이미 제외)
    for bucket_results in buckets.values():
        for result in bucket_results:
            assert result["metadata"].get("evidence_grade") not in {"D", "F"}
