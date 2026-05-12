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
from .checkpointing import get_async_langchain_checkpointer, runtime_checkpoint_config
from .contact_artifact_store import save_contact_artifacts
from .contact_subagents import normalize_contact_subagents_payload
from .events import event_to_reference, make_event
from .middleware import (
    SafetyValidationError,
    build_blocked_response,
    redact_pii,
    _safe_rag_contexts_from_records,
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
from .tools import RuntimePreflightError, retrieve_workforce_materials


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
        selected_agent = agent or create_workbridge_agent(
            model=model,
            checkpointer=await get_async_langchain_checkpointer(),
        )
        checkpoint_config = runtime_checkpoint_config(thread_id=runtime_input.thread_id)
        result = await _ainvoke_agent(selected_agent, runtime_input, context, checkpoint_config)
        if isinstance(result, dict) and "__interrupt__" in result:
            context.interrupt_metadata = _extract_interrupt_metadata(result)
            response = build_blocked_response(
                reason="LangChain HITL interrupt received",
                user_message=runtime_input.user_message,
            )
        else:
            response = _extract_structured_response(result)
            response.domain_payload = normalize_contact_subagents_payload(
                response.domain_payload
            )
            response.domain_payload = _normalize_visa_subagents_payload(
                response.domain_payload
            )
            if not response.rag_contexts and context.rag_contexts:
                response.rag_contexts = context.rag_contexts
            if not response.rag_contexts:
                response.rag_contexts = _retrieve_safe_rag_contexts(runtime_input, response)
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
    if context.contact_artifacts:
        save_contact_artifacts(runtime_input.request_id, context.contact_artifacts)

    state = LangChainRuntimeState(
        request_id=runtime_input.request_id,
        input=_snapshot_safe_runtime_input(runtime_input),
        raw_input_payload=dict(runtime_input.input_payload),
        structured_response=response,
        evidence_events=[event.model_dump() for event in events],
        approval=response.approval,
        interrupt_metadata=context.interrupt_metadata,
        checkpoint_metadata=_checkpoint_metadata_from_agent(
            selected_agent if "selected_agent" in locals() else None,
            runtime_input=runtime_input,
            checkpoint_config=checkpoint_config
            if "checkpoint_config" in locals()
            else runtime_checkpoint_config(thread_id=runtime_input.thread_id),
            interrupt_metadata=context.interrupt_metadata,
        ),
    )
    runtime_state_store.save(state)
    return state


def _snapshot_safe_runtime_input(runtime_input: AgentRuntimeInput) -> AgentRuntimeInput:
    payload = dict(runtime_input.input_payload)
    for key in ("worker_reply", "translated_ko", "korean_text", "translated_text", "message_body"):
        if key in payload:
            payload[key] = "[REDACTED]"
    return runtime_input.model_copy(update={"input_payload": payload})


def to_foreign_hiring_state(runtime_state: LangChainRuntimeState) -> ForeignHiringState:
    response = runtime_state.structured_response
    runtime_input = runtime_state.input
    raw_payload = runtime_state.raw_input_payload or runtime_input.input_payload
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
        user_id=runtime_state.input.user_id,
        company_id=runtime_state.input.company_id,
        worker_id=runtime_state.input.worker_id,
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
            {"id": runtime_input.worker_id, "visa_type": str(raw_payload.get("visa_type") or "E-9")}
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
    config: dict[str, Any],
) -> Any:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": _build_user_prompt(runtime_input),
            }
        ]
    }
    fallback_kwargs = (
        {"context": context, "config": config},
        {"config": config},
        {"context": context},
        {},
    )
    last_type_error: TypeError | None = None
    for kwargs in fallback_kwargs:
        try:
            return await selected_agent.ainvoke(payload, **kwargs)
        except TypeError as exc:
            if "context" not in str(exc) and "config" not in str(exc):
                raise
            last_type_error = exc
    if last_type_error is not None:
        raise last_type_error
    raise RuntimeError("LangChain agent invocation failed")


def _extract_interrupt_metadata(result: dict[str, Any]) -> dict[str, Any]:
    interrupt = result.get("__interrupt__")
    interrupt_id = ""
    if isinstance(interrupt, (list, tuple)) and interrupt:
        interrupt_id = str(getattr(interrupt[0], "id", "") or "")
    return {
        "action": "human_in_the_loop_interrupt",
        "reason": redact_pii(str(interrupt)),
        "blocked_actions": ["external_delivery_or_submission"],
        "interrupt_id": interrupt_id,
    }


def _checkpoint_metadata_from_agent(
    selected_agent: Any | None,
    *,
    runtime_input: AgentRuntimeInput,
    checkpoint_config: dict[str, Any],
    interrupt_metadata: dict[str, Any],
) -> dict[str, Any]:
    configurable = dict(checkpoint_config.get("configurable") or {})
    metadata: dict[str, Any] = {
        "thread_id": configurable.get("thread_id") or runtime_input.thread_id,
        "checkpoint_ns": configurable.get("checkpoint_ns") or "",
        "latest_checkpoint_id": None,
        "interrupt_id": interrupt_metadata.get("interrupt_id"),
        "status": "INTERRUPTED" if interrupt_metadata else "RECORDED",
        "resume_blocked_reason": None,
    }
    get_state = getattr(selected_agent, "get_state", None)
    if callable(get_state):
        try:
            state = get_state(checkpoint_config)
            state_config = dict(getattr(state, "config", {}) or {})
            state_configurable = dict(state_config.get("configurable") or {})
            metadata["latest_checkpoint_id"] = state_configurable.get("checkpoint_id")
        except Exception as exc:
            metadata["resume_blocked_reason"] = redact_pii(str(exc))
    return metadata


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


def _retrieve_safe_rag_contexts(
    runtime_input: AgentRuntimeInput,
    response: WorkBridgeAgentResponse,
) -> list[dict[str, Any]]:
    if not _should_backfill_rag_contexts(response):
        return []
    visa_type = str(runtime_input.input_payload.get("visa_type") or "E-9")
    for case_type in _rag_case_types(runtime_input, response):
        try:
            payload = retrieve_workforce_materials.invoke(
                {
                    "query": runtime_input.user_message,
                    "case_type": case_type,
                    "visa_type": visa_type,
                    "top_k": 5,
                }
            )
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        contexts = _safe_rag_contexts_from_records(payload.get("records") or [])
        if contexts:
            return contexts
    return []


def _should_backfill_rag_contexts(response: WorkBridgeAgentResponse) -> bool:
    if response.blocked_reason:
        return False
    intents = set(response.detected_intents)
    return bool(
        intents.intersection({"HIRING", "VISA_CHECK", "DOCUMENT_CHECK"})
        or response.handoff.available
    )


def _rag_case_types(
    runtime_input: AgentRuntimeInput,
    response: WorkBridgeAgentResponse,
) -> list[str]:
    explicit = runtime_input.input_payload.get("case_type")
    if explicit:
        return [str(explicit), ""]
    candidates: list[str] = []
    if "HIRING" in response.detected_intents:
        candidates.append("new_hiring")
    if (
        response.handoff.available
        or "VISA_CHECK" in response.detected_intents
        or "DOCUMENT_CHECK" in response.detected_intents
    ):
        candidates.append("stay_extension")
    candidates.append("")
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _handoff_payload(handoff: HandoffDraft) -> dict[str, Any]:
    if not handoff.available:
        return {}
    source = handoff.payload if isinstance(handoff.payload, dict) else {}
    payload: dict[str, Any] = {
        "package_type": "expert_handoff_draft",
        "approval_required": True,
        "approval": {"status": "PENDING"},
        "not_for_legal_judgment": True,
        "handoff_ready": bool(handoff.handoff_ready or source.get("handoff_ready")),
        "handoff_blockers": _safe_list(
            handoff.handoff_blockers or source.get("handoff_blockers")
        ),
        "raw_worker_reply_included": False,
        "full_translation_included": False,
        "message_body_included": False,
    }
    for key in (
        "case_type",
        "case_summary",
        "worker_summary",
        "document_summary",
        "contact_summary",
        "evidence",
        "risk_flags",
    ):
        if key in source:
            payload[key] = _safe_handoff_payload_value(key, source[key])
    return payload


def _safe_handoff_payload_value(key: str, value: Any) -> Any:
    if key == "worker_summary" and isinstance(value, dict):
        return {
            "masked_worker_id": _safe_handoff_text(value.get("masked_worker_id")),
            "visa_type": _safe_handoff_text(value.get("visa_type")),
            "stay_expires_at": _safe_handoff_text(value.get("stay_expires_at")),
            "contract_ends_at": _safe_handoff_text(value.get("contract_ends_at")),
        }
    if key == "contact_summary" and isinstance(value, dict):
        return {
            "last_contact_summary": _safe_handoff_text(value.get("last_contact_summary")),
            "message_draft_exists": value.get("message_draft_exists"),
            "raw_worker_reply_included": False,
            "full_translation_included": False,
            "message_body_included": False,
        }
    if key == "evidence" and isinstance(value, dict):
        return {
            "citation_ids": _safe_list(value.get("citation_ids")),
            "evidence_log_ids": _safe_list(value.get("evidence_log_ids")),
            "not_for_legal_judgment": True,
        }
    if key == "case_summary" and isinstance(value, dict):
        return {
            "summary": _safe_handoff_text(value.get("summary")),
            "risk_level": _safe_handoff_text(value.get("risk_level")),
            "risk_reasons": _safe_list(value.get("risk_reasons")),
        }
    if key == "document_summary" and isinstance(value, dict):
        return {
            "submitted_documents": _safe_list(value.get("submitted_documents")),
            "missing_documents": _safe_list(value.get("missing_documents")),
        }
    if key == "risk_flags":
        return _safe_list(value)
    if key == "case_type" and value is not None:
        return _safe_handoff_text(value)
    return {} if isinstance(value, dict) else _safe_list(value) if isinstance(value, list) else value


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_handoff_text(item) for item in value if item is not None]


_HANDOFF_FORBIDDEN_TEXT_MARKERS = (
    "worker_reply 원문",
    "translated_ko 전문",
    "메시지 전문",
    "여권번호",
    "외국인등록번호",
    "전화번호 전체",
    "주소 전체",
    "OCR 원문",
    "비자 가능 여부 확정",
    "비자 승인 확정",
    "법률 판단 확정",
    "노무 판단 확정",
)


def _safe_handoff_text(value: Any) -> str | None:
    if value is None:
        return None
    text = redact_pii(str(value))
    if any(marker in text for marker in _HANDOFF_FORBIDDEN_TEXT_MARKERS):
        return "담당자 검토가 필요한 항목입니다."
    return text


def _normalize_visa_subagents_payload(domain_payload: dict[str, Any]) -> dict[str, Any]:
    """LLM이 채운 visa_subagents를 민감정보 마스킹 후 유지. 없으면 그대로 반환."""
    visa = domain_payload.get("visa_subagents")
    if not isinstance(visa, dict):
        return domain_payload

    _VISA_FORBIDDEN_KEYS = {"worker_id", "passport_number", "alien_registration_number", "phone"}
    sanitized: dict[str, Any] = {}
    for agent_key, agent_val in visa.items():
        if not isinstance(agent_val, dict):
            sanitized[agent_key] = agent_val
            continue
        sanitized[agent_key] = {
            k: v for k, v in agent_val.items() if k not in _VISA_FORBIDDEN_KEYS
        }

    return {**domain_payload, "visa_subagents": sanitized}


def _agent_for_intents(intents: list[Intent]) -> str:
    if Intent.CONTACT in intents:
        return "contact_agent"
    if Intent.HIRING in intents:
        return "workforce_agent"
    if Intent.VISA_CHECK in intents or Intent.DOCUMENT_CHECK in intents:
        return "visa_document_agent"
    return "langchain_v1_agent"
