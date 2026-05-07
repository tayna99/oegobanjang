import pytest

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.graph.workflow import build_workflow
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


@pytest.mark.asyncio
async def test_workflow_loads_company_context_before_execution(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.intent_router.ChatOpenAI",
        _FakeIntentLLM,
    )
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.executor.RAGRetriever",
        _FakeRetriever,
    )

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
async def test_workflow_accepts_worker_id_for_state_loader(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.intent_router.ChatOpenAI",
        _FakeIntentLLM,
    )
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.executor.RAGRetriever",
        _FakeRetriever,
    )

    state = await run_workflow(
        user_message="이 근로자의 체류연장 상태를 확인해줘",
        user_id="user-1",
        company_id="550e8400-e29b-41d4-a716-446655440001",
        worker_id="650e8400-e29b-41d4-a716-446655440001",
        thread_id="state-loader-worker-thread",
    )

    assert state.worker_context["id"] == "650e8400-e29b-41d4-a716-446655440001"
    assert state.worker_context["visa_type"] == "E-9"


def test_workflow_includes_handoff_package_node_between_approval_and_final_response() -> None:
    graph_spec = build_workflow().compile().get_graph()

    assert "handoff_package" in graph_spec.nodes
    assert any(
        edge.source == "approval_gate" and edge.target == "handoff_package"
        for edge in graph_spec.edges
    )
    assert any(
        edge.source == "handoff_package" and edge.target == "final_response"
        for edge in graph_spec.edges
    )
