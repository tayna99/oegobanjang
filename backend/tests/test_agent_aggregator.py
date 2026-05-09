import pytest

from app.agent_runtime.legacy_graph.nodes.aggregator import aggregator_node
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
                "approval_reasons": ["worker_message_draft"],
            },
            {
                "agent": "visa_document_agent",
                "summary": "체류 D-day 확인",
                "risk_flags": ["D-30 임박"],
                "key_findings": [
                    {
                        "agent": "visa_document_agent",
                        "type": "document_gap",
                        "message": "여권 사본이 누락되었습니다.",
                        "severity": "MEDIUM",
                        "citation_ids": ["doc_requirement_e9_renewal"],
                    }
                ],
            },
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
    assert len(result.aggregated_output["key_findings"]) == 1
    assert result.aggregated_output["key_findings"][0]["type"] == "document_gap"
    assert "worker_message_draft" in result.aggregated_output["approval_reasons"]
    assert len(result.aggregated_output["risk_reasons"]) > 0
    assert any(event.event_type.value == "risk_flagged" for event in result.evidence_events)


def test_risk_level_high_d30() -> None:
    state = ForeignHiringState(
        request_id="risk-high-d30",
        agent_results=[],
        risk_flags=["D-30 임박"],
    )

    result = aggregator_node(state)
    assert result.aggregated_output["risk_level"] == "HIGH"


def test_risk_level_high_guardrail() -> None:
    state = ForeignHiringState(
        request_id="risk-high-guardrail",
        agent_results=[],
        risk_flags=["guardrail 차단: 법적 판단 불가"],
    )

    result = aggregator_node(state)
    assert result.aggregated_output["risk_level"] == "HIGH"


def test_risk_level_medium_approval_only() -> None:
    state = ForeignHiringState(
        request_id="risk-medium",
        agent_results=[{"agent": "test_agent", "summary": "테스트", "approval_required": True}],
        risk_flags=[],
    )

    result = aggregator_node(state)
    assert result.aggregated_output["risk_level"] == "MEDIUM"
    assert result.aggregated_output["approval_required"] is True


def test_risk_level_low() -> None:
    state = ForeignHiringState(
        request_id="risk-low",
        agent_results=[{"agent": "test_agent", "summary": "정보 조회 완료", "risk_flags": []}],
        risk_flags=[],
    )

    result = aggregator_node(state)
    assert result.aggregated_output["risk_level"] == "LOW"
    assert result.aggregated_output["approval_required"] is False


def test_approval_reasons_collected() -> None:
    state = ForeignHiringState(
        request_id="approval-reasons",
        agent_results=[
            {
                "agent": "contact_agent",
                "summary": "메시지 생성",
                "approval_reasons": ["worker_message_draft", "translation_review"],
            }
        ],
    )

    result = aggregator_node(state)
    assert "worker_message_draft" in result.aggregated_output["approval_reasons"]
    assert "translation_review" in result.aggregated_output["approval_reasons"]


def test_key_findings_collected() -> None:
    state = ForeignHiringState(
        request_id="key-findings",
        agent_results=[
            {
                "agent": "visa_agent",
                "summary": "비자 확인",
                "key_findings": [
                    {
                        "agent": "visa_agent",
                        "type": "document_gap",
                        "message": "여권 사본 누락",
                        "severity": "HIGH",
                        "citation_ids": ["doc_requirement"],
                    }
                ],
            }
        ],
    )

    result = aggregator_node(state)
    assert len(result.aggregated_output["key_findings"]) == 1
    assert result.key_findings[0]["type"] == "document_gap"
    assert result.key_findings[0]["message"] == "여권 사본 누락"


def test_handoff_ready_true() -> None:
    state = ForeignHiringState(
        request_id="handoff-ready",
        agent_results=[{"agent": "visa_agent", "summary": "비자 확인"}],
        key_findings=[
            {
                "agent": "visa_agent",
                "type": "document_gap",
                "message": "여권 사본",
            }
        ],
    )
    state.plan.requires_approval = True

    result = aggregator_node(state)
    assert result.aggregated_output["handoff_ready"] is True
    assert len(result.aggregated_output["handoff_blockers"]) == 0


def test_handoff_blockers_populated() -> None:
    state = ForeignHiringState(
        request_id="handoff-blockers",
        agent_results=[
            {
                "agent": "visa_agent",
                "summary": "비자 확인",
                "key_findings": [
                    {
                        "agent": "visa_agent",
                        "type": "missing_info",
                        "message": "회사 정보 누락",
                    },
                    {
                        "agent": "visa_agent",
                        "type": "missing_info",
                        "message": "근로자 연락처 없음",
                    },
                ],
            }
        ],
    )
    state.plan.requires_approval = True

    result = aggregator_node(state)
    assert result.aggregated_output["handoff_ready"] is False
    assert len(result.aggregated_output["handoff_blockers"]) == 2
    assert "회사 정보 누락" in result.aggregated_output["handoff_blockers"]


@pytest.mark.asyncio
async def test_workflow_exposes_langchain_v1_aggregated_compatibility_output(monkeypatch) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module
    from app.agent_runtime.langchain_v1.tools import RuntimePreflightError

    def fail_create_agent(*args, **kwargs):
        raise RuntimePreflightError("test uses structured blocked response")

    monkeypatch.setattr(runtime_module, "create_workbridge_agent", fail_create_agent)

    state = await run_workflow(
        user_message="E-9 채용과 비자 서류 확인해줘",
        user_id="user-1",
        company_id="company-1",
        thread_id="aggregator-three-agent-thread",
    )

    assert state.aggregated_output["agent_count"] == 1
    assert state.aggregated_output["approval_required"] is True
    assert state.approval.required is True
    assert state.approval.status == "PENDING"
    assert "langchain_v1" in state.aggregated_output["agents"]
