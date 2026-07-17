"""근거 라이브러리 조회 — plans/BACKEND_CONNECT.md B2.

전역 공식 근거(company_id IS NULL, evidence_ingest.upsert_citations가 A/B등급으로 적재)
+ 요청한 회사의 내부 템플릿(E등급)을 함께 반환한다. F등급은 애초에 저장되지 않는다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.citation import Citation
from app.models.membership import Membership
from app.schemas.citation import CitationOut

router = APIRouter(prefix="/api/v1/citations", tags=["citations"])


@router.get("", response_model=list[CitationOut])
def list_citations(
    company_id: str = Query(..., min_length=1),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Citation]:
    membership = db.execute(
        select(Membership).where(
            Membership.company_id == company_id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "해당 사업장 접근 권한이 없습니다")

    rows = (
        db.execute(
            select(Citation)
            .where(
                (Citation.company_id.is_(None)) | (Citation.company_id == company_id),
                Citation.grade != "F",
            )
            .order_by(Citation.grade, Citation.title)
        )
        .scalars()
        .all()
    )
    return list(rows)
