from __future__ import annotations

from .schemas import AgentRuntimeInput, WorkBridgeAgentResponse

__all__ = [
    "AgentRuntimeInput",
    "WorkBridgeAgentResponse",
    "run_langchain_v1_agent",
    "runtime_state_store",
]


def __getattr__(name: str):
    if name == "run_langchain_v1_agent":
        from .runtime import run_langchain_v1_agent

        return run_langchain_v1_agent
    if name == "runtime_state_store":
        from .state_store import runtime_state_store

        return runtime_state_store
    raise AttributeError(name)
