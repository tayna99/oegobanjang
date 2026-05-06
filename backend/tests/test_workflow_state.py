from app.agent_runtime.graph.nodes.evidence_logger import make_event
from app.agent_runtime.graph.nodes.final_response import final_response_node
from app.agent_runtime.schemas import EventType, ForeignHiringState


class _FakeFinalResponse:
    content = "연락처는 010-1234-5678, 여권번호는 M12345678입니다."


class _FakeFinalLLM:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, messages):
        return _FakeFinalResponse()


def test_final_response_masks_raw_pii(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_runtime.graph.nodes.final_response.ChatOpenAI",
        _FakeFinalLLM,
    )
    state = ForeignHiringState(
        request_id="pii-final",
        user_message="근로자 연락처 010-1234-5678과 여권 M12345678을 요약해줘",
        rag_contexts=[
            {
                "source_id": "source-1",
                "title": "공식 안내",
                "evidence_grade": "B",
                "content": "담당자 승인 후 안내합니다.",
            }
        ],
    )

    final = final_response_node(state)

    assert "010-1234-5678" not in final.final_response
    assert "M12345678" not in final.final_response
    assert "[전화번호]" in final.final_response
    assert "[여권번호]" in final.final_response


def test_evidence_event_summary_masks_raw_pii() -> None:
    event = make_event(
        event_type=EventType.TOOL_EXECUTED,
        request_id="pii-event",
        summary="근로자 연락처 010-1234-5678 확인",
        step_name="test",
    )

    assert "010-1234-5678" not in event.summary
    assert "[전화번호]" in event.summary
