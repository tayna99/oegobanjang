"""drafts + draft_variants 응답 스키마 — GET /api/v1/cases/{case_id}/draft(SD-5).
docs/DB_SCHEMA.md §4.7, plans/SEED_DESIGN_2026-07-20.md Part B5(b).

revised_text(mock DraftFixture의 단일 "부드러운 톤 제안" 캔버스)는 DB 컬럼 대응이 없어
여기 두지 않는다 — draft_variants.is_revised가 이미 그 개념을 언어별 행으로 담고 있고,
langs에 그대로 노출한다(프론트가 화면에서 걸러 쓴다).
"""

from __future__ import annotations

from pydantic import BaseModel


class DraftLangVariantOut(BaseModel):
    lang: str
    text: str
    is_revised: bool


class DraftOut(BaseModel):
    draft_id: str
    channel: str
    purpose: str
    status: str
    langs: list[DraftLangVariantOut]
