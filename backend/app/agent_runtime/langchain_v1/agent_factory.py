from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings

from .checkpointing import get_langchain_checkpointer
from .middleware import build_langchain_v1_middleware
from .schemas import RuntimeContext, WorkBridgeAgentResponse
from .tools import RuntimePreflightError, get_langchain_v1_tools, preflight_chroma


SYSTEM_PROMPT = """당신은 외국인 고용 운영 OS '외고반장'의 LangChain 1.0 통합 에이전트입니다.

역할 원칙:
- RAG는 공식 근거와 절차를 찾는 곳입니다.
- DB/Rule은 현재 상태와 true/false 판단을 담당합니다.
- LLM은 자연어 구조화, 요약, 초안 생성을 담당합니다.
- 외부 발송, 제출, 행정사 전달, 상태 완료 처리는 반드시 approval_required=true/PENDING입니다.

금지:
- 비자 가능 여부를 확정하지 않습니다.
- 법률/노무 자문을 하지 않습니다.
- 후보자의 성실도, 이탈 가능성, 국적별 우열을 판단하지 않습니다.
- 정부 포털 제출이나 외부 발송을 자동 실행하지 않습니다.
- 다국어 컨택 요청은 기존 generate_multilingual_message_draft보다
  run_contact_onboarding 또는 run_worker_reply_interpreter tool을 우선 사용합니다.
- run_contact_onboarding 결과는 메시지 초안이며 실제 발송이 아닙니다.
- run_worker_reply_interpreter 결과의 status_update_candidates는 후보이며 상태에 자동 반영하지 않습니다.

출력:
- 반드시 WorkBridgeAgentResponse structured output만 반환합니다.
- contact sub-agent tool 결과를 사용한 경우 domain_payload.contact_subagents에
  list가 아니라 object/dict 형태로 안전 요약만 넣습니다.
- domain_payload.contact_subagents의 key는 contact_onboarding_subagent 또는
  worker_reply_interpreter_subagent입니다.
- sub-agent 실행 status는 SUCCESS 또는 FAILED만 사용합니다. PENDING을 실행 status로
  쓰지 말고, 승인 상태는 approval_status=PENDING으로 별도 표시합니다.
- contact sub-agent 요약에는 worker_reply 원문, translated_ko 전문, korean_text 전문,
  translated_text 전문, message body 전문, worker_id 원문, 전화번호, 여권번호,
  외국인등록번호를 넣지 않습니다.
- 예:
  {"contact_subagents":{"contact_onboarding_subagent":{"status":"SUCCESS",
  "approval_required":true,"approval_status":"PENDING","risk_flags":[]}}}
- 행정사/전문가 검토용 handoff 초안을 준비한 경우 handoff.available=true로 두고
  handoff.package_type은 expert_handoff_draft만 사용합니다.
- handoff는 항상 approval_required=true, approval_status=PENDING,
  not_for_legal_judgment=true, raw_worker_reply_included=false,
  full_translation_included=false, message_body_included=false입니다.
- 근거가 부족하면 blocked_reason 또는 risk_flags에 명시하고 행정사 검토 필요로 표시합니다.
"""


def _default_model() -> ChatOpenAI:
    settings = get_settings()
    if not settings.langchain_runtime_enabled:
        raise RuntimePreflightError("LangChain runtime disabled by configuration")
    if not settings.openai_api_key:
        raise RuntimePreflightError("OPENAI_API_KEY is required for langchain_v1 runtime")
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )


def create_workbridge_agent(
    *,
    model: str | BaseChatModel | None = None,
    tools: list[Any] | None = None,
    middleware: list[Any] | None = None,
    checkpointer: Any | None = None,
):
    """Create the LangChain v1 agent.

    Tests pass a fake chat model through `model` so the backend suite never
    needs a live OpenAI request.
    """

    preflight_chroma()
    selected_model: str | BaseChatModel = model or _default_model()
    selected_tools = tools if tools is not None else get_langchain_v1_tools()
    selected_middleware = (
        middleware if middleware is not None else list(build_langchain_v1_middleware())
    )
    return create_agent(
        model=selected_model,
        tools=selected_tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=selected_middleware,
        response_format=WorkBridgeAgentResponse,
        context_schema=RuntimeContext,
        checkpointer=checkpointer if checkpointer is not None else get_langchain_checkpointer(),
    )
