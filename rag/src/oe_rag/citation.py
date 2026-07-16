from __future__ import annotations

from typing import Any

ANSWER_EVIDENCE_GRADES = frozenset({"A", "B", "E"})


def can_use_as_answer_evidence(metadata: dict[str, Any]) -> bool:
    return str(metadata.get("evidence_grade", "")).upper() in ANSWER_EVIDENCE_GRADES


def format_citation(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata", {})
    return {
        "source_id": result.get("source_id"),
        "chunk_id": result.get("chunk_id"),
        "title": result.get("title") or metadata.get("title"),
        "publisher": metadata.get("publisher"),
        "url": metadata.get("url", ""),
        "evidence_grade": metadata.get("evidence_grade"),
    }
