from __future__ import annotations

import pytest

from app.agent_runtime.langchain_v1.runtime import normalize_runtime_input, run_langchain_v1_agent
from app.agent_runtime.langchain_v1.schemas import ApprovalBlock, WorkBridgeAgentResponse
from app.agent_runtime.langchain_v1.state_store import runtime_state_store


class ApprovalAgent:
    async def ainvoke(self, payload, *, context=None):
        if context is not None:
            context.approval_metadata = {
                "tool_name": "send_worker_message",
                "status": "NEEDS_APPROVAL",
                "reason": "담당자 승인 후 실행 가능한 작업입니다.",
                "blocked_actions": ["send_worker_message"],
            }
            context.interrupt_metadata = {
                "tool_name": "send_worker_message",
                "action": "approval_required_tool_call",
                "reason": "담당자 승인 후 실행 가능한 작업입니다.",
                "blocked_actions": ["send_worker_message"],
            }
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="메시지 초안은 승인 전 발송되지 않습니다.",
                detected_intents=["CONTACT"],
                approval=ApprovalBlock(required=False, status="NOT_REQUIRED"),
            )
        }


class InterruptAgent:
    async def ainvoke(self, payload, *, context=None):
        return {"__interrupt__": [{"value": {"tool_name": "send_worker_message"}}]}


@pytest.mark.asyncio
async def test_state_store_persists_pending_approval_and_interrupt_metadata() -> None:
    runtime_state_store.clear()
    runtime_input = normalize_runtime_input(user_message="근로자에게 문자 발송해줘")

    state = await run_langchain_v1_agent(runtime_input, agent=ApprovalAgent())

    saved = runtime_state_store.get(runtime_input.request_id)
    assert saved is not None
    assert saved.approval.required is True
    assert saved.approval.status == "PENDING"
    assert saved.interrupt_metadata["tool_name"] == "send_worker_message"
    assert saved.structured_response.approval.required is True


@pytest.mark.asyncio
async def test_human_in_the_loop_interrupt_becomes_pending_state() -> None:
    runtime_state_store.clear()
    runtime_input = normalize_runtime_input(user_message="행정사에게 바로 전달해줘")

    state = await run_langchain_v1_agent(runtime_input, agent=InterruptAgent())

    assert state.approval.required is True
    assert state.approval.status == "PENDING"
    assert state.interrupt_metadata["action"] == "human_in_the_loop_interrupt"
    assert state.structured_response.blocked_reason
