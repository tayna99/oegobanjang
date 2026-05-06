from __future__ import annotations

from typing import Any

from backend.app.agent_runtime.agents.multilingual_contact_input_extractor import (
    extract_multilingual_contact_input,
)
from backend.app.agent_runtime.graph.state import AgentRuntimeState, dedupe, ensure_state


def contact_input_extractor_node(
    state: AgentRuntimeState | dict[str, Any],
) -> AgentRuntimeState:
    current = ensure_state(state)
    if current.intent != "CONTACT":
        return current

    extracted = extract_multilingual_contact_input(
        current.user_request,
        current.input_payload,
    )
    current.input_payload = extracted.input_payload
    current.risk_flags = dedupe(current.risk_flags + extracted.risk_flags)

    if extracted.extracted_fields:
        current.plan["extracted_fields"] = extracted.extracted_fields
    if extracted.missing_recommended_fields:
        current.plan["missing_recommended_fields"] = extracted.missing_recommended_fields

    return current
