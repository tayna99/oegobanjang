"""create_agent + retrieve_workforce_materials 오프라인 스모크 — OPENAI_API_KEY 불필요.

ScriptedToolCallingChatModel/OfflineEchoChatModel로 실제 LLM 호출 없이
tool-calling → structured output(RagAnswer) 배선이 동작함을 검증한다.
"""

from __future__ import annotations

import pytest

from oe_rag.agent.factory import RagAnswer, create_workforce_rag_agent
from oe_rag.agent.fake_model import OfflineEchoChatModel, ScriptedToolCallingChatModel
from oe_rag.agent.tools import RuntimePreflightError, retrieve_workforce_materials

pytestmark = pytest.mark.pgvector


def _invoke(agent, query: str, thread_id: str) -> dict:
    return agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": thread_id}},
    )


def test_agent_runs_offline_with_scripted_tool_call_and_structured_response() -> None:
    fake_model = ScriptedToolCallingChatModel(
        steps=[
            [{"name": "retrieve_workforce_materials", "args": {"query": "내국인 구인노력 확인", "case_type": "new_hiring"}}],
            [
                {
                    "name": "RagAnswer",
                    "args": {
                        "final_response": "내국인 구인노력 절차를 확인하세요.",
                        "citations": [
                            {
                                "source_id": "E9_EMPLOYER_STEP_NATIVE_RECRUITMENT",
                                "title": "내국인 구인노력",
                                "evidence_grade": "B",
                            }
                        ],
                        "missing_evidence": False,
                        "risk_flags": [],
                    },
                }
            ],
        ]
    )

    agent = create_workforce_rag_agent(model=fake_model, tools=[retrieve_workforce_materials])
    result = _invoke(agent, "내국인 구인노력 확인해줘", thread_id="smoke-scripted")

    structured = result["structured_response"]
    assert isinstance(structured, RagAnswer)
    assert structured.citations[0].source_id == "E9_EMPLOYER_STEP_NATIVE_RECRUITMENT"
    assert structured.missing_evidence is False


def test_offline_echo_model_derives_citations_from_real_retrieval() -> None:
    """OfflineEchoChatModel은 실제 pgvector 검색 결과를 그대로 구조화 응답에 반영한다."""
    fake_model = OfflineEchoChatModel(
        tool_args={"query": "내국인 구인노력은 언제 확인해야 해?", "case_type": "new_hiring"}
    )

    agent = create_workforce_rag_agent(model=fake_model, tools=[retrieve_workforce_materials])
    result = _invoke(agent, "내국인 구인노력은 언제 확인해야 해?", thread_id="smoke-echo")

    structured = result["structured_response"]
    assert isinstance(structured, RagAnswer)
    assert structured.citations, "실제 검색 결과가 있으면 citations가 비어 있으면 안 된다"
    assert all(c.evidence_grade not in {"D", "F"} for c in structured.citations)


def test_offline_echo_model_reports_missing_evidence_when_nothing_matches() -> None:
    fake_model = OfflineEchoChatModel(
        tool_args={"query": "존재하지 않는 질의", "case_type": "nonexistent_case_type_xyz"}
    )

    agent = create_workforce_rag_agent(model=fake_model, tools=[retrieve_workforce_materials])
    result = _invoke(agent, "존재하지 않는 질의", thread_id="smoke-missing")

    structured = result["structured_response"]
    assert structured.missing_evidence is True
    assert structured.citations == []


def test_create_workforce_rag_agent_requires_openai_key_without_explicit_model(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimePreflightError, match="OPENAI_API_KEY"):
        create_workforce_rag_agent(tools=[retrieve_workforce_materials])


def test_create_workforce_rag_agent_fails_preflight_when_collection_missing(monkeypatch) -> None:
    import oe_rag.agent.tools as tools_module

    monkeypatch.setattr(tools_module, "read_manifest", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimePreflightError, match="missing pgvector collection"):
        create_workforce_rag_agent(
            model=OfflineEchoChatModel(tool_args={"query": "x"}),
            tools=[retrieve_workforce_materials],
        )
