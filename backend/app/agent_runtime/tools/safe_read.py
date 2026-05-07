import csv
import os
from typing import Any
from langchain_core.tools import tool

from app.agent_runtime.schemas.tool import ToolResult, ToolContractLevel, ToolStatus, Citation
from app.agent_runtime.rag_tayna.retriever import RAGRetriever

_SEED_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data-pipeline", "seed")
)

_rag_retriever = None


def _get_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = os.path.join(_SEED_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@tool
def get_worker_profile(worker_id: str) -> dict[str, Any]:
    """근로자 기본 정보를 조회합니다. (비자 유형, 체류 만료일, 국적, 상태)"""
    rows = _read_csv("workers.csv")
    for row in rows:
        if row.get("id") == worker_id:
            return ToolResult(
                tool_name="get_worker_profile",
                tool_grade=ToolContractLevel.SAFE_READ,
                status=ToolStatus.SUCCESS,
                input_snapshot={"worker_id": worker_id},
                output={
                    "id": row["id"],
                    "name": row["name"],
                    "nationality": row["nationality"],
                    "preferred_language": row["preferred_language"],
                    "visa_type": row["visa_type"],
                    "visa_expires_at": row["visa_expires_at"],
                    "contract_starts_at": row["contract_starts_at"],
                    "contract_ends_at": row["contract_ends_at"],
                    "status": row["status"],
                },
            ).model_dump()
    return ToolResult(
        tool_name="get_worker_profile",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.FAILED,
        input_snapshot={"worker_id": worker_id},
        error="근로자를 찾을 수 없습니다.",
    ).model_dump()


@tool
def get_visa_status(worker_id: str) -> dict[str, Any]:
    """근로자의 비자 상태와 체류 만료일을 조회합니다."""
    rows = _read_csv("visas.csv")
    for row in rows:
        if row.get("worker_id") == worker_id:
            return ToolResult(
                tool_name="get_visa_status",
                tool_grade=ToolContractLevel.SAFE_READ,
                status=ToolStatus.SUCCESS,
                input_snapshot={"worker_id": worker_id},
                output=dict(row),
            ).model_dump()

    workers = _read_csv("workers.csv")
    for row in workers:
        if row.get("id") == worker_id:
            return ToolResult(
                tool_name="get_visa_status",
                tool_grade=ToolContractLevel.SAFE_READ,
                status=ToolStatus.SUCCESS,
                input_snapshot={"worker_id": worker_id},
                output={
                    "worker_id": worker_id,
                    "visa_type": row["visa_type"],
                    "visa_expires_at": row["visa_expires_at"],
                    "status": row["status"],
                },
            ).model_dump()

    return ToolResult(
        tool_name="get_visa_status",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.FAILED,
        input_snapshot={"worker_id": worker_id},
        error="비자 정보를 찾을 수 없습니다.",
    ).model_dump()


@tool
def get_document_status(worker_id: str) -> dict[str, Any]:
    """근로자의 서류 제출 현황을 조회합니다."""
    rows = _read_csv("worker_documents.csv")
    docs = [row for row in rows if row.get("worker_id") == worker_id]
    return ToolResult(
        tool_name="get_document_status",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"worker_id": worker_id},
        output={"documents": docs, "total": len(docs)},
    ).model_dump()


@tool
def search_policy_documents(
    query: str,
    visa_type: str | None = None,
    evidence_grade: str | None = None,
) -> dict[str, Any]:
    """정책 문서(법령·절차·서식·안전자료)를 RAG 검색합니다.

    Args:
        query: 검색할 자연어 질의
        visa_type: 비자 유형 필터 (E-9, H-2, E-7 등)
        evidence_grade: 증거 등급 필터 (A, B, C, D)
    """
    retriever = _get_retriever()
    result = retriever.search(query=query, visa_type=visa_type, evidence_grade=evidence_grade)

    if not result.found:
        return ToolResult(
            tool_name="search_policy_documents",
            tool_grade=ToolContractLevel.SAFE_READ,
            status=ToolStatus.SUCCESS,
            input_snapshot={"query": query, "visa_type": visa_type, "evidence_grade": evidence_grade},
            output={"found": False, "reason": result.reason, "message": "공식 근거를 찾지 못했습니다. 행정사 또는 노무사 검토가 필요합니다."},
        ).model_dump()

    return ToolResult(
        tool_name="search_policy_documents",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"query": query, "visa_type": visa_type, "evidence_grade": evidence_grade},
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
        citations=result.citations,
    ).model_dump()


@tool
def get_document_requirements(case_type: str, visa_type: str) -> dict[str, Any]:
    """비자 유형과 케이스 유형에 따른 필요 서류 목록을 조회합니다.

    Args:
        case_type: 케이스 유형 (stay_extension, workplace_change, renewal 등)
        visa_type: 비자 유형 (E-9, H-2, E-7 등)
    """
    rows = _read_csv("document_requirements.csv")
    matched = [
        row for row in rows
        if row.get("visa_type", "").upper() == visa_type.upper()
        and row.get("case_type", "").lower() == case_type.lower()
    ]
    return ToolResult(
        tool_name="get_document_requirements",
        tool_grade=ToolContractLevel.SAFE_READ,
        status=ToolStatus.SUCCESS,
        input_snapshot={"case_type": case_type, "visa_type": visa_type},
        output={"requirements": matched, "total": len(matched)},
    ).model_dump()
