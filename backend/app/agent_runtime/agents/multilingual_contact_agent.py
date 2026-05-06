from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from string import Formatter
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.agent_runtime.tools.search_multilingual_contact_rag_tool import (
    SearchMultilingualContactRagInput,
    search_multilingual_contact_rag_tool,
)


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
    summary_ko: str | None = None
    status_update_candidates: list[dict[str, Any]] = Field(default_factory=list)
    approval_required: bool = True
    manager_review_required: bool = True
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    error: str | None = None


class MultilingualContactAgent:
    def __init__(self, template_path: str | Path = DEFAULT_TEMPLATE_PATH) -> None:
        self.template_path = Path(template_path)

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
        translated_text = self.render_template(template["translated_text"], values)
        review_status = str(template.get("review_status", "")).strip()
        if review_status in TRANSLATION_REVIEW_STATUSES or not translated_text.strip():
            risk_flags.append("TRANSLATION_REVIEW_REQUIRED")

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
        summary_ko, candidates, risk_flags = summarize_worker_reply_rule_based(
            request.worker_reply
        )
        evidence_events = [
            build_evidence_event(
                "worker_reply_summarized",
                "근로자 답변을 요약했습니다. 원문은 Evidence Log 후보에 저장하지 않습니다.",
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
            summary_ko=summary_ko,
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
    normalized = worker_reply.lower()
    candidates: list[dict[str, Any]] = []
    fragments: list[str] = []

    if _contains_any(normalized, ("여권", "hộ chiếu", "passport")):
        candidates.append(
            {
                "candidate_type": "passport_received_candidate",
                "field": "passport",
                "candidate_status": "available",
                "is_final": False,
            }
        )
        fragments.append("여권은 보유한 것으로 보입니다")

    if _contains_any(normalized, ("사진", "ảnh", "photo")):
        status = "pending"
        if _contains_any(normalized, ("내일", "ngày mai", "besok")):
            status = "pending_until_next_day"
        candidates.append(
            {
                "candidate_type": "photo_pending_candidate",
                "field": "photo",
                "candidate_status": status,
                "is_final": False,
            }
        )
        fragments.append("사진 제출 상태 확인이 필요합니다")

    if _contains_any(normalized, ("내일", "ngày mai", "besok")):
        candidates.append(
            {
                "candidate_type": "expected_submission_date_candidate",
                "field": "expected_submission_date",
                "candidate_status": "next_day",
                "is_final": False,
            }
        )
        fragments.append("내일 제출 가능하다는 의미가 포함되어 있습니다")

    if _contains_any(normalized, ("못", "không thể", "belum", "belum bisa")):
        candidates.append(
            {
                "candidate_type": "delay_or_unavailable_candidate",
                "field": "submission_status",
                "candidate_status": "needs_follow_up",
                "is_final": False,
            }
        )
        fragments.append("제출 지연 또는 준비 어려움 가능성이 있습니다")

    if _contains_any(normalized, ("전화", "call", "gọi")):
        candidates.append(
            {
                "candidate_type": "contact_request_candidate",
                "field": "contact_request",
                "candidate_status": "requested",
                "is_final": False,
            }
        )
        fragments.append("전화 연락 요청 가능성이 있습니다")

    if _contains_any(normalized, ("기숙사", "housing", "asrama")):
        candidates.append(
            {
                "candidate_type": "housing_issue_candidate",
                "field": "housing",
                "candidate_status": "needs_review",
                "is_final": False,
            }
        )
        fragments.append("기숙사 또는 주거 관련 확인이 필요할 수 있습니다")

    if _contains_any(normalized, ("상담", "counseling")):
        candidates.append(
            {
                "candidate_type": "counseling_support_candidate",
                "field": "support_channel",
                "candidate_status": "counseling_may_help",
                "is_final": False,
            }
        )
        fragments.append("상담 지원이 필요할 수 있습니다")

    if not fragments:
        fragments.append("근로자 답변의 주요 의미를 규칙 기반으로 확정하기 어렵습니다")

    summary = "근로자 답변 요약 후보: " + ", ".join(fragments) + "."
    risk_flags = ["MANAGER_REVIEW_REQUIRED"]
    return summary, candidates, risk_flags


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


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
