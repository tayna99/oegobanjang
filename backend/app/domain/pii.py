"""자유 텍스트 필드(반려 사유 등)에 흔한 PII 패턴이 섞였는지 보수적으로 확인한다.

docs/DB_SCHEMA.md §4.3 approvals.reason "서비스 계층에서 PII 패턴 차단",
rules/safety.md 마스킹 규칙(외국인등록번호/여권번호/전화번호 포맷)과 짝을 이룬다.
완벽한 탐지가 목적이 아니라 흔한 실수(등록번호·전화번호를 그대로 타이핑)를 막는
방어선이다 — 통과했다고 원문이 절대 없다는 보증은 아니다.
"""

import re

_PATTERNS = (
    # RAG 입력 가드와 같은 범위를 사용한다. 동일한 원문이 DB·RAG·evidence 경로에서 다르게
    # 마스킹되는 상태를 만들지 않도록 backend에서도 스크럽의 정본을 둔다.
    re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}\d{7,9}(?![A-Za-z0-9])"),  # 여권번호
    re.compile(r"(?<!\d)\d{6}-\d{7}(?!\d)"),  # 외국인/주민등록번호
    re.compile(r"(?<!\d)01[016789]-?\d{3,4}-?\d{4}(?!\d)"),  # 한국 전화번호
)


def contains_pii(value: str | None) -> bool:
    if not value:
        return False
    return any(pattern.search(value) for pattern in _PATTERNS)


def redact_pii(value: str) -> str:
    """DB·RAG·SSE로 나가는 자유 텍스트에서 등록/여권/전화번호를 제거한다."""
    redacted = value
    for pattern in _PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_pii_payload(value: object) -> object:
    """SSE·evidence JSON에 들어가는 모든 자유 텍스트를 재귀적으로 스크럽한다."""
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, list):
        return [redact_pii_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_pii_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_pii_payload(item) for key, item in value.items()}
    return value


_PHONE_FORMAT = re.compile(r"^(01[016789])-?(\d{3,4})-?(\d{4})$")


def mask_phone(phone: str) -> str:
    """010-1234-5678 → 010-****-5678 (docs/DB_SCHEMA.md §7). 형식이 안 맞으면 원문 그대로 반환."""
    match = _PHONE_FORMAT.match(phone)
    if not match:
        return phone
    front, _mid, tail = match.groups()
    return f"{front}-****-{tail}"
