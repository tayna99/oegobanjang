from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event
from app.agent_runtime.legacy_graph.nodes.final_response import (
    _HANDOFF_DRAFT_NOTICE,
    final_response_node,
)
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
        "app.agent_runtime.legacy_graph.nodes.final_response.ChatOpenAI",
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


def test_final_response_without_handoff_draft_keeps_existing_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent_runtime.legacy_graph.nodes.final_response.ChatOpenAI",
        _FakeFinalLLM,
    )
    state = ForeignHiringState(
        request_id="no-handoff-final",
        user_message="요약해줘",
        rag_contexts=[
            {
                "source_id": "source-1",
                "title": "공식 안내",
                "evidence_grade": "B",
                "content": "담당자 승인 후 안내합니다.",
            }
        ],
        handoff_package_draft={},
    )

    final = final_response_node(state)

    assert _HANDOFF_DRAFT_NOTICE not in final.final_response
    assert "handoff package 초안" not in final.final_response


def test_final_response_appends_handoff_draft_notice() -> None:
    state = ForeignHiringState(
        request_id="handoff-final",
        user_message="전문가 검토 준비해줘",
        handoff_package_draft={"package_type": "expert_handoff_draft"},
    )

    final = final_response_node(state)

    assert "handoff package 초안" in final.final_response
    assert "자동 전달" in final.final_response
    assert "담당자 승인" in final.final_response


def test_final_response_handoff_notice_does_not_include_draft_sensitive_values() -> None:
    state = ForeignHiringState(
        request_id="handoff-sensitive-final",
        user_message="전문가 검토 준비해줘",
        handoff_package_draft={
            "package_type": "expert_handoff_draft",
            "worker_reply": "Tôi có hộ chiếu, ảnh mai gửi.",
            "translated_ko": "여권이 있고 사진은 내일 보내겠다는 답변입니다.",
            "message_body": "안녕하세요. 여권 사본을 제출해주세요.",
            "worker_id": "worker-demo-001",
            "worker_name": "Nguyen Van A",
            "passport_number": "M12345678",
            "alien_registration_number": "900101-1234567",
            "phone": "010-1234-5678",
        },
    )

    final = final_response_node(state)

    assert "handoff package 초안" in final.final_response
    assert "Tôi có hộ chiếu" not in final.final_response
    assert "여권이 있고 사진은 내일" not in final.final_response
    assert "안녕하세요. 여권 사본" not in final.final_response
    assert "worker-demo-001" not in final.final_response
    assert "Nguyen Van A" not in final.final_response
    assert "M12345678" not in final.final_response
    assert "900101-1234567" not in final.final_response
    assert "010-1234-5678" not in final.final_response
