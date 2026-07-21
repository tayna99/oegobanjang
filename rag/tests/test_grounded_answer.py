"""LLM citation 선택은 retrieval candidate catalog에서만 정본화되어야 한다."""

from __future__ import annotations

from typing import Any

from oe_rag.agent.fake_model import ScriptedToolCallingChatModel
from oe_rag.missions import rag_answer as mission


def test_rag_answer_rehydrates_llm_citation_metadata_from_retrieval_catalog(monkeypatch) -> None:
    class _Retriever:
        @staticmethod
        def invoke(_payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "records": [
                    {
                        "source_id": "official_b_source",
                        "title": "Canonical official source",
                        "evidence_grade": "B",
                    },
                    {
                        "source_id": "internal_e_source",
                        "title": "Canonical internal template",
                        "evidence_grade": "E",
                    },
                ],
                "retrieved_count": 2,
                "missing_evidence": False,
            }

    monkeypatch.setattr(mission, "retrieve_workforce_materials", _Retriever())
    model = ScriptedToolCallingChatModel(
        steps=[
            [
                {
                    "name": "RagAnswer",
                    "args": {
                        "final_response": "Grounded answer",
                        "citations": [
                            {
                                "source_id": "official_b_source",
                                "title": "Forged A-grade title",
                                "evidence_grade": "A",
                            },
                            {
                                "source_id": "unknown_or_other_company_source",
                                "title": "Forged internal source",
                                "evidence_grade": "E",
                            },
                        ],
                        "missing_evidence": False,
                        "risk_flags": [],
                    },
                }
            ]
        ]
    )

    result = mission.run_rag_answer_mission(
        request_id="test-grounded-answer",
        user_message="question",
        chat_model=model,
    )

    assert result["structured_response"]["citations"] == [
        {
            "source_id": "official_b_source",
            "title": "Canonical official source",
            "evidence_grade": "B",
        }
    ]
    assert result["citation_catalog"] == [
        {
            "source_id": "official_b_source",
            "title": "Canonical official source",
            "evidence_grade": "B",
        },
        {
            "source_id": "internal_e_source",
            "title": "Canonical internal template",
            "evidence_grade": "E",
        },
    ]
