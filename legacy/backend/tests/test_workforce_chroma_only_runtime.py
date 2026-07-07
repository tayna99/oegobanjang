from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent_runtime.langchain_v1 import tools as runtime_tools


class FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name

    def count(self) -> int:
        return 1

    def query(self, **kwargs):
        return {
            "ids": [[
                f"{self.name}_official",
                f"{self.name}_case",
                f"{self.name}_draft",
            ]],
            "documents": [["official", "case", "draft"]],
            "distances": [[0.1, 0.2, 0.3]],
            "metadatas": [[
                {
                    "source_id": "eps_employer_process",
                    "doc_type": "procedure_step",
                    "evidence_grade": "B",
                    "case_type": "new_hiring",
                    "visa_type": "E-9",
                    "title": "사업주 고용절차",
                },
                {
                    "source_id": "synthetic_case",
                    "doc_type": "case_record",
                    "evidence_grade": "F",
                    "case_type": "new_hiring",
                    "visa_type": "E-9",
                    "title": "합성 사례",
                },
                {
                    "source_id": "internal_draft",
                    "doc_type": "template",
                    "evidence_grade": "D",
                    "case_type": "new_hiring",
                    "visa_type": "E-9",
                    "title": "참고 초안",
                },
            ]],
        }


class FakeClient:
    def list_collections(self):
        return [SimpleNamespace(name="workforce_official"), SimpleNamespace(name="workforce_templates")]

    def get_collection(self, name: str) -> FakeCollection:
        return FakeCollection(name)


def test_runtime_retrieval_uses_chroma_and_filters_case_d_f(monkeypatch) -> None:
    monkeypatch.setattr(runtime_tools, "_persistent_client", lambda: FakeClient())

    from app.agent_runtime.rag.retriever import PolicyRetriever

    monkeypatch.setattr(
        PolicyRetriever,
        "search",
        lambda *args, **kwargs: pytest.fail("PolicyRetriever must not be used by runtime retrieval"),
    )

    result = runtime_tools.retrieve_workforce_materials.invoke(
        {"query": "E-9 신규 고용 절차", "case_type": "new_hiring", "visa_type": "E-9"}
    )

    assert result["records"]
    assert {record["source_id"] for record in result["records"]} == {"eps_employer_process"}
    assert all(record["evidence_grade"] not in {"D", "F"} for record in result["records"])
    assert all(record["doc_type"] not in {"case", "case_record"} for record in result["records"])
