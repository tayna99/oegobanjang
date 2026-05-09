from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings

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

출력:
- 반드시 WorkBridgeAgentResponse structured output만 반환합니다.
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
    )
