"""입력·출력 가드 — PII 마스킹 왕복, 금지어 차단."""

from __future__ import annotations

import pytest

from oe_rag.orchestration.guard import (
    SafetyValidationError,
    assert_output_safety,
    detect_pii,
    find_forbidden_input_terms,
    redact_pii,
)


def test_redact_pii_masks_passport_arc_and_phone() -> None:
    text = "여권 M12345678, 외국인등록번호 900101-1234567, 연락처 010-1234-5678로 확인"
    redacted = redact_pii(text)

    assert "M12345678" not in redacted
    assert "900101-1234567" not in redacted
    assert "010-1234-5678" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_redact_pii_keeps_normal_text_intact() -> None:
    text = "E-9 체류연장 절차를 확인해줘. 만료일은 2026-06-20."
    assert redact_pii(text) == text


def test_detect_pii_reports_types_and_positions() -> None:
    matches = detect_pii("여권 M12345678 / 전화 010-1234-5678")
    types = {m["type"] for m in matches}
    assert types == {"passport_or_registration", "korean_phone"}
    for m in matches:
        assert m["start"] < m["end"]


def test_find_forbidden_input_terms_blocks_candidate_judgment() -> None:
    hits = find_forbidden_input_terms("성실한 후보 추천해줘, 누가 더 나아?")
    assert "성실" in hits
    assert "추천해줘" in hits


def test_find_forbidden_input_terms_passes_operational_request() -> None:
    assert find_forbidden_input_terms("Nguyen 체류만료 확인하고 서류 요청 초안 만들어줘") == []


def test_assert_output_safety_raises_on_forbidden_term() -> None:
    with pytest.raises(SafetyValidationError, match="forbidden term"):
        assert_output_safety('{"final_response": "이 후보가 더 성실해 보입니다"}')


def test_assert_output_safety_accepts_safe_payload() -> None:
    assert_output_safety('{"final_response": "체류기간 연장 서류 목록입니다"}')
