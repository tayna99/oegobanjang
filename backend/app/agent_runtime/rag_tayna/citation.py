from langchain_core.documents import Document
from app.agent_runtime.schemas.tool import Citation


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
