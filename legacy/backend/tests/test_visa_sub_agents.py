"""visa_agent 서브에이전트 2개 단위 테스트.

검증 대상:
- _run_visa_risk_sub_agent: assess_visa_risk Tool 호출 여부, risk_flags 반환
- _run_document_priority_sub_agent: assess_document_priority Tool 호출 여부
- run_visa_agent: 서브에이전트 2개 결과 병합, agent_results/tool_results/risk_flags 반영
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.agent_runtime.agents.visa_agent import (
    _run_visa_risk_sub_agent,
    _run_document_priority_sub_agent,
    run_visa_agent,
)
from app.agent_runtime.schemas import ForeignHiringState


# ─── 픽스처 ──────────────────────────────────────────────────────────────────

def _make_state(message: str = "비자 상태 확인해줘") -> ForeignHiringState:
    return ForeignHiringState(
        request_id=str(uuid.uuid4()),
        user_id="user-test",
        company_id="company-test",
        worker_id="W001",
        user_message=message,
    )


def _ai_with_tool_call(tool_name: str, args: dict) -> AIMessage:
    """tool_calls가 포함된 AIMessage 목 생성."""
    msg = AIMessage(content="")
    msg.tool_calls = [{"name": tool_name, "args": args, "id": "tc-001"}]
    return msg


def _ai_no_tool() -> AIMessage:
    msg = AIMessage(content="분석 완료")
    msg.tool_calls = []
    return msg


# ─── 서브에이전트 1: 비자 위험도 ─────────────────────────────────────────────

class TestVisaRiskSubAgent:
    def test_returns_sub_agent_key(self):
        """결과 dict에 sub_agent 키가 visa_risk_sub_agent인지 확인."""
        state = _make_state()
        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.return_value = _ai_no_tool()

        result = _run_visa_risk_sub_agent(state, "W001", llm_mock)

        assert result["sub_agent"] == "visa_risk_sub_agent"

    def test_tool_result_appended_when_assess_visa_risk_called(self):
        """assess_visa_risk Tool이 호출되면 tool_results에 결과가 담긴다."""
        import app.agent_runtime.agents.visa_agent as visa_agent_module

        state = _make_state()

        fake_tool_output = {
            "tool_name": "assess_visa_risk",
            "status": "SUCCESS",
            "output": {
                "risk_level": "HIGH",
                "effective_d_day": 20,
                "combined_risk_reason": "체류만료 D-20 (E-9 준비기간 120일 기준)",
                "visa_type": "E-9",
                "prep_days": 120,
            },
            "risk_flags": ["체류만료 D-20 (E-9 준비기간 120일 기준)"],
            "citations": [],
        }

        ai_msg = _ai_with_tool_call("assess_visa_risk", {"worker_id": "W001"})

        fake_tool = MagicMock()
        fake_tool.name = "assess_visa_risk"
        fake_tool.invoke.return_value = fake_tool_output

        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.side_effect = [ai_msg, _ai_no_tool()]

        original_tools = visa_agent_module._VISA_RISK_TOOLS
        try:
            visa_agent_module._VISA_RISK_TOOLS = [fake_tool]
            result = _run_visa_risk_sub_agent(state, "W001", llm_mock)
        finally:
            visa_agent_module._VISA_RISK_TOOLS = original_tools

        assert result["tool_calls"] == 1
        assert result["tool_results"][0]["output"]["risk_level"] == "HIGH"
        assert "체류만료 D-20" in result["risk_flags"][0]

    def test_evidence_event_logged(self):
        """서브에이전트 실행 후 evidence_events에 step_name=visa_risk_sub_agent가 기록된다."""
        state = _make_state()
        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.return_value = _ai_no_tool()

        _run_visa_risk_sub_agent(state, "W001", llm_mock)

        step_names = [e.step_name for e in state.evidence_events]
        assert "visa_risk_sub_agent" in step_names

    def test_error_handling_returns_error_key(self):
        """LLM 호출 실패 시 error 키를 가진 결과를 반환한다."""
        state = _make_state()
        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.side_effect = RuntimeError("LLM 오류")

        result = _run_visa_risk_sub_agent(state, "W001", llm_mock)

        assert "error" in result
        assert result["tool_calls"] == 0


# ─── 서브에이전트 2: 서류 우선순위 ───────────────────────────────────────────

class TestDocumentPrioritySubAgent:
    def test_returns_sub_agent_key(self):
        """결과 dict에 sub_agent 키가 document_priority_sub_agent인지 확인."""
        state = _make_state()
        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.return_value = _ai_no_tool()

        result = _run_document_priority_sub_agent(state, "W001", llm_mock)

        assert result["sub_agent"] == "document_priority_sub_agent"

    def test_tool_result_appended_when_assess_document_priority_called(self):
        """assess_document_priority Tool이 호출되면 tool_results에 결과가 담긴다."""
        import app.agent_runtime.agents.visa_agent as visa_agent_module

        state = _make_state()

        fake_tool_output = {
            "tool_name": "assess_document_priority",
            "status": "SUCCESS",
            "output": {
                "priority_risk_level": "CRITICAL",
                "submission_readiness": "신청 불가",
                "critical_missing": [{"doc_type": "여권", "notes": "만료"}],
                "supplementary_missing": [],
                "total_missing": 1,
            },
            "risk_flags": ["필수 서류 누락 1건: ['여권']"],
            "citations": [],
        }

        ai_msg = _ai_with_tool_call(
            "assess_document_priority",
            {"worker_id": "W001", "case_type": "stay_extension"},
        )

        fake_tool = MagicMock()
        fake_tool.name = "assess_document_priority"
        fake_tool.invoke.return_value = fake_tool_output

        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.side_effect = [ai_msg, _ai_no_tool()]

        original_tools = visa_agent_module._DOC_PRIORITY_TOOLS
        try:
            visa_agent_module._DOC_PRIORITY_TOOLS = [fake_tool]
            result = _run_document_priority_sub_agent(state, "W001", llm_mock)
        finally:
            visa_agent_module._DOC_PRIORITY_TOOLS = original_tools

        assert result["tool_calls"] == 1
        assert result["tool_results"][0]["output"]["priority_risk_level"] == "CRITICAL"
        assert result["tool_results"][0]["output"]["submission_readiness"] == "신청 불가"
        assert "필수 서류 누락 1건" in result["risk_flags"][0]

    def test_evidence_event_logged(self):
        """서브에이전트 실행 후 evidence_events에 step_name=document_priority_sub_agent 기록."""
        state = _make_state()
        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.return_value = _ai_no_tool()

        _run_document_priority_sub_agent(state, "W001", llm_mock)

        step_names = [e.step_name for e in state.evidence_events]
        assert "document_priority_sub_agent" in step_names

    def test_rag_context_included_in_message(self):
        """state.rag_contexts가 있으면 서브에이전트 메시지에 포함된다."""
        state = _make_state()
        state.rag_contexts = [
            {"title": "체류연장 서류", "evidence_grade": "A", "content": "여권 원본 필수"}
        ]

        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            return _ai_no_tool()

        llm_mock = MagicMock()
        llm_mock.bind_tools.return_value.invoke.side_effect = capture_invoke

        _run_document_priority_sub_agent(state, "W001", llm_mock)

        user_content = str(captured_messages[1])
        assert "체류연장 서류" in user_content or "여권 원본 필수" in user_content


# ─── 오케스트레이터: run_visa_agent ──────────────────────────────────────────

class TestRunVisaAgent:
    def _patch_sub_agents(self, risk_flags: list[str] | None = None):
        """두 서브에이전트를 mock으로 교체하는 context manager 반환."""
        risk_result = {
            "sub_agent": "visa_risk_sub_agent",
            "summary": "비자 위험도 HIGH",
            "tool_calls": 1,
            "tool_results": [{"tool_name": "assess_visa_risk", "output": {"risk_level": "HIGH"}, "risk_flags": risk_flags or [], "citations": []}],
            "risk_flags": risk_flags or [],
            "citations": [],
        }
        doc_result = {
            "sub_agent": "document_priority_sub_agent",
            "summary": "서류 우선순위 MEDIUM",
            "tool_calls": 1,
            "tool_results": [{"tool_name": "assess_document_priority", "output": {"priority_risk_level": "MEDIUM"}, "risk_flags": [], "citations": []}],
            "risk_flags": [],
            "citations": [],
        }
        return risk_result, doc_result

    def test_agent_result_has_two_sub_agents(self):
        """agent_results에 서브에이전트 2개 항목이 포함된다."""
        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents()

        with (
            patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
            patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
            patch("app.agent_runtime.agents.visa_agent.ChatOpenAI"),
        ):
            result = run_visa_agent(state, worker_id="W001")

        assert len(result["sub_agents"]) == 2
        names = [s["name"] for s in result["sub_agents"]]
        assert "visa_risk_sub_agent" in names
        assert "document_priority_sub_agent" in names

    def test_tool_results_merged_into_state(self):
        """두 서브에이전트의 tool_results가 state.tool_results에 병합된다."""
        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents()

        with (
            patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
            patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
            patch("app.agent_runtime.agents.visa_agent.ChatOpenAI"),
        ):
            run_visa_agent(state, worker_id="W001")

        assert len(state.tool_results) == 2

    def test_risk_flags_merged_into_state(self):
        """두 서브에이전트의 risk_flags가 state.risk_flags에 병합된다."""
        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents(risk_flags=["체류만료 D-20"])

        with (
            patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
            patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
            patch("app.agent_runtime.agents.visa_agent.ChatOpenAI"),
        ):
            run_visa_agent(state, worker_id="W001")

        assert "체류만료 D-20" in state.risk_flags

    def test_handoff_triggered_on_critical_risk(self):
        """CRITICAL 위험 플래그가 있으면 handoff_triggered=True이고 handoff 결과가 있다."""
        import app.agent_runtime.agents.visa_agent as visa_agent_module

        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents(risk_flags=["CRITICAL 위험"])

        handoff_tool_result = {
            "tool_name": "generate_expert_handoff_package_draft",
            "output": {"package_id": "HP-001"},
            "risk_flags": [],
            "citations": [],
        }
        handoff_ai = _ai_with_tool_call("generate_expert_handoff_package_draft", {"worker_id": "W001"})

        fake_handoff_tool = MagicMock()
        fake_handoff_tool.name = "generate_expert_handoff_package_draft"
        fake_handoff_tool.invoke.return_value = handoff_tool_result

        llm_instance = MagicMock()
        llm_instance.bind_tools.return_value.invoke.return_value = handoff_ai

        original_handoff = visa_agent_module._HANDOFF_TOOLS
        try:
            visa_agent_module._HANDOFF_TOOLS = [fake_handoff_tool]
            with (
                patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
                patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
                patch("app.agent_runtime.agents.visa_agent.ChatOpenAI", return_value=llm_instance),
            ):
                result = run_visa_agent(state, worker_id="W001")
        finally:
            visa_agent_module._HANDOFF_TOOLS = original_handoff

        assert result["handoff_triggered"] is True
        assert result["handoff"] is not None

    def test_handoff_not_triggered_on_low_risk(self):
        """risk_flags가 없으면 handoff_triggered=False."""
        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents(risk_flags=[])

        with (
            patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
            patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
            patch("app.agent_runtime.agents.visa_agent.ChatOpenAI"),
        ):
            result = run_visa_agent(state, worker_id="W001")

        assert result["handoff_triggered"] is False

    def test_evidence_event_logged_for_orchestrator(self):
        """오케스트레이터 완료 후 step_name=visa_agent Evidence event가 기록된다."""
        state = _make_state()
        risk_result, doc_result = self._patch_sub_agents()

        with (
            patch("app.agent_runtime.agents.visa_agent._run_visa_risk_sub_agent", return_value=risk_result),
            patch("app.agent_runtime.agents.visa_agent._run_document_priority_sub_agent", return_value=doc_result),
            patch("app.agent_runtime.agents.visa_agent.ChatOpenAI"),
        ):
            run_visa_agent(state, worker_id="W001")

        step_names = [e.step_name for e in state.evidence_events]
        assert "visa_agent" in step_names

    def test_llm_limit_blocks_execution(self):
        """LLM 호출 제한 초과 시 error 반환."""
        state = _make_state()

        with patch(
            "app.agent_runtime.agents.visa_agent.check_llm_limit",
            return_value=(False, "LLM 호출 한도 초과"),
        ):
            result = run_visa_agent(state, worker_id="W001")

        assert "error" in result
        assert "한도 초과" in result["error"]
