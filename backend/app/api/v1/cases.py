"""케이스 목록/상세 조회 엔드포인트 — GET /api/v1/cases(R2.3), GET /api/v1/cases/{case_id}(R2.4).
docs/DB_SCHEMA.md §4.3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.case import Case
from app.models.membership import Membership
from app.schemas.case import CaseDetailOut, CaseOut
from app.services.cases import get_case_detail_out, list_cases_out

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
