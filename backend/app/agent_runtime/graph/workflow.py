from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent_runtime.schemas import ForeignHiringState
from app.agent_runtime.graph.nodes import (
    intent_router_node,
    planner_node,
    executor_node,
    aggregator_node,
    approval_gate_node,
    final_response_node,
)


def _state_to_dict(state: ForeignHiringState) -> dict[str, Any]:
    return state.model_dump()


def _dict_to_state(d: dict[str, Any]) -> ForeignHiringState:
    return ForeignHiringState.model_validate(d)


def _wrap(node_fn):
    def wrapped(state_dict: dict[str, Any]) -> dict[str, Any]:
        state = _dict_to_state(state_dict)
        result = node_fn(state)
        return _state_to_dict(result)
    return wrapped


def build_workflow() -> StateGraph:
    graph = StateGraph(dict)

    graph.add_node("intent_router", _wrap(intent_router_node))
    graph.add_node("planner", _wrap(planner_node))
    graph.add_node("executor", _wrap(executor_node))
    graph.add_node("aggregator", _wrap(aggregator_node))
    graph.add_node("approval_gate", _wrap(approval_gate_node))
    graph.add_node("final_response", _wrap(final_response_node))

    graph.set_entry_point("intent_router")
    graph.add_edge("intent_router", "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "aggregator")
    graph.add_edge("aggregator", "approval_gate")
    graph.add_edge("approval_gate", "final_response")
    graph.add_edge("final_response", END)

    return graph


_checkpointer = MemorySaver()
_compiled_app = None


def get_compiled_app():
    global _compiled_app
    if _compiled_app is None:
        workflow = build_workflow()
        _compiled_app = workflow.compile(checkpointer=_checkpointer)
    return _compiled_app
