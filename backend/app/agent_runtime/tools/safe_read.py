from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.rag_tayna.retriever import RAGRetriever
from app.agent_runtime.schemas.tool import (
    Citation,
    ToolContractLevel,
    ToolResult,
    ToolStatus,
)
from app.services.context_data_service import (
    calculate_candidate_readiness,
    get_candidate_profile_data,
    get_company_data,
    get_document_requirements_data,
    get_visa_status_data,
    get_worker_documents_data,
    get_worker_profile_data,
)


_rag_retriever: RAGRetriever | None = None


def _get_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever


@tool
def get_worker_profile(worker_id: str) -> dict[str, Any]:
    """Read a worker profile from the DB-backed context repository."""

    worker = get_worker_profile_data(worker_id)
    if worker is None:
        return ToolResult(
            tool_name="get_worker_profile",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="근로자 정보를 찾을 수 없습니다.",
        ).model_dump()
    return ToolResult(
        tool_name="get_worker_profile",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={
            "id": worker.get("id"),
            "name": worker.get("name"),
            "nationality": worker.get("nationality"),
            "preferred_language": worker.get("preferred_language"),
            "visa_type": worker.get("visa_type"),
            "visa_expires_at": worker.get("visa_expires_at"),
            "contract_starts_at": worker.get("contract_starts_at"),
            "contract_ends_at": worker.get("contract_ends_at"),
            "status": worker.get("status"),
        },
    ).model_dump()


@tool
def get_company_profile(company_id: str) -> dict[str, Any]:
    """Read a company profile from the DB-backed context repository."""

    company = get_company_data(company_id)
    if company is None:
        return ToolResult(
            tool_name="get_company_profile",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.FAILED,
            input_snapshot={"company_id": company_id},
            error="사업장 정보를 찾을 수 없습니다.",
        ).model_dump()
    return ToolResult(
        tool_name="get_company_profile",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"company_id": company_id},
        output={
            "id": company.get("id"),
            "name": company.get("name"),
            "industry": company.get("industry"),
            "region": company.get("region"),
            "current_foreign_workers": company.get("current_foreign_workers"),
            "housing_available": company.get("housing_available"),
            "shift_type": company.get("shift_type"),
            "requested_role": company.get("requested_role"),
            "preferred_start_date": company.get("preferred_start_date"),
        },
    ).model_dump()


@tool
def get_candidate_profile(candidate_id: str) -> dict[str, Any]:
    """Read a candidate profile without scoring, ranking, or preference judgment."""

    candidate = get_candidate_profile_data(candidate_id)
    if candidate is None:
        return ToolResult(
            tool_name="get_candidate_profile",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.FAILED,
            input_snapshot={"candidate_id": candidate_id},
            error="후보자 정보를 찾을 수 없습니다.",
        ).model_dump()
    return ToolResult(
        tool_name="get_candidate_profile",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"candidate_id": candidate_id},
        output={
            "id": candidate.get("id"),
            "company_id": candidate.get("company_id"),
            "nationality": candidate.get("nationality"),
            "desired_role": candidate.get("desired_role"),
            "available_from": candidate.get("available_from"),
            "language": candidate.get("language"),
            "passport": candidate.get("passport"),
            "photo": candidate.get("photo"),
            "health_check": candidate.get("health_check"),
            "understood_housing": candidate.get("understood_housing"),
            "understood_shift": candidate.get("understood_shift"),
            "status": candidate.get("status"),
            "policy": "후보자 정보는 제출 준비도와 추가 확인 항목에만 사용합니다.",
        },
    ).model_dump()


@tool
def get_visa_status(worker_id: str) -> dict[str, Any]:
    """Read visa status from context DB first, then demo fixture service fallback."""

    visa = get_visa_status_data(worker_id)
    if visa is None:
        return ToolResult(
            tool_name="get_visa_status",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.FAILED,
            input_snapshot={"worker_id": worker_id},
            error="비자 정보를 찾을 수 없습니다.",
        ).model_dump()
    return ToolResult(
        tool_name="get_visa_status",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output=dict(visa),
    ).model_dump()


@tool
def get_document_status(worker_id: str) -> dict[str, Any]:
    """Read submitted document status from context DB first."""

    docs = get_worker_documents_data(worker_id)
    return ToolResult(
        tool_name="get_document_status",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={"documents": docs, "total": len(docs)},
    ).model_dump()


@tool
def get_candidate_readiness(
    candidate_id: str | None = None,
    company_id: str | None = None,
    requested_role: str | None = None,
) -> dict[str, Any]:
    """Read candidate submission readiness without scoring or recommending people."""

    rows = calculate_candidate_readiness(
        candidate_id=candidate_id,
        company_id=company_id,
        requested_role=requested_role,
    )
    return ToolResult(
        tool_name="get_candidate_readiness",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={
            "candidate_id": candidate_id,
            "company_id": company_id,
            "requested_role": requested_role,
        },
        output={
            "readiness": rows,
            "total": len(rows),
            "policy": "준비도는 제출/확인 항목만 보며 점수, 추천, 성실도 판단을 하지 않습니다.",
        },
    ).model_dump()


@tool
def search_policy_documents(
    query: str,
    visa_type: str | None = None,
    evidence_grade: str | None = None,
) -> dict[str, Any]:
    """Search official policy documents in the legacy RAG reader path."""

    retriever = _get_retriever()
    result = retriever.search(query=query, visa_type=visa_type, evidence_grade=evidence_grade)

    if not result.found:
        return ToolResult(
            tool_name="search_policy_documents",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.SUCCESS,
            input_snapshot={
                "query": query,
                "visa_type": visa_type,
                "evidence_grade": evidence_grade,
            },
            output={
                "found": False,
                "reason": result.reason,
                "message": "공식 근거를 찾지 못했습니다. 행정사 또는 노무사 검토가 필요합니다.",
            },
        ).model_dump()

    citations = [
        Citation(
            source_id=c.source_id,
            title=c.title,
            evidence_grade=c.evidence_grade,
            url=c.url,
        )
        for c in result.citations
    ]
    return ToolResult(
        tool_name="search_policy_documents",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={
            "query": query,
            "visa_type": visa_type,
            "evidence_grade": evidence_grade,
        },
        output={
            "found": True,
            "count": len(result.documents),
            "excerpts": [
                {
                    "source_id": doc.metadata.get("source_id", ""),
                    "title": doc.metadata.get("title", ""),
                    "evidence_grade": doc.metadata.get("evidence_grade", ""),
                    "content": doc.page_content,
                }
                for doc in result.documents
            ],
        },
        citations=citations,
    ).model_dump()


@tool
def get_document_requirements(case_type: str, visa_type: str) -> dict[str, Any]:
    """Read required document rules by case type and visa type."""

    requirements = get_document_requirements_data(case_type, visa_type)
    return ToolResult(
        tool_name="get_document_requirements",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"case_type": case_type, "visa_type": visa_type},
        output={"requirements": requirements, "total": len(requirements)},
    ).model_dump()
