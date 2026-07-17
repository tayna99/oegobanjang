"""companies 표시 번호 카운터(case_seq·evidence_seq) 원자 증가 단일 지점 — docs/DB_SCHEMA.md §9
(번호·식별 체계). case_code("case_002")·evidence_events.event_no("#4789") 발급이 이 카운터를 쓴다.

app/services/approvals.py·evidence_ingest.py·briefing_service.py 세 곳에 거의 동일한 헬퍼가
중복돼 있던 것을 여기 하나로 모았다 — 단문 UPDATE ... RETURNING으로 경합 안전하게 증가시키는
계약을 한 곳에서만 보장한다. commit()/flush()는 하지 않는다 — 호출자의 트랜잭션에 맡긴다.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.company import Company


def next_case_seq(db: Session, company_id: str) -> int:
    """companies.case_seq를 원자적으로 증가시키고 새 값을 받는다 — case_code 발급 카운터."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(case_seq=Company.case_seq + 1)
        .returning(Company.case_seq)
    ).scalar_one()


def next_event_no(db: Session, company_id: str) -> int:
    """companies.evidence_seq를 원자적으로 증가시키고 새 값을 받는다 — evidence_events.event_no 발급 카운터."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(evidence_seq=Company.evidence_seq + 1)
        .returning(Company.evidence_seq)
    ).scalar_one()
