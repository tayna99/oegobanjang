"""자유 텍스트 필드(반려 사유 등)에 흔한 PII 패턴이 섞였는지 보수적으로 확인한다.

docs/DB_SCHEMA.md §4.3 approvals.reason "서비스 계층에서 PII 패턴 차단",
rules/safety.md 마스킹 규칙(외국인등록번호/여권번호/전화번호 포맷)과 짝을 이룬다.
완벽한 탐지가 목적이 아니라 흔한 실수(등록번호·전화번호를 그대로 타이핑)를 막는
방어선이다 — 통과했다고 원문이 절대 없다는 보증은 아니다.
"""

import re

_PATTERNS = (
    re.compile(r"\d{6}-\d{7}"),  # 외국인등록번호/주민등록번호 형식: 900101-1234567
    re.compile(r"01[016789]-?\d{3,4}-?\d{4}"),  # 휴대전화 형식: 010-1234-5678
    re.compile(r"\b[A-Z]\d{8}\b"),  # 여권번호 형식: M12345678
)


def contains_pii(value: str | None) -> bool:
    if not value:
        return False
    return any(pattern.search(value) for pattern in _PATTERNS)
