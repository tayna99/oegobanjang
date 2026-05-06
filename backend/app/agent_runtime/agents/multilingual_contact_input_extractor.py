from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


COUNSELING_CENTER_NAME = "외국인력상담센터"
COUNSELING_CENTER_PHONE = "1577-0071"


class ExtractedContactInput(BaseModel):
    input_payload: dict[str, Any]
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    missing_recommended_fields: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


def extract_multilingual_contact_input(
    user_request: str,
    input_payload: dict[str, Any] | None = None,
) -> ExtractedContactInput:
    payload = dict(input_payload or {})
    extracted: dict[str, Any] = {}
    risk_flags: list[str] = []
    text = user_request.strip()
    normalized = text.lower()

    _set_if_missing(payload, extracted, "task_type", _infer_task_type(normalized))
    task_type = payload.get("task_type")

    _set_if_missing(payload, extracted, "language_code", _infer_language_code(normalized))
    _set_if_missing(
        payload,
        extracted,
        "message_purpose",
        _infer_message_purpose(normalized, task_type),
    )

    message_purpose = payload.get("message_purpose")
    if message_purpose == "counseling_center_guide":
        _set_if_missing(payload, extracted, "center_name", COUNSELING_CENTER_NAME)
        _set_if_missing(
            payload,
            extracted,
            "counseling_center_phone",
            COUNSELING_CENTER_PHONE,
        )

    _set_if_missing(payload, extracted, "worker_name", _extract_worker_name(text))

    date_value = _extract_date(text)
    if date_value:
        target_field = "training_date" if message_purpose == "safety_training_notice" else "due_date"
        _set_if_missing(payload, extracted, target_field, date_value)

    _set_if_missing(payload, extracted, "training_time", _extract_time(text))
    _set_if_missing(payload, extracted, "location", _extract_location(text))

    if task_type == "worker_reply_summary":
        _set_if_missing(payload, extracted, "worker_reply", _extract_worker_reply(text))
        _set_if_missing(payload, extracted, "message_purpose", "document_reply")

    missing = _missing_recommended_fields(payload)
    return ExtractedContactInput(
        input_payload=payload,
        extracted_fields=extracted,
        missing_recommended_fields=missing,
        risk_flags=risk_flags,
    )


def _set_if_missing(
    payload: dict[str, Any],
    extracted: dict[str, Any],
    key: str,
    value: Any,
) -> None:
    if key in payload and payload[key] not in (None, ""):
        return
    if value in (None, ""):
        return
    payload[key] = value
    extracted[key] = value


def _infer_task_type(text: str) -> str | None:
    reply_keywords = ("답변", "요약", "상태 업데이트", "제출 예정", "확인해줘")
    draft_keywords = (
        "메시지",
        "안내",
        "작성",
        "만들어줘",
        "보내줘",
        "발송",
    )
    if any(keyword in text for keyword in reply_keywords):
        return "worker_reply_summary"
    if any(keyword in text for keyword in draft_keywords):
        return "message_draft"
    return None


def _infer_language_code(text: str) -> str | None:
    if _contains_any(text, ("베트남", "베트남어", "vietnamese", " vi ")):
        return "vi"
    if _contains_any(text, ("인도네시아", "인도네시아어", "indonesian", " id ")):
        return "id"
    return None


def _infer_message_purpose(text: str, task_type: Any) -> str | None:
    if task_type == "worker_reply_summary":
        return "document_reply"
    purpose_keywords = (
        ("safety_training_notice", ("안전교육", "교육", "안전")),
        ("counseling_center_guide", ("상담센터", "상담", "연락처", "전화번호", "1577")),
        ("housing_notice", ("기숙사", "숙소", "생활")),
        ("passport_request", ("여권",)),
        ("photo_request", ("증명사진", "사진")),
        ("arc_request", ("외국인등록증", "등록증", "arc")),
        ("missing_document_request", ("서류", "누락", "제출")),
    )
    for purpose, keywords in purpose_keywords:
        if any(keyword in text for keyword in keywords):
            return purpose
    return None


def _extract_date(text: str) -> str | None:
    iso_match = re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", text)
    if iso_match:
        return iso_match.group(0)

    korean_match = re.search(r"\d{1,2}\s*월\s*\d{1,2}\s*일", text)
    if korean_match:
        return re.sub(r"\s+", " ", korean_match.group(0)).replace(" 월", "월").replace(" 일", "일")

    return None


def _extract_time(text: str) -> str | None:
    match = re.search(r"(오전|오후)?\s*\d{1,2}\s*시", text)
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip().replace(" 시", "시")
    return None


def _extract_location(text: str) -> str | None:
    known_locations = ("교육장", "회의실")
    for location in known_locations:
        if location in text:
            return location

    match = re.search(r"([가-힣A-Za-z0-9_-]+(?:교육장|회의실))", text)
    if match:
        return match.group(1)
    return None


def _extract_worker_name(text: str) -> str | None:
    match = re.search(
        r"([A-Z][A-Za-z.\-]{1,40}|[가-힣A-Za-z]{1,20}씨)(?:한테|에게|께)",
        text,
    )
    if match:
        return match.group(1)
    return None


def _extract_worker_reply(text: str) -> str | None:
    if ":" in text:
        candidate = text.split(":", 1)[1].strip()
        return candidate or None
    if "：" in text:
        candidate = text.split("：", 1)[1].strip()
        return candidate or None
    return None


def _missing_recommended_fields(payload: dict[str, Any]) -> list[str]:
    task_type = payload.get("task_type")
    if task_type == "worker_reply_summary":
        recommended = ("language_code", "worker_reply", "message_purpose")
    elif payload.get("message_purpose") == "safety_training_notice":
        recommended = (
            "language_code",
            "message_purpose",
            "training_date",
            "training_time",
            "location",
        )
    elif payload.get("message_purpose") == "counseling_center_guide":
        recommended = (
            "language_code",
            "message_purpose",
            "center_name",
            "counseling_center_phone",
        )
    else:
        recommended = ("language_code", "message_purpose")

    return [
        field
        for field in recommended
        if payload.get(field) in (None, "")
    ]


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    padded = f" {text} "
    return any(keyword in padded or keyword.strip() in text for keyword in keywords)
