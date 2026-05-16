from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic import model_validator
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.agent_runtime.runner import run_workflow
from app.agent_runtime.schemas import ForeignHiringState
from backend.app.db.session import get_sync_db
from backend.app.models.worker import Worker
from backend.app.services.langchain_checkpoint_service import (
    LangChainCheckpointConflictError,
    LangChainCheckpointForbiddenError,
    LangChainCheckpointNotFoundError,
    resume_langchain_checkpoint_for_company,
)
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from backend.app.services.runtime_state_persistence_service import (
    get_runtime_state_snapshot,
    save_runtime_state_snapshot,
)
from backend.app.services.runtime_metrics_service import (
    RuntimeMetricsForbiddenError,
    RuntimeMetricsNotFoundError,
    get_runtime_metrics_summary_for_company,
    get_runtime_metrics_for_company,
)
from backend.app.services.runtime_resume_service import (
    RuntimeResumeForbiddenError,
    RuntimeResumeNotFoundError,
    get_runtime_resume_summary_for_company,
    resume_runtime_action_for_company,
)
from backend.app.services.runtime_outbox_service import (
    RuntimeOutboxConflictError,
    RuntimeOutboxForbiddenError,
    RuntimeOutboxNotFoundError,
    prepare_runtime_delivery_outbox_for_company,
)
from backend.app.services.agent_service import (
    AgentRunRequest as ContactAgentRunRequest,
    HandoffResponse,
    build_handoff_response,
    run_agent as run_contact_agent,
)
from backend.app.agent_runtime.langchain_v1.contact_artifact_store import (
    pop_contact_artifacts,
)
from backend.app.agent_runtime.langchain_v1.contact_subagents import (
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
    run_contact_onboarding_subagent,
    run_worker_reply_interpreter_subagent,
)
from backend.app.services.contact_persistence_service import (
    SourceMessageValidationError,
    resolve_source_message_for_status_update,
    save_message_draft_result,
    save_worker_reply_summary_result,
)
from backend.app.services.handoff_persistence_service import save_handoff_package_draft
from app.services.agent_chat_rag import (
    RAGFirstChatContext,
    prepare_agent_chat_rag_first,
    rag_first_forbidden_response,
    rag_first_not_found_response,
    run_agent_chat_rag_first,
)
from app.services.context_data_service import DOCUMENT_LABELS
from app.services.daily_briefing_planner import plan_daily_briefing_from_message
from app.services.daily_briefing_service import build_sqlalchemy_daily_briefing_service


router = APIRouter(prefix="/agent", tags=["agent"])

_DEMO_RESPONSES: list[tuple[tuple[str, ...], str]] = [
    (
        ("비자 만료", "만료되는 직원", "비자 끝나는", "체류 만료"),
        "비자 만료가 임박하거나 이미 만료된 직원이 5명 있습니다. Dang T.와 Nguyen V.는 이미 만료 상태이며 누락 서류도 있어 즉시 조치가 필요합니다.",
    ),
    (
        ("사람 더 필요", "인원 더", "채용 필요", "사람이 더", "사람 필요"),
        "어떤 역할로 몇 명이 필요한지 알려주시면 채용 요청서 초안을 만들어드리겠습니다. 현재 외국인 고용 허가 잔여 쿼터와 숙소 가용 여부도 함께 확인해드립니다.",
    ),
    (
        ("베트남어로", "여권 보내달라", "여권 요청", "베트남어 메시지"),
        "베트남어 메시지 초안입니다.\n\n[한국어 원문]\n여권 사본을 제출해 주세요.\n\n[베트남어]\nKính gửi,\n\nĐể hoàn tất hồ sơ lao động, vui lòng nộp bản sao hộ chiếu trong vòng 5 ngày làm việc.\n\nCảm ơn sự hợp tác của bạn.",
    ),
]


def _demo_fixed_response(message: str) -> str | None:
    for keywords, answer in _DEMO_RESPONSES:
        if any(kw in message for kw in keywords):
            return answer
    return None


# ---------------------------------------------------------------------------
# 인텐트 분류 (RAG 없이 구어체 직접 매칭)
# ---------------------------------------------------------------------------

_VISA_INTENTS = frozenset({"visa_expiry", "document_gap", "contract_visa_conflict"})
_MULTILINGUAL_INTENTS = frozenset({"document_request_message"})
_HIRING_INTENTS = frozenset({"quota_review", "candidate_readiness", "reporting_deadline", "handoff_preview"})
_AGENT_DISPATCHABLE_INTENTS = _VISA_INTENTS | _MULTILINGUAL_INTENTS | _HIRING_INTENTS
_ENABLE_PRE_RAG_AGENT_DISPATCH = True

_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("비자", "체류", "만료", "갱신", "끝나는", "기간 만료"), "visa_expiry"),
    (("서류", "누락", "빠진", "미제출", "제출 안"), "document_gap"),
    (("계약", "날짜", "안 맞", "안맞", "충돌"), "contract_visa_conflict"),
    (("베트남어", "네팔어", "인도네시아어", "다국어", "번역", "메시지 만들", "안내문"), "document_request_message"),
    (("신고", "변동", "기한", "고용변동"), "reporting_deadline"),
    (("후보자", "채용", "뽑", "쿼터", "인원"), "quota_review"),
    (("행정사", "전문가", "검토패키지", "검토 패키지"), "handoff_preview"),
]


def _classify_intent_from_message(message: str) -> str:
    from app.services.agent_chat_rag import _exact_phrase_intent
    phrase = _exact_phrase_intent(message)
    if phrase and phrase != "unsupported":
        return phrase
    if any(keyword in message for keyword in ("누락", "빠진", "미제출", "제출 안", "없는")):
        if any(keyword in message for keyword in ("비자", "체류", "갱신", "서류", "인원", "사람")):
            return "document_gap"
    best, best_count = "daily_briefing", 0
    for keywords, intent in _KEYWORD_MAP:
        count = sum(1 for kw in keywords if kw in message)
        if count > best_count:
            best_count, best = count, intent
    return best


def _agent_dispatch_response(
    dispatch: Any,
    briefing: Any,
    intent: str,
) -> dict[str, Any]:
    selected_items = _select_daily_briefing_items(briefing.items, intent)
    actions = _selected_actions(briefing.recommended_actions, selected_items)
    sources = _selected_sources(briefing.citation_summaries, selected_items)
    return {
        "answer": dispatch.answer,
        "final_response": dispatch.answer,
        "route": "rag_first_chat",
        "orchestration_version": "agent_dispatch_v1",
        "normalized_intent": intent,
        "agent_used": dispatch.agent_used,
        "rag_collections_used": dispatch.rag_collections_used,
        "agent_sub_agents": dispatch.sub_agents,
        "llm_used": False,
        "latency_mode": "agent_dispatch",
        "tool_calls": [{"name": dispatch.agent_used, "route": "rag_first_chat",
                        "intent": intent, "result_count": len(selected_items),
                        "action_count": len(actions), "source_count": len(sources)}],
        "rag_hits": [],
        "retrieval_source_types": dispatch.rag_collections_used,
        "llm_provider": None,
        "fallback_used": False,
        "fallback_reason": None,
        "actions": [a.model_dump() for a in actions] if dispatch.approval_required else [],
        "sources": [s.model_dump() for s in sources],
        "detected_intents": [intent],
        "approval_required": dispatch.approval_required,
        "approval_status": "pending" if dispatch.approval_required else "not_required",
        "daily_briefing": briefing.model_dump(),
        "structured_plan": {
            "should_run": True,
            "intent": intent,
            "plan_steps": [],
            "required_context": [],
            "entities": {},
            "blocked_actions": [],
            "approval_required": dispatch.approval_required,
            "execution_allowed": True,
            "target_service": "agent_dispatch",
        },
    }


RISK_TYPES_BY_INTENT: dict[str, tuple[str, ...]] = {
    "visa_expiry": ("visa_expiry", "missing_document", "contract_visa_conflict"),
    "document_gap": ("missing_document", "candidate_readiness"),
    "document_request_message": ("missing_document",),
    "contract_visa_conflict": ("contract_visa_conflict",),
    "reporting_deadline": ("reporting_deadline",),
    "quota_review": ("quota_review", "candidate_readiness"),
    "candidate_readiness": ("candidate_readiness",),
    "handoff_preview": (
        "visa_expiry",
        "missing_document",
        "contract_visa_conflict",
        "reporting_deadline",
    ),
    "evidence_audit_review": (
        "reporting_deadline",
        "contract_visa_conflict",
        "visa_expiry",
        "missing_document",
        "quota_review",
        "candidate_readiness",
    ),
}

INTENT_LABELS: dict[str, str] = {
    "visa_expiry": "비자 관련 업무",
    "document_gap": "서류 누락 업무",
    "contract_visa_conflict": "계약-체류기간 충돌 검토 업무",
    "reporting_deadline": "신고기한 업무",
    "quota_review": "채용/쿼터 검토 업무",
    "handoff_preview": "전문가 검토 패키지 업무",
    "document_request_message": "다국어 서류 요청 메시지 업무",
    "candidate_readiness": "후보자 서류 준비상태 확인 업무",
    "evidence_audit_review": "근거/감사 재현 업무",
    "daily_briefing": "오늘 확인할 외국인 고용 업무",
}

RISK_LABELS: dict[str, str] = {
    "visa_expiry": "체류기간 연장 준비",
    "missing_document": "체류/고용 서류 누락 확인",
    "contract_visa_conflict": "계약-체류기간 충돌 검토",
    "reporting_deadline": "고용변동 신고기한 확인",
    "quota_review": "신규 인력/쿼터 검토",
    "candidate_readiness": "후보자 서류 준비상태 확인",
}



class AgentRunRequest(BaseModel):
    user_message: str | None = None
    user_request: str | None = None
    user_id: str = ""
    company_id: str = ""
    thread_id: str | None = None
    persist_result: bool = False
    worker_id: str | None = None
    created_by: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _has_message(self) -> "AgentRunRequest":
        if not (self.user_message or self.user_request):
            raise ValueError("user_message or user_request is required")
        return self

    @property
    def normalized_message(self) -> str:
        return (self.user_message or self.user_request or "").strip()


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    company_id: str = Field(default="company_001", alias="companyId")
    user_id: str = Field(default="manager_001", alias="userId")
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    active_tab: str | None = Field(default=None, alias="activeTab")
    date: str | None = None
    selected_case_id: str | None = Field(default=None, alias="selectedCaseId")
    selected_action_id: str | None = Field(default=None, alias="selectedActionId")
    session_id: str | None = Field(default=None, alias="sessionId")


class AgentRunResponse(BaseModel):
    request_id: str
    final_response: str
    detected_intents: list[str]
    risk_flags: list[str]
    approval_required: bool
    approval_status: str
    handoff: HandoffResponse = Field(
        default_factory=lambda: HandoffResponse(available=False)
    )
    persistence: dict[str, Any] = Field(default_factory=dict)
    evidence_event_count: int
    rag_context_count: int
    daily_briefing: dict[str, Any] | None = None
    structured_plan: dict[str, Any] | None = None


class AgentResumeRequest(BaseModel):
    action_type: str


class AgentCheckpointResumeRequest(BaseModel):
    action_type: str
    resume_value: Any | None = None


@router.post("/chat")
async def chat_agent(
    request: AgentChatRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    # --- 데모 고정 응답 (시현용) ---
    _demo_answer = _demo_fixed_response(request.message)
    if _demo_answer:
        return {
            "answer": _demo_answer,
            "final_response": _demo_answer,
            "route": "demo_fixed",
            "llm_used": False,
            "latency_mode": "demo",
            "tool_calls": [],
            "rag_hits": [],
            "retrieval_source_types": [],
            "llm_provider": None,
            "fallback_used": False,
            "fallback_reason": None,
            "actions": [],
            "sources": [],
            "detected_intents": ["demo"],
            "approval_required": False,
            "structured_plan": {},
        }
    # --- 데모 고정 응답 끝 ---

    daily_briefing_plan = plan_daily_briefing_from_message(request.message)
    if not daily_briefing_plan.should_run and daily_briefing_plan.intent == "forbidden":
        return {
            "answer": "처리 가능한 외국인 고용 운영 질문으로 다시 입력해 주세요.",
            "final_response": "처리 가능한 외국인 고용 운영 질문으로 다시 입력해 주세요.",
            "route": "unsupported",
            "llm_used": False,
            "latency_mode": "fast_guardrail",
            "tool_calls": [],
            "rag_hits": [],
            "retrieval_source_types": [],
            "llm_provider": None,
            "fallback_used": False,
            "fallback_reason": None,
            "actions": [],
            "sources": [],
            "detected_intents": [daily_briefing_plan.intent or "unknown"],
            "approval_required": daily_briefing_plan.approval_required,
            "structured_plan": daily_briefing_plan.model_dump(),
        }

    # 1단계: 구어체 인텐트 직접 분류 → 에이전트 디스패치 (RAG 실패 우회)
    quick_intent = _classify_intent_from_message(request.message)
    if quick_intent in _AGENT_DISPATCHABLE_INTENTS:
        from app.services.agent_chat_rag import _is_hiring_start_question, _is_policy_faq

        should_skip_quick_dispatch = (
            bool(request.selected_case_id or request.selected_action_id)
            or quick_intent in _HIRING_INTENTS
            and (
                _is_hiring_start_question(request.message)
                or _is_policy_faq(request.message)
            )
        )
    else:
        should_skip_quick_dispatch = False

    if (
        _ENABLE_PRE_RAG_AGENT_DISPATCH
        and quick_intent in _AGENT_DISPATCHABLE_INTENTS
        and not should_skip_quick_dispatch
    ):
        try:
            _svc = build_sqlalchemy_daily_briefing_service(db)
            _briefing = _svc.run_daily_briefing(
                company_id=request.company_id,
                date=request.date,
                user_role=x_user_role,
                allowed_company_ids=[x_company_id] if x_company_id else None,
            )
            db.commit()
            from app.services.agent_dispatcher import dispatch_to_agent
            from app.services.agent_chat_rag import RAGFirstChatContext as _RCtx
            _selected = _select_daily_briefing_items(_briefing.items, quick_intent)
            _ctx = _RCtx(
                company_id=request.company_id,
                user_role=x_user_role,
                fallback_plan={},
                date=request.date,
                workspace_id=request.workspace_id,
                active_tab=request.active_tab,
                selected_case_id=request.selected_case_id,
                selected_action_id=request.selected_action_id,
            )
            _dispatch = dispatch_to_agent(
                intent=quick_intent,
                message=request.message,
                company_id=request.company_id,
                daily_briefing=_briefing,
                selected_items=_selected,
                context=_ctx,
            )
            if not _dispatch.skipped:
                return _agent_dispatch_response(_dispatch, _briefing, quick_intent)
        except Exception as _exc:
            logger.warning("에이전트 디스패치 실패, RAG-first 폴백: %s", _exc)

    preflight = prepare_agent_chat_rag_first(request.message)
    if preflight.blocked:
        return rag_first_forbidden_response(message=request.message, preflight=preflight)
    if not preflight.rag_results and preflight.intent == "unsupported":
        return rag_first_not_found_response(message=request.message, preflight=preflight)

    try:
        service = build_sqlalchemy_daily_briefing_service(db)
        result = service.run_daily_briefing(
            company_id=request.company_id,
            date=request.date,
            user_role=x_user_role,
            allowed_company_ids=[x_company_id] if x_company_id else None,
        )
        db.commit()
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": str(e.args[0]) if e.args else "TENANT_SCOPE_VIOLATION",
                "message": "Requested company is outside the allowed company scope.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except LookupError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": str(e.args[0]) if e.args else "MISSING_REQUIRED_CONTEXT",
                "message": "Required company or worker context is missing.",
                "trace_id": "trace_unavailable",
            },
        ) from e

    try:
        return run_agent_chat_rag_first(
            message=request.message,
            daily_briefing=result,
            context=RAGFirstChatContext(
                company_id=request.company_id,
                user_role=x_user_role,
                fallback_plan=daily_briefing_plan.model_dump(),
                date=request.date,
                workspace_id=request.workspace_id,
                active_tab=request.active_tab,
                selected_case_id=request.selected_case_id,
                selected_action_id=request.selected_action_id,
            ),
            preflight=preflight,
        )
    except Exception:
        if not daily_briefing_plan.should_run:
            state = await run_workflow(
                user_message=request.message,
                user_id=request.user_id,
                company_id=request.company_id,
                thread_id=request.session_id,
            )
            return _agent_runtime_chat_response(
                state,
                daily_briefing_plan.model_dump(),
                fallback_used=True,
                fallback_reason="rag_first_failed",
            )

    return _daily_briefing_chat_response(
        result,
        daily_briefing_plan.intent,
        fallback_used=True,
        fallback_reason="rag_first_failed",
    )


def _daily_briefing_chat_response(
    result: Any,
    intent: str | None,
    *,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    selected_items = _select_daily_briefing_items(
        result.items,
        intent,
    )
    actions = _selected_actions(result.recommended_actions, selected_items)
    sources = _selected_sources(result.citation_summaries, selected_items)
    answer = _daily_briefing_answer(
        result,
        intent,
        selected_items=selected_items,
        selected_actions=actions,
    )
    display_context = _display_context(selected_items, actions, sources)
    return {
        "answer": answer,
        "final_response": answer,
        "route": "daily_briefing_service",
        "llm_used": False,
        "latency_mode": "fast_operational",
        "tool_calls": [
            _tool_trace(
                "daily_briefing_lookup",
                intent,
                selected_items,
                actions,
                sources,
            )
        ],
        "rag_hits": [],
        "retrieval_source_types": [],
        "llm_provider": None,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "actions": [action.model_dump() for action in actions],
        "sources": [source.model_dump() for source in sources],
        **display_context,
        "detected_intents": [intent or "daily_briefing"],
        "approval_required": result.approval_required,
        "approval_status": "pending" if result.approval_required else "not_required",
        "daily_briefing": result.model_dump(),
        "structured_plan": {
            "should_run": True,
            "intent": intent or "daily_briefing",
            "plan_steps": [],
            "required_context": [],
            "entities": {},
            "blocked_actions": [],
            "approval_required": True,
            "execution_allowed": True,
            "target_service": "daily_briefing",
        },
    }


def _agent_runtime_chat_response(
    state: ForeignHiringState,
    structured_plan: dict[str, Any],
    *,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    tool_calls = [
        {
            "name": result.get("agent", "agent_runtime"),
            "route": "agent_runtime_workflow",
            "intent": state.detected_intents[0].value if state.detected_intents else "unknown",
            "result_count": int(result.get("tool_calls") or 0),
            "action_count": 0,
            "source_count": len(state.rag_contexts),
        }
        for result in state.agent_results
        if isinstance(result, dict)
    ]
    if not tool_calls:
        tool_calls.append(
            {
                "name": "agent_runtime_workflow",
                "route": "agent_runtime_workflow",
                "intent": state.detected_intents[0].value if state.detected_intents else "unknown",
                "result_count": len(state.tool_results),
                "action_count": 0,
                "source_count": len(state.rag_contexts),
            }
        )

    return {
        "answer": state.final_response,
        "final_response": state.final_response,
        "route": "agent_runtime_workflow",
        "llm_used": True,
        "latency_mode": "llm_agent_runtime",
        "tool_calls": tool_calls,
        "rag_hits": [],
        "retrieval_source_types": [],
        "llm_provider": None,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "actions": [],
        "sources": [],
        "detected_intents": [intent.value for intent in state.detected_intents],
        "approval_required": state.approval.required,
        "approval_status": state.approval.status,
        "daily_briefing": None,
        "structured_plan": structured_plan,
    }


@router.post("/run")
async def run_agent(
    body: dict[str, Any] = Body(...),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    if "user_request" in body and "user_message" not in body:
        contact_payload = dict(body.get("input_payload") or {})
        for key in ("worker_id", "company_id", "persist_result", "created_by", "user_id"):
            if key in body and key not in contact_payload:
                contact_payload[key] = body[key]
        contact_request = ContactAgentRunRequest(
            user_request=str(body["user_request"]),
            input_payload=contact_payload,
        )
        return run_contact_agent(contact_request, db=db).model_dump()

    try:
        request = AgentRunRequest.model_validate(body)
        normalized_payload, resolved_worker_id = _normalize_worker_lookup(
            db,
            company_id=request.company_id,
            worker_id=request.worker_id or "",
            input_payload=request.input_payload,
        )
        daily_briefing_plan = plan_daily_briefing_from_message(request.normalized_message)
        if daily_briefing_plan.should_run:
            try:
                service = build_sqlalchemy_daily_briefing_service(db)
                result = service.run_daily_briefing(
                    company_id=request.company_id,
                    date=None,
                    user_role=x_user_role,
                    allowed_company_ids=[x_company_id] if x_company_id else None,
                )
                db.commit()
                selected_items = _select_daily_briefing_items(
                    result.items,
                    daily_briefing_plan.intent,
                )
                selected_actions = _selected_actions(
                    result.recommended_actions,
                    selected_items,
                )
                return AgentRunResponse(
                    request_id=result.briefing_run_id,
                    final_response=_daily_briefing_answer(
                        result,
                        daily_briefing_plan.intent,
                        selected_items=selected_items,
                        selected_actions=selected_actions,
                    ),
                    detected_intents=[daily_briefing_plan.intent or "daily_briefing"],
                    risk_flags=[
                        item.risk_type
                        for item in result.items
                        if item.severity in {"CRITICAL", "HIGH"}
                    ],
                    approval_required=result.approval_required,
                    approval_status="pending" if result.approval_required else "not_required",
                    evidence_event_count=len(result.evidence_event_ids),
                    rag_context_count=len(
                        [
                            summary
                            for summary in result.citation_summaries
                            if summary.validation_status == "validated"
                        ]
                    ),
                    daily_briefing=result.model_dump(),
                    structured_plan=daily_briefing_plan.model_dump(),
                ).model_dump()
            except LookupError:
                db.rollback()
        state: ForeignHiringState = await run_workflow(
            user_message=request.normalized_message,
            user_id=request.user_id,
            company_id=request.company_id,
            worker_id=resolved_worker_id,
            thread_id=request.thread_id,
            input_payload=normalized_payload,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": str(e.args[0]) if e.args else "TENANT_SCOPE_VIOLATION",
                "message": "Requested company is outside the allowed company scope.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except LookupError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": str(e.args[0]) if e.args else "MISSING_REQUIRED_CONTEXT",
                "message": "Required company or worker context is missing.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": str(e.args[0]) if e.args else "STATE_SAVE_FAILED",
                "message": "Agent request failed safely.",
                "trace_id": "trace_unavailable",
            },
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    runtime_state = runtime_state_store.get(state.request_id)
    raw_runtime_payload = (
        dict(runtime_state.raw_input_payload)
        if runtime_state is not None and runtime_state.raw_input_payload
        else normalized_payload
    )
    if runtime_state is not None:
        try:
            save_runtime_state_snapshot(db, runtime_state)
            db.commit()
        except Exception:
            db.rollback()

    contact_artifacts = pop_contact_artifacts(state.request_id)
    handoff_persistence: dict[str, Any] | None = None
    contact_message_persistence: dict[str, Any] | None = None
    status_update_persistence: dict[str, Any] | None = None
    if request.persist_result:
        try:
            if state.handoff_package_draft:
                handoff_persistence = save_handoff_package_draft(
                    db,
                    request_id=state.request_id,
                    handoff_package_draft=state.handoff_package_draft,
                    worker_id=resolved_worker_id,
                    company_id=request.company_id,
                    created_by=request.created_by or request.user_id,
                )
            contact_message_persistence = _save_contact_message_artifact(
                db,
                request=request,
                request_id=state.request_id,
                worker_id=resolved_worker_id,
                input_payload=raw_runtime_payload,
                artifacts=contact_artifacts,
            )
            status_update_persistence = _save_worker_reply_artifact(
                db,
                request=request,
                request_id=state.request_id,
                worker_id=resolved_worker_id,
                input_payload=raw_runtime_payload,
                artifacts=contact_artifacts,
            )
            if handoff_persistence or contact_message_persistence or status_update_persistence:
                db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e)) from e

    handoff_response = build_handoff_response(state.handoff_package_draft, handoff_persistence)
    persistence_response = _build_persistence_response(
        enabled=request.persist_result,
        handoff_persistence=handoff_persistence,
        contact_message_persistence=contact_message_persistence,
        status_update_persistence=status_update_persistence,
        contact_artifacts=contact_artifacts,
    )
    approval_required = _effective_approval_required(
        state_approval_required=state.approval.required,
        state_approval_status=state.approval.status,
        handoff_response=handoff_response,
        persistence_response=persistence_response,
    )
    approval_status = state.approval.status
    if approval_required and str(approval_status).upper() in {"", "NOT_REQUIRED", "NONE"}:
        approval_status = "PENDING"

    return AgentRunResponse(
        request_id=state.request_id,
        final_response=state.final_response,
        detected_intents=[i.value for i in state.detected_intents],
        risk_flags=state.risk_flags,
        approval_required=approval_required,
        approval_status=approval_status,
        handoff=handoff_response,
        persistence=persistence_response,
        evidence_event_count=len(state.evidence_events),
        rag_context_count=len(state.rag_contexts),
    ).model_dump()


def _effective_approval_required(
    *,
    state_approval_required: bool,
    state_approval_status: str | None,
    handoff_response: HandoffResponse,
    persistence_response: dict[str, Any],
) -> bool:
    if state_approval_required:
        return True
    if str(state_approval_status or "").upper() == "PENDING":
        return True
    if handoff_response.available:
        return True

    handoff = persistence_response.get("handoff", {})
    contact_message = persistence_response.get("contact_message", {})
    status_update_candidates = persistence_response.get("status_update_candidates", {})
    return bool(
        handoff.get("saved")
        or contact_message.get("saved")
        or status_update_candidates.get("saved")
    )


def _save_contact_message_artifact(
    db: Session,
    *,
    request: AgentRunRequest,
    request_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = artifacts.get(CONTACT_ONBOARDING_SUB_AGENT)
    if not _is_persistable_contact_artifact(artifact):
        artifact = _build_contact_onboarding_artifact_from_input(
            db=db,
            request=request,
            worker_id=worker_id,
            input_payload=input_payload,
        )
    if not _is_persistable_contact_artifact(artifact):
        return None
    if not request.company_id or not worker_id:
        return None
    message = save_message_draft_result(
        db,
        agent_result=artifact,
        worker_id=worker_id,
        company_id=request.company_id,
        created_by=request.created_by or request.user_id,
        request_id=request_id,
    )
    return {
        "contact_message_id": message.id,
        "approval_id": message.approval_id,
        "status": message.status,
    }


def _select_daily_briefing_items(
    items: list[Any],
    intent: str | None,
) -> list[Any]:
    risk_types = RISK_TYPES_BY_INTENT.get(intent or "")
    if not risk_types:
        return items[:5]
    selected = [item for item in items if item.risk_type in risk_types]
    return selected[:5]


def _selected_actions(actions: list[Any], items: list[Any]) -> list[Any]:
    action_ids = {
        action_id
        for item in items
        for action_id in item.next_action_ids
    }
    return [action for action in actions if action.action_id in action_ids]


def _selected_sources(sources: list[Any], items: list[Any]) -> list[Any]:
    citation_ids = {
        citation_id
        for item in items
        for citation_id in item.citation_ids
    }
    return [source for source in sources if source.citation_id in citation_ids]


def _tool_trace(
    name: str,
    intent: str | None,
    items: list[Any],
    actions: list[Any],
    sources: list[Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "route": "daily_briefing_service",
        "intent": intent or "daily_briefing",
        "result_count": len(items),
        "action_count": len(actions),
        "source_count": len(sources),
    }


def _display_context(
    selected_items: list[Any],
    actions: list[Any],
    sources: list[Any],
) -> dict[str, Any]:
    item = selected_items[0] if selected_items else None
    primary_action = actions[0].model_dump() if actions else None
    if item is None:
        return {
            "subject_display_name": None,
            "subject_display_id": None,
            "risk_timing_label": None,
            "case_title": None,
            "case_summary": None,
            "primary_action": primary_action,
            "source_labels": [source.title for source in sources],
        }
    return {
        "subject_display_name": getattr(item, "subject_display_name", item.subject_id),
        "subject_display_id": getattr(item, "subject_display_id", item.subject_id),
        "risk_timing_label": getattr(item, "risk_timing_label", _risk_timing(item)),
        "case_title": getattr(item, "case_title", None),
        "case_summary": getattr(item, "case_summary", None),
        "primary_action": primary_action or getattr(item, "primary_action", None),
        "source_labels": getattr(item, "source_labels", None) or [source.title for source in sources],
    }


def _daily_briefing_answer(
    result: Any,
    intent: str | None,
    *,
    selected_items: list[Any],
    selected_actions: list[Any],
) -> str:
    label = INTENT_LABELS.get(intent or "", INTENT_LABELS["daily_briefing"])
    if intent == "evidence_audit_review":
        citation_count = len(
            {
                citation_id
                for item in selected_items
                for citation_id in item.citation_ids
            }
        )
        return "\n".join(
            [
                f"오늘 기준 {label} {len(selected_items)}건입니다.",
                f"- 재현 가능한 Evidence/Audit Review 케이스: {len(result.evidence_event_ids)}개 이벤트",
                f"- 연결된 근거 문서: {citation_count}개 citation",
                "- 다음 처리: 판단 기록 열람 / 근거 문서 확인 / 담당자 승인 이력 확인",
                "민감정보 원문은 응답에 포함하지 않았고, 외부 발송이나 제출은 수행하지 않았습니다.",
            ]
        )
    if not selected_items:
        return (
            f"오늘 기준 {label}는 확인된 항목이 없습니다. "
            "외부 발송이나 제출은 수행하지 않았습니다."
        )

    actions_by_id = {action.action_id: action for action in selected_actions}
    lines = [f"오늘 기준 {label} {len(selected_items)}건입니다."]
    for item in selected_items:
        action_labels = [
            _action_label(actions_by_id[action_id])
            for action_id in item.next_action_ids
            if action_id in actions_by_id
        ]
        if action_labels:
            action_labels.append("담당자 승인 요청")
        else:
            action_labels.append("담당자 확인")
        lines.append(
            "- "
            f"{item.subject_id}: "
            f"{RISK_LABELS.get(item.risk_type, item.risk_type)} "
            f"({_risk_timing(item)}, {item.severity})"
        )
        lines.append(f"  누락 서류: {_document_list(item.missing_documents)}")
        lines.append(f"  다음 처리: {' / '.join(dict.fromkeys(action_labels))}")
    lines.append("외부 발송, 정부 제출, 상태 완료 처리는 아직 수행하지 않았습니다.")
    return "\n".join(lines)


def _risk_timing(item: Any) -> str:
    if item.expired:
        if item.days_overdue is not None:
            return f"만료 후 {item.days_overdue}일 경과"
        return "기한 경과"
    if item.d_day is not None:
        return f"D-{item.d_day}"
    return "기한 확인 필요"


def _document_list(documents: list[str]) -> str:
    if not documents:
        return "현재 응답 범위에서 확인된 누락 없음"
    return ", ".join(DOCUMENT_LABELS.get(document, document) for document in documents)


def _action_label(action: Any) -> str:
    if action.action_type == "request_document":
        return "누락서류 요청 초안 보기"
    if action.action_type == "create_handoff":
        return "전문가 검토 패키지 초안 보기"
    return str(action.label)



def _is_persistable_contact_artifact(artifact: Any) -> bool:
    return (
        isinstance(artifact, dict)
        and str(artifact.get("status") or "").upper() == "SUCCESS"
        and bool(artifact.get("korean_text"))
        and bool(artifact.get("message_purpose"))
        and bool(artifact.get("language_code"))
    )


def _build_contact_onboarding_artifact_from_input(
    *,
    db: Session,
    request: AgentRunRequest,
    worker_id: str,
    input_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not worker_id:
        return None
    language_code = input_payload.get("language_code")
    message_purpose = input_payload.get("message_purpose")
    if not language_code or not message_purpose:
        return None
    try:
        return run_contact_onboarding_subagent(
            worker_id=worker_id,
            language_code=str(language_code),
            message_purpose=str(message_purpose),
            user_request=request.normalized_message,
            due_date=input_payload.get("due_date"),
            contact_person=str(input_payload.get("contact_person") or "담당자"),
            training_date=input_payload.get("training_date"),
            training_time=input_payload.get("training_time"),
            location=input_payload.get("location"),
            worker_name=input_payload.get("worker_name")
            or _worker_name_for_persistence(db, worker_id, request.company_id)
            or _worker_name_hint_from_message(request.normalized_message),
        )
    except Exception:
        return None


def _worker_name_for_persistence(
    db: Session,
    worker_id: str,
    company_id: str,
) -> str | None:
    if not worker_id or not company_id:
        return None
    worker = db.get(Worker, worker_id)
    if worker is None or worker.company_id != company_id:
        return None
    return worker.name


def _worker_name_hint_from_message(message: str) -> str | None:
    match = re.search(r"(?:직원|근로자)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})", message)
    if match:
        return match.group(1).strip()
    match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", message)
    return match.group(1).strip() if match else None


def _save_worker_reply_artifact(
    db: Session,
    *,
    request: AgentRunRequest,
    request_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = artifacts.get(WORKER_REPLY_INTERPRETER_SUB_AGENT)
    if not _is_persistable_worker_reply_artifact(artifact):
        artifact = _build_worker_reply_artifact_from_input(
            worker_id=worker_id,
            input_payload=input_payload,
        )
    if not _is_persistable_worker_reply_artifact(artifact):
        return None
    if not request.company_id or not worker_id:
        return None
    source_message_id = input_payload.get("source_message_id")
    if source_message_id:
        try:
            resolve_source_message_for_status_update(
                db,
                source_message_id=str(source_message_id),
                company_id=request.company_id,
                worker_id=worker_id,
            )
        except SourceMessageValidationError as exc:
            return {
                "saved": False,
                "reason": exc.reason,
                "status_update_candidate_ids": [],
                "approval_ids": [],
            }
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=artifact,
        worker_id=worker_id,
        company_id=request.company_id,
        request_id=request_id,
        source_message_id=str(source_message_id) if source_message_id else None,
        requested_by=request.created_by or request.user_id,
        worker_reply=input_payload.get("worker_reply"),
    )
    result = {
        "saved": True,
        "status_update_candidate_ids": [candidate.id for candidate in candidates],
        "approval_ids": [
            candidate.approval_id for candidate in candidates if candidate.approval_id
        ],
    }
    if source_message_id:
        result["source_message_id"] = str(source_message_id)
    return result


def _is_persistable_worker_reply_artifact(artifact: Any) -> bool:
    return (
        isinstance(artifact, dict)
        and str(artifact.get("status") or "").upper() == "SUCCESS"
        and artifact.get("manager_review_required") is True
        and bool(artifact.get("status_update_candidates"))
    )


def _build_worker_reply_artifact_from_input(
    *,
    worker_id: str,
    input_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not worker_id:
        return None
    if input_payload.get("task_type") != "worker_reply_summary":
        return None
    language_code = input_payload.get("language_code")
    worker_reply = input_payload.get("worker_reply")
    if not language_code or not worker_reply:
        return None
    try:
        artifact = run_worker_reply_interpreter_subagent(
            worker_id=worker_id,
            language_code=str(language_code),
            worker_reply=str(worker_reply),
            use_llm_translation=bool(input_payload.get("use_llm_translation", False)),
        )
    except Exception:
        return None
    artifact.pop("worker_reply", None)
    return artifact


def _build_persistence_response(
    *,
    enabled: bool,
    handoff_persistence: dict[str, Any] | None,
    contact_message_persistence: dict[str, Any] | None,
    status_update_persistence: dict[str, Any] | None,
    contact_artifacts: dict[str, Any],
) -> dict[str, Any]:
    handoff_saved = bool(handoff_persistence)
    contact_saved = bool(contact_message_persistence)
    status_update_saved = bool(
        status_update_persistence and status_update_persistence.get("saved", True)
    )
    contact_artifact_available = CONTACT_ONBOARDING_SUB_AGENT in contact_artifacts
    worker_reply_artifact_available = WORKER_REPLY_INTERPRETER_SUB_AGENT in contact_artifacts
    return {
        "enabled": enabled,
        "saved": bool(enabled and (handoff_saved or contact_saved or status_update_saved)),
        "handoff": (
            {
                "saved": True,
                "draft_id": handoff_persistence.get("handoff_package_draft_id"),
                "approval_id": handoff_persistence.get("approval_id"),
                "status": handoff_persistence.get("status"),
            }
            if handoff_saved
            else {"saved": False, "reason": "handoff package draft not available"}
        ),
        "contact_message": (
            {
                "saved": True,
                "id": contact_message_persistence.get("contact_message_id"),
                "approval_id": contact_message_persistence.get("approval_id"),
                "status": contact_message_persistence.get("status"),
            }
            if contact_saved
            else {
                "saved": False,
                "reason": "contact artifact not available"
                if not contact_artifact_available
                else "contact artifact not persisted",
            }
        ),
        "status_update_candidates": (
            {
                "saved": True,
                **(
                    {"source_message_id": status_update_persistence.get("source_message_id")}
                    if status_update_persistence.get("source_message_id")
                    else {}
                ),
                "ids": status_update_persistence.get("status_update_candidate_ids", []),
                "approval_ids": status_update_persistence.get("approval_ids", []),
            }
            if status_update_saved
            else {
                "saved": False,
                "reason": (
                    status_update_persistence.get("reason")
                    if status_update_persistence
                    else "worker reply artifact not available"
                    if not worker_reply_artifact_available
                    else "worker reply artifact not persisted"
                ),
                "ids": [],
                "approval_ids": [],
            }
        ),
    }


@router.get("/state/{request_id}")
async def get_agent_state(
    request_id: str,
    db: Session = Depends(get_sync_db),
) -> dict:
    """request_id 기반으로 LangChain v1 process-local state를 조회합니다."""
    state = runtime_state_store.get(request_id)
    if state is not None:
        return state.model_dump()
    snapshot = get_runtime_state_snapshot(db, request_id)
    if snapshot is not None:
        return snapshot
    raise HTTPException(status_code=404, detail="state를 찾을 수 없습니다.")


@router.post("/resume/{request_id}")
async def resume_agent_runtime_action(
    request_id: str,
    body: AgentResumeRequest,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = resume_runtime_action_for_company(
            db,
            request_id=request_id,
            action_type=body.action_type,
            company_id=company_id,
        )
        db.commit()
        return result
    except RuntimeResumeNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="runtime resume action not found") from exc
    except RuntimeResumeForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="resume action forbidden") from exc


@router.get("/resume/{request_id}")
async def get_agent_runtime_resume_summary(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        return get_runtime_resume_summary_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
    except RuntimeResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="runtime resume action not found") from exc
    except RuntimeResumeForbiddenError as exc:
        raise HTTPException(status_code=403, detail="resume action forbidden") from exc


@router.get("/metrics/{request_id}")
async def get_agent_runtime_metrics(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        return get_runtime_metrics_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
    except RuntimeMetricsNotFoundError as exc:
        raise HTTPException(status_code=404, detail="runtime metrics not found") from exc
    except RuntimeMetricsForbiddenError as exc:
        raise HTTPException(status_code=403, detail="runtime metrics access forbidden") from exc


@router.get("/metrics")
async def get_agent_runtime_metrics_summary(
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
    from_at: str | None = Query(default=None, alias="from"),
    to_at: str | None = Query(default=None, alias="to"),
) -> dict[str, Any]:
    try:
        return get_runtime_metrics_summary_for_company(
            db,
            company_id=company_id,
            from_at=from_at,
            to_at=to_at,
        )
    except RuntimeMetricsForbiddenError as exc:
        raise HTTPException(status_code=403, detail="runtime metrics access forbidden") from exc


@router.post("/checkpoints/{request_id}/resume")
async def resume_agent_langchain_checkpoint(
    request_id: str,
    body: AgentCheckpointResumeRequest,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = await resume_langchain_checkpoint_for_company(
            db,
            request_id=request_id,
            action_type=body.action_type,
            company_id=company_id,
            resume_value=body.resume_value,
        )
        db.commit()
        return result
    except LangChainCheckpointNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="langchain checkpoint not found") from exc
    except LangChainCheckpointForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="langchain checkpoint resume forbidden") from exc
    except LangChainCheckpointConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="langchain checkpoint resume conflict") from exc


@router.post("/outbox/{request_id}/prepare")
async def prepare_agent_runtime_outbox(
    request_id: str,
    db: Session = Depends(get_sync_db),
    company_id: str = Header(default="", alias="X-Company-Id"),
) -> dict[str, Any]:
    try:
        result = prepare_runtime_delivery_outbox_for_company(
            db,
            request_id=request_id,
            company_id=company_id,
        )
        db.commit()
        return result
    except RuntimeOutboxNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="runtime outbox not found") from exc
    except RuntimeOutboxForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="runtime outbox access forbidden") from exc
    except RuntimeOutboxConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="runtime outbox conflict") from exc


def _normalize_worker_lookup(
    db: Session,
    *,
    company_id: str,
    worker_id: str,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    payload = dict(input_payload or {})
    worker_name = str(payload.pop("worker_name", "") or "").strip()
    if worker_id:
        return payload, worker_id
    if not worker_name:
        return payload, worker_id
    if not company_id:
        payload["worker_lookup_status"] = "not_found"
        return payload, ""

    rows = db.scalars(
        select(Worker).where(
            Worker.company_id == company_id,
            Worker.name == worker_name,
            Worker.status == "ACTIVE",
        )
    ).all()
    if len(rows) == 1:
        payload["worker_lookup_status"] = "matched"
        return payload, rows[0].id
    if len(rows) > 1:
        payload["worker_lookup_status"] = "ambiguous"
        return payload, ""
    payload["worker_lookup_status"] = "not_found"
    return payload, ""
