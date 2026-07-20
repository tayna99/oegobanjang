"""rag CLI — ingest / index / query / eval / chat 서브커맨드."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import pipeline
from .config import CHUNKS_DIR
from .embeddings import (
    DETERMINISTIC_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    embed_query,
    embedding_dimensions,
    resolve_embedding_provider,
)
from .store.base import VectorRecord, flatten_metadata
from .store.pgvector_store import PgVectorIndex, open_index

COLLECTION_FILES = {
    "workforce_official": "workforce_official_vector_records.jsonl",
    "workforce_templates": "workforce_templates_vector_records.jsonl",
}


def _provider_model(provider: str) -> str:
    if provider == "openai":
        return OPENAI_EMBEDDING_MODEL
    return f"deterministic-sha256-{DETERMINISTIC_DIMENSIONS}d"


def load_collection_records(chunks_dir: Path) -> dict[str, list[dict[str, Any]]]:
    collections: dict[str, list[dict[str, Any]]] = {}
    for collection_name, file_name in COLLECTION_FILES.items():
        path = chunks_dir / file_name
        records: list[dict[str, Any]] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    raw = line.strip()
                    if not raw:
                        continue
                    record = json.loads(raw)
                    _validate_record(record, path=path, line_no=line_no, collection_name=collection_name)
                    records.append(record)
        collections[collection_name] = records
    return collections


def _validate_record(record: dict[str, Any], *, path: Path, line_no: int, collection_name: str) -> None:
    missing = [field for field in ("id", "text", "embedding", "metadata") if field not in record]
    if missing:
        raise ValueError(f"{path}:{line_no} missing fields: {', '.join(missing)}")
    if record.get("metadata", {}).get("collection") != collection_name:
        raise ValueError(f"{path}:{line_no} collection mismatch")
    if not isinstance(record["embedding"], list) or not record["embedding"]:
        raise ValueError(f"{path}:{line_no} embedding must be non-empty list")


def cmd_index(args: argparse.Namespace) -> int:
    provider = resolve_embedding_provider(args.embedding_provider)
    model = _provider_model(provider)
    dimensions = embedding_dimensions(provider)
    collections = load_collection_records(args.chunks_dir)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "chunks_dir": str(args.chunks_dir),
                    "collections": {name: len(records) for name, records in collections.items()},
                    "embedding_provider": provider,
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    report: dict[str, Any] = {
        "chunks_dir": str(args.chunks_dir),
        "embedding_provider": provider,
        "embedding_model": model,
        "dimensions": dimensions,
        "reset": args.reset,
        "collections": {},
    }
    for collection_name, records in collections.items():
        index = PgVectorIndex(
            collection_name,
            provider=provider,
            model=model,
            dimensions=dimensions,
        )
        try:
            index.ensure(reset=args.reset)
            vector_records = [
                VectorRecord(
                    id=str(record["id"]),
                    text=str(record["text"]),
                    metadata=flatten_metadata(dict(record.get("metadata") or {})),
                )
                for record in records
            ]
            upserted = index.upsert(vector_records)
            report["collections"][collection_name] = {
                "input_records": len(records),
                "upserted": upserted,
                "indexed_records": index.count(),
            }
        finally:
            index.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    provider = resolve_embedding_provider(args.embedding_provider)
    index = open_index(args.collection, provider=provider)
    try:
        embedding = embed_query(args.query, provider=provider)
        hits = index.query(embedding, top_k=args.top_k)
    finally:
        index.close()
    print(
        json.dumps(
            [
                {
                    "id": hit.id,
                    "distance": hit.distance,
                    "title": hit.metadata.get("title"),
                    "source_id": hit.metadata.get("source_id"),
                    "evidence_grade": hit.metadata.get("evidence_grade"),
                    "text": hit.text[:200],
                }
                for hit in hits
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from . import evaluate_workforce
    from .retriever import close_indexes

    cases = evaluate_workforce.load_cases(args.dataset)
    try:
        results, summary = evaluate_workforce.evaluate_cases(cases, top_k=args.top_k)
    finally:
        close_indexes()
    evaluate_workforce.write_reports(
        results, summary, csv_path=args.report_csv, json_path=args.report_json
    )
    passed = evaluate_workforce.gates_passed(
        summary,
        min_hit_at_1=args.min_hit_at_1,
        min_hit_at_3=args.min_hit_at_3,
        min_hit_at_5=args.min_hit_at_5,
        min_mrr=args.min_mrr,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV report: {args.report_csv}")
    print(f"JSON report: {args.report_json}")
    print(f"GATE: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def cmd_eval_orchestration(args: argparse.Namespace) -> int:
    from . import evaluate_orchestration as eo
    from .retriever import close_indexes

    try:
        summary = eo.run_all(
            intent_router_path=args.intent_router_dataset,
            safety_guardrail_path=args.safety_guardrail_dataset,
            workflow_e2e_path=args.workflow_e2e_dataset,
            min_intent_accuracy=args.min_intent_accuracy,
        )
    finally:
        close_indexes()
    report_path = eo.write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {report_path}")
    print(f"GATE: {'PASS' if summary['gate_passed'] else 'FAIL'}")
    return 0 if summary["gate_passed"] else 1


def cmd_chat(args: argparse.Namespace) -> int:
    from .agent.factory import create_workforce_rag_agent
    from .agent.tools import retrieve_workforce_materials
    from .retriever import close_indexes

    if args.offline:
        from .agent.fake_model import OfflineEchoChatModel

        model = OfflineEchoChatModel(
            tool_args={"query": args.query, "case_type": args.case_type}
        )
    else:
        model = None  # create_workforce_rag_agent falls back to ChatOpenAI (needs OPENAI_API_KEY)

    try:
        agent = create_workforce_rag_agent(model=model, tools=[retrieve_workforce_materials])
        result = agent.invoke(
            {"messages": [{"role": "user", "content": args.query}]},
            config={"configurable": {"thread_id": "cli-chat"}},
        )
    finally:
        close_indexes()
    structured = result.get("structured_response")
    print(
        json.dumps(
            structured.model_dump() if structured is not None else None,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_index_multilingual(args: argparse.Namespace) -> int:
    from .multilingual import (
        MULTILINGUAL_COLLECTION,
        build_multilingual_vector_records,
        load_multilingual_contact_records,
    )

    provider = resolve_embedding_provider(args.embedding_provider)
    model = _provider_model(provider)
    dimensions = embedding_dimensions(provider)

    records, quarantined = load_multilingual_contact_records(args.chunks_path)
    vector_records = build_multilingual_vector_records(records)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "chunks_path": str(args.chunks_path),
                    "accepted": len(vector_records),
                    "quarantined": len(quarantined),
                    "quarantine_reasons": _count_reasons(quarantined),
                    "embedding_provider": provider,
                    "dry_run": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    index = PgVectorIndex(MULTILINGUAL_COLLECTION, provider=provider, model=model, dimensions=dimensions)
    try:
        index.ensure(reset=args.reset)
        upserted = index.upsert(
            [
                VectorRecord(id=str(r["id"]), text=str(r["text"]), metadata=flatten_metadata(dict(r["metadata"])))
                for r in vector_records
            ]
        )
        report = {
            "chunks_path": str(args.chunks_path),
            "embedding_provider": provider,
            "embedding_model": model,
            "dimensions": dimensions,
            "reset": args.reset,
            "input_records": len(records),
            "quarantined": len(quarantined),
            "quarantine_reasons": _count_reasons(quarantined),
            "upserted": upserted,
            "indexed_records": index.count(),
        }
    finally:
        index.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _count_reasons(quarantined: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in quarantined:
        reason = str(item.get("reason", "unknown"))
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def cmd_query_multilingual(args: argparse.Namespace) -> int:
    from .multilingual import search_multilingual_contact_docs

    results = search_multilingual_contact_docs(
        args.query,
        top_k=args.top_k,
        language_code=args.language_code or None,
        intent=args.intent or None,
    )
    print(
        json.dumps(
            [
                {
                    "id": r["id"],
                    "score": r["score"],
                    "matched_intent": r.get("matched_intent"),
                    "matched_language": r.get("matched_language"),
                    "title": r["metadata"].get("title"),
                    "doc_type": r["metadata"].get("doc_type"),
                    "text": r["text"][:200],
                }
                for r in results
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    return pipeline.run_ingest(
        strict=args.strict,
        dry_run=args.dry_run,
        report=args.report,
        eval_dataset=args.eval_dataset,
        min_hit_rate=args.min_hit_rate,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag", description="외고반장 RAG 파이프라인 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="수집·청킹·전처리 → processed/chunks/*.jsonl")
    p_ingest.add_argument("--strict", action="store_true")
    p_ingest.add_argument("--dry-run", action="store_true")
    p_ingest.add_argument("--report", action="store_true")
    p_ingest.add_argument("--eval-dataset", type=Path)
    p_ingest.add_argument("--min-hit-rate", type=float, default=pipeline.DEFAULT_MIN_HIT_RATE)
    p_ingest.set_defaults(func=cmd_ingest)

    p_index = sub.add_parser("index", help="워크포스 컬렉션을 pgvector에 적재 (멱등 upsert)")
    p_index.add_argument("--chunks-dir", type=Path, default=CHUNKS_DIR)
    p_index.add_argument("--reset", action="store_true", help="테이블 드롭 후 재생성 (provider 전환 시 필수)")
    p_index.add_argument("--dry-run", action="store_true")
    p_index.add_argument(
        "--embedding-provider",
        choices=["auto", "deterministic", "openai"],
        default="deterministic",
        help="deterministic은 오프라인 기본값; openai는 OPENAI_API_KEY 필요.",
    )
    p_index.set_defaults(func=cmd_index)

    p_query = sub.add_parser("query", help="단일 컬렉션 직접 질의 (디버깅용)")
    p_query.add_argument("query")
    p_query.add_argument("--collection", default="workforce_official", choices=list(COLLECTION_FILES))
    p_query.add_argument("--top-k", type=int, default=5)
    p_query.add_argument("--embedding-provider", choices=["auto", "deterministic", "openai"], default="deterministic")
    p_query.set_defaults(func=cmd_query)

    from .multilingual import DEFAULT_MULTILINGUAL_CHUNKS_PATH

    p_index_ml = sub.add_parser(
        "index-multilingual", help="다국어 컨택 청크(HTML 정제 후)를 pgvector에 적재"
    )
    p_index_ml.add_argument("--chunks-path", type=Path, default=DEFAULT_MULTILINGUAL_CHUNKS_PATH)
    p_index_ml.add_argument("--reset", action="store_true")
    p_index_ml.add_argument("--dry-run", action="store_true")
    p_index_ml.add_argument(
        "--embedding-provider", choices=["auto", "deterministic", "openai"], default="deterministic"
    )
    p_index_ml.set_defaults(func=cmd_index_multilingual)

    p_query_ml = sub.add_parser("query-multilingual", help="다국어 컨택 검색 직접 질의 (디버깅용)")
    p_query_ml.add_argument("query")
    p_query_ml.add_argument("--intent", default="", choices=["", "counseling", "safety", "life", "notice"])
    p_query_ml.add_argument("--language-code", default="", choices=["", "vi", "id"])
    p_query_ml.add_argument("--top-k", type=int, default=5)
    p_query_ml.set_defaults(func=cmd_query_multilingual)

    from . import evaluate_workforce as _ew

    p_eval = sub.add_parser("eval", help="런타임 검색 품질 평가 게이트 (hit@3 ≥ 0.80 등)")
    p_eval.add_argument("--dataset", type=Path, default=_ew.DEFAULT_DATASET_PATH)
    p_eval.add_argument("--top-k", type=int, default=5)
    p_eval.add_argument("--min-hit-at-1", type=float, default=0.60)
    p_eval.add_argument("--min-hit-at-3", type=float, default=0.80)
    p_eval.add_argument("--min-hit-at-5", type=float, default=0.90)
    p_eval.add_argument("--min-mrr", type=float, default=0.65)
    p_eval.add_argument("--report-csv", type=Path, default=_ew.DEFAULT_REPORT_CSV)
    p_eval.add_argument("--report-json", type=Path, default=_ew.DEFAULT_REPORT_JSON)
    p_eval.set_defaults(func=cmd_eval)

    from . import evaluate_orchestration as _eo

    p_eval_orch = sub.add_parser(
        "eval-orchestration",
        help="오케스트레이션 안전성·의도분류 평가 (R4.6 — safety violation=0 게이트, intent 정확도 리포트)",
    )
    p_eval_orch.add_argument(
        "--intent-router-dataset", type=Path, default=_eo.INTENT_ROUTER_DATASET
    )
    p_eval_orch.add_argument(
        "--safety-guardrail-dataset", type=Path, default=_eo.SAFETY_GUARDRAIL_DATASET
    )
    p_eval_orch.add_argument(
        "--workflow-e2e-dataset", type=Path, default=_eo.WORKFLOW_E2E_DATASET
    )
    p_eval_orch.add_argument(
        "--min-intent-accuracy",
        type=float,
        default=0.50,
        help="intent_router_cases 정확도 회귀 방지 하한(정보성 — 현재 결정론 키워드 라우터 측정치 0.50)",
    )
    p_eval_orch.set_defaults(func=cmd_eval_orchestration)

    p_chat = sub.add_parser(
        "chat", help="워크포스 RAG 에이전트 대화 (--offline: OPENAI_API_KEY 불필요 스모크)"
    )
    p_chat.add_argument("query")
    p_chat.add_argument("--offline", action="store_true")
    p_chat.add_argument("--case-type", default="new_hiring")
    p_chat.set_defaults(func=cmd_chat)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔(cp949)에서 한글·특수문자 JSON 출력이 깨지지 않도록 UTF-8 강제
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
