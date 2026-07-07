from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent_runtime.llm.workforce_contract import WorkforceAgentResponse


@dataclass
class WorkforceValidationReport:
    passed: bool
    errors: list[str] = field(default_factory=list)


def validate_workforce_response(
    response: WorkforceAgentResponse,
    *,
    retrieved_sources: list[dict[str, Any]],
    rule_results: dict[str, Any] | None = None,
) -> WorkforceValidationReport:
    errors: list[str] = []
    source_ids = {
        str(source.get("source_id") or source.get("id") or "")
        for source in retrieved_sources
        if source.get("source_id") or source.get("id")
    }
    if source_ids:
        for evidence in response.evidence:
            if evidence.source_id not in source_ids:
                errors.append(f"evidence_source_not_retrieved:{evidence.source_id}")
            if evidence.evidence_grade in {"D", "F"} and evidence.used_for != "reference_only":
                errors.append(f"low_grade_evidence_used_as_official:{evidence.source_id}")

    if response.approval.requires_human_approval is not True:
        errors.append("human_approval_required_missing")

    if rule_results and rule_results.get("approval_required") and response.approval.requires_human_approval is not True:
        errors.append("business_rule_approval_conflict")

    return WorkforceValidationReport(passed=not errors, errors=errors)
