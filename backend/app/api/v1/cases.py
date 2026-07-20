"""케이스 목록/상세 조회 엔드포인트 — GET /api/v1/cases(R2.3), GET /api/v1/cases/{case_id}(R2.4),
GET /api/v1/cases/{case_id}/draft(SD-5). docs/DB_SCHEMA.md §4.3·§4.7.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.case import Case
from app.models.membership import Membership
from app.schemas.case import CaseDetailOut, CaseOut
from app.schemas.draft import DraftOut
from app.services.cases import get_case_detail_out, list_cases_out
from app.services.drafts import get_draft_out

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[CaseOut]:
    return list_cases_out(db, membership.company_id)


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(
    case_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = db.get(Case, case_id)
    # 타사 케이스는 존재 비노출 — 404(7단계 §1 원칙과 동일).
    if case is None or case.company_id != membership.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "케이스를 찾을 수 없습니다")
    return get_case_detail_out(db, membership.company_id, case)


@router.get("/{case_id}/draft", response_model=DraftOut)
def get_case_draft(
    case_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DraftOut:
    case = db.get(Case, case_id)
    # 케이스 자체가 타사 소속이면 존재 비노출(위 get_case와 동일 원칙) — 404.
    if case is None or case.company_id != membership.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "케이스를 찾을 수 없습니다")
    draft = get_draft_out(db, membership.company_id, case_id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "초안을 찾을 수 없습니다")
    return draft
