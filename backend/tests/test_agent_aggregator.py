import pytest

from app.agent_runtime.graph.nodes.aggregator import aggregator_node
from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import (
    Citation,
    ForeignHiringState,
    Intent,
    ToolContractLevel,
    ToolResult,
    ToolStatus,
)


class _IntentResponse:
    content = '{"intents": ["HIRING", "CONTACT", "VISA_CHECK"]}'


class _IntentLLM:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, messages):
        return _IntentResponse()


class _FinalResponse:
    content = "세 agent 결과를 합쳐 승인 대기 상태로 정리했습니다."


class _FinalLLM:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, messages):
        return _FinalResponse()


class _NoResultRetriever:
    found = False
    documents = []


class _FakeRetriever:
    def search(self, query: str, k: int = 5):
        return _NoResultRetriever()


def test_aggregator_combines_three_agent_results_and_tool_evidence() -> None:
    state = ForeignHiringState(
        request_id="agg-test",
        detected_intents=[Intent.HIRING, Intent.CONTACT, Intent.VISA_CHECK],
        agent_results=[
            {"agent": "workforce_agent", "summary": "채용 요건 정리", "risk_flags": []},
            {
                "agent": "multilingual_contact_agent",
                "summary": "베트남어 메시지 초안",
                "approval_required": True,
                "risk_flags": ["메시지 발송 전 승인 필요"],
            },
            {"agent": "visa_document_agent", "summary": "체류 D-day 확인", "risk_flags": ["D-30 임박"]},
        ],
        tool_results=[
            ToolResult(
                tool_name="send_worker_message",
                tool_grade=ToolContractLevel.APPROVAL_REQUIRED,
                status=ToolStatus.NEEDS_APPROVAL,
                approval_required=True,
                citations=[
                    Citation(
                        source_id="eps_employer_process_001",
                        title="사업주 고용절차",
                        evidence_grade="B",
                    )
                ],
            )
        ],
        rag_contexts=[
            {
                "source_id": "gov24_stay_extension_001",
                "title": "체류기간 연장",
                "evidence_grade": "B",
            }
        ],
        risk_flags=["계약 종료일 확인 필요"],
    )

    result = aggregator_node(state)

    assert result.aggregated_output["agent_count"] == 3
    assert result.aggregated_output["agents"] == [
        "workforce_agent",
        "multilingual_contact_agent",
        "visa_document_agent",
    ]
    assert result.aggregated_output["approval_required"] is True
    assert result.aggregated_output["risk_level"] == "HIGH"
    assert "D-30 임박" in result.aggregated_output["risk_flags"]
    assert {
        "eps_employer_process_001",
        "gov24_stay_extension_001",
    } <= set(result.aggregated_output["citation_ids"])
    assert any(event.event_type.value == "risk_flagged" for event in result.evidence_events)


@pytest.mark.asyncio
async def test_workflow_runs_aggregator_before_approval_for_three_agents(monkeypatch) -> None:
    def fake_hiring_agent(state: ForeignHiringState) -> dict:
        result = {"agent": "workforce_agent", "summary": "채용 요건 정리", "risk_flags": []}
        state.agent_results.append(result)
        return result

    def fake_contact_agent(state: ForeignHiringState) -> dict:
        result = {
            "agent": "multilingual_contact_agent",
            "summary": "메시지 초안 생성",
            "approval_required": True,
            "risk_flags": ["메시지 발송 전 승인 필요"],
        }
        state.agent_results.append(result)
        return result

    def fake_visa_agent(state: ForeignHiringState) -> dict:
        result = {"agent": "visa_document_agent", "summary": "비자 서류 확인", "risk_flags": ["D-30 임박"]}
        state.agent_results.append(result)
        state.risk_flags.append("D-30 임박")
        return result

    monkeypatch.setattr("app.agent_runtime.graph.nodes.intent_router.ChatOpenAI", _IntentLLM)
    monkeypatch.setattr("app.agent_runtime.graph.nodes.executor.RAGRetriever", _FakeRetriever)
    monkeypatch.setattr("app.agent_runtime.graph.nodes.final_response.ChatOpenAI", _FinalLLM)
    monkeypatch.setattr("app.agent_runtime.agents.hiring_agent.run_hiring_agent", fake_hiring_agent)
    monkeypatch.setattr("app.agent_runtime.agents.contact_agent.run_contact_agent", fake_contact_agent)
    monkeypatch.setattr("app.agent_runtime.agents.visa_agent.run_visa_agent", fake_visa_agent)

    state = await run_workflow(
        user_message="E-9 채용, 비자 서류 확인하고 베트남어로 메시지 보내줘",
        user_id="user-1",
        company_id="company-1",
        thread_id="aggregator-three-agent-thread",
    )

    assert state.aggregated_output["agent_count"] == 3
    assert state.aggregated_output["approval_required"] is True
    assert state.approval.required is True
    assert state.approval.status == "PENDING"
    assert "multilingual_contact_agent" in state.aggregated_output["agents"]
