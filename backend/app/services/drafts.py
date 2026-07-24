"""drafts + draft_variants 읽기 서비스 — GET /api/v1/cases/{case_id}/draft(SD-5).
plans/SEED_DESIGN_2026-07-20.md Part B5(b), docs/DB_SCHEMA.md §4.7.

케이스당 여러 초안이 있을 수 있다(반려 후 재작성 등, mock DraftPage.findDraft은 이 자체를
모르고 그냥 첫 매치를 쓴다) — 여기서는 "가장 관련 있는 살아있는 초안"을 명시적으로 고른다:
rejected/superseded가 아닌 것 중 가장 최근 생성분. 전부 종결 상태면(예: 전부 반려) 가장
최근 1건으로 폴백한다(이력이라도 보여주는 편이 빈 화면보다 낫다는 판단). 케이스에 초안이
아예 없으면 None을 반환해 라우터가 404로 변환한다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draft import Draft, DraftVariant
from app.schemas.draft import DraftLangVariantOut, DraftOut

_TERMINAL_STATUSES = {"rejected", "superseded"}


def _select_live_draft(db: Session, company_id: str, case_id: str) -> Draft | None:
    drafts = (
        db.execute(
            select(Draft)
            .where(Draft.company_id == company_id, Draft.case_id == case_id)
            .order_by(Draft.created_at.desc(), Draft.id.desc())
        )
        .scalars()
        .all()
    )
    if not drafts:
        return None
    live = [d for d in drafts if d.status not in _TERMINAL_STATUSES]
    return live[0] if live else drafts[0]


def get_draft_out(db: Session, company_id: str, case_id: str) -> DraftOut | None:
    draft = _select_live_draft(db, company_id, case_id)
    if draft is None:
        return None
    variants = (
        db.execute(
            select(DraftVariant)
            .where(DraftVariant.company_id == company_id, DraftVariant.draft_id == draft.id)
            .order_by(DraftVariant.created_at.asc(), DraftVariant.id.asc())
        )
        .scalars()
        .all()
    )
    return DraftOut(
        draft_id=draft.id,
        channel=draft.channel,
        purpose=draft.purpose,
        status=draft.status,
        langs=[DraftLangVariantOut(lang=v.lang, text=v.text, is_revised=v.is_revised) for v in variants],
    )
