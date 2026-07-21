"""rag 서비스 — backend 전용 내부 API (B1 + M7-G3).

프론트는 이 서비스를 직접 호출하지 않는다 — backend가 유일한 접속점이고, 이 서비스는
backend가 호출하는 내부 부품이다(상태 기록은 backend의 책임, RAG=근거 검색 경계 유지).

- GET  /health       — pgvector 컬렉션 존재·비어있지 않음 확인
- POST /retrieve     — 워크포스 3버킷 근거 검색 (rag_retrieved 이벤트 포함)
- POST /agent/run    — (B1) create_agent SSE — B3' 결선 후 dev·디버그 보조로 강등 예정
- POST /intent       — (G3) 결정론 라우팅(키워드 정본) — backend 2-phase의 1단계
- POST /graph/run    — (G3) 직선 StateGraph SSE: step* → evidence* → structured → done

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
from pydantic import BaseModel, Field

from .agent.factory import RagAnswer, create_workforce_rag_agent
from .agent.tools import (
    RUNTIME_COLLECTIONS,
    RuntimePreflightError,
    preflight_pgvector,
    retrieve_workforce_materials,
    search_multilingual_contact_materials,
    search_policy_documents,
)
from .orchestration.graph import build_orchestration_graph, new_request_id
from .orchestration.router import RoutePlan, route_message

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


# --- M7-G3: 직선 오케스트레이션 그래프 ---------------------------------------------------


class IntentRequest(BaseModel):
    message: str


class GraphRunRequest(BaseModel):
    message: str
    thread_id: str = "graph-default"
    request_id: str | None = None
    # backend가 조립한 ContextSnapshot(v1) — 없으면 상태 없는 미션(M0)만 의미 있게 동작
    context_snapshot: dict[str, Any] = Field(default_factory=dict)


@app.post("/intent")
def intent(request: IntentRequest) -> RoutePlan:
    """2-phase의 1단계 — 결정론 키워드 라우팅(정본). backend는 이 결과의
    required_context로 ContextSnapshot을 조립해 /graph/run에 주입한다."""
    return route_message(request.message)


# 그래프 노드 → 프론트 RunStep(kind: thinking/tool_call/guardrail/handoff/replan) 매핑.
_NODE_STEP_BUILDERS: dict[str, Any] = {
    "input_guard": lambda update: {
        "kind": "guardrail" if update.get("blocked") else "thinking",
        "label": "입력 가드 차단" if update.get("blocked") else "입력 검증·PII 마스킹",
        "detail": update.get("blocked_reason", "") or ("PII 마스킹 적용" if update.get("pii_masked") else "통과"),
    },
    "intent_router": lambda update: {
        "kind": "thinking",
        "label": "의도 분류",
        "detail": f"{update.get('route', {}).get('intent', '?')} → {update.get('route', {}).get('mission') or '-'}",
    },
    "planner": lambda update: {
        "kind": "thinking",
        "label": "실행 계획 수립 (코드 dict)",
        "detail": "",
    },
    "executor": lambda update: {
        "kind": "tool_call",
        "label": "미션 실행",
        "detail": ", ".join(r.get("mission", "?") for r in update.get("mission_results", [])),
    },
    "aggregator": lambda update: {
        "kind": "thinking",
        "label": "결과 집계",
        "detail": f"key findings {len(update.get('aggregated', {}).get('key_findings', []))}건",
    },
    "approval_gate": lambda update: {
        "kind": "handoff" if (update.get("approval") or {}).get("required") else "thinking",
        "label": "승인 게이트",
        "detail": (update.get("approval") or {}).get("status", ""),
    },
    "blocked_response": lambda update: {
        "kind": "guardrail",
        "label": "요청 차단",
        "detail": "안전 규칙 — 자동 실행 없이 담당자 검토 필요",
    },
}


async def _graph_event_stream(
    request: GraphRunRequest, chat_model: BaseChatModel | None
) -> AsyncIterator[str]:
    graph = build_orchestration_graph(chat_model)
    request_id = request.request_id or new_request_id()

    initial_state = {
        "request_id": request_id,
        "thread_id": request.thread_id,
        "user_message": request.message,
        "context_snapshot": request.context_snapshot,
        "mission_results": [],
        "evidence_events": [],
    }

    final_structured: dict[str, Any] | None = None
    final_approval: dict[str, Any] | None = None
    final_citation_catalog: list[dict[str, Any]] = []
    try:
        async for chunk in graph.astream(initial_state, stream_mode="updates"):
            for node, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                builder = _NODE_STEP_BUILDERS.get(node)
                if builder is not None:
                    yield _sse_event("step", builder(update))
                for event in update.get("evidence_events", []) or []:
                    yield _sse_event("evidence", event)
                if update.get("structured_response"):
                    final_structured = update["structured_response"]
                if isinstance(update.get("citation_catalog"), list):
                    final_citation_catalog = update["citation_catalog"]
                if update.get("approval"):
                    final_approval = update["approval"]
    except Exception as exc:  # noqa: BLE001 — SSE 내부 오류는 error 이벤트로
        yield _sse_event("error", {"detail": str(exc), "request_id": request_id})
        return

    yield _sse_event(
        "structured",
        {
            "request_id": request_id,
            "answer": final_structured,
            "citation_catalog": final_citation_catalog,
            "approval": final_approval,
        },
    )
    yield _sse_event("done", {"request_id": request_id})


def get_graph_chat_model() -> BaseChatModel | None:
    """그래프 미션 합성용 모델 — 키가 있으면 ChatOpenAI, 없으면 None(결정론 폴백 — 정본).

    /agent/run의 get_chat_model과 달리 모델이 없어도 전 경로가 동작해야 하므로
    (오프라인 데모가 정본) 예외를 던지지 않는다. 테스트는 dependency_overrides로
    fake 모델을 주입해 LLM 합성 경로를 검증할 수 있다.
    """
    import os

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)


GraphChatModelDep = Annotated[BaseChatModel | None, Depends(get_graph_chat_model)]


@app.post("/graph/run")
async def graph_run(request: GraphRunRequest, chat_model: GraphChatModelDep) -> StreamingResponse:
    return StreamingResponse(
        _graph_event_stream(request, chat_model),
        media_type="text/event-stream",
    )
