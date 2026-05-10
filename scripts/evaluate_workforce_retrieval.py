#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_DATASET_PATH = ROOT_DIR / "evals" / "datasets" / "workforce_retrieval_quality_cases.csv"
DEFAULT_REPORT_CSV = ROOT_DIR / "evals" / "reports" / "workforce_retrieval_quality_latest.csv"
DEFAULT_REPORT_JSON = ROOT_DIR / "evals" / "reports" / "workforce_retrieval_quality_latest.json"
DEFAULT_CHUNKS_DIR = ROOT_DIR / "data-pipeline" / "processed" / "chunks"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent_runtime.rag.workforce_runtime_retriever import retrieve_workforce_runtime_materials


RESULT_COLUMNS = [
    "test_id",
    "question",
    "expected_source_id",
    "top1_source_id",
    "top2_source_id",
    "top3_source_id",
    "top4_source_id",
    "top5_source_id",
    "hit_at_1",
    "hit_at_3",
    "hit_at_5",
    "mrr",
    "pass_fail",
    "fail_reason",
]


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"test_id", "question", "intent", "expected_source_id", "expected_doc_type", "expected_top_k", "notes"}
    if not rows:
        raise ValueError(f"Dataset is empty: {path}")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Dataset {path} missing columns: {', '.join(sorted(missing))}")
    return rows


def load_known_sources(chunks_dir: Path = DEFAULT_CHUNKS_DIR) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for file_name in ("workforce_official_chroma_records.jsonl", "workforce_templates_chroma_records.jsonl"):
        path = chunks_dir / file_name
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                metadata = dict(record.get("metadata") or {})
                source_id = str(metadata.get("source_id") or record.get("id") or "")
                if source_id and source_id not in sources:
                    sources[source_id] = metadata
    return sources


def retrieve_case(case: dict[str, str], *, top_k: int) -> list[dict[str, Any]]:
    case_type = _case_type_for(case)
    sub_agent = _sub_agent_for(case)
    buckets = retrieve_workforce_runtime_materials(
        query=case["question"],
        case_type=case_type,
        sub_agent=sub_agent,
        visa_type="E-9",
        top_k=top_k,
    )
    return flatten_ranked_results(buckets, expected_doc_type=case["expected_doc_type"], top_k=top_k)


def flatten_ranked_results(
    buckets: dict[str, list[dict[str, Any]]],
    *,
    expected_doc_type: str,
    top_k: int,
) -> list[dict[str, Any]]:
    bucket_priority = _bucket_priority(expected_doc_type)
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in bucket_priority:
        for result in buckets.get(bucket, []):
            metadata = dict(result.get("metadata") or {})
            source_id = str(metadata.get("source_id") or result.get("id") or "")
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            ranked.append(
                {
                    "source_id": source_id,
                    "doc_type": str(metadata.get("doc_type", "")),
                    "source_unit_type": str(metadata.get("source_unit_type", "")),
                    "evidence_grade": str(metadata.get("evidence_grade", "")),
                    "bucket": bucket,
                    "title": str(metadata.get("title", "")),
                }
            )
            if len(ranked) >= top_k:
                return ranked
    return ranked


def compute_case_result(
    *,
    case: dict[str, str],
    ranked_results: list[dict[str, Any]],
    known_source_ids: set[str],
) -> dict[str, Any]:
    expected_source_id = case["expected_source_id"]
    expected_doc_type = case["expected_doc_type"]
    expected_top_k = int(case.get("expected_top_k") or 3)
    retrieved_source_ids = [str(result.get("source_id", "")) for result in ranked_results]
    rank = _rank(expected_source_id, retrieved_source_ids)
    official_misuse = _is_official_misuse(expected_doc_type, expected_source_id, ranked_results)
    hit_at_1 = rank == 1 and not official_misuse
    hit_at_3 = rank is not None and rank <= 3 and not official_misuse
    hit_at_5 = rank is not None and rank <= 5 and not official_misuse
    mrr = round(1 / rank, 4) if rank and not official_misuse else 0.0
    pass_fail = "PASS" if rank is not None and rank <= expected_top_k and not official_misuse else "FAIL"
    fail_reason = ""
    if pass_fail == "FAIL":
        fail_reason = _failure_reason(
            case=case,
            rank=rank,
            ranked_results=ranked_results,
            known_source_ids=known_source_ids,
            official_misuse=official_misuse,
        )
    output = {
        "test_id": case["test_id"],
        "question": case["question"],
        "expected_source_id": expected_source_id,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "mrr": mrr,
        "pass_fail": pass_fail,
        "fail_reason": fail_reason,
        "rank": rank,
        "official_misuse": official_misuse,
        "safety_fail": expected_doc_type == "safety_policy" and pass_fail == "FAIL",
    }
    for index in range(5):
        output[f"top{index + 1}_source_id"] = retrieved_source_ids[index] if index < len(retrieved_source_ids) else ""
    return output


def evaluate_cases(
    cases: list[dict[str, str]],
    *,
    top_k: int,
    known_sources: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    known_sources = known_sources or load_known_sources()
    known_source_ids = set(known_sources)
    results = [
        compute_case_result(
            case=case,
            ranked_results=retrieve_case(case, top_k=top_k),
            known_source_ids=known_source_ids,
        )
        for case in cases
    ]
    total = len(results)
    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "hit_at_1": _rate(results, "hit_at_1"),
        "hit_at_3": _rate(results, "hit_at_3"),
        "hit_at_5": _rate(results, "hit_at_5"),
        "mrr": round(sum(float(result["mrr"]) for result in results) / total, 4) if total else 0.0,
        "safety_fail_count": sum(1 for result in results if result["safety_fail"]),
        "official_misuse_count": sum(1 for result in results if result["official_misuse"]),
        "failed_cases": [result for result in results if result["pass_fail"] == "FAIL"],
    }
    return results, summary


def write_reports(results: list[dict[str, Any]], summary: dict[str, Any], *, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow({column: result.get(column, "") for column in RESULT_COLUMNS})
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def _case_type_for(case: dict[str, str]) -> str:
    intent = case.get("intent", "")
    if intent in {"candidate_review", "handoff_question"}:
        return intent
    if case.get("expected_doc_type") in {"checklist", "safety_policy"} and "후보" in case.get("question", ""):
        return "candidate_review"
    return "new_hiring"


def _sub_agent_for(case: dict[str, str]) -> str:
    if _case_type_for(case) == "candidate_review":
        return "candidate_readiness_agent"
    return "workforce_requirement_agent"


def _bucket_priority(expected_doc_type: str) -> list[str]:
    if expected_doc_type == "procedure_step":
        return ["official_procedure", "allowed_industry", "internal_template"]
    if expected_doc_type == "allowed_industry":
        return ["allowed_industry", "official_procedure", "internal_template"]
    return ["internal_template", "official_procedure", "allowed_industry"]


def _rank(expected_source_id: str, source_ids: list[str]) -> int | None:
    for index, source_id in enumerate(source_ids, start=1):
        if source_id == expected_source_id:
            return index
    return None


def _is_official_misuse(expected_doc_type: str, expected_source_id: str, ranked_results: list[dict[str, Any]]) -> bool:
    official_expected = expected_doc_type in {"procedure_step", "allowed_industry"}
    if not official_expected:
        return False
    for result in ranked_results:
        if result.get("source_id") != expected_source_id:
            continue
        if result.get("evidence_grade") in {"D", "F"}:
            return True
        if result.get("doc_type") == "case" or result.get("source_unit_type") == "case_record":
            return True
    return False


def _failure_reason(
    *,
    case: dict[str, str],
    rank: int | None,
    ranked_results: list[dict[str, Any]],
    known_source_ids: set[str],
    official_misuse: bool,
) -> str:
    if case["expected_source_id"] not in known_source_ids:
        return "missing_source"
    if official_misuse:
        return "official_misuse"
    if case["expected_doc_type"] == "safety_policy":
        return "safety_fail"
    if not ranked_results:
        return "metadata_or_filter"
    if rank is None:
        return "query_rewrite" if _looks_like_natural_language(case["question"]) else "ranking"
    return "ranking"


def _looks_like_natural_language(question: str) -> bool:
    official_terms = ("E-9", "고용허가", "내국인", "허용업종", "표준근로계약", "사증발급")
    return not any(term in question for term in official_terms)


def _rate(results: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for result in results if result[key]) / len(results), 4) if results else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate workforce runtime Chroma retrieval quality.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-hit-at-1", type=float, default=0.60)
    parser.add_argument("--min-hit-at-3", type=float, default=0.80)
    parser.add_argument("--min-hit-at-5", type=float, default=0.90)
    parser.add_argument("--min-mrr", type=float, default=0.65)
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    results, summary = evaluate_cases(cases, top_k=args.top_k)
    write_reports(results, summary, csv_path=args.report_csv, json_path=args.report_json)
    passed = (
        summary["hit_at_1"] >= args.min_hit_at_1
        and summary["hit_at_3"] >= args.min_hit_at_3
        and summary["hit_at_5"] >= args.min_hit_at_5
        and summary["mrr"] >= args.min_mrr
        and summary["safety_fail_count"] == 0
        and summary["official_misuse_count"] == 0
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV report: {args.report_csv}")
    print(f"JSON report: {args.report_json}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
