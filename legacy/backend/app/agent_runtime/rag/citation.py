from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

try:
    from app.agent_runtime.schemas.tool import Citation
except ModuleNotFoundError:
    from backend.app.agent_runtime.schemas.tool import Citation


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


def build_citations(results: list[Document]) -> list[Citation]:
    citations = []
    seen = set()
    for doc in results:
        meta = doc.metadata or {}
        source_id = meta.get("source_id", "")
        if source_id in seen:
            continue
        seen.add(source_id)
        citations.append(
            Citation(
                source_id=source_id,
                title=meta.get("title", ""),
                evidence_grade=meta.get("evidence_grade", ""),
                publisher=meta.get("publisher"),
                url=meta.get("url"),
                excerpt=doc.page_content[:200] if doc.page_content else None,
            )
        )
    return citations
