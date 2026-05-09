from __future__ import annotations

import uuid
from typing import Any

from app.agent_runtime.schemas import (
    ApprovalStatus,
    EventType,
    ExecutionPlan,
    ForeignHiringState,
    Intent,
)

from .agent_factory import create_workbridge_agent
from .events import event_to_reference, make_event
from .middleware import (
    SafetyValidationError,
    build_blocked_response,
    redact_pii,
    validate_response_safety,
)
from .schemas import (
    AgentRuntimeInput,
    ApprovalBlock,
    EvidenceReference,
    HandoffDraft,
    LangChainRuntimeState,
    RuntimeContext,
    WorkBridgeAgentResponse,
)
from .state_store import runtime_state_store
from .tools import RuntimePreflightError


def normalize_runtime_input(
    *,
    user_message: str | None = None,
    user_request: str | None = None,
    user_id: str = "",
    company_id: str = "",
    worker_id: str = "",
    candidate_id: str = "",
    thread_id: str | None = None,
    persist_result: bool = False,
    created_by: str | None = None,
    input_payload: dict[str, Any] | None = None,
) -> AgentRuntimeInput:
    message = (user_message or user_request or "").strip()
    if not message:
        raise ValueError("user_message or user_request is required")
    request_id = str(uuid.uuid4())
    return AgentRuntimeInput(
        request_id=request_id,
        user_message=message,
        user_id=user_id,
        company_id=company_id,
        worker_id=worker_id,
        candidate_id=candidate_id,
        thread_id=thread_id or request_id,
        persist_result=persist_result,
        created_by=created_by,
        input_payload=input_payload or {},
    )


async def run_langchain_v1_agent(
    runtime_input: AgentRuntimeInput,
    *,
    model: Any | None = None,
    agent: Any | None = None,
) -> LangChainRuntimeState:
    context = RuntimeContext(
        request_id=runtime_input.request_id,
        user_message=runtime_input.user_message,
    )
    events = [
        make_event(
            event_type=EventType.INTENT_CLASSIFIED,
            request_id=runtime_input.request_id,
            step_name="langchain_v1_runtime",
            summary="LangChain v1 runtime request accepted",
            metadata={"runtime": "langchain_v1"},
        )
    ]

    try:
        selected_agent = agent or create_workbridge_agent(model=model)
        result = await _ainvoke_agent(selected_agent, runtime_input, context)
        if isinstance(result, dict) and "__interrupt__" in result:
            context.interrupt_metadata = _extract_interrupt_metadata(result)
            response = build_blocked_response(
                reason="LangChain HITL interrupt received",
                user_message=runtime_input.user_message,
            )
        else:
            response = _extract_structured_response(result)
            validate_response_safety(response)
    except (RuntimePreflightError, SafetyValidationError, ValueError) as exc:
        response = _blocked_response(runtime_input, str(exc))
    except Exception as exc:
        response = _blocked_response(runtime_input, f"langchain_v1 runtime error: {exc}")

    context_events = [
        event
        for event in (
            _event_from_context(runtime_input.request_id, raw)
            for raw in context.evidence_events
        )
        if event is not None
    ]
    events.extend(context_events)

    if response.rag_contexts and not any(
        event.event_type == EventType.RAG_RETRIEVED for event in events
    ):
        events.append(
            make_event(
                event_type=EventType.RAG_RETRIEVED,
                request_id=runtime_input.request_id,
                step_name="retrieve_workforce_materials",
                summary=f"RAG materials attached: {len(response.rag_contexts)}",
                metadata={
                    "retrieval_count": len(response.rag_contexts),
                    "source_ids": [row.get("source_id") for row in response.rag_contexts],
                },
            )
        )

    if context.approval_metadata and not response.approval.required:
        response.approval = ApprovalBlock(
            required=True,
            status="PENDING",
            reason=str(context.approval_metadata.get("reason") or "담당자 승인 대기 상태입니다."),
            blocked_actions=[
                str(action) for action in context.approval_metadata.get("blocked_actions", [])
            ],
        )

    if response.approval.required and not any(
        event.event_type == EventType.APPROVAL_REQUESTED for event in events
    ):
        events.append(
            make_event(
                event_type=EventType.APPROVAL_REQUESTED,
                request_id=runtime_input.request_id,
                step_name="approval_adapter",
                summary=response.approval.reason or "담당자 승인 대기 상태입니다.",
                risk_level="MEDIUM",
                metadata={"blocked_actions": response.approval.blocked_actions},
            )
        )

    events.append(
        make_event(
            event_type=EventType.FINAL_RESPONSE_GENERATED,
            request_id=runtime_input.request_id,
            step_name="structured_response",
            summary="LangChain v1 structured_response generated",
            metadata={
                "blocked": bool(response.blocked_reason),
                "model": context.model_metadata,
                "approval_required": response.approval.required,
            },
        )
    )

    response.evidence_events = [
        *response.evidence_events,
        *[EvidenceReference.model_validate(event_to_reference(event)) for event in events],
    ]

    state = LangChainRuntimeState(
        request_id=runtime_input.request_id,
        input=runtime_input,
        structured_response=response,
        evidence_events=[event.model_dump() for event in events],
        approval=response.approval,
        interrupt_metadata=context.interrupt_metadata,
    )
    runtime_state_store.save(state)
    return state


def to_foreign_hiring_state(runtime_state: LangChainRuntimeState) -> ForeignHiringState:
    response = runtime_state.structured_response
    runtime_input = runtime_state.input
    intents = []
    for value in response.detected_intents:
        try:
            intents.append(Intent(value))
        except ValueError:
            continue

    handoff_payload = _handoff_payload(response.handoff)
    approval = ApprovalStatus(
        required=response.approval.required,
        status=response.approval.status,
        reason=response.approval.reason,
    )

    return ForeignHiringState(
        request_id=runtime_state.request_id,
        user_id=runtime_input.user_id,
        company_id=runtime_input.company_id,
        worker_id=runtime_input.worker_id,
        candidate_id=runtime_input.candidate_id,
        user_message=runtime_input.user_message,
        detected_intents=intents,
        plan=ExecutionPlan(
            steps=["langchain_v1_create_agent"],
            required_agents=[_agent_for_intents(intents)],
            requires_approval=response.approval.required,
            blocked=bool(response.blocked_reason),
            blocked_reasons=[response.blocked_reason] if response.blocked_reason else [],
        ),
        rag_contexts=response.rag_contexts,
        company_context={"id": runtime_input.company_id} if runtime_input.company_id else {},
        worker_context=(
            {"id": runtime_input.worker_id, "visa_type": "E-9"}
            if runtime_input.worker_id
            else {}
        ),
        context_loaded=True,
        agent_results=[
            {
                "agent": "langchain_v1",
                "summary": response.final_response,
                "risk_flags": response.risk_flags,
                "approval_required": response.approval.required,
                "domain_payload": response.domain_payload,
            }
        ],
        aggregated_output={
            "agent_count": 1,
            "agents": ["langchain_v1"],
            "approval_required": response.approval.required,
            "risk_flags": response.risk_flags,
            "blocked_reason": response.blocked_reason,
            "rag_context_count": len(response.rag_contexts),
        },
        handoff_package_draft=handoff_payload,
        risk_flags=response.risk_flags,
        approval=approval,
        evidence_events=[
            make_event(
                event_type=EventType(event["event_type"]),
                request_id=runtime_state.request_id,
                summary=event["summary"],
                agent_name=event.get("agent_name"),
                step_name=event.get("step_name"),
                citation_ids=event.get("citation_ids", []),
                risk_level=event.get("risk_level", "LOW"),
                metadata=event.get("metadata", {}),
            )
            for event in runtime_state.evidence_events
        ],
        final_response=response.final_response,
    )


def _extract_structured_response(result: Any) -> WorkBridgeAgentResponse:
    if not isinstance(result, dict):
        raise ValueError("LangChain agent returned a non-dict result")
    if "__interrupt__" in result:
        raise ValueError("LangChain HITL interrupt received")
    raw = result.get("structured_response")
    if raw is None:
        raise ValueError("LangChain agent did not return structured_response")
    if isinstance(raw, WorkBridgeAgentResponse):
        return raw
    if isinstance(raw, dict):
        return WorkBridgeAgentResponse.model_validate(raw)
    raise ValueError(f"Unexpected structured_response type: {type(raw).__name__}")


def _blocked_response(runtime_input: AgentRuntimeInput, reason: str) -> WorkBridgeAgentResponse:
    response = build_blocked_response(
        reason=redact_pii(reason),
        user_message=runtime_input.user_message,
    )
    response.domain_payload = {"input_payload": runtime_input.input_payload}
    return response


def _build_user_prompt(runtime_input: AgentRuntimeInput) -> str:
    return (
        f"요청 ID: {runtime_input.request_id}\n"
        f"사용자 ID: {runtime_input.user_id}\n"
        f"회사 ID: {runtime_input.company_id}\n"
        f"근로자 ID: {runtime_input.worker_id}\n"
        f"후보자 ID: {runtime_input.candidate_id}\n"
        f"사용자 요청:\n{runtime_input.user_message}\n\n"
        f"입력 payload:\n{runtime_input.input_payload}\n\n"
        "필요하면 retrieve_workforce_materials tool로 공식 근거와 템플릿을 검색하세요. "
        "외부 발송, 제출, 전달은 실행하지 말고 approval_required=true/PENDING으로 표시하세요."
    )


async def _ainvoke_agent(
    selected_agent: Any,
    runtime_input: AgentRuntimeInput,
    context: RuntimeContext,
) -> Any:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": _build_user_prompt(runtime_input),
            }
        ]
    }
    try:
        return await selected_agent.ainvoke(payload, context=context)
    except TypeError as exc:
        if "context" not in str(exc):
            raise
        return await selected_agent.ainvoke(payload)


def _extract_interrupt_metadata(result: dict[str, Any]) -> dict[str, Any]:
    interrupt = result.get("__interrupt__")
    return {
        "action": "human_in_the_loop_interrupt",
        "reason": redact_pii(str(interrupt)),
        "blocked_actions": ["external_delivery_or_submission"],
    }


def _event_from_context(request_id: str, raw: dict[str, Any]) -> Any | None:
    try:
        return make_event(
            event_type=EventType(raw["event_type"]),
            request_id=request_id,
            summary=str(raw.get("summary") or ""),
            step_name=raw.get("step_name"),
            risk_level=str(raw.get("risk_level") or "LOW"),
            metadata=dict(raw.get("metadata") or {}),
        )
    except Exception:
        return None


def _handoff_payload(handoff: HandoffDraft) -> dict[str, Any]:
    if not handoff.available:
        return {}
    payload = dict(handoff.payload)
    payload.setdefault("package_type", handoff.package_type or "expert_handoff_draft")
    payload.setdefault("approval_required", handoff.approval_required)
    payload.setdefault("approval", {"status": handoff.approval_status or "PENDING"})
    payload.setdefault("not_for_legal_judgment", handoff.not_for_legal_judgment)
    payload.setdefault("handoff_ready", handoff.handoff_ready)
    payload.setdefault("handoff_blockers", handoff.handoff_blockers)
    payload.setdefault("raw_worker_reply_included", handoff.raw_worker_reply_included)
    payload.setdefault("full_translation_included", handoff.full_translation_included)
    payload.setdefault("message_body_included", handoff.message_body_included)
    return payload


def _agent_for_intents(intents: list[Intent]) -> str:
    if Intent.CONTACT in intents:
        return "contact_agent"
    if Intent.HIRING in intents:
        return "workforce_agent"
    if Intent.VISA_CHECK in intents or Intent.DOCUMENT_CHECK in intents:
        return "visa_document_agent"
    return "langchain_v1_agent"
