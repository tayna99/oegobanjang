from __future__ import annotations

from .schemas import (
    ReplyInterpretationRequest,
    ReplyInterpretationResult,
    StatusUpdateCandidateDraft,
)


def interpret_worker_reply(
    request: ReplyInterpretationRequest,
) -> ReplyInterpretationResult:
    text = " ".join(
        value.lower()
        for value in (request.worker_reply, request.translated_ko)
        if value
    )
    candidates: list[StatusUpdateCandidateDraft] = []

    if _contains_any(text, ("여권", "hộ chiếu", "passport", "paspor")):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="passport_received_candidate",
                field="passport",
                candidate_status="available",
                is_final=False,
            )
        )

    if _contains_any(text, ("사진", "ảnh", "photo", "foto")):
        status = "pending"
        if _contains_any(text, ("내일", "ngày mai", "besok", "tomorrow")):
            status = "pending_until_next_day"
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="photo_pending_candidate",
                field="photo",
                candidate_status=status,
                is_final=False,
            )
        )

    if _contains_any(text, ("내일", "ngày mai", "besok", "tomorrow")):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="expected_submission_date_candidate",
                field="expected_submission_date",
                candidate_status="next_day",
                is_final=False,
            )
        )

    if _contains_any(
        text,
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
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="submission_status_candidate",
                field="submission_status",
                candidate_status="submitted_claimed",
                is_final=False,
            )
        )

    if _contains_any(
        text,
        ("못", "không thể", "belum", "belum bisa", "can't", "cannot"),
    ):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="delay_or_unavailable_candidate",
                field="submission_status",
                candidate_status="needs_follow_up",
                is_final=False,
            )
        )

    if _contains_any(
        text,
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
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="clarification_request_candidate",
                field="clarification_request",
                candidate_status="requested",
                is_final=False,
            )
        )

    if _contains_any(
        text,
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
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="safety_training_attendance_candidate",
                field="safety_training_attendance",
                candidate_status="unavailable_needs_follow_up",
                is_final=False,
            )
        )
    elif _contains_any(
        text,
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
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="safety_training_attendance_candidate",
                field="safety_training_attendance",
                candidate_status="available",
                is_final=False,
            )
        )

    if _contains_any(
        text,
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
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="deadline_extension_candidate",
                field="deadline_extension",
                candidate_status="requested",
                is_final=False,
            )
        )

    if _contains_any(text, ("전화", "call", "gọi", "hubungi")):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="contact_request_candidate",
                field="contact_request",
                candidate_status="requested",
                is_final=False,
            )
        )

    if _contains_any(text, ("기숙사", "housing", "asrama", "ký túc xá")):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="housing_issue_candidate",
                field="housing",
                candidate_status="needs_review",
                is_final=False,
            )
        )

    if _contains_any(text, ("상담", "counseling", "konseling", "tư vấn")):
        candidates.append(
            StatusUpdateCandidateDraft(
                candidate_type="counseling_support_candidate",
                field="support_channel",
                candidate_status="counseling_may_help",
                is_final=False,
            )
        )

    uncertainty_flags = ["MANAGER_REVIEW_REQUIRED"]
    if not candidates:
        uncertainty_flags.append("WORKER_REPLY_MEANING_UNCERTAIN")

    return ReplyInterpretationResult(
        status_update_candidates=_dedupe_candidates(candidates),
        uncertainty_flags=uncertainty_flags,
        manager_review_required=True,
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _dedupe_candidates(
    candidates: list[StatusUpdateCandidateDraft],
) -> list[StatusUpdateCandidateDraft]:
    output: list[StatusUpdateCandidateDraft] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.candidate_type, candidate.field)
        if key not in seen:
            seen.add(key)
            output.append(candidate)
    return output
