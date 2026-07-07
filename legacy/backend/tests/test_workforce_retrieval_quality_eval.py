from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "evaluate_workforce_retrieval.py"
DATASET_PATH = ROOT_DIR / "evals" / "datasets" / "workforce_retrieval_quality_cases.csv"
PLAN_DOC_PATH = ROOT_DIR / "docs" / "WORKFORCE_RETRIEVAL_QUALITY_EVAL.md"

SPEC = importlib.util.spec_from_file_location("evaluate_workforce_retrieval", SCRIPT_PATH)
assert SPEC is not None
evaluate_workforce_retrieval = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate_workforce_retrieval)


def test_workforce_retrieval_quality_dataset_contract() -> None:
    rows = list(csv.DictReader(DATASET_PATH.open("r", encoding="utf-8-sig")))
    required_columns = {
        "test_id",
        "question",
        "intent",
        "expected_source_id",
        "expected_doc_type",
        "expected_top_k",
        "notes",
    }

    assert len(rows) >= 20
    assert required_columns.issubset(rows[0])
    assert {row["test_id"] for row in rows} >= {f"T{index:03d}" for index in range(1, 21)}
    assert {"procedure_step", "allowed_industry", "checklist", "template", "safety_policy"}.issubset(
        {row["expected_doc_type"] for row in rows}
    )


def test_workforce_retrieval_quality_plan_document_exists() -> None:
    content = PLAN_DOC_PATH.read_text(encoding="utf-8")

    assert "Hit@1 >= 0.60" in content
    assert "Hit@3 >= 0.80" in content
    assert "Hit@5 >= 0.90" in content
    assert "MRR >= 0.65" in content
    assert "Safety Fail = 0" in content
    assert "official_misuse_count = 0" in content
    assert "evals/datasets/workforce_retrieval_quality_cases.csv" in content


def test_safety_questions_expect_forbidden_policy_source() -> None:
    rows = list(csv.DictReader(DATASET_PATH.open("r", encoding="utf-8-sig")))
    safety_rows = [row for row in rows if row["expected_doc_type"] == "safety_policy"]

    assert len(safety_rows) >= 4
    for row in safety_rows:
        assert row["expected_source_id"] == "candidate_forbidden_policy"
        assert int(row["expected_top_k"]) <= 3


def test_compute_case_result_calculates_hits_and_mrr() -> None:
    result = evaluate_workforce_retrieval.compute_case_result(
        case={
            "test_id": "T999",
            "question": "테스트 질문",
            "expected_source_id": "expected_source",
            "expected_doc_type": "procedure_step",
            "expected_top_k": "3",
        },
        ranked_results=[
            {"source_id": "other_source", "doc_type": "procedure"},
            {"source_id": "expected_source", "doc_type": "procedure"},
            {"source_id": "third_source", "doc_type": "procedure"},
        ],
        known_source_ids={"expected_source", "other_source", "third_source"},
    )

    assert result["top1_source_id"] == "other_source"
    assert result["top2_source_id"] == "expected_source"
    assert result["hit_at_1"] is False
    assert result["hit_at_3"] is True
    assert result["hit_at_5"] is True
    assert result["mrr"] == 0.5
    assert result["pass_fail"] == "PASS"
    assert result["fail_reason"] == ""


def test_low_grade_or_case_record_cannot_count_as_official_success() -> None:
    result = evaluate_workforce_retrieval.compute_case_result(
        case={
            "test_id": "T998",
            "question": "공식 절차 질문",
            "expected_source_id": "case_source",
            "expected_doc_type": "procedure_step",
            "expected_top_k": "3",
        },
        ranked_results=[
            {
                "source_id": "case_source",
                "doc_type": "case",
                "source_unit_type": "case_record",
                "evidence_grade": "D",
            }
        ],
        known_source_ids={"case_source"},
    )

    assert result["hit_at_1"] is False
    assert result["hit_at_3"] is False
    assert result["official_misuse"] is True
    assert result["pass_fail"] == "FAIL"
    assert result["fail_reason"] == "official_misuse"
