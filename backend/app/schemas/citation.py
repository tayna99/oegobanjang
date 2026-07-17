from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class CitationOut(BaseModel):
    """근거 라이브러리 조회 응답 — 기존 스키마 관례대로 snake_case(camelCase 매핑은
    프론트가 실제로 이 API를 소비하는 시점, B4에서 결정). F등급은 애초에 저장하지
    않으므로(evidence_ingest.upsert_citations) 여기 나타나지 않는다."""

    id: str
    grade: str
    title: str
    source: str
    status: str
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
