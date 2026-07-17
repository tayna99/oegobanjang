"""POST /api/v1/briefings/generate — 데일리 브리핑 수동 트리거 (G6, rule-only·LLM 0회).

스케줄러 연동은 후속 작업(plans/ROADMAP.md) — 지금은 인증된 사업장 멤버가 수동으로
생성을 요청한다(citations·runs API와 동일한 테넌트 인가 패턴).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.briefing import BriefingItem
from app.models.case import Case
from app.models.membership import Membership
from app.schemas.briefing import BriefingGenerateRequest, BriefingItemOut, BriefingOut
from app.services.briefing_service import generate_daily_briefing

router = APIRouter(prefix="/api/v1/briefings", tags=["briefings"])


@router.post("/generate", response_model=BriefingOut)
def create_briefing(
    request: BriefingGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BriefingOut:
    membership = db.execute(
        select(Membership).where(
            Membership.company_id == request.company_id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "해당 사업장 접근 권한이 없습니다")

    briefing = generate_daily_briefing(
        db, company_id=request.company_id, reference_date=request.reference_date
    )

    rows = db.execute(
        select(BriefingItem, Case)
        .join(Case, Case.id == BriefingItem.case_id)
        .where(
            BriefingItem.company_id == request.company_id,
            BriefingItem.briefing_id == briefing.id,
        )
        .order_by(BriefingItem.rank)
    ).all()

    return BriefingOut(
        id=briefing.id,
        company_id=briefing.company_id,
        briefing_date=briefing.briefing_date,
        generated_at=briefing.generated_at,
        rerun_count=briefing.rerun_count,
        items=[
            BriefingItemOut(
                case_id=case.id,
                case_code=case.case_code,
                rank=item.rank,
                risk_type=case.case_type,
                severity=case.severity,
                title=case.title,
            )
            for item, case in rows
        ],
    )
