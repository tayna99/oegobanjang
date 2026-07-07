from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["ko", "vi", "id"]


class TranslationRequest(BaseModel):
    text: str
    source_language: LanguageCode
    target_language: LanguageCode
    purpose: str | None = None


class TranslationResult(BaseModel):
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    risk_flags: list[str] = Field(default_factory=list)
    review_required: bool = False
    provider: str = "rule_based"


class WorkerReplySummaryRequest(BaseModel):
    worker_reply: str
    language_code: Literal["vi", "id"]


class WorkerReplySummaryResult(BaseModel):
    translated_ko: str
    summary_ko: str
    risk_flags: list[str] = Field(default_factory=list)
    manager_review_required: bool = True
    translation_provider: str | None = None


class StatusUpdateCandidateDraft(BaseModel):
    candidate_type: str
    field: str
    candidate_status: str
    is_final: bool = False
    target_type: str | None = None
    confidence: float | None = None
    summary: str | None = None


class ReplyInterpretationRequest(BaseModel):
    translated_ko: str
    language_code: Literal["vi", "id"]
    worker_reply: str | None = None


class ReplyInterpretationResult(BaseModel):
    status_update_candidates: list[StatusUpdateCandidateDraft] = Field(
        default_factory=list
    )
    uncertainty_flags: list[str] = Field(default_factory=list)
    manager_review_required: bool = True


class TranslationQualityCheckRequest(BaseModel):
    korean_text: str
    translated_text: str
    purpose: str
    privacy_purpose: str | None = None
    deadline: str | None = None
    contact_person: str | None = None
    required_elements: list[str] = Field(default_factory=list)


class TranslationQualityCheckResult(BaseModel):
    passed: bool
    risk_flags: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    review_required: bool = False
