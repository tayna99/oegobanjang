"""rag 서비스(B1, plans/BACKEND_CONNECT.md) — backend 전용 내부 API.

프론트는 이 서비스를 직접 호출하지 않는다 — backend가 유일한 접속점이고, 이 서비스는
backend가 호출하는 내부 부품이다(상태 기록은 backend의 책임, RAG=근거 검색 경계 유지).

- GET  /health       — pgvector 컬렉션 존재·비어있지 않음 확인
- POST /retrieve     — 워크포스 3버킷 근거 검색 (rag_retrieved 이벤트 포함)
- POST /agent/run    — create_agent SSE 스트림: step 이벤트(RunStep kind 매핑) → structured 이벤트(RagAnswer)

실행: uv run uvicorn oe_rag.api:app --port 8100
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

from .agent.factory import RagAnswer, create_workforce_rag_agent
from .agent.tools import (
    RUNTIME_COLLECTIONS,
    RuntimePreflightError,
    preflight_pgvector,
    retrieve_workforce_materials,
    search_multilingual_contact_materials,
    search_policy_documents,
)

app = FastAPI(title="oe-rag", version="0.1.0")

_AGENT_TOOLS = [retrieve_workforce_materials, search_policy_documents, search_multilingual_contact_materials]

# 이 tool 이름 집합에 있으면 근거 검색(guardrail이 아니라 정상 조회) — RunStep kind 매핑에 사용.
_RETRIEVAL_TOOL_NAMES = frozenset(
    {"retrieve_workforce_materials", "search_policy_documents", "search_multilingual_contact_materials"}
)


class RetrieveRequest(BaseModel):
    query: str
    case_type: str = "new_hiring"
    sub_agent: str = "workforce_requirement_agent"
    visa_type: str = "E-9"
    top_k: int = 5


class AgentRunRequest(BaseModel):
    query: str
    case_type: str = "new_hiring"
    thread_id: str = "api-default"


def get_chat_model() -> BaseChatModel | None:
    """기본값 None → create_workforce_rag_agent가 ChatOpenAI로 폴백(OPENAI_API_KEY 필요).

    테스트는 FastAPI dependency_overrides로 이 함수를 OfflineEchoChatModel 등으로
    바꿔치기해 실제 LLM 호출 없이 SSE 계약을 검증한다.
    """
    return None


ChatModelDep = Annotated[BaseChatModel | None, Depends(get_chat_model)]


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        preflight_pgvector()
    except RuntimePreflightError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "collections": list(RUNTIME_COLLECTIONS)}


@app.post("/retrieve")
def retrieve(request: RetrieveRequest) -> dict[str, Any]:
    return retrieve_workforce_materials.invoke(request.model_dump())


def _sse_event(event: str, data: dict[str, Any] | None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _step_from_model_update(value: dict[str, Any]) -> dict[str, Any] | None:
    """node='model' 업데이트 → RunStep. tool_calls가 있으면 '근거를 찾는 중', 없으면 최종 응답이므로
    step이 아니라 structured 이벤트로 처리하니 여기서는 None을 반환해 건너뛴다."""
    messages = value.get("messages", [])
    for message in messages:
        if not isinstance(message, AIMessage) or not message.tool_calls:
            continue
        tool_names = [call.get("name", "") for call in message.tool_calls]
        if any(name in _RETRIEVAL_TOOL_NAMES for name in tool_names):
            return {
                "kind": "thinking",
                "label": "근거를 검색하는 중",
                "detail": ", ".join(tool_names),
            }
        if any(name == "RagAnswer" for name in tool_names):
            return None  # 최종 구조화 응답 — structured 이벤트에서 별도 처리
    return None


def _step_from_tools_update(value: dict[str, Any]) -> dict[str, Any] | None:
    """node='tools' 업데이트 → RunStep. 근거 0건이면 guardrail, 있으면 tool_call."""
    messages = value.get("messages", [])
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        try:
            content = json.loads(message.content) if isinstance(message.content, str) else message.content
        except json.JSONDecodeError:
            content = {}
        if not isinstance(content, dict):
            continue
        retrieved_count = content.get("retrieved_count")
        if retrieved_count is None:
            continue  # RagAnswer 구조화 응답 확인용 ToolMessage 등 — 근거검색 도구가 아님
        if content.get("missing_evidence"):
            return {
                "kind": "guardrail",
                "label": "근거를 찾지 못함",
                "detail": "MISSING_EVIDENCE — 행정사 검토 필요",
            }
        return {
            "kind": "tool_call",
            "label": "근거 검색 완료",
            "detail": f"{retrieved_count}건 검색됨",
        }
    return None


async def _agent_event_stream(
    query: str, case_type: str, thread_id: str, model: BaseChatModel | None
) -> AsyncIterator[str]:
    try:
        agent = create_workforce_rag_agent(model=model, tools=_AGENT_TOOLS)
    except RuntimePreflightError as exc:
        yield _sse_event("error", {"detail": str(exc)})
        return

    config = {"configurable": {"thread_id": thread_id}}
    try:
        async for chunk in agent.astream(
            {"messages": [{"role": "user", "content": query}]},
            config=config,
            stream_mode="updates",
        ):
            for node, value in chunk.items():
                if not isinstance(value, dict):
                    continue
                step = (
                    _step_from_model_update(value)
                    if node == "model"
                    else _step_from_tools_update(value)
                    if node == "tools"
                    else None
                )
                if step is not None:
                    yield _sse_event("step", step)
    except Exception as exc:  # noqa: BLE001 — SSE 스트림 안에서 죽지 않고 에러 이벤트로 알린다
        yield _sse_event("error", {"detail": str(exc)})
        return

    final_state = agent.get_state(config)
    structured: RagAnswer | None = final_state.values.get("structured_response")
    yield _sse_event("structured", structured.model_dump() if structured is not None else None)
    yield _sse_event("done", {})


@app.post("/agent/run")
async def agent_run(request: AgentRunRequest, model: ChatModelDep) -> StreamingResponse:
    return StreamingResponse(
        _agent_event_stream(request.query, request.case_type, request.thread_id, model),
        media_type="text/event-stream",
    )
