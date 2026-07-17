"""briefings 도메인 읽기 서비스 — GET /api/v1/briefings/latest(R2.3). docs/DB_SCHEMA.md §4.9.

케이스 조립은 app.services.cases.get_case_out을 그대로 재사용한다 — 다시 만들지 않는다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.briefing import Briefing, BriefingItem
from app.models.case import Case
from app.schemas.briefing import BriefingOut
from app.services.cases import get_case_out


def get_latest_briefing_out(db: Session, company_id: str) -> BriefingOut | None:
    """company_id로 스코프된 최신 브리핑(briefing_date desc, generated_at desc) 1건을
    briefing_items(rank asc) 순서 그대로 케이스와 조립해 반환한다. 브리핑이 없으면 None."""
    briefing = db.execute(
        select(Briefing)
        .where(Briefing.company_id == company_id)
        .order_by(Briefing.briefing_date.desc(), Briefing.generated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if briefing is None:
        return None

    items = db.execute(
        select(BriefingItem)
        .where(BriefingItem.company_id == company_id, BriefingItem.briefing_id == briefing.id)
        .order_by(BriefingItem.rank.asc())
    ).scalars().all()

    cases = []
    for item in items:
        case = db.execute(
            select(Case).where(Case.company_id == company_id, Case.id == item.case_id)
        ).scalar_one_or_none()
        if case is None:
            continue
        cases.append(get_case_out(db, company_id, case))

    return BriefingOut(
        id=briefing.id,
        briefing_date=briefing.briefing_date,
        generated_at=briefing.generated_at,
        cases=cases,
    )
