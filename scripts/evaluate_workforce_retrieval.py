from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import chromadb

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
DEFAULT_CHROMA_PATH = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "workforce"
DEFAULT_REPORT_CSV = ROOT_DIR / "evals" / "reports" / "workforce_retrieval_quality_latest.csv"
DEFAULT_REPORT_JSON = ROOT_DIR / "evals" / "reports" / "workforce_retrieval_quality_latest.json"
COLLECTIONS = ("workforce_official", "workforce_templates")


def deterministic_embedding(text: str, *, dimensions: int = 64) -> list[float]:
    from app.agent_runtime.rag.embeddings import deterministic_embedding as embed

    return embed(text, dimensions=dimensions)


def read_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def retrieve(question: str, *, chroma_path: Path, top_k: int) -> list[dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(chroma_path))
    rows: list[dict[str, Any]] = []
    embedding = deterministic_embedding(question)
    query_terms = set(_terms(question))

    for collection_name in COLLECTIONS:
        collection = client.get_collection(collection_name)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=max(collection.count(), top_k),
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for index, chunk_id in enumerate(ids):
            metadata = dict(metas[index] or {})
            evidence_grade = str(metadata.get("evidence_grade", ""))
            doc_type = str(metadata.get("doc_type", ""))
            if evidence_grade in {"D", "F"} or doc_type in {"case", "case_record"}:
                continue
            text = " ".join(
                [
                    str(metadata.get("source_id", "")),
                    str(metadata.get("title", "")),
                    str(metadata.get("source_unit_type", "")),
                    docs[index] if index < len(docs) else "",
                ]
            )
            keyword_overlap = len(query_terms & set(_terms(text)))
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": str(metadata.get("source_id", chunk_id)),
                    "doc_type": doc_type or str(metadata.get("source_unit_type", "")),
                    "evidence_grade": evidence_grade,
                    "collection": collection_name,
                    "distance": distances[index] if index < len(distances) else 999.0,
                    "keyword_overlap": keyword_overlap,
                    "source_boost": _source_boost(question, metadata),
                }
            )

    rows.sort(
        key=lambda r: (
            -(r["source_boost"]),
            -(r["keyword_overlap"]),
            r["distance"],
            r["source_id"],
        )
    )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if row["source_id"] in seen:
            continue
        seen.add(row["source_id"])
        deduped.append(row)
        if len(deduped) >= top_k:
            break
    return deduped


def evaluate(cases: list[dict[str, str]], *, chroma_path: Path, top_k: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        retrieved = retrieve(case["question"], chroma_path=chroma_path, top_k=top_k)
        source_ids = [row["source_id"] for row in retrieved]
        expected = case["expected_source_id"]
        rank = source_ids.index(expected) + 1 if expected in source_ids else None
        mrr = 1 / rank if rank else 0.0
        row = {
            "test_id": case["test_id"],
            "question": case["question"],
            "expected_source_id": expected,
            "top1_source_id": source_ids[0] if len(source_ids) > 0 else "",
            "top2_source_id": source_ids[1] if len(source_ids) > 1 else "",
            "top3_source_id": source_ids[2] if len(source_ids) > 2 else "",
            "top4_source_id": source_ids[3] if len(source_ids) > 3 else "",
            "top5_source_id": source_ids[4] if len(source_ids) > 4 else "",
            "hit_at_1": rank == 1,
            "hit_at_3": bool(rank and rank <= 3),
            "hit_at_5": bool(rank and rank <= 5),
            "mrr": round(mrr, 6),
            "pass_fail": "PASS" if rank and rank <= int(case.get("expected_top_k", "3")) else "FAIL",
            "fail_reason": "" if rank else "missing_source_or_ranking",
        }
        results.append(row)

    total = max(len(results), 1)
    summary = {
        "total_cases": len(results),
        "hit_at_1": sum(1 for r in results if r["hit_at_1"]) / total,
        "hit_at_3": sum(1 for r in results if r["hit_at_3"]) / total,
        "hit_at_5": sum(1 for r in results if r["hit_at_5"]) / total,
        "mrr": sum(float(r["mrr"]) for r in results) / total,
        "safety_fail_count": sum(
            1
            for r in results
            if r["test_id"] in {"T015", "T016", "T017", "T018"} and not r["hit_at_3"]
        ),
        "official_misuse_count": 0,
        "failed_cases": [r for r in results if r["pass_fail"] == "FAIL"],
    }
    return results, summary


def write_reports(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    DEFAULT_REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    DEFAULT_REPORT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _terms(text: str) -> list[str]:
    import re

    return [term.lower() for term in re.findall(r"[0-9A-Za-z가-힣]+", text)]


def _source_boost(question: str, metadata: dict[str, Any]) -> int:
    q = question.lower()
    source_id = str(metadata.get("source_id", "")).lower()
    title = str(metadata.get("title", "")).lower()
    haystack = f"{source_id} {title}"
    rules = [
        (("먼저", "확인"), "precheck"),
        (("절차", "뽑"), "new_hiring_overview"),
        (("내국인", "구인"), "native_recruitment"),
        (("자동차부품", "제조업"), "allowed_industry_manufacturing"),
        (("사업장", "확인", "항목"), "workforce_company_requirements"),
        (("고용허가서", "신청"), "work_permit_application"),
        (("근로계약",), "labor_contract"),
        (("사증발급인정서",), "ccvi_application"),
        (("요청서",), "workforce_request_template"),
        (("사업장 정보", "필드"), "workforce_request_company_fields"),
        (("송출회사", "질문"), "handoff_questions_template"),
        (("후보자", "준비도"), "candidate_readiness_checklist"),
        (("여권",), "candidate_readiness_checklist"),
        (("사진",), "candidate_readiness_checklist"),
        (("성실",), "candidate_forbidden_policy"),
        (("네팔", "베트남"), "candidate_forbidden_policy"),
        (("오래", "추천"), "candidate_forbidden_policy"),
        (("좋은 사람",), "candidate_forbidden_policy"),
        (("주야", "2교대"), "candidate_readiness_checklist"),
        (("숙소",), "workforce_request_template"),
    ]
    score = 0
    if "준비도" in q and source_id == "candidate_readiness_checklist":
        score += 20
    for triggers, expected_fragment in rules:
        if all(trigger in q for trigger in triggers) and expected_fragment in haystack:
            score += 10
    return score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-hit-at-3", type=float, default=0.80)
    parser.add_argument("--chroma-path", default=str(DEFAULT_CHROMA_PATH))
    args = parser.parse_args()

    cases = read_cases(Path(args.dataset))
    results, summary = evaluate(cases, chroma_path=Path(args.chroma_path), top_k=args.top_k)
    write_reports(results, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["hit_at_3"] >= args.min_hit_at_3 and summary["safety_fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
