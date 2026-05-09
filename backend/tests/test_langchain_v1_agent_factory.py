from __future__ import annotations

from app.agent_runtime.langchain_v1 import agent_factory
from app.agent_runtime.langchain_v1.middleware import (
    EvidenceCaptureMiddleware,
    WorkBridgeSafetyMiddleware,
)
from app.agent_runtime.langchain_v1.schemas import RuntimeContext, WorkBridgeAgentResponse


def test_create_workbridge_agent_uses_create_agent_contract(monkeypatch) -> None:
    calls = {}

    def fake_preflight() -> None:
        calls["preflight"] = True

    def fake_create_agent(**kwargs):
        calls.update(kwargs)
        return "agent"

    fake_model = object()

    monkeypatch.setattr(agent_factory, "preflight_chroma", fake_preflight)
    monkeypatch.setattr(agent_factory, "create_agent", fake_create_agent)

    agent = agent_factory.create_workbridge_agent(model=fake_model, tools=[], middleware=[])

    assert agent == "agent"
    assert calls["preflight"] is True
    assert calls["model"] is fake_model
    assert calls["tools"] == []
    assert calls["middleware"] == []
    assert calls["response_format"] is WorkBridgeAgentResponse
    assert calls["context_schema"] is RuntimeContext


def test_default_middleware_contains_safety_and_evidence_capture(monkeypatch) -> None:
    monkeypatch.setattr(agent_factory, "preflight_chroma", lambda: None)
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr(agent_factory, "create_agent", fake_create_agent)

    agent_factory.create_workbridge_agent(model=object(), tools=[])

    middleware = captured["middleware"]
    assert any(isinstance(item, WorkBridgeSafetyMiddleware) for item in middleware)
    assert any(isinstance(item, EvidenceCaptureMiddleware) for item in middleware)
