from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import scripts.run_evals as run_evals
from backend.app.agent_runtime.translation.quality_checker import (
    check_translation_quality,
)
from backend.app.agent_runtime.translation.reply_interpreter import (
    interpret_worker_reply,
)
from backend.app.agent_runtime.translation.reply_summarizer import (
    translate_and_summarize_worker_reply,
)
from backend.app.agent_runtime.translation.schemas import (
    ReplyInterpretationRequest,
    TranslationQualityCheckRequest,
    WorkerReplySummaryRequest,
)
from backend.app.agent_runtime.translation.translator import (
    LLMTranslationProvider,
    MockTranslationProvider,
    translate_text,
)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(
        self,
        *,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.content = content
        self.error = error
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return _FakeResponse(self.content or "")


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


def test_translate_text_uses_mock_provider_for_ko_to_vi_and_id() -> None:
    provider = MockTranslationProvider(
        {
            ("ko", "vi", "서류를 제출해 주세요."): "Vui lòng nộp hồ sơ.",
            ("ko", "id", "서류를 제출해 주세요."): "Mohon kirim dokumen.",
        }
    )

    vi_result = translate_text(
        text="서류를 제출해 주세요.",
        source_language="ko",
        target_language="vi",
        purpose="document_request",
        provider=provider,
    )
    id_result = translate_text(
        text="서류를 제출해 주세요.",
        source_language="ko",
        target_language="id",
        purpose="document_request",
        provider=provider,
    )

    assert vi_result.translated_text == "Vui lòng nộp hồ sơ."
    assert id_result.translated_text == "Mohon kirim dokumen."
    assert vi_result.provider == "mock"
    assert id_result.provider == "mock"


def test_llm_provider_without_api_key_falls_back_gracefully(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    completions = _FakeCompletions(
        content='{"translated_text":"SHOULD_NOT_BE_USED","risk_flags":[]}'
    )
    provider = LLMTranslationProvider(client=_FakeOpenAIClient(completions))

    result = translate_text(
        text="Tôi có hộ chiếu.",
        source_language="vi",
        target_language="ko",
        purpose="worker_reply_summary",
        provider=provider,
    )

    assert completions.calls == 0
    assert result.provider == "rule_based_fallback"
    assert result.review_required is True
    assert "LLM_TRANSLATION_UNAVAILABLE" in result.risk_flags


def test_llm_provider_api_exception_falls_back_after_retries(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    completions = _FakeCompletions(error=TimeoutError("timeout"))
    provider = LLMTranslationProvider(
        client=_FakeOpenAIClient(completions),
        max_retries=2,
    )

    result = translate_text(
        text="Tôi có hộ chiếu.",
        source_language="vi",
        target_language="ko",
        purpose="worker_reply_summary",
        provider=provider,
    )

    assert completions.calls == 3
    assert result.provider == "rule_based_fallback"
    assert result.review_required is True
    assert "LLM_TRANSLATION_FAILED" in result.risk_flags


def test_llm_provider_invalid_json_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    completions = _FakeCompletions(content="not json")
    provider = LLMTranslationProvider(
        client=_FakeOpenAIClient(completions),
        max_retries=1,
    )

    result = translate_text(
        text="Tôi có hộ chiếu.",
        source_language="vi",
        target_language="ko",
        purpose="worker_reply_summary",
        provider=provider,
    )

    assert completions.calls == 2
    assert result.provider == "rule_based_fallback"
    assert result.review_required is True
    assert "LLM_TRANSLATION_FAILED" in result.risk_flags


def test_llm_provider_success_returns_review_required_draft(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    completions = _FakeCompletions(
        content=(
            '{"translated_text":"여권은 있고 사진은 내일 보낼 수 있습니다.",'
            '"risk_flags":["NEEDS_MANAGER_REVIEW"],'
            '"review_required":false}'
        )
    )
    provider = LLMTranslationProvider(client=_FakeOpenAIClient(completions))

    result = translate_text(
        text="Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi.",
        source_language="vi",
        target_language="ko",
        purpose="worker_reply_summary",
        provider=provider,
    )

    assert result.translated_text == "여권은 있고 사진은 내일 보낼 수 있습니다."
    assert result.provider == "llm"
    assert result.review_required is True
    assert result.risk_flags == ["NEEDS_MANAGER_REVIEW"]


def test_worker_reply_summary_uses_llm_translated_ko(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    completions = _FakeCompletions(
        content='{"translated_text":"여권은 있고 사진은 내일 보낼 수 있습니다.","risk_flags":[]}'
    )
    provider = LLMTranslationProvider(client=_FakeOpenAIClient(completions))

    result = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(
            worker_reply="Tôi có hộ chiếu, ảnh thì ngày mai tôi gửi.",
            language_code="vi",
        ),
        provider=provider,
    )

    assert result.translated_ko == "여권은 있고 사진은 내일 보낼 수 있습니다."
    assert "여권" in result.summary_ko
    assert "사진" in result.summary_ko
    assert result.manager_review_required is True


def test_run_evals_uses_rule_based_provider_by_default(monkeypatch) -> None:
    monkeypatch.delenv("USE_LLM_TRANSLATION", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert run_evals._build_eval_translation_provider() is None
    assert (
        run_evals._eval_translation_provider_mode(
            "worker_reply_understanding_cases"
        )
        == "rule_based"
    )


def test_run_evals_llm_opt_in_uses_fallback_mode_without_api_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("USE_LLM_TRANSLATION", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = run_evals._build_eval_translation_provider()

    assert isinstance(provider, LLMTranslationProvider)
    assert (
        run_evals._eval_translation_provider_mode(
            "worker_reply_understanding_cases"
        )
        == "rule_based_fallback"
    )


def test_worker_reply_translation_summary_and_interpretation_create_candidates() -> None:
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="vi")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="vi",
        )
    )

    candidate_types = {
        candidate.candidate_type
        for candidate in interpretation.status_update_candidates
    }
    assert summary.translated_ko
    assert summary.summary_ko
    assert "passport_received_candidate" in candidate_types
    assert "photo_pending_candidate" in candidate_types
    assert "expected_submission_date_candidate" in candidate_types
    assert all(
        candidate.is_final is False
        for candidate in interpretation.status_update_candidates
    )
    assert interpretation.manager_review_required is True


def test_interpret_worker_reply_creates_clarification_request_candidate() -> None:
    worker_reply = "Tôi chưa hiểu cần gửi giấy tờ nào. Bạn có thể nói rõ không?"
    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="vi")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="vi",
        )
    )

    candidate = _candidate_by_field(interpretation, "clarification_request")
    assert candidate.candidate_status == "requested"
    assert candidate.is_final is False
    assert "어떤 서류" in summary.summary_ko
    assert "확인 필요" in summary.summary_ko


def test_interpret_worker_reply_creates_safety_training_available_candidate() -> None:
    worker_reply = "Saya bisa hadir pelatihan keselamatan pada waktu yang dijadwalkan."
    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="id")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="id",
        )
    )

    candidate = _candidate_by_field(interpretation, "safety_training_attendance")
    assert candidate.candidate_status == "available"
    assert candidate.is_final is False
    assert "안전교육" in summary.summary_ko
    assert "참석 가능" in summary.summary_ko


def test_interpret_worker_reply_creates_safety_training_unavailable_candidate() -> None:
    worker_reply = "Tôi không thể tham dự buổi đào tạo an toàn hôm đó."
    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="vi")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="vi",
        )
    )

    candidate = _candidate_by_field(interpretation, "safety_training_attendance")
    assert candidate.candidate_status == "unavailable_needs_follow_up"
    assert candidate.is_final is False
    assert "안전교육" in summary.summary_ko
    assert "참석 불가" in summary.summary_ko
    assert "후속 확인" in summary.summary_ko


def test_interpret_worker_reply_creates_submitted_claimed_candidate() -> None:
    worker_reply = "Saya sudah mengirim dokumen yang diminta."
    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="id")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="id",
        )
    )

    candidate = _candidate_by_field(interpretation, "submission_status")
    assert candidate.candidate_status == "submitted_claimed"
    assert candidate.is_final is False
    assert "서류" in summary.summary_ko
    assert "이미 보냈" in summary.summary_ko or "제출" in summary.summary_ko


def test_interpret_worker_reply_creates_deadline_extension_candidate() -> None:
    worker_reply = "Tôi cần thêm thời gian. Có thể gia hạn hạn nộp giấy tờ không?"
    summary = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="vi")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary.translated_ko,
            language_code="vi",
        )
    )

    candidate = _candidate_by_field(interpretation, "deadline_extension")
    assert candidate.candidate_status == "requested"
    assert candidate.is_final is False
    assert "기한" in summary.summary_ko
    assert "연장" in summary.summary_ko
    assert "요청" in summary.summary_ko


def test_quality_checker_detects_missing_privacy_purpose() -> None:
    result = check_translation_quality(
        TranslationQualityCheckRequest(
            korean_text="서류를 5월 10일까지 제출해 주세요. 문의는 담당자에게 해 주세요.",
            translated_text="Vui lòng nộp hồ sơ trước ngày 10/5. Hãy liên hệ người phụ trách.",
            purpose="missing_document_request",
            privacy_purpose="외국인 고용 업무 및 서류 확인",
            deadline="5월 10일",
            contact_person="담당자",
        )
    )

    assert result.passed is False
    assert "PRIVACY_PURPOSE_MISSING" in result.risk_flags
    assert "privacy_purpose" in result.missing_elements


def test_quality_checker_detects_missing_deadline() -> None:
    result = check_translation_quality(
        TranslationQualityCheckRequest(
            korean_text="개인정보는 외국인 고용 업무 및 서류 확인 목적으로 사용됩니다. 문의는 담당자에게 해 주세요.",
            translated_text="Thông tin cá nhân được dùng cho mục đích kiểm tra hồ sơ. Vui lòng liên hệ người phụ trách.",
            purpose="missing_document_request",
            privacy_purpose="외국인 고용 업무 및 서류 확인",
            deadline="2026-05-10",
            contact_person="담당자",
        )
    )

    assert result.passed is False
    assert "DEADLINE_MISSING" in result.risk_flags
    assert "deadline" in result.missing_elements


def test_quality_checker_detects_coercive_or_discriminatory_language() -> None:
    result = check_translation_quality(
        TranslationQualityCheckRequest(
            korean_text="개인정보는 외국인 고용 업무 및 서류 확인 목적으로 사용됩니다. 5월 10일까지 제출해 주세요. 문의는 담당자에게 해 주세요. 안 내면 해고될 수 있습니다.",
            translated_text="Vui lòng nộp trước hạn. Nếu không nộp sẽ bị đuổi việc.",
            purpose="missing_document_request",
            privacy_purpose="외국인 고용 업무 및 서류 확인",
            deadline="5월 10일",
            contact_person="담당자",
        )
    )

    assert result.passed is False
    assert "COERCIVE_OR_DISCRIMINATORY_LANGUAGE" in result.risk_flags


def _candidate_by_field(interpretation, field: str):
    matches = [
        candidate
        for candidate in interpretation.status_update_candidates
        if candidate.field == field
    ]
    assert matches
    return matches[0]
