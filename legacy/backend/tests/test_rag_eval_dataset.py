from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_rag_retrieval_cases_have_expected_source_ids() -> None:
    dataset_path = ROOT_DIR / "evals" / "datasets" / "rag_retrieval_cases.jsonl"
    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) >= 5

    for row in rows:
        assert isinstance(row["id"], str)
        assert isinstance(row["input"], str)
        assert isinstance(row["expected_source_ids"], list)
        assert row["expected_source_ids"]
        assert "answer_evidence_only" in row
