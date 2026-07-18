"""LangChain 1.x create_agent 팩토리 — legacy langchain_v1/agent_factory.py 축약 이식.

RAG 근거 검색에 집중한 단일 에이전트다. 비자/컨택 서브에이전트·middleware·SQLite
체크포인터는 이번 범위 밖("백엔드 접속점" 이후) — 체크포인터는 InMemorySaver를 쓴다.
"""

from __future__ import annotations

import os
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel, Field

from .tools import (
    RuntimePreflightError,
    preflight_pgvector,
    retrieve_workforce_materials,
    search_multilingual_contact_materials,
    search_policy_documents,
)

DEFAULT_AGENT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """당신은 외국인 고용 운영 OS '외고반장'의 근거 검색 에이전트입니다.

역할 원칙:
- RAG는 공식 근거와 절차를 찾는 곳입니다. 근거가 필요한 질문에는 아래 세 도구 중 맞는 것을 호출합니다.
  - retrieve_workforce_materials: 신규 E-9 인력 확보(고용허가 절차·허용업종·내부 템플릿)
  - search_policy_documents: 비자·체류 절차(체류연장·사업장변경·법령)
  - search_multilingual_contact_materials: 다국어 근로자 컨택용 공식 안내(상담센터·안전교육·생활안내·공지)
- DB/Rule은 현재 상태와 true/false 판단을 담당합니다. LLM은 자연어 구조화·요약·초안 생성만 담당합니다.
- 외부 발송, 제출, 행정사 전달, 상태 완료 처리는 이 에이전트의 권한 밖입니다.

금지:
- 비자 가능 여부를 확정하지 않습니다.
- 법률/노무 자문을 하지 않습니다.
- 후보자의 성실도, 이탈 가능성, 국적별 우열을 판단하지 않습니다.
- 정부 포털 제출이나 외부 발송을 자동 실행하지 않습니다.

출력:
- 반드시 RagAnswer structured output만 반환합니다.
- citations에는 도구 검색 결과의 source_id만 사용합니다 (지어내지 않습니다).
- evidence_grade가 D/F인 근거는 인용하지 않습니다.
- 검색 결과가 비어 있으면(missing_evidence=true) 근거 없이 답하지 말고
  missing_evidence=true, risk_flags에 "MISSING_EVIDENCE"를 넣고 행정사 검토 필요로 안내합니다.
"""


class RagCitation(BaseModel):
    source_id: str
    title: str = ""
    evidence_grade: str = ""


class RagAnswer(BaseModel):
    """근거 기반 응답 계약 — 최종 답변 + 인용 + 근거 부족 신호."""

    final_response: str = Field(description="사용자에게 보여줄 한국어 답변")
    citations: list[RagCitation] = Field(default_factory=list)
    missing_evidence: bool = False
    risk_flags: list[str] = Field(default_factory=list)


def _default_checkpointer() -> InMemorySaver:
    # response_format(RagAnswer)이 체크포인트에 msgpack 직렬화되는데, LangGraph 기본
    # 직렬화기(permissive 모드, allowed_msgpack_modules=True)는 등록되지 않은 커스텀
    # 타입마다 "future version에서 차단 예정" 경고를 낸다. permissive(True)에서
    # with_msgpack_allowlist()를 부르면 얼리리턴으로 무시되므로, 처음부터 명시적
    # allowlist로 생성해야 경고가 사라진다.
    serde = JsonPlusSerializer(allowed_msgpack_modules=[RagAnswer])
    return InMemorySaver(serde=serde)


def _default_model() -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimePreflightError("OPENAI_API_KEY is required for the workforce RAG agent")
    return ChatOpenAI(model=DEFAULT_AGENT_MODEL, temperature=0, api_key=api_key)


def create_workforce_rag_agent(
    *,
    model: str | BaseChatModel | None = None,
    tools: list[Any] | None = None,
    checkpointer: Any | None = None,
):
    """워크포스 RAG 에이전트 생성.

    테스트는 `model`로 fake chat model을 넘겨 실제 OpenAI 호출 없이 검증한다
    (legacy create_workbridge_agent와 같은 계약).
    """
    preflight_pgvector()
    selected_model: str | BaseChatModel = model or _default_model()
    selected_tools = (
        tools
        if tools is not None
        else [retrieve_workforce_materials, search_policy_documents, search_multilingual_contact_materials]
    )
    return create_agent(
        model=selected_model,
        tools=selected_tools,
        system_prompt=SYSTEM_PROMPT,
        response_format=RagAnswer,
        checkpointer=checkpointer if checkpointer is not None else _default_checkpointer(),
    )
