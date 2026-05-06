from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.app.agent_runtime.rag.multilingual_contact_retriever import (
    RetrievedContext,
    search_multilingual_contact_docs,
)


TOOL_NAME = "search_multilingual_contact_rag"
TOOL_GRADE = "SAFE_READ"
SUPPORTED_LANGUAGES = {"vi", "id"}
SUPPORTED_INTENTS = {"counseling", "safety", "life", "notice"}
FORBIDDEN_RESULT_MARKERS = (
    "worker_replies",
    "synthetic_cases",
    "public_cases",
    "templates",
    "synthetic_worker_reply",
    "public_case_patterns",
    "interview_case_patterns",
)


class SearchMultilingualContactRagInput(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=10)
    language_code: str | None = None
    intent: str | None = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be empty")
        return value.strip()

    @field_validator("language_code")
    @classmethod
    def language_must_be_supported(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError("unsupported language_code")
        return normalized

    @field_validator("intent")
    @classmethod
    def intent_must_be_supported(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if normalized not in SUPPORTED_INTENTS:
            raise ValueError("unsupported intent")
        return normalized


class SearchMultilingualContactRagOutput(BaseModel):
    tool_name: str = TOOL_NAME
    tool_grade: Literal["SAFE_READ"] = "SAFE_READ"
    status: Literal["SUCCESS", "FAILED"]
    input_snapshot: dict[str, Any]
    output: dict[str, Any]
    citations: list[dict[str, Any]]
    risk_flags: list[str]
    approval_required: bool = False
    error: str | None = None


def search_multilingual_contact_rag_tool(
    payload: SearchMultilingualContactRagInput | dict[str, Any],
) -> SearchMultilingualContactRagOutput:
    try:
        tool_input = (
            payload
            if isinstance(payload, SearchMultilingualContactRagInput)
            else SearchMultilingualContactRagInput.model_validate(payload)
        )
    except ValidationError as exc:
        risk_flags = _validation_risk_flags(exc)
        return _failed_output(
            input_snapshot=payload if isinstance(payload, dict) else payload.model_dump(),
            error=_compact_validation_error(exc),
            risk_flags=risk_flags,
        )

    input_snapshot = tool_input.model_dump()

    try:
        results = search_multilingual_contact_docs(
            tool_input.query,
            top_k=tool_input.top_k,
            language_code=tool_input.language_code,
            intent=tool_input.intent,
        )
    except Exception as exc:
        return _failed_output(
            input_snapshot=input_snapshot,
            error=f"{type(exc).__name__}: {exc}",
            risk_flags=[],
        )

    safe_results = [result for result in results if _is_safe_context(result)]
    citations = [_to_citation(result) for result in safe_results]
    risk_flags: list[str] = []

    if not safe_results:
        risk_flags.append("NO_OFFICIAL_CONTEXT_FOUND")
    elif len(safe_results) < tool_input.top_k:
        risk_flags.append("LOW_CONFIDENCE_RESULTS")

    citation_source_ids = [citation["source_id"] for citation in citations]
    output = {
        "tool_name": TOOL_NAME,
        "tool_grade": TOOL_GRADE,
        "query": tool_input.query,
        "result_count": len(safe_results),
        "results": [result.model_dump() for result in safe_results],
        "citation_source_ids": citation_source_ids,
        "approval_required": False,
        "status": "SUCCESS",
        "risk_flags": risk_flags,
    }

    return SearchMultilingualContactRagOutput(
        status="SUCCESS",
        input_snapshot=input_snapshot,
        output=output,
        citations=citations,
        risk_flags=risk_flags,
        approval_required=False,
        error=None,
    )


def _failed_output(
    *,
    input_snapshot: dict[str, Any],
    error: str,
    risk_flags: list[str],
) -> SearchMultilingualContactRagOutput:
    return SearchMultilingualContactRagOutput(
        status="FAILED",
        input_snapshot=input_snapshot,
        output={
            "tool_name": TOOL_NAME,
            "tool_grade": TOOL_GRADE,
            "query": input_snapshot.get("query"),
            "result_count": 0,
            "results": [],
            "citation_source_ids": [],
            "approval_required": False,
            "status": "FAILED",
            "risk_flags": risk_flags,
        },
        citations=[],
        risk_flags=risk_flags,
        approval_required=False,
        error=error,
    )


def _to_citation(result: RetrievedContext) -> dict[str, Any]:
    return {
        "citation_label": result.citation_label,
        "source_id": result.source_id,
        "title": result.title,
        "publisher": result.publisher,
        "doc_type": result.doc_type,
        "evidence_grade": result.evidence_grade,
        "raw_path": result.raw_path,
        "page_number": result.page_number,
    }


def _is_safe_context(result: RetrievedContext) -> bool:
    if result.evidence_grade == "F":
        return False

    if result.not_for_legal_basis is True:
        return False

    combined = "\n".join(
        [
            result.raw_path,
            result.context,
            result.text,
            result.source_id,
        ]
    )
    return not any(marker in combined for marker in FORBIDDEN_RESULT_MARKERS)


def _validation_risk_flags(exc: ValidationError) -> list[str]:
    flags: list[str] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        message = str(error.get("msg", ""))
        if "language_code" in loc:
            flags.append("UNSUPPORTED_LANGUAGE")
        elif "intent" in loc:
            flags.append("UNSUPPORTED_INTENT")
        elif "top_k" in loc:
            flags.append("LOW_CONFIDENCE_RESULTS")
        elif "query" in loc and "empty" in message:
            flags.append("NO_OFFICIAL_CONTEXT_FOUND")
    return flags


def _compact_validation_error(exc: ValidationError) -> str:
    messages = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        msg = error.get("msg", "validation error")
        messages.append(f"{loc}: {msg}")
    return "; ".join(messages)
