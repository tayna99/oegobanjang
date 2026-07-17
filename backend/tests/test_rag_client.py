"""rag_client — httpx 목킹(respx). 실제 rag 서비스 기동 불필요."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.services.rag_client import RagServiceError, check_health, fetch_intent, retrieve, stream_graph_run

RAG_BASE = "http://localhost:8100"


@pytest.mark.asyncio
@respx.mock
async def test_check_health_returns_json_on_200() -> None:
    respx.get(f"{RAG_BASE}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok", "collections": ["workforce_official"]})
    )

    result = await check_health()

    assert result["status"] == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_check_health_raises_on_503() -> None:
    respx.get(f"{RAG_BASE}/health").mock(return_value=httpx.Response(503, text="empty collection"))

    with pytest.raises(RagServiceError, match="unhealthy"):
        await check_health()


@pytest.mark.asyncio
@respx.mock
async def test_check_health_raises_on_connection_error() -> None:
    respx.get(f"{RAG_BASE}/health").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(RagServiceError, match="unreachable"):
        await check_health()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_intent_returns_route_plan() -> None:
    respx.post(f"{RAG_BASE}/intent").mock(
        return_value=httpx.Response(
            200,
            json={"should_run": True, "intent": "visa_expiry", "mission": "m2_visa", "required_context": ["workers"]},
        )
    )

    result = await fetch_intent("체류만료 확인해줘")

    assert result["mission"] == "m2_visa"


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_proxies_to_rag_service() -> None:
    respx.post(f"{RAG_BASE}/retrieve").mock(
        return_value=httpx.Response(200, json={"records": [], "retrieved_count": 0, "missing_evidence": True})
    )

    result = await retrieve("아무 질의")

    assert result["missing_evidence"] is True


def _sse_body(*frames: tuple[str, dict]) -> bytes:
    text = "".join(f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n" for name, data in frames)
    return text.encode("utf-8")


@pytest.mark.asyncio
@respx.mock
async def test_stream_graph_run_parses_all_frames_in_order() -> None:
    body = _sse_body(
        ("step", {"kind": "thinking", "label": "입력 검증"}),
        ("evidence", {"event_type": "intent_classified", "summary": "ok"}),
        ("structured", {"answer": {"final_response": "완료"}, "approval": {"required": False}}),
        ("done", {}),
    )
    respx.post(f"{RAG_BASE}/graph/run").mock(
        return_value=httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
    )

    events = [e async for e in stream_graph_run(message="질문", thread_id="t1")]

    assert [e.event for e in events] == ["step", "evidence", "structured", "done"]
    assert events[2].data["answer"]["final_response"] == "완료"


@pytest.mark.asyncio
@respx.mock
async def test_stream_graph_run_raises_on_non_200() -> None:
    respx.post(f"{RAG_BASE}/graph/run").mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(RagServiceError, match="failed"):
        async for _ in stream_graph_run(message="질문", thread_id="t1"):
            pass
