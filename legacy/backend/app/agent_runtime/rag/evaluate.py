from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .retriever import retrieve_policy_documents


ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_DATASET_PATH = ROOT_DIR / "evals" / "datasets" / "rag_retrieval_cases.jsonl"
DEFAULT_CHUNK_PATH = ROOT_DIR / "data-pipeline" / "processed" / "chunks" / "all_chunks.jsonl"
REPORTS_DIR = ROOT_DIR / "evals" / "reports"


@dataclass
class RetrievalEvalCaseResult:
    case_id: str
    expected_source_ids: list[str]
    retrieved_source_ids: list[str]
    hit: bool


@dataclass
class RetrievalEvalReport:
    started_at: str
    dataset_path: str
    chunk_path: str
    top_k: int
    total_cases: int
    hits: int
    hit_rate: float
    case_results: list[dict[str, Any]]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: row must be an object")
            records.append(record)
    return records


def evaluate_retrieval(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    chunk_path: Path = DEFAULT_CHUNK_PATH,
    top_k: int = 3,
) -> RetrievalEvalReport:
    if not chunk_path.exists():
        raise FileNotFoundError(
            f"Chunk file not found: {chunk_path}. Run `uv run python scripts/ingest_rag_docs.py` first."
        )

    cases = _load_jsonl(dataset_path)
    case_results: list[RetrievalEvalCaseResult] = []

    for case in cases:
        expected_source_ids = case.get("expected_source_ids")
        if not isinstance(expected_source_ids, list) or not expected_source_ids:
            raise ValueError(f"Missing expected_source_ids for case {case.get('id', '<unknown>')}")

        results = retrieve_policy_documents(
            str(case["input"]),
            chunk_path,
            top_k=top_k,
            answer_evidence_only=bool(case.get("answer_evidence_only", True)),
        )
        retrieved_source_ids = [str(result["source_id"]) for result in results]
        hit = any(source_id in retrieved_source_ids for source_id in expected_source_ids)
        case_results.append(
            RetrievalEvalCaseResult(
                case_id=str(case["id"]),
                expected_source_ids=[str(source_id) for source_id in expected_source_ids],
                retrieved_source_ids=retrieved_source_ids,
                hit=hit,
            )
        )

    hits = sum(1 for result in case_results if result.hit)
    total_cases = len(case_results)
    hit_rate = hits / total_cases if total_cases else 0.0

    return RetrievalEvalReport(
        started_at=datetime.now(timezone.utc).isoformat(),
        dataset_path=str(dataset_path),
        chunk_path=str(chunk_path),
        top_k=top_k,
        total_cases=total_cases,
        hits=hits,
        hit_rate=hit_rate,
        case_results=[asdict(result) for result in case_results],
    )


def write_report(report: RetrievalEvalReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"rag_retrieval_report_{timestamp}.json"
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path


def main() -> int:
    report = evaluate_retrieval()
    report_path = write_report(report)
    print(f"Hit@{report.top_k}: {report.hits}/{report.total_cases} = {report.hit_rate:.0%}")
    print(f"Report: {report_path}")
    return 0 if report.hit_rate >= 0.90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
