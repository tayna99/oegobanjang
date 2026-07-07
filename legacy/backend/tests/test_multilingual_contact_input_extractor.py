from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agent_runtime.agents.multilingual_contact_input_extractor import (
    extract_multilingual_contact_input,
)


def test_extract_vi_safety_training_message_fields() -> None:
    result = extract_multilingual_contact_input(
        "Nguyen한테 베트남어로 5월 10일 10시에 교육장에서 안전교육 있다고 안내 메시지 만들어줘",
        {},
    )

    payload = result.input_payload
    assert payload["task_type"] == "message_draft"
    assert payload["worker_name"] == "Nguyen"
    assert payload["language_code"] == "vi"
    assert payload["message_purpose"] == "safety_training_notice"
    assert payload["training_date"] == "5월 10일"
    assert payload["training_time"] == "10시"
    assert payload["location"] == "교육장"


def test_extract_id_safety_training_message_fields() -> None:
    result = extract_multilingual_contact_input(
        "Budi에게 인도네시아어로 안전교육 안내 메시지 작성해줘",
        {},
    )

    payload = result.input_payload
    assert payload["task_type"] == "message_draft"
    assert payload["worker_name"] == "Budi"
    assert payload["language_code"] == "id"
    assert payload["message_purpose"] == "safety_training_notice"


def test_extract_counseling_center_defaults_only_for_counseling() -> None:
    result = extract_multilingual_contact_input(
        "베트남 근로자에게 상담센터 연락처 안내해줘",
        {},
    )

    payload = result.input_payload
    assert payload["language_code"] == "vi"
    assert payload["message_purpose"] == "counseling_center_guide"
    assert payload["center_name"] == "외국인력상담센터"
    assert payload["counseling_center_phone"] == "1577-0071"


def test_extract_worker_reply_summary_payload() -> None:
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    result = extract_multilingual_contact_input(
        f"이 베트남어 답변 요약하고 서류 상태 후보 만들어줘: {worker_reply}",
        {},
    )

    payload = result.input_payload
    assert payload["task_type"] == "worker_reply_summary"
    assert payload["language_code"] == "vi"
    assert payload["worker_reply"] == worker_reply
    assert payload["message_purpose"] == "document_reply"


def test_explicit_payload_values_are_not_overwritten() -> None:
    result = extract_multilingual_contact_input(
        "Nguyen한테 베트남어로 안전교육 안내 메시지 작성해줘",
        {"language_code": "id"},
    )

    assert result.input_payload["language_code"] == "id"
    assert result.extracted_fields.get("language_code") is None
