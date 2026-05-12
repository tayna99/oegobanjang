from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.tools import BaseTool, tool

from app.agent_runtime.rag.embeddings import deterministic_embedding
from app.agent_runtime.langchain_v1.contact_subagents import (
    run_contact_onboarding,
    run_worker_reply_interpreter,
)
from app.agent_runtime.tools.registry import (
    APPROVAL_REQUIRED_TOOLS,
    SAFE_DRAFT_TOOLS,
)
from app.agent_runtime.tools.safe_read import (
    get_company_profile,
    get_candidate_profile,
    get_candidate_readiness,
    search_policy_documents,
    get_document_requirements,
)
from app.agent_runtime.tools.safe_calculate import (
    calculate_contract_gap,
    calculate_candidate_readiness,
)
from app.config import get_settings


class RuntimePreflightError(RuntimeError):
    pass


def _collection_names() -> tuple[str, str]:
    settings = get_settings()
    return (
        settings.chroma_workforce_official_collection,
        settings.chroma_workforce_templates_collection,
    )


def _persistent_client() -> chromadb.PersistentClient:
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.normalized_chroma_persist_directory)


def preflight_chroma() -> None:
    client = _persistent_client()
    existing = {collection.name: collection for collection in client.list_collections()}
    for collection_name in _collection_names():
        collection = existing.get(collection_name)
        if collection is None:
            raise RuntimePreflightError(f"missing Chroma collection: {collection_name}")
        if collection.count() <= 0:
            raise RuntimePreflightError(f"empty Chroma collection: {collection_name}")


@tool
def retrieve_workforce_materials(
    query: str,
    case_type: str = "new_hiring",
    visa_type: str = "E-9",
    top_k: int = 5,
) -> dict[str, Any]:
    """Search workforce official/template Chroma collections for grounding material."""

    client = _persistent_client()
    query_embedding = deterministic_embedding(query)
    records: list[dict[str, Any]] = []

    for collection_name in _collection_names():
        collection = client.get_collection(collection_name)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, min(top_k, 10)),
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for idx, chunk_id in enumerate(ids):
            metadata = dict(metadatas[idx] or {})
            evidence_grade = str(metadata.get("evidence_grade", ""))
            doc_type = str(metadata.get("doc_type", ""))
            if evidence_grade in {"D", "F"} or doc_type in {"case", "case_record"}:
                continue
            if case_type and str(metadata.get("case_type", "")) not in {case_type, "ALL", ""}:
                continue
            if visa_type and str(metadata.get("visa_type", "")) not in {visa_type, "ALL", ""}:
                continue

            records.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": metadata.get("source_id", chunk_id),
                    "title": metadata.get("title", ""),
                    "doc_type": doc_type,
                    "evidence_grade": evidence_grade,
                    "collection": collection_name,
                    "distance": distances[idx] if idx < len(distances) else None,
                    "content": documents[idx] if idx < len(documents) else "",
                    "metadata": metadata,
                }
            )

    records.sort(key=lambda row: (row.get("distance") is None, row.get("distance") or 0.0))
    return {
        "query": query,
        "records": records[:top_k],
        "approval_required": False,
    }


@tool
def run_visa_sub_agents(
    worker_id: str,
    user_message: str,
    company_id: str = "",
) -> dict[str, Any]:
    """비자 위험도(visa_risk_sub_agent) + 서류 우선순위(document_priority_sub_agent) 서브에이전트를 순차 실행해 종합 결과를 반환합니다.
    비자 상태 확인, 서류 누락 분석, handoff 초안이 모두 필요한 경우 이 툴을 사용합니다."""
    from app.agent_runtime.agents.visa_agent import run_visa_agent
    from app.agent_runtime.schemas import ForeignHiringState, Intent

    state = ForeignHiringState(
        request_id=str(uuid.uuid4()),
        worker_id=worker_id,
        company_id=company_id,
        user_message=user_message,
        detected_intents=[Intent.VISA_CHECK, Intent.DOCUMENT_CHECK],
    )
    result = run_visa_agent(state, worker_id=worker_id)
    return result


def get_langchain_v1_tools() -> list[BaseTool]:
    # get_worker_profile, get_visa_status, get_document_status,
    # assess_visa_risk, assess_document_priority 는 run_visa_sub_agents 내부에서만 사용
    tools = [
        get_company_profile,
        get_candidate_profile,
        get_candidate_readiness,
        search_policy_documents,
        get_document_requirements,
        calculate_contract_gap,
        calculate_candidate_readiness,
        *SAFE_DRAFT_TOOLS,
        run_visa_sub_agents,
        run_contact_onboarding,
        run_worker_reply_interpreter,
        *APPROVAL_REQUIRED_TOOLS,
        retrieve_workforce_materials,
    ]
    if not tools:
        raise RuntimePreflightError("missing LangChain tool registry")
    return tools


def chroma_persist_path() -> Path:
    return Path(get_settings().normalized_chroma_persist_directory)
