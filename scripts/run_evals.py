#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT_DIR / "evals" / "datasets"
REPORTS_DIR = ROOT_DIR / "evals" / "reports"


REQUIRED_FIELDS_BY_DATASET: dict[str, list[str]] = {
    "intent_router_cases": ["id", "input", "expected_intents"],
    "rag_retrieval_cases": ["id", "input"],
    "safety_guardrail_cases": ["id", "input"],
    "workflow_e2e_cases": ["id", "input"],
    "document_gap_cases": ["id"],
    "message_generation_cases": ["id", "input"],
}


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