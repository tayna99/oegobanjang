"""rag_retrieved 이벤트 계약.

AGENTS.md §9(Evidence Log) 준수: RAG 검색은 `rag_retrieved` 이벤트를 남긴다.
민감정보·질의 원문·청크 원문은 저장하지 않는다 — 질의는 sha256 해시로만,
검색 결과는 source_id·evidence_grade·건수만 기록한다.

실제 Evidence Log 백엔드는 "백엔드 접속점" 계획 범위이므로 여기서는
페이로드 계약 + 로컬 JSONL 적재까지만 담당한다.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PROCESSED_DIR

DEFAULT_EVENTS_LOG = PROCESSED_DIR / "events" / "rag_retrieved.jsonl"

# 이벤트에 절대 실리면 안 되는 키 (가드레일 테스트가 검사)
FORBIDDEN_PAYLOAD_KEYS = frozenset({"text", "excerpt", "document", "query", "user_message"})


def build_rag_retrieved_payload(
    *,
    query: str,
    buckets: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    source_ids: list[str] = []
    evidence_grades: set[str] = set()
    bucket_counts: dict[str, int] = {}
    for bucket_name, results in buckets.items():
        bucket_counts[bucket_name] = len(results)
        for result in results:
            metadata = dict(result.get("metadata") or {})
            source_id = str(metadata.get("source_id") or result.get("id") or "")
            if source_id and source_id not in source_ids:
                source_ids.append(source_id)
            grade = str(metadata.get("evidence_grade") or "")
            if grade:
                evidence_grades.add(grade)

    retrieved_count = sum(bucket_counts.values())
    payload = {
        "event_type": "rag_retrieved",
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "retrieved_count": retrieved_count,
        "bucket_counts": bucket_counts,
        "source_ids": source_ids,
        "evidence_grades": sorted(evidence_grades),
        "missing_evidence": retrieved_count == 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    assert not (set(payload) & FORBIDDEN_PAYLOAD_KEYS)
    return payload


def emit_rag_retrieved(
    *,
    query: str,
    buckets: dict[str, list[dict[str, Any]]],
    log_path: Path | None = None,
) -> dict[str, Any]:
    payload = build_rag_retrieved_payload(query=query, buckets=buckets)
    path = log_path or Path(os.getenv("RAG_EVENTS_LOG", str(DEFAULT_EVENTS_LOG)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload
