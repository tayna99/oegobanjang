from __future__ import annotations

from collections import Counter
from typing import Any


WORKFORCE_REQUIRED_METADATA = (
    "mission_agent",
    "sub_agent",
    "case_type",
    "workflow_stage",
    "output_usage",
    "source_unit_type",
)

WORKFORCE_COVERAGE_CATEGORIES = (
    "official_procedure",
    "allowed_industry",
    "employer_requirement",
    "internal_template",
    "candidate_readiness_template",
    "candidate_readiness_checklist",
)


def normalize_workforce_metadata(record: dict[str, Any], source_path: str | None = None) -> dict[str, Any]:
    """Infer workforce-agent routing metadata from an already cleaned source record."""
    raw_metadata = record.get("raw_metadata") if isinstance(record.get("raw_metadata"), dict) else {}
    metadata = {**raw_metadata, **record}
    text = _search_text(record, raw_metadata, source_path)

    source_unit_type = _infer_source_unit_type(metadata, text)
    sub_agent = (_as_list(metadata.get("sub_agent")) or [_infer_sub_agent(text, source_unit_type)])[0]
    case_type = (_as_list(metadata.get("case_type")) or [_infer_case_type(text, sub_agent)])[0]
    workflow_stage = str(metadata.get("workflow_stage") or _infer_workflow_stage(case_type, sub_agent))
    output_usage = _as_list(metadata.get("output_usage")) or _infer_output_usage(
        text, sub_agent, case_type, source_unit_type
    )

    return {
        "mission_agent": _merge_list(metadata.get("mission_agent"), "workforce_agent"),
        "sub_agent": [sub_agent],
        "case_type": [case_type],
        "workflow_stage": workflow_stage,
        "output_usage": output_usage,
        "source_unit_type": source_unit_type,
        "industry": _infer_industry(metadata, text),
        "workforce_metadata_confidence": "high" if source_unit_type != "general" else "low",
    }


def is_workforce_relevant_record(record: dict[str, Any], source_path: str | None = None) -> bool:
    raw_metadata = record.get("raw_metadata") if isinstance(record.get("raw_metadata"), dict) else {}
    mission_agent = _as_list(record.get("mission_agent") or raw_metadata.get("mission_agent"))
    if "workforce_agent" in mission_agent:
        return True
    text = _search_text(record, raw_metadata, source_path)
    return _has_any(
        text,
        (
            "고용허가",
            "내국인 구인",
            "구인노력",
            "사업주 고용절차",
            "근로계약",
            "사증발급인정서",
            "취업교육",
            "허용업종",
            "허용 범위",
            "신규 고용",
            "신규 인력",
            "후보 제출 준비도",
            "후보자 기본 확인",
            "여권 보유",
            "증명사진",
            "건강검진",
            "송출회사",
            "행정사",
        ),
    )


def build_workforce_source_inventory(records: list[dict[str, Any]]) -> dict[str, Any]:
    coverage: Counter[str] = Counter()
    metadata_gaps: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        normalized = normalize_workforce_metadata(record, source_path=str(record.get("source_path") or ""))
        merged = {**record, **normalized}
        for category in _coverage_categories_for(merged):
            coverage[category] += 1

        missing = [field for field in WORKFORCE_REQUIRED_METADATA if not merged.get(field)]
        if missing:
            metadata_gaps.append(
                {
                    "index": index,
                    "source_id": record.get("source_id"),
                    "title": record.get("title"),
                    "missing": missing,
                }
            )

    coverage_dict = {category: coverage.get(category, 0) for category in WORKFORCE_COVERAGE_CATEGORIES}
    missing_categories = [category for category, count in coverage_dict.items() if count == 0]
    return {
        "coverage": coverage_dict,
        "missing_categories": missing_categories,
        "metadata_gaps": metadata_gaps,
    }


def _coverage_categories_for(metadata: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    source_type = str(metadata.get("source_type", ""))
    source_unit_type = str(metadata.get("source_unit_type", ""))
    sub_agent = _as_list(metadata.get("sub_agent"))
    output_usage = _as_list(metadata.get("output_usage"))

    if source_type == "official_procedure" and source_unit_type == "procedure_step":
        categories.append("official_procedure")
    if source_unit_type == "allowed_industry":
        categories.append("allowed_industry")
    if source_unit_type == "employer_requirement" and "workforce_requirement_agent" in sub_agent:
        categories.append("employer_requirement")
    if source_type in {"internal_template", "message_template"} or (
        str(metadata.get("evidence_grade", "")).upper() == "E" and "request_form" in output_usage
    ):
        categories.append("internal_template")
    if "candidate_readiness_agent" in sub_agent and (
        source_type == "internal_template" or "candidate_readiness_table" in output_usage
    ):
        categories.append("candidate_readiness_template")
    if "candidate_readiness_agent" in sub_agent and source_type == "internal_checklist":
        categories.append("candidate_readiness_checklist")
    return categories


def _infer_source_unit_type(metadata: dict[str, Any], text: str) -> str:
    existing = str(metadata.get("source_unit_type") or "")
    if existing and existing != "general":
        return existing
    if str(metadata.get("source_type", "")) == "internal_template" or str(metadata.get("doc_type", "")) == "template":
        return existing or "template_purpose"
    if _has_any(text, ("허용업종", "허용 범위", "제조업 허용", "농축산업 허용", "어업 허용")):
        return "allowed_industry"
    if _has_any(text, ("후보자 기본 확인", "후보 제출 준비도", "여권 보유", "증명사진", "건강검진", "근무 가능일")):
        return "employer_requirement"
    if _has_any(text, ("사업주 확인 항목", "신규 e-9 고용 전", "고용 전 사업주", "숙소 제공 여부", "근무 형태")):
        return "employer_requirement"
    return existing or "general"


def _infer_sub_agent(text: str, source_unit_type: str) -> str:
    if source_unit_type == "employer_requirement" and _has_any(
        text, ("후보", "여권", "증명사진", "건강검진", "근무 가능", "기숙사 안내", "근무조건 안내")
    ):
        return "candidate_readiness_agent"
    if _has_any(text, ("후보 제출 준비도", "candidate_readiness", "candidate_review")):
        return "candidate_readiness_agent"
    return "workforce_requirement_agent"


def _infer_case_type(text: str, sub_agent: str) -> str:
    if sub_agent == "candidate_readiness_agent":
        return "candidate_review"
    if _has_any(text, ("송출회사", "행정사", "확인 질문")):
        return "handoff_question"
    if _has_any(text, ("요청서", "request_form")):
        return "request_form"
    return "new_hiring"


def _infer_workflow_stage(case_type: str, sub_agent: str) -> str:
    if sub_agent == "candidate_readiness_agent":
        return "candidate_readiness"
    if case_type == "handoff_question":
        return "handoff_preparation"
    return "pre_hiring"


def _infer_output_usage(text: str, sub_agent: str, case_type: str, source_unit_type: str) -> list[str]:
    if sub_agent == "candidate_readiness_agent":
        return ["readiness_check", "candidate_readiness_table", "additional_questions"]
    if case_type == "handoff_question":
        return ["handoff_question", "additional_questions"]
    if case_type == "request_form" or source_unit_type == "employer_requirement":
        return ["requirement_check", "request_form", "handoff_question"]
    if source_unit_type == "allowed_industry":
        return ["requirement_check"]
    return ["requirement_check", "request_form", "handoff_question"]


def _infer_industry(metadata: dict[str, Any], text: str) -> list[str]:
    existing = metadata.get("industry")
    if isinstance(existing, list) and existing:
        return existing
    if isinstance(existing, str) and existing:
        return [existing]
    if _has_any(text, ("제조", "자동차부품", "manufacturing")):
        return ["manufacturing"]
    if _has_any(text, ("농축산", "agriculture")):
        return ["agriculture"]
    if _has_any(text, ("어업", "fishery")):
        return ["fishery"]
    if _has_any(text, ("서비스", "service")):
        return ["service"]
    return ["ALL"]


def _search_text(record: dict[str, Any], raw_metadata: dict[str, Any], source_path: str | None) -> str:
    values = [
        source_path or "",
        str(record.get("source_id", "")),
        str(record.get("title", "")),
        str(record.get("source_type", "")),
        str(record.get("doc_type", "")),
        str(record.get("text") or record.get("content") or ""),
        str(raw_metadata.get("source_unit_type", "")),
    ]
    return " ".join(values).lower()


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _merge_list(value: Any, required: str) -> list[str]:
    items = _as_list(value)
    if required not in items:
        items.append(required)
    return items


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
