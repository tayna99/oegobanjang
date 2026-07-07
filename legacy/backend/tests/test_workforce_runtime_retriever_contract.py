import pytest

from app.agent_runtime.rag import workforce_runtime_retriever


def test_workforce_runtime_retriever_rejects_jsonl_backend(monkeypatch) -> None:
    monkeypatch.setenv("WORKFORCE_RAG_RUNTIME_BACKEND", "jsonl")

    with pytest.raises(RuntimeError, match="Chroma"):
        workforce_runtime_retriever.retrieve_workforce_runtime_materials(
            query="E-9 신규 고용 절차",
            case_type="new_hiring",
            sub_agent="workforce_requirement_agent",
        )
