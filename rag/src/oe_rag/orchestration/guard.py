"""입력·출력 가드 — legacy langchain_v1/middleware.py에서 함수 발췌 이식.

주의: legacy 파일은 통복사하지 않는다(파일 내 데드코드·절단 결함 존재 — 검수 노트).
PII 패턴·redact·금지어 검사만 순수 함수로 가져온다.

역할 (발표 p.15 "입력 검증 및 필터링 계층" + p.16 Guardrail):
- PII 마스킹(여권/외국인등록번호/전화) — 그래프 입구·출구와 evidence 요약에 적용
- 금지어 입력 차단(후보 평가·국적 우열·비자 확정 등) — LLM 호출 전에 차단
"""

from __future__ import annotations

import re
from typing import Any

FORBIDDEN_TERMS: tuple[str, ...] = (
    "성실",
    "성격",
    "이탈 가능성",
    "도망",
    "국적별 선호",
    "국적 우열",
    "좋은 사람",
    "더 나은 후보",
    "더 낫",
    "오래 일할",
    "장기근속",
    "추천",
    "비자 가능 확정",
    "비자 불가능 확정",
    "최종 판정",
    "candidate_score",
    "nationality_preference",
    "reliability_score",
    "absconding_prediction",
    "final_eligibility_decision",
)

FORBIDDEN_INPUT_TERMS: tuple[str, ...] = FORBIDDEN_TERMS + (
    "추천해줘",
    "누가 나아",
    "누가 더 나아",
    "비자 발급 가능",
    "가능 여부 확정",
)

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("passport_or_registration", re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}[0-9]{7,9}(?![A-Za-z0-9])")),
    ("alien_registration_number", re.compile(r"(?<!\d)\d{6}-\d{7}(?!\d)")),
    ("korean_phone", re.compile(r"(?<!\d)010-\d{3,4}-\d{4}(?!\d)")),
)


class SafetyValidationError(ValueError):
    pass


def redact_pii(text: str) -> str:
    redacted = text
    for _, pattern in PII_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def detect_pii(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for pii_type, pattern in PII_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(
                {
                    "type": pii_type,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return matches


def find_forbidden_input_terms(text: str) -> list[str]:
    """입력에서 금지어를 찾는다 — 하나라도 있으면 LLM 호출 전에 차단해야 한다."""
    lowered = text.lower()
    return [term for term in FORBIDDEN_INPUT_TERMS if term.lower() in lowered]


def assert_output_safety(payload_text: str) -> None:
    """구조화 응답 직렬화본에 금지어가 없는지 최종 검증 (legacy validate_response_safety 축약)."""
    for term in FORBIDDEN_TERMS:
        if term in payload_text:
            raise SafetyValidationError(f"forbidden term in structured response: {term}")
