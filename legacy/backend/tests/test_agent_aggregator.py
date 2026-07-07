from __future__ import annotations

import pytest

from app.agent_runtime.langchain_v1.runtime import (
    normalize_runtime_input,
    run_langchain_v1_agent,
    to_foreign_hiring_state,
)
from app.agent_runtime.langchain_v1.schemas import (
    ApprovalBlock,
    HandoffDraft,
    WorkBridgeAgentResponse,
)
from app.agent_runtime.schemas import Intent


class _FakeAgent:
    async def ainvoke(self, payload):
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="세 agent 결과를 LangChain v1 structured response로 정리했습니다.",
                detected_intents=["HIRING", "CONTACT", "VISA_CHECK"],
                risk_flags=["D-30 임박", "메시지 발송 전 승인 필요"],
                approval=ApprovalBlock(
                    required=True,
                    status="PENDING",
                    reason="외부 전달 전 담당자 승인 필요",
                    blocked_actions=["send_worker_message"],
                ),
                handoff=HandoffDraft(
                    available=True,
                    package_type="expert_handoff_draft",
                    approval_required=True,
                    approval_status="PENDING",
                    handoff_ready=False,
                    handoff_blockers=["worker_context.visa_type 누락"],
                ),
                rag_contexts=[
                    {
                        "source_id": "gov24_stay_extension_001",
                        "title": "체류기간 연장",
                        "evidence_grade": "B",
                    }
                ],
                domain_payload={"agent_count": 3},
            )
        }


@pytest.mark.asyncio
async def test_langchain_v1_compatibility_output_combines_intents_risks_and_handoff() -> None:
    runtime_state = await run_langchain_v1_agent(
        normalize_runtime_input(
            user_message="채용, 연락, 비자 서류를 같이 정리해줘",
            user_id="manager-001",
            company_id="company-001",
        ),
        agent=_FakeAgent(),
    )

    state = to_foreign_hiring_state(runtime_state)

    assert state.detected_intents == [Intent.HIRING, Intent.CONTACT, Intent.VISA_CHECK]
    assert state.aggregated_output["agent_count"] == 1
    assert state.aggregated_output["agents"] == ["langchain_v1"]
    assert state.aggregated_output["approval_required"] is True
    assert "D-30 임박" in state.aggregated_output["risk_flags"]
    assert state.handoff_package_draft["package_type"] == "expert_handoff_draft"
    assert len(state.rag_contexts) == 1


@pytest.mark.asyncio
async def test_langchain_v1_preflight_failure_returns_blocked_approval_state(monkeypatch) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module
    from app.agent_runtime.langchain_v1.tools import RuntimePreflightError

    async def no_checkpointer():
        return None

    def fail_create_agent(*args, **kwargs):
        raise RuntimePreflightError("test uses structured blocked response")

    monkeypatch.setattr(runtime_module, "get_async_langchain_checkpointer", no_checkpointer)
    monkeypatch.setattr(runtime_module, "create_workbridge_agent", fail_create_agent)

    state = await run_langchain_v1_agent(
        normalize_runtime_input(
            user_message="E-9 채용과 비자 서류 확인해줘",
            user_id="user-1",
            company_id="company-1",
        )
    )
    compat_state = to_foreign_hiring_state(state)

    assert compat_state.aggregated_output["agent_count"] == 1
    assert compat_state.aggregated_output["approval_required"] is True
    assert compat_state.approval.required is True
    assert compat_state.approval.status == "PENDING"
    assert "langchain_v1" in compat_state.aggregated_output["agents"]
