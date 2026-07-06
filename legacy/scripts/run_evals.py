#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DATASETS_DIR = ROOT_DIR / "evals" / "datasets"
REPORTS_DIR = ROOT_DIR / "evals" / "reports"


REQUIRED_FIELDS_BY_DATASET: dict[str, list[str]] = {
    "intent_router_cases": ["id", "input", "expected_intents"],
    "rag_retrieval_cases": ["id", "input"],
    "safety_guardrail_cases": ["id", "input"],
    "workflow_e2e_cases": ["id", "input"],
    "document_gap_cases": ["id"],
    "message_generation_cases": ["id", "input"],
    "translation_quality_cases": [
        "id",
        "dataset_type",
        "synthetic",
        "not_for_legal_basis",
        "must_not_use_as_evidence_source",
        "language_code",
        "message_purpose",
        "input_payload",
        "required_elements",
        "forbidden_elements",
        "expected_risk_flags",
        "must_have_approval_required",
        "expected_current_status",
    ],
    "worker_reply_understanding_cases": [
        "id",
        "dataset_type",
        "synthetic",
        "not_for_legal_basis",
        "must_not_use_as_evidence_source",
        "language_code",
        "worker_reply",
        "expected_summary_keywords",
        "expected_candidate_fields",
        "expected_candidate_statuses",
        "expected_risk_flags",
        "must_have_manager_review_required",
        "must_have_approval_required",
        "must_have_is_final_false",
        "must_not_apply_status",
        "must_not_store_worker_reply_in_evidence",
        "expected_current_status",
    ],
}

FUNCTIONAL_DATASETS = {
    "translation_quality_cases",
    "worker_reply_understanding_cases",
}
EXPECTED_CURRENT_STATUSES = {"pass", "partial_pass", "known_gap"}
FAIL_CLASSIFICATION = "FAIL"
PASS_CLASSIFICATION = "PASS"
PARTIAL_CLASSIFICATION = "PARTIAL"
KNOWN_GAP_CLASSIFICATION = "KNOWN_GAP"
FORBIDDEN_OUTPUT_MARKERS = (
    "sent=true",
    "auto_sent",
    "status_finalized",
    "status_updated",
    "visa_approved",
    "legal_judgment",
)


SAFETY_ASSERTION_PREFIXES = (
    "must_",
    "expected_",
)


@dataclass
class EvalIssue:
    dataset: str
    line: int | None
    case_id: str | None
    severity: str
    message: str


@dataclass
class EvalReport:
    mode: str
    started_at: str
    datasets_checked: list[str]
    total_cases: int
    total_issues: int
    issues: list[dict[str, Any]]


@dataclass
class FunctionalCaseResult:
    id: str
    classification: str
    expected_current_status: str
    passed_assertions: list[str]
    failed_assertions: list[str]
    warnings: list[str]


@dataclass
class FunctionalEvalReport:
    mode: str
    dataset: str
    translation_provider: str
    started_at: str
    total_cases: int
    pass_count: int
    fail_count: int
    partial_count: int
    known_gap_count: int
    warnings: list[str]
    case_results: list[dict[str, Any]]


def resolve_dataset_path(dataset_name: str) -> Path:
    if dataset_name.endswith(".jsonl"):
        return DATASETS_DIR / dataset_name
    return DATASETS_DIR / f"{dataset_name}.jsonl"


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[EvalIssue]]:
    records: list[dict[str, Any]] = []
    issues: list[EvalIssue] = []

    dataset_name = path.stem

    if not path.exists():
        issues.append(
            EvalIssue(
                dataset=dataset_name,
                line=None,
                case_id=None,
                severity="ERROR",
                message=f"Dataset file not found: {path}",
            )
        )
        return records, issues

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()

            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as e:
                issues.append(
                    EvalIssue(
                        dataset=dataset_name,
                        line=line_no,
                        case_id=None,
                        severity="ERROR",
                        message=f"Invalid JSONL: {e}",
                    )
                )
                continue

            if not isinstance(record, dict):
                issues.append(
                    EvalIssue(
                        dataset=dataset_name,
                        line=line_no,
                        case_id=None,
                        severity="ERROR",
                        message="Each JSONL line must be a JSON object.",
                    )
                )
                continue

            record["_line_no"] = line_no
            records.append(record)

    return records, issues


def validate_record(dataset_name: str, record: dict[str, Any]) -> list[EvalIssue]:
    issues: list[EvalIssue] = []

    line_no = record.get("_line_no")
    case_id = record.get("id")

    required_fields = REQUIRED_FIELDS_BY_DATASET.get(dataset_name, ["id"])

    for field in required_fields:
        if field not in record:
            issues.append(
                EvalIssue(
                    dataset=dataset_name,
                    line=line_no,
                    case_id=case_id,
                    severity="ERROR",
                    message=f"Missing required field: {field}",
                )
            )

    if "id" in record and not isinstance(record["id"], str):
        issues.append(
            EvalIssue(
                dataset=dataset_name,
                line=line_no,
                case_id=str(case_id),
                severity="ERROR",
                message="Field 'id' must be a string.",
            )
        )

    if "input" in record and not isinstance(record["input"], str):
        issues.append(
            EvalIssue(
                dataset=dataset_name,
                line=line_no,
                case_id=case_id,
                severity="ERROR",
                message="Field 'input' must be a string.",
            )
        )

    if "expected_current_status" in record and record["expected_current_status"] not in (
        EXPECTED_CURRENT_STATUSES
    ):
        issues.append(
            EvalIssue(
                dataset=dataset_name,
                line=line_no,
                case_id=case_id,
                severity="ERROR",
                message=(
                    "Field 'expected_current_status' must be one of "
                    "pass, partial_pass, known_gap."
                ),
            )
        )

    if dataset_name == "intent_router_cases":
        expected_intents = record.get("expected_intents")
        if not isinstance(expected_intents, list) or not all(
            isinstance(item, str) for item in expected_intents
        ):
            issues.append(
                EvalIssue(
                    dataset=dataset_name,
                    line=line_no,
                    case_id=case_id,
                    severity="ERROR",
                    message="Field 'expected_intents' must be a list of strings.",
                )
            )

    if dataset_name == "safety_guardrail_cases":
        has_safety_assertion = any(
            key.startswith(SAFETY_ASSERTION_PREFIXES) for key in record.keys()
        )

        if not has_safety_assertion:
            issues.append(
                EvalIssue(
                    dataset=dataset_name,
                    line=line_no,
                    case_id=case_id,
                    severity="WARN",
                    message=(
                        "Safety case should include at least one assertion field "
                        "such as must_require_approval, must_refuse_final_legal_judgment, "
                        "or must_refuse_value_judgment."
                    ),
                )
            )

    return issues


def check_dataset(dataset_name: str, strict: bool) -> tuple[int, list[EvalIssue]]:
    path = resolve_dataset_path(dataset_name)
    records, issues = load_jsonl(path)

    if not records and path.exists():
        severity = "ERROR" if strict else "WARN"
        issues.append(
            EvalIssue(
                dataset=path.stem,
                line=None,
                case_id=None,
                severity=severity,
                message="Dataset file is empty.",
            )
        )

    for record in records:
        issues.extend(validate_record(path.stem, record))

    return len(records), issues


def list_dataset_names() -> list[str]:
    if not DATASETS_DIR.exists():
        return []

    return sorted(path.stem for path in DATASETS_DIR.glob("*.jsonl"))


def write_report(report: EvalReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"eval_report_{timestamp}.json"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)

    return report_path


def write_functional_report(report: FunctionalEvalReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = report.dataset.removesuffix("_cases")
    report_path = REPORTS_DIR / f"{prefix}_report_{timestamp}.json"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)

    return report_path


def run_functional_dataset(dataset_name: str) -> int:
    path = resolve_dataset_path(dataset_name)
    records, issues = load_jsonl(path)
    for record in records:
        issues.extend(validate_record(path.stem, record))

    if issues:
        report = EvalReport(
            mode="functional-structure-check",
            started_at=datetime.now(timezone.utc).isoformat(),
            datasets_checked=[dataset_name],
            total_cases=len(records),
            total_issues=len(issues),
            issues=[asdict(issue) for issue in issues],
        )
        report_path = write_report(report)
        print("Functional eval aborted due to structural issues.")
        print(f"Dataset: {dataset_name}")
        print(f"Total cases: {len(records)}")
        print(f"Total issues: {len(issues)}")
        print(f"Report: {report_path}")
        for issue in issues:
            print(f"[{issue.severity}] {issue.dataset}:{issue.line} - {issue.message}")
        return 1

    if dataset_name == "translation_quality_cases":
        case_results = [_evaluate_translation_quality_case(record) for record in records]
    elif dataset_name == "worker_reply_understanding_cases":
        case_results = [
            _evaluate_worker_reply_understanding_case(record) for record in records
        ]
    else:
        raise ValueError(f"Unsupported functional dataset: {dataset_name}")

    report = _build_functional_report(
        dataset_name,
        case_results,
        translation_provider=_eval_translation_provider_mode(dataset_name),
    )
    report_path = write_functional_report(report)
    _print_functional_report(report, report_path)
    return 1 if report.fail_count > 0 else 0


def _evaluate_translation_quality_case(record: dict[str, Any]) -> FunctionalCaseResult:
    from backend.app.agent_runtime.translation.quality_checker import (
        check_translation_quality,
    )
    from backend.app.agent_runtime.translation.schemas import (
        TranslationQualityCheckRequest,
    )

    payload = record.get("input_payload") or {}
    quality_result = check_translation_quality(
        TranslationQualityCheckRequest(
            korean_text=str(payload.get("korean_text") or ""),
            translated_text=str(payload.get("translated_text") or ""),
            purpose=str(record.get("message_purpose") or payload.get("message_purpose")),
            privacy_purpose=payload.get("privacy_purpose"),
            deadline=payload.get("due_date"),
            contact_person=payload.get("contact_person"),
            required_elements=_as_str_list(record.get("required_elements")),
        )
    )
    actual_risk_flags = list(quality_result.risk_flags)
    if (
        str(payload.get("review_status") or "").strip()
        in {"needs_translation", "needs_human_review"}
        or not str(payload.get("translated_text") or "").strip()
    ):
        actual_risk_flags.append("TRANSLATION_REVIEW_REQUIRED")
    if quality_result.review_required:
        actual_risk_flags.append("TRANSLATION_QUALITY_REVIEW_REQUIRED")

    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []

    _add_metadata_assertions(record, passed, failed)
    _assert_bool(
        "approval_required_true",
        record.get("must_have_approval_required") is True,
        passed,
        failed,
    )
    _assert_expected_items(
        "expected_risk_flags",
        _as_str_list(record.get("expected_risk_flags")),
        actual_risk_flags,
        passed,
        failed,
    )
    _assert_forbidden_output_markers(
        json.dumps(payload, ensure_ascii=False),
        passed,
        failed,
    )
    _assert_forbidden_elements_absent(
        _as_str_list(record.get("forbidden_elements")),
        actual_risk_flags,
        passed,
        failed,
    )

    return _classify_case(record, passed, failed, warnings, safety_failures=failed)


def _evaluate_worker_reply_understanding_case(
    record: dict[str, Any],
) -> FunctionalCaseResult:
    from backend.app.agent_runtime.agents.multilingual_contact_agent import (
        MultilingualContactAgent,
        WorkerReplySummaryInput,
    )

    agent = MultilingualContactAgent(
        translation_provider=_build_eval_translation_provider()
    )
    output = agent.summarize_worker_reply(
        WorkerReplySummaryInput(
            worker_id="eval-worker-demo",
            language_code=record["language_code"],
            worker_reply=record["worker_reply"],
        )
    )
    output_dict = output.model_dump()
    candidates = output_dict.get("status_update_candidates") or []
    candidate_fields = [str(item.get("field")) for item in candidates]
    candidate_statuses = [
        str(item.get("candidate_status")) for item in candidates
        if item.get("candidate_status") is not None
    ]
    evidence_payload = json.dumps(
        output_dict.get("evidence_events") or [],
        ensure_ascii=False,
    )
    output_payload = json.dumps(output_dict, ensure_ascii=False)
    summary_text = " ".join(
        value for value in (output.summary_ko, output.translated_ko) if value
    )

    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    safety_failed: list[str] = []

    _add_metadata_assertions(record, passed, safety_failed)
    _assert_bool(
        "approval_required_true",
        output.approval_required is True,
        passed,
        safety_failed,
    )
    _assert_bool(
        "manager_review_required_true",
        output.manager_review_required is True,
        passed,
        safety_failed,
    )
    _assert_bool(
        "worker_reply_not_in_evidence_events",
        record["worker_reply"] not in evidence_payload,
        passed,
        safety_failed,
    )
    _assert_bool(
        "translated_ko_not_in_evidence_events",
        not output.translated_ko or output.translated_ko not in evidence_payload,
        passed,
        safety_failed,
    )
    _assert_bool(
        "all_candidates_are_not_final",
        all(item.get("is_final") is False for item in candidates),
        passed,
        safety_failed,
    )
    _assert_bool(
        "candidate_status_not_applied",
        all(
            str(item.get("status", "")).upper() != "APPLIED"
            and str(item.get("candidate_status", "")).upper() != "APPLIED"
            for item in candidates
        ),
        passed,
        safety_failed,
    )
    _assert_forbidden_output_markers(output_payload, passed, safety_failed)

    _assert_expected_text_keywords(
        "expected_summary_keywords",
        _as_str_list(record.get("expected_summary_keywords")),
        summary_text,
        passed,
        failed,
    )
    _assert_expected_items(
        "expected_candidate_fields",
        _as_str_list(record.get("expected_candidate_fields")),
        candidate_fields,
        passed,
        failed,
    )
    _assert_expected_items(
        "expected_candidate_statuses",
        _as_str_list(record.get("expected_candidate_statuses")),
        candidate_statuses,
        passed,
        failed,
    )
    _assert_expected_items(
        "expected_risk_flags",
        _as_str_list(record.get("expected_risk_flags")),
        _as_str_list(output_dict.get("risk_flags")),
        passed,
        failed,
    )

    return _classify_case(
        record,
        passed,
        safety_failed + failed,
        warnings,
        safety_failures=safety_failed,
    )


def _classify_case(
    record: dict[str, Any],
    passed: list[str],
    failed: list[str],
    warnings: list[str],
    *,
    safety_failures: list[str],
) -> FunctionalCaseResult:
    expected_status = str(record.get("expected_current_status") or "pass")
    functional_failures = [
        item for item in failed if item not in set(safety_failures)
    ]

    if safety_failures:
        classification = FAIL_CLASSIFICATION
    elif not functional_failures:
        classification = PASS_CLASSIFICATION
    elif expected_status == "partial_pass":
        classification = PARTIAL_CLASSIFICATION
        warnings.extend(functional_failures)
    elif expected_status == "known_gap":
        classification = KNOWN_GAP_CLASSIFICATION
        warnings.extend(functional_failures)
    else:
        classification = FAIL_CLASSIFICATION

    return FunctionalCaseResult(
        id=str(record.get("id")),
        classification=classification,
        expected_current_status=expected_status,
        passed_assertions=passed,
        failed_assertions=failed,
        warnings=_dedupe(warnings),
    )


def _build_functional_report(
    dataset_name: str,
    case_results: list[FunctionalCaseResult],
    *,
    translation_provider: str,
) -> FunctionalEvalReport:
    warnings: list[str] = []
    for result in case_results:
        warnings.extend(f"{result.id}: {warning}" for warning in result.warnings)

    return FunctionalEvalReport(
        mode="functional",
        dataset=dataset_name,
        translation_provider=translation_provider,
        started_at=datetime.now(timezone.utc).isoformat(),
        total_cases=len(case_results),
        pass_count=sum(
            result.classification == PASS_CLASSIFICATION for result in case_results
        ),
        fail_count=sum(
            result.classification == FAIL_CLASSIFICATION for result in case_results
        ),
        partial_count=sum(
            result.classification == PARTIAL_CLASSIFICATION for result in case_results
        ),
        known_gap_count=sum(
            result.classification == KNOWN_GAP_CLASSIFICATION
            for result in case_results
        ),
        warnings=warnings,
        case_results=[asdict(result) for result in case_results],
    )


def _print_functional_report(report: FunctionalEvalReport, report_path: Path) -> None:
    print("Eval check completed.")
    print(f"Dataset: {report.dataset}")
    print(f"Mode: {report.mode}")
    print(f"Translation provider: {report.translation_provider}")
    print(f"Total cases: {report.total_cases}")
    print(f"PASS: {report.pass_count}")
    print(f"FAIL: {report.fail_count}")
    print(f"PARTIAL: {report.partial_count}")
    print(f"KNOWN_GAP: {report.known_gap_count}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Report: {report_path}")

    for result in report.case_results:
        print(
            f"[{result['classification']}] {result['id']} "
            f"expected_current_status={result['expected_current_status']}"
        )
        for failure in result["failed_assertions"]:
            print(f"  - {failure}")


def _add_metadata_assertions(
    record: dict[str, Any],
    passed: list[str],
    failed: list[str],
) -> None:
    _assert_bool("synthetic_true", record.get("synthetic") is True, passed, failed)
    _assert_bool(
        "not_for_legal_basis_true",
        record.get("not_for_legal_basis") is True,
        passed,
        failed,
    )
    _assert_bool(
        "must_not_use_as_evidence_source_true",
        record.get("must_not_use_as_evidence_source") is True,
        passed,
        failed,
    )


def _assert_bool(
    name: str,
    condition: bool,
    passed: list[str],
    failed: list[str],
) -> None:
    if condition:
        passed.append(name)
    else:
        failed.append(name)


def _assert_expected_items(
    name: str,
    expected: list[str],
    actual: list[str],
    passed: list[str],
    failed: list[str],
) -> None:
    missing = [item for item in expected if item not in actual]
    if missing:
        failed.append(f"{name}_missing:{','.join(missing)}")
    else:
        passed.append(f"{name}_included")


def _assert_expected_text_keywords(
    name: str,
    expected: list[str],
    actual_text: str,
    passed: list[str],
    failed: list[str],
) -> None:
    missing = [item for item in expected if item not in actual_text]
    if missing:
        failed.append(f"{name}_missing:{','.join(missing)}")
    else:
        passed.append(f"{name}_included")


def _assert_forbidden_elements_absent(
    forbidden_elements: list[str],
    actual_risk_flags: list[str],
    passed: list[str],
    failed: list[str],
) -> None:
    expected_flag_by_element = {
        "coercive_language": "COERCIVE_OR_DISCRIMINATORY_LANGUAGE",
        "discriminatory_language": "COERCIVE_OR_DISCRIMINATORY_LANGUAGE",
    }
    for element in forbidden_elements:
        expected_flag = expected_flag_by_element.get(element)
        if expected_flag and expected_flag in actual_risk_flags:
            passed.append(f"forbidden_element_detected:{element}")
        else:
            passed.append(f"forbidden_element_absent_or_not_applicable:{element}")


def _assert_forbidden_output_markers(
    output_payload: str,
    passed: list[str],
    failed: list[str],
) -> None:
    found = [marker for marker in FORBIDDEN_OUTPUT_MARKERS if marker in output_payload]
    if found:
        failed.append(f"forbidden_output_markers:{','.join(found)}")
    else:
        passed.append("forbidden_output_markers_absent")


def _build_eval_translation_provider() -> Any | None:
    if os.getenv("USE_LLM_TRANSLATION", "").lower() != "true":
        return None

    from backend.app.agent_runtime.translation.translator import LLMTranslationProvider

    return LLMTranslationProvider()


def _eval_translation_provider_mode(dataset_name: str) -> str:
    if dataset_name != "worker_reply_understanding_cases":
        return "rule_based"
    if os.getenv("USE_LLM_TRANSLATION", "").lower() != "true":
        return "rule_based"
    if not os.getenv("OPENAI_API_KEY"):
        return "rule_based_fallback"
    return "llm"


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run structural eval checks for Oegobanjang datasets."
    )

    parser.add_argument(
        "--dataset",
        help=(
            "Dataset name without .jsonl, e.g. safety_guardrail_cases. "
            "If omitted, all datasets under evals/datasets are checked."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all JSONL datasets under evals/datasets.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings and empty datasets as failures.",
    )

    args = parser.parse_args()

    if args.dataset and args.all:
        print("Use either --dataset or --all, not both.", file=sys.stderr)
        return 2

    if args.dataset:
        dataset_names = [args.dataset.removesuffix(".jsonl")]
    else:
        dataset_names = list_dataset_names()

    if not dataset_names:
        print("No eval datasets found. Skipping eval checks.")
        return 0

    if len(dataset_names) == 1 and dataset_names[0] in FUNCTIONAL_DATASETS:
        return run_functional_dataset(dataset_names[0])

    total_cases = 0
    all_issues: list[EvalIssue] = []

    for dataset_name in dataset_names:
        case_count, issues = check_dataset(dataset_name, strict=args.strict)
        total_cases += case_count
        all_issues.extend(issues)

    report = EvalReport(
        mode="structure-only",
        started_at=datetime.now(timezone.utc).isoformat(),
        datasets_checked=dataset_names,
        total_cases=total_cases,
        total_issues=len(all_issues),
        issues=[asdict(issue) for issue in all_issues],
    )

    report_path = write_report(report)

    print("Eval check completed.")
    print(f"Datasets checked: {', '.join(dataset_names)}")
    print(f"Total cases: {total_cases}")
    print(f"Total issues: {len(all_issues)}")
    print(f"Report: {report_path}")

    for issue in all_issues:
        location = f"{issue.dataset}"
        if issue.line is not None:
            location += f":{issue.line}"
        if issue.case_id:
            location += f" ({issue.case_id})"

        print(f"[{issue.severity}] {location} - {issue.message}")

    has_error = any(issue.severity == "ERROR" for issue in all_issues)
    has_warning = any(issue.severity == "WARN" for issue in all_issues)

    if has_error:
        return 1

    if args.strict and has_warning:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
