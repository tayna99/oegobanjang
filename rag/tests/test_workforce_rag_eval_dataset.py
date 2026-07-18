import json

from oe_rag import pipeline
from oe_rag.config import DATASETS_DIR


def test_workforce_rag_eval_dataset_has_20_raw_based_cases() -> None:
    dataset_path = DATASETS_DIR / "workforce_rag_retrieval_cases.jsonl"
    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) >= 20
    assert {
        "new_hiring_preparation",
        "allowed_industry_employer_requirement",
        "candidate_readiness",
        "handoff_questions_template",
    }.issubset({str(row.get("case_group")) for row in rows})

    inventory = pipeline.load_raw_source_inventory()

    for row in rows:
        assert row["id"].startswith("workforce-rag-")
        assert row["expected_source_ids"]
        assert row.get("agent") == "workforce_agent"
        assert row.get("case_group")
        assert row.get("answer_evidence_only") is True
        for source_id in row["expected_source_ids"]:
            assert not str(source_id).startswith("seed_")
            assert not str(source_id).startswith("document_requirement_")
            assert source_id in inventory
