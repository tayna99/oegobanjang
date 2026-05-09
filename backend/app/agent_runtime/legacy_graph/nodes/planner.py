from app.agent_runtime.schemas import ForeignHiringState, Intent, EventType, ExecutionPlan
from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event

_INTENT_TO_AGENTS: dict[str, list[str]] = {
    Intent.HIRING.value: ["workforce_agent"],
    Intent.VISA_CHECK.value: ["visa_document_agent"],
    Intent.DOCUMENT_CHECK.value: ["visa_document_agent"],
    Intent.CONTACT.value: ["multilingual_contact_agent"],
    Intent.BRIEFING.value: ["visa_document_agent", "workforce_agent"],
    Intent.UNSUPPORTED_VALUE_JUDGMENT.value: [],
    Intent.UNSUPPORTED_LEGAL_JUDGMENT.value: [],
    Intent.UNSUPPORTED_AUTO_SUBMISSION.value: [],
}

_UNSUPPORTED_INTENTS = {
    Intent.UNSUPPORTED_VALUE_JUDGMENT,
    Intent.UNSUPPORTED_LEGAL_JUDGMENT,
    Intent.UNSUPPORTED_AUTO_SUBMISSION,
}


def planner_node(state: ForeignHiringState) -> ForeignHiringState:
    intents = state.detected_intents or []

    required_agents: list[str] = []
    steps: list[str] = []
    requires_approval = False
    blocked = False
    blocked_reasons: list[str] = []

    unsupported = [i for i in intents if i in _UNSUPPORTED_INTENTS]
    supported = [i for i in intents if i not in _UNSUPPORTED_INTENTS]

    for intent in supported:
        agents = _INTENT_TO_AGENTS.get(intent.value, [])
        for agent in agents:
            if agent not in required_agents:
                required_agents.append(agent)
        steps.append(f"{intent.value} → {agents}")

    if Intent.CONTACT in intents:
        requires_approval = True

    if unsupported:
        blocked = True
        blocked_reasons = [i.value for i in unsupported]
        steps.append(f"지원하지 않는 요청: {blocked_reasons}")

    state.plan = ExecutionPlan(
        steps=steps,
        required_agents=required_agents,
        requires_approval=requires_approval,
        blocked=blocked,
        blocked_reasons=blocked_reasons,
    )

    event = make_event(
        event_type=EventType.PLAN_CREATED,
        request_id=state.request_id,
        summary=f"실행 계획 수립. agents={required_agents}, approval={requires_approval}",
        step_name="planner",
    )
    return log_event(state, event)
