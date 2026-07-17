"""rag 서비스(내부, py3.13) 클라이언트 — plans/BACKEND_CONNECT.md B2.

backend가 rag 서비스(GET /health, POST /intent, POST /retrieve, POST /graph/run SSE)를
호출하는 유일한 지점이다. RAG_STRATEGY의 런타임 경계("검색 실패 시 fallback 금지")를
그대로 따른다 — rag 서비스가 다운되면 503을 그대로 전파하고, 여기서 검색 결과를
합성하거나 캐시로 흉내내지 않는다.

SSE 파싱은 event/data 두 줄짜리 프레임(rag/src/oe_rag/api.py의 _sse_event와 동일 포맷)을
가정한다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings


class RagServiceError(RuntimeError):
    """rag 서비스 호출 실패 — 네트워크 오류·5xx·SSE 프로토콜 위반을 감싼다."""


@dataclass(frozen=True)
class SseEvent:
    event: str
    data: dict[str, Any]


def _client(timeout: float | None = None) -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        base_url=settings.rag_service_url,
        timeout=timeout if timeout is not None else settings.rag_service_timeout_seconds,
    )


async def check_health() -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get("/health")
        except httpx.HTTPError as exc:
            raise RagServiceError(f"rag service unreachable: {exc}") from exc
    if response.status_code != 200:
        raise RagServiceError(f"rag service unhealthy: {response.status_code} {response.text}")
    return response.json()


async def fetch_intent(message: str) -> dict[str, Any]:
    """2-phase의 1단계 — RoutePlan(dict)을 받는다. backend는 required_context로
    ContextSnapshot을 조립해 stream_graph_run에 넘긴다."""
    async with _client() as client:
        try:
            response = await client.post("/intent", json={"message": message})
        except httpx.HTTPError as exc:
            raise RagServiceError(f"rag /intent unreachable: {exc}") from exc
    if response.status_code != 200:
        raise RagServiceError(f"rag /intent failed: {response.status_code} {response.text}")
    return response.json()


async def retrieve(query: str, *, case_type: str = "new_hiring", top_k: int = 5) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.post(
                "/retrieve", json={"query": query, "case_type": case_type, "top_k": top_k}
            )
        except httpx.HTTPError as exc:
            raise RagServiceError(f"rag /retrieve unreachable: {exc}") from exc
    if response.status_code != 200:
        raise RagServiceError(f"rag /retrieve failed: {response.status_code} {response.text}")
    return response.json()


def _parse_sse_block(block: str) -> SseEvent | None:
    import json

    if not block.strip():
        return None
    lines = block.splitlines()
    event = next((line.removeprefix("event: ") for line in lines if line.startswith("event: ")), "")
    data_line = next((line.removeprefix("data: ") for line in lines if line.startswith("data: ")), "{}")
    return SseEvent(event=event, data=json.loads(data_line))


async def stream_graph_run(
    *,
    message: str,
    thread_id: str,
    request_id: str | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> AsyncIterator[SseEvent]:
    """POST /graph/run SSE를 소비해 SseEvent를 순서대로 yield한다.

    프레임 순서 계약(rag가 보장): step*, evidence* (교차 가능) → structured → done.
    이 함수는 파싱만 하고 영속화는 호출자(runs API, B3')의 몫이다.
    """
    payload: dict[str, Any] = {"message": message, "thread_id": thread_id}
    if request_id is not None:
        payload["request_id"] = request_id
    if context_snapshot is not None:
        payload["context_snapshot"] = context_snapshot

    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.rag_service_url, timeout=settings.rag_service_timeout_seconds
    ) as client:
        try:
            async with client.stream("POST", "/graph/run", json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RagServiceError(
                        f"rag /graph/run failed: {response.status_code} {body.decode(errors='replace')}"
                    )
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        block, buffer = buffer.split("\n\n", 1)
                        parsed = _parse_sse_block(block)
                        if parsed is not None:
                            yield parsed
                trailing = _parse_sse_block(buffer)
                if trailing is not None:
                    yield trailing
        except httpx.HTTPError as exc:
            raise RagServiceError(f"rag /graph/run unreachable: {exc}") from exc
