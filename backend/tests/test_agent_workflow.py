import pytest

from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState


def _disable_live_agent(monkeypatch) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module
    from app.agent_runtime.langchain_v1.tools import RuntimePreflightError

    def fail_create_agent(*args, **kwargs):
        raise RuntimePreflightError("test uses structured blocked response")

    monkeypatch.setattr(runtime_module, "create_workbridge_agent", fail_create_agent)


@pytest.mark.asyncio
async def test_workflow_uses_langchain_v1_state_and_blocks_legal_judgment(monkeypatch) -> None:
    _disable_live_agent(monkeypatch)
    state = await run_workflow(
        user_message="이 사람 비자가 확실히 가능한지 법적으로 판단해줘",
        user_id="user-1",
        company_id="company-1",
        thread_id="legal-refusal-thread",
    )

    assert isinstance(state, ForeignHiringState)
    assert "UNSUPPORTED_LEGAL_JUDGMENT" in [intent.value for intent in state.detected_intents]
    assert state.plan.blocked is True
    assert state.approval.required is True
    assert state.approval.status == "PENDING"
    assert runtime_state_store.get(state.request_id) is not None


@pytest.mark.asyncio
async def test_workflow_preserves_company_context_for_api_compatibility(monkeypatch) -> None:
    _disable_live_agent(monkeypatch)
    state = await run_workflow(
        user_message="이 회사의 비자 업무 상태를 확인해줘",
        user_id="user-1",
        company_id="550e8400-e29b-41d4-a716-446655440001",
        thread_id="state-loader-thread",
    )

    assert state.company_context["id"] == "550e8400-e29b-41d4-a716-446655440001"
    assert state.context_loaded is True
    assert state.context_blockers == []


@pytest.mark.asyncio
async def test_workflow_preserves_worker_context_for_api_compatibility(monkeypatch) -> None:
    _disable_live_agent(monkeypatch)
    state = await run_workflow(
        user_message="이 근로자의 체류연장 상태를 확인해줘",
        user_id="user-1",
        company_id="550e8400-e29b-41d4-a716-446655440001",
        worker_id="650e8400-e29b-41d4-a716-446655440001",
        thread_id="state-loader-worker-thread",
    )

    assert state.worker_context["id"] == "650e8400-e29b-41d4-a716-446655440001"
    assert state.worker_context["visa_type"] == "E-9"


def test_workflow_no_longer_imports_custom_graph_workflow() -> None:
    import app.agent_runtime.runner as runner

    assert "get_compiled_app" not in runner.__dict__
