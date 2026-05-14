from dataclasses import dataclass, field
from langchain_core.documents import Document

try:
    from app.agent_runtime.rag.vector_store import get_chroma_store
    from app.agent_runtime.rag.citation import build_citations
    from app.agent_runtime.schemas.tool import Citation
except ModuleNotFoundError:
    from backend.app.agent_runtime.rag.vector_store import get_chroma_store
    from backend.app.agent_runtime.rag.citation import build_citations
    from backend.app.agent_runtime.schemas.tool import Citation

CONFIDENCE_THRESHOLD = 0.5


@dataclass
class RetrievalResult:
    documents: list[Document] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    found: bool = True
    reason: str = ""


class RAGRetriever:
    def __init__(self):
        self._store = None

    @property
    def store(self):
        if self._store is None:
            self._store = get_chroma_store()
        return self._store

    def search(
        self,
        query: str,
        visa_type: str | None = None,
        evidence_grade: str | None = None,
        k: int = 5,
    ) -> RetrievalResult:
        where_filter: dict = {}
        if visa_type:
            where_filter["visa_type"] = visa_type
        if evidence_grade:
            where_filter["evidence_grade"] = evidence_grade

        try:
            if where_filter:
                results_with_scores = self.store.similarity_search_with_relevance_scores(
                    query, k=k, filter=where_filter
                )
            else:
                results_with_scores = self.store.similarity_search_with_relevance_scores(
                    query, k=k
                )
        except Exception:
            return RetrievalResult(found=False, reason="vector_store_error")

        if not results_with_scores:
            return RetrievalResult(found=False, reason="no_results")

        docs = [doc for doc, score in results_with_scores if score >= CONFIDENCE_THRESHOLD]
        if not docs:
            return RetrievalResult(found=False, reason="low_confidence")

        return RetrievalResult(
            documents=docs,
            citations=build_citations(docs),
            found=True,
        )


def retrieve_policy_documents(
    query: str,
    *,
    visa_type: str | None = None,
    evidence_grade: str | None = None,
    k: int = 5,
) -> RetrievalResult:
    return RAGRetriever().search(
        query=query,
        visa_type=visa_type,
        evidence_grade=evidence_grade,
        k=k,
    )
