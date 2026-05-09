"""Multilingual Contact Agent: 다국어 메시지 초안 생성. 발송은 항상 승인 필요."""
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.agent_runtime.schemas import ForeignHiringState, EventType
from app.agent_runtime.tools.registry import (
    get_worker_profile,
    search_policy_documents,
    generate_multilingual_message_draft,
    send_worker_message,
)
from app.agent_runtime.middleware.call_limiter import check_llm_limit
from app.agent_runtime.evidence_events import make_event, log_event
from app.config import get_settings

_TOOLS = [
    get_worker_profile,
    search_policy_documents,
    generate_multilingual_message_draft,
    send_worker_message,
]

_SYSTEM_PROMPT = """당신은 외국인 고용 운영 시스템의 다국어 소통 전문 에이전트입니다.

역할:
- 근로자 모국어로 메시지 초안 생성 (베트남어, 크메르어, 우즈베크어, 네팔어, 인도네시아어)
- 비자 만료 알림, 서류 요청, 계약 종료 안내

제약:
- 메시지 초안 생성 후 반드시 담당자 승인 대기 (send_worker_message는 NEEDS_APPROVAL 반환)
- 근로자 SNS, 단톡방, 외부 커뮤니티 감시 금지
- 이탈 예측, 성실도 판단 금지

사용 가능한 tools: get_worker_profile, search_policy_documents,
generate_multilingual_message_draft, send_worker_message(승인 필요)"""


def run_contact_agent(state: ForeignHiringState, worker_id: str | None = None) -> dict[str, Any]:
    """multilingual_contact_agent 실행."""
    allowed, reason = check_llm_limit(state)
    if not allowed:
        return {"error": reason}

    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    ).bind_tools(_TOOLS)

    context_parts = [f"사용자 질문: {state.user_message}"]
    if worker_id:
        context_parts.append(f"대상 근로자 ID: {worker_id}")

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]

    tool_results = []
    risk_flags_new = []
    approval_required = False

    try:
        response = llm.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_fn = next((t for t in _TOOLS if t.name == tool_call["name"]), None)
                if not tool_fn:
                    continue
                result = tool_fn.invoke(tool_call.get("args", {}))
                if isinstance(result, dict):
                    tool_results.append(result)
                    risk_flags_new.extend(result.get("risk_flags", []))
                    if result.get("approval_required") or result.get("status") == "NEEDS_APPROVAL":
                        approval_required = True

        agent_result = {
            "agent": "multilingual_contact_agent",
            "summary": response.content or "메시지 초안 생성 완료",
            "tool_calls": len(tool_results),
            "risk_flags": risk_flags_new,
            "approval_required": approval_required,
        }

    except Exception as e:
        agent_result = {
            "agent": "multilingual_contact_agent",
            "error": str(e),
            "tool_calls": 0,
            "risk_flags": [],
            "approval_required": False,
        }

    state.agent_results.append(agent_result)
    state.tool_results.extend(tool_results)
    state.risk_flags.extend(risk_flags_new)

    if approval_required:
        from app.agent_runtime.schemas import ApprovalStatus
        state.approval = ApprovalStatus(
            required=True,
            status="PENDING",
            reason="메시지 발송 전 담당자 승인이 필요합니다.",
        )
        approval_event = make_event(
            event_type=EventType.APPROVAL_REQUESTED,
            request_id=state.request_id,
            agent_name="multilingual_contact_agent",
            step_name="contact_agent",
            summary="근로자 메시지 발송 승인 요청",
            risk_level="MEDIUM",
        )
        log_event(state, approval_event)

    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id=state.request_id,
        agent_name="multilingual_contact_agent",
        step_name="contact_agent",
        summary=f"multilingual_contact_agent 실행. tool {len(tool_results)}건, approval={approval_required}",
    )
    log_event(state, event)

    return agent_result
