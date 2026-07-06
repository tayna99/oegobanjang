"""PII 필터: Evidence Log와 LLM 응답에서 민감정보 원문을 마스킹합니다."""
import re

_PATTERNS = [
    # 외국인등록번호: 000000-0000000
    (re.compile(r"\b\d{6}-\d{7}\b"), "[외국인등록번호]"),
    # 여권번호: 알파벳 1-2자 + 숫자 7-8자
    (re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}\d{7,8}(?![A-Za-z0-9])"), "[여권번호]"),
    # 전화번호: 010-0000-0000, 010 0000 0000, 01000000000
    (re.compile(r"\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b"), "[전화번호]"),
    # 주민등록번호: 000000-0000000 (외국인등록번호와 동일 패턴, 중복 적용 무방)
    (re.compile(r"\b\d{6}-[1-4]\d{6}\b"), "[주민번호]"),
]


def mask_pii(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_dict(data: dict) -> dict:
    """dict의 모든 string 값에 PII 마스킹을 적용합니다."""
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = mask_pii(v)
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [
                sanitize_dict(i) if isinstance(i, dict)
                else mask_pii(i) if isinstance(i, str)
                else i
                for i in v
            ]
        else:
            result[k] = v
    return result
