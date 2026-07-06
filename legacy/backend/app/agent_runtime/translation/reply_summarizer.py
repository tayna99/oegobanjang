from __future__ import annotations

from .schemas import (
    WorkerReplySummaryRequest,
    WorkerReplySummaryResult,
)
from .translator import (
    TranslationProvider,
    translate_text,
)


def translate_and_summarize_worker_reply(
    request: WorkerReplySummaryRequest,
    *,
    provider: TranslationProvider | None = None,
) -> WorkerReplySummaryResult:
    translation = translate_text(
        text=request.worker_reply,
        source_language=request.language_code,
        target_language="ko",
        purpose="worker_reply_summary",
        provider=provider,
    )
    summary_ko = _summary_from_translation(
        translation.translated_text,
        source_text=request.worker_reply,
    )
    risk_flags = _dedupe(translation.risk_flags + ["MANAGER_REVIEW_REQUIRED"])

    return WorkerReplySummaryResult(
        translated_ko=translation.translated_text,
        summary_ko=summary_ko,
        risk_flags=risk_flags,
        manager_review_required=True,
        translation_provider=translation.provider,
    )


def _summary_from_translation(
    translated_ko: str,
    *,
    source_text: str = "",
) -> str:
    combined = f"{translated_ko}\n{source_text}"
    normalized = combined.lower()
    fragments: list[str] = []

    if "여권" in combined:
        fragments.append("여권은 보유한 것으로 보입니다")
    if "사진" in combined:
        fragments.append("사진 제출 상태 확인이 필요합니다")
    if "내일" in combined or _contains_any(normalized, ("ngày mai", "besok")):
        fragments.append("내일 제출 가능하다는 의미가 포함되어 있습니다")
    if any(keyword in normalized for keyword in ("지연", "어려움", "못")):
        fragments.append("제출 지연 또는 준비 어려움 가능성이 있습니다")
    if _contains_any(
        normalized,
        (
            "무슨 서류",
            "어떤 서류",
            "모르겠",
            "không biết",
            "không rõ",
            "chưa hiểu",
            "giấy tờ nào",
            "dokumen apa",
            "tidak tahu",
            "tidak mengerti",
        ),
    ):
        fragments.append("근로자가 어떤 서류인지 질문하며 추가 설명 확인 필요 상태입니다")
    if _contains_any(
        normalized,
        (
            "참석 불가",
            "못 가",
            "못 참석",
            "không thể tham gia",
            "không thể tham dự",
            "không đi được",
            "tidak bisa ikut",
            "tidak bisa hadir",
        ),
    ):
        fragments.append("근로자가 안전교육 참석 불가로 후속 확인이 필요합니다")
    elif _contains_any(
        normalized,
        (
            "참석 가능",
            "갈 수 있어",
            "참석할 수",
            "tham gia được",
            "có thể tham gia",
            "bisa ikut",
            "bisa hadir",
        ),
    ):
        fragments.append("근로자가 안전교육 참석 가능하다고 응답했습니다")
    if _contains_any(
        normalized,
        (
            "이미 보냈",
            "제출했",
            "đã gửi",
            "đã nộp",
            "sudah kirim",
            "sudah mengirim",
            "sudah diserahkan",
        ),
    ):
        fragments.append("근로자가 서류를 이미 보냄 또는 제출했다고 답해 확인 필요 상태입니다")
    if _contains_any(
        normalized,
        (
            "기한 연장",
            "마감 연장",
            "더 시간",
            "gia hạn",
            "thêm thời gian",
            "perpanjang",
            "tambahan waktu",
        ),
    ):
        fragments.append("근로자가 제출 기한 연장을 요청했습니다")
    if any(keyword in combined for keyword in ("전화", "연락")):
        fragments.append("연락 요청 가능성이 있습니다")
    if any(keyword in combined for keyword in ("기숙사", "주거")):
        fragments.append("기숙사 또는 주거 관련 확인이 필요할 수 있습니다")
    if "상담" in combined:
        fragments.append("상담 지원이 필요할 수 있습니다")

    if not fragments:
        fragments.append("근로자 답변의 주요 의미를 규칙 기반으로 확정하기 어렵습니다")

    return "근로자 답변 요약 후보: " + ", ".join(fragments) + "."


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)
