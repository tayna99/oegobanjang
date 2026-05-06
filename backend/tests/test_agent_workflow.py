import pytest

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState


class _FakeIntentResponse:
    content = '{"intents": ["UNSUPPORTED_LEGAL_JUDGMENT"]}'


class _FakeIntentLLM:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, messages):
        return _FakeIntentResponse()


class _NoResultRetriever:
    found = False
    documents = []


class _FakeRetriever:
    def search(self, query: str, k: int = 5):
        return _NoResultRetriever()


@pytest.mark.asyncio
async def test_workflow_preserves_langgraph_state_and_refuses_legal_judgment(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.intent_router.ChatOpenAI",
        _FakeIntentLLM,
    )
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.executor.RAGRetriever",
        _FakeRetriever,
    )

    state = await run_workflow(
        user_message="이 사람 비자가 확실히 가능한지 법적으로 판단해줘",
        user_id="user-1",
        company_id="company-1",
        thread_id="legal-refusal-thread",
    )

    assert isinstance(state, ForeignHiringState)
    assert "UNSUPPORTED_LEGAL_JUDGMENT" in [intent.value for intent in state.detected_intents]
    assert "비자 가능 여부 확정" in state.final_response
    assert state.plan.blocked is True
    assert state.approval.required is False
