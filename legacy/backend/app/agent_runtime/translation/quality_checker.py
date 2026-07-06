from __future__ import annotations

import re

from .schemas import (
    TranslationQualityCheckRequest,
    TranslationQualityCheckResult,
)


DEADLINE_PURPOSES = {
    "passport_request",
    "photo_request",
    "arc_request",
    "missing_document_request",
    "document_request",
}
COERCIVE_OR_DISCRIMINATORY_KEYWORDS = (
    "안 내면",
    "해고",
    "추방",
    "벌금",
    "불이익",
    "도망",
    "게으른",
    "국적",
    "민족",
    "đuổi việc",
    "trục xuất",
    "phạt",
    "malas",
    "dipecat",
    "dideportasi",
    "denda",
)


def check_translation_quality(
    request: TranslationQualityCheckRequest,
) -> TranslationQualityCheckResult:
    combined = f"{request.korean_text}\n{request.translated_text}".lower()
    missing_elements: list[str] = []
    risk_flags: list[str] = []

    if _requires("privacy_purpose", request) and not _has_privacy_purpose(
        request,
        combined,
    ):
        missing_elements.append("privacy_purpose")
        risk_flags.append("PRIVACY_PURPOSE_MISSING")

    if _requires("deadline", request) and not _has_deadline(request, combined):
        missing_elements.append("deadline")
        risk_flags.append("DEADLINE_MISSING")

    if _requires("contact_channel", request) and not _has_contact_channel(
        request,
        combined,
    ):
        missing_elements.append("contact_channel")
        risk_flags.append("CONTACT_CHANNEL_MISSING")

    if not _has_polite_tone(combined):
        missing_elements.append("polite_tone")
        risk_flags.append("POLITE_TONE_REVIEW_REQUIRED")

    if _has_coercive_or_discriminatory_language(combined):
        risk_flags.append("COERCIVE_OR_DISCRIMINATORY_LANGUAGE")

    if _possible_omission(request):
        missing_elements.append("possible_sentence_omission")
        risk_flags.append("POSSIBLE_SENTENCE_OMISSION")

    return TranslationQualityCheckResult(
        passed=not risk_flags,
        risk_flags=_dedupe(risk_flags),
        missing_elements=_dedupe(missing_elements),
        review_required=bool(risk_flags),
    )


def _requires(element: str, request: TranslationQualityCheckRequest) -> bool:
    if element in request.required_elements:
        return True
    if element == "deadline":
        return bool(request.deadline) or request.purpose in DEADLINE_PURPOSES
    return True


def _has_privacy_purpose(
    request: TranslationQualityCheckRequest,
    combined: str,
) -> bool:
    if request.privacy_purpose and request.privacy_purpose.lower() in combined:
        return True
    return any(
        keyword in combined
        for keyword in (
            "개인정보",
            "외국인 고용 업무",
            "서류 확인",
            "mục đích",
            "thông tin cá nhân",
            "tujuan",
            "data pribadi",
        )
    )


def _has_deadline(request: TranslationQualityCheckRequest, combined: str) -> bool:
    if request.deadline and request.deadline.lower() in combined:
        return True
    if re.search(
        r"\d{4}-\d{2}-\d{2}|\d{1,2}\s*월\s*\d{1,2}\s*일|\d{1,2}/\d{1,2}",
        combined,
    ):
        return True
    return any(
        keyword in combined
        for keyword in (
            "기한",
            "까지",
            "deadline",
            "hạn",
            "batas",
            "sebelum",
            "trước",
        )
    )


def _has_contact_channel(
    request: TranslationQualityCheckRequest,
    combined: str,
) -> bool:
    if request.contact_person and request.contact_person.lower() in combined:
        return True
    return any(
        keyword in combined
        for keyword in (
            "담당자",
            "문의",
            "연락",
            "contact",
            "liên hệ",
            "người phụ trách",
            "hubungi",
            "penanggung jawab",
        )
    )


def _has_polite_tone(combined: str) -> bool:
    return any(
        keyword in combined
        for keyword in (
            "부탁",
            "주세요",
            "안내",
            "확인",
            "vui lòng",
            "xin",
            "mohon",
            "silakan",
        )
    )


def _has_coercive_or_discriminatory_language(combined: str) -> bool:
    return any(keyword in combined for keyword in COERCIVE_OR_DISCRIMINATORY_KEYWORDS)


def _possible_omission(request: TranslationQualityCheckRequest) -> bool:
    translated = request.translated_text.strip()
    korean = request.korean_text.strip()
    if not translated:
        return True
    return len(translated) < max(12, len(korean) * 0.25)


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
