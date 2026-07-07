from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from string import Formatter
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..tools.search_multilingual_contact_rag_tool import (
    SearchMultilingualContactRagInput,
    search_multilingual_contact_rag_tool,
)
from ..translation.quality_checker import (
    check_translation_quality,
)
from ..translation.reply_interpreter import (
    interpret_worker_reply,
)
from ..translation.reply_summarizer import (
    translate_and_summarize_worker_reply,
)
from ..translation.schemas import (
    ReplyInterpretationRequest,
    TranslationQualityCheckRequest,
    WorkerReplySummaryRequest,
)
from ..translation.translator import TranslationProvider


ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_TEMPLATE_PATH = ROOT_DIR / "data-pipeline" / "seed" / "message_templates.csv"
AGENT_NAME = "multilingual_contact_agent"

PURPOSE_TO_RAG_INTENT = {
    "safety_training_notice": "safety",
    "counseling_center_guide": "counseling",
    "housing_notice": "life",
    "passport_request": None,
    "photo_request": None,
    "arc_request": None,
    "missing_document_request": None,
}
TRANSLATION_REVIEW_STATUSES = {"needs_translation", "needs_human_review"}


class MessageDraftInput(BaseModel):
    worker_id: str
    language_code: Literal["vi", "id"]
    message_purpose: str
    due_date: str | None = None
    contact_person: str = "담당자"
    user_request: str
    privacy_purpose: str = "외국인 고용 업무 및 서류 확인"
    training_date: str | None = None
    training_time: str | None = None
    location: str | None = None
    center_name: str | None = None
    counseling_center_phone: str | None = None
    worker_name: str | None = None


class MessageDraftOutput(BaseModel):
    worker_id: str
    language_code: str
    message_purpose: str
    status: Literal["SUCCESS", "FAILED"]
    korean_text: str | None = None
    translated_text: str | None = None
    approval_required: bool = True
    citations: list[dict[str, Any]] = Field(default_factory=list)
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    error: str | None = None


class WorkerReplySummaryInput(BaseModel):
    worker_id: str
    language_code: Literal["vi", "id"]
    worker_reply: str
    message_purpose: str = "document_reply"


class WorkerReplySummaryOutput(BaseModel):
    worker_id: str
    language_code: str
    status: Literal["SUCCESS", "FAILED"]
    translated_ko: str | None = None
    translation_provider: str | None = None
    summary_ko: str | None = None
    status_update_candidates: list[dict[str, Any]] = Field(default_factory=list)
    approval_required: bool = True
    manager_review_required: bool = True
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    error: str | None = None


class MultilingualContactAgent:
    def __init__(
        self,
        template_path: str | Path = DEFAULT_TEMPLATE_PATH,
        *,
        translation_provider: TranslationProvider | None = None,
    ) -> None:
        self.template_path = Path(template_path)
        self.translation_provider = translation_provider

    def generate_message_draft(self, request: MessageDraftInput) -> MessageDraftOutput:
        risk_flags: list[str] = []
        template = self.load_message_template(
            purpose=request.message_purpose,
            language_code=request.language_code,
        )
        if template is None:
            return MessageDraftOutput(
                worker_id=request.worker_id,
                language_code=request.language_code,
                message_purpose=request.message_purpose,
                status="FAILED",
                risk_flags=_dedupe(risk_flags + ["TEMPLATE_NOT_FOUND"]),
                error=(
                    "Message template not found for "
                    f"purpose={request.message_purpose}, "
                    f"language_code={request.language_code}"
                ),
            )

        values = request.model_dump()
        translated_values = _localized_template_values(values, request.language_code)
        missing_fields = _missing_required_fields(template, values)
        if missing_fields:
            return MessageDraftOutput(
                worker_id=request.worker_id,
                language_code=request.language_code,
                message_purpose=request.message_purpose,
                status="FAILED",
                risk_flags=_dedupe(risk_flags + ["MISSING_REQUIRED_FIELD"]),
                error=f"Missing required field(s): {', '.join(missing_fields)}",
            )

        rag_intent = PURPOSE_TO_RAG_INTENT.get(request.message_purpose)
        rag_output = search_multilingual_contact_rag_tool(
            SearchMultilingualContactRagInput(
                query=request.user_request,
                top_k=5,
                language_code=request.language_code,
                intent=rag_intent,
            )
        )
        citations = rag_output.citations
        source_ids = [citation["source_id"] for citation in citations]
        risk_flags.extend(rag_output.risk_flags)

        korean_text = self.render_template(template["korean_text"], values)
        translated_text = self.render_template(
            template["translated_text"],
            translated_values,
        )
        review_status = str(template.get("review_status", "")).strip()
        if review_status in TRANSLATION_REVIEW_STATUSES or not translated_text.strip():
            risk_flags.append("TRANSLATION_REVIEW_REQUIRED")
        quality_result = check_translation_quality(
            TranslationQualityCheckRequest(
                korean_text=korean_text,
                translated_text=translated_text,
                purpose=request.message_purpose,
                privacy_purpose=request.privacy_purpose,
                deadline=request.due_date,
                contact_person=request.contact_person,
            )
        )
        risk_flags.extend(quality_result.risk_flags)
        if quality_result.review_required:
            risk_flags.append("TRANSLATION_QUALITY_REVIEW_REQUIRED")

        evidence_events = [
            build_evidence_event(
                "rag_retrieved",
                "공식 다국어 컨택 RAG 근거 후보를 조회했습니다.",
                source_ids,
                approval_required=False,
            ),
            build_evidence_event(
                "message_draft_created",
                "다국어 메시지 초안을 생성했습니다. 실제 발송 전 담당자 승인이 필요합니다.",
                source_ids,
                approval_required=True,
            ),
            build_evidence_event(
                "approval_requested",
                "근로자에게 메시지를 발송하기 전 담당자 승인이 필요합니다.",
                source_ids,
                approval_required=True,
            ),
        ]

        return MessageDraftOutput(
            worker_id=request.worker_id,
            language_code=request.language_code,
            message_purpose=request.message_purpose,
            status="SUCCESS",
            korean_text=korean_text,
            translated_text=translated_text,
            approval_required=True,
            citations=citations,
            evidence_events=evidence_events,
            risk_flags=_dedupe(risk_flags),
            error=None,
        )

    def summarize_worker_reply(
        self, request: WorkerReplySummaryInput
    ) -> WorkerReplySummaryOutput:
        summary_result = translate_and_summarize_worker_reply(
            WorkerReplySummaryRequest(
                worker_reply=request.worker_reply,
                language_code=request.language_code,
            ),
            provider=self.translation_provider,
        )
        interpretation = interpret_worker_reply(
            ReplyInterpretationRequest(
                worker_reply=request.worker_reply,
                translated_ko=summary_result.translated_ko,
                language_code=request.language_code,
            )
        )
        candidates = [
            candidate.model_dump(exclude_none=True)
            for candidate in interpretation.status_update_candidates
        ]
        risk_flags = _dedupe(
            summary_result.risk_flags + interpretation.uncertainty_flags
        )
        evidence_events = [
            build_evidence_event(
                "worker_reply_summarized",
                "근로자 답변을 번역 및 요약했습니다. 원문과 번역 전문은 Evidence Log 후보에 저장하지 않습니다.",
                [],
                approval_required=True,
            ),
            build_evidence_event(
                "status_update_candidate_created",
                "서류/상태 업데이트 후보를 생성했습니다. 확정 업데이트는 수행하지 않았습니다.",
                [],
                approval_required=True,
            ),
            build_evidence_event(
                "approval_requested",
                "상태 업데이트 후보는 담당자 검토 후 확정할 수 있습니다.",
                [],
                approval_required=True,
            ),
        ]

        return WorkerReplySummaryOutput(
            worker_id=request.worker_id,
            language_code=request.language_code,
            status="SUCCESS",
            translated_ko=summary_result.translated_ko,
            translation_provider=summary_result.translation_provider,
            summary_ko=summary_result.summary_ko,
            status_update_candidates=candidates,
            approval_required=True,
            manager_review_required=True,
            evidence_events=evidence_events,
            risk_flags=risk_flags,
            error=None,
        )

    def load_message_template(
        self,
        *,
        purpose: str,
        language_code: str,
    ) -> dict[str, str] | None:
        if not self.template_path.exists():
            return None

        with self.template_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (
                    row.get("purpose") == purpose
                    and row.get("target_language") == language_code
                    and str(row.get("approval_required", "")).lower() == "true"
                ):
                    return row

        return None

    def render_template(self, template: str, values: dict[str, Any]) -> str:
        safe_values = {
            key: "" if value is None else value
            for key, value in values.items()
        }
        return template.format(**safe_values)


def build_evidence_event(
    event_type: str,
    summary: str,
    source_ids: list[str],
    *,
    approval_required: bool,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "agent_name": AGENT_NAME,
        "summary": summary,
        "source_ids": source_ids,
        "approval_required": approval_required,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_worker_reply_rule_based(
    worker_reply: str,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    summary_result = translate_and_summarize_worker_reply(
        WorkerReplySummaryRequest(worker_reply=worker_reply, language_code="vi")
    )
    interpretation = interpret_worker_reply(
        ReplyInterpretationRequest(
            worker_reply=worker_reply,
            translated_ko=summary_result.translated_ko,
            language_code="vi",
        )
    )
    candidates = [
        candidate.model_dump(exclude_none=True)
        for candidate in interpretation.status_update_candidates
    ]
    risk_flags = _dedupe(summary_result.risk_flags + interpretation.uncertainty_flags)
    return summary_result.summary_ko, candidates, risk_flags


def _missing_required_fields(
    template: dict[str, str],
    values: dict[str, Any],
) -> list[str]:
    required = [
        field.strip()
        for field in str(template.get("required_fields", "")).split("|")
        if field.strip()
    ]
    placeholders = _template_fields(template.get("korean_text", "")) | _template_fields(
        template.get("translated_text", "")
    )
    required_set = set(required) | placeholders
    return sorted(
        field
        for field in required_set
        if values.get(field) is None or values.get(field) == ""
    )


def _template_fields(template: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _localized_template_values(
    values: dict[str, Any],
    language_code: str,
) -> dict[str, Any]:
    localized = dict(values)
    localized["privacy_purpose"] = _localized_privacy_purpose(
        localized.get("privacy_purpose"),
        language_code,
    )
    localized["contact_person"] = _localized_contact_person(
        localized.get("contact_person"),
        language_code,
    )
    return localized


def _localized_privacy_purpose(value: Any, language_code: str) -> str:
    text = "" if value is None else str(value).strip()
    if language_code == "vi":
        return "kiểm tra hồ sơ và thủ tục liên quan đến việc tuyển dụng lao động nước ngoài"
    if language_code == "id":
        return "pemeriksaan dokumen dan administrasi terkait perekrutan tenaga kerja asing"
    return text


def _localized_contact_person(value: Any, language_code: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return text
    if language_code == "vi" and _contains_hangul(text):
        return "người phụ trách"
    if language_code == "id" and _contains_hangul(text):
        return "penanggung jawab"
    return text


def _contains_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
