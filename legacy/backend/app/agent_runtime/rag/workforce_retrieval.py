"""Deprecated compatibility wrapper for offline workforce JSONL retrieval.

Product runtime must use app.agent_runtime.rag.workforce_runtime_retriever.
This wrapper remains only for older eval/test imports and must not be used by
agents serving requests.
"""

from .workforce_jsonl_retrieval import build_workforce_retrieval_filters, retrieve_workforce_materials

__all__ = ["build_workforce_retrieval_filters", "retrieve_workforce_materials"]
