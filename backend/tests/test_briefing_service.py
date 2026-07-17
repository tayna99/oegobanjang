"""데일리 브리핑 서비스 — rule_findings → briefings/briefing_items/cases + risk_flagged evidence (G6).

PG 테스트 하니스 사용(conftest.py). LLM을 호출하지 않는다 — context_service의 Risk Rule
Engine 결과를 그대로 소비만 한다는 계약을 여기서 고정한다.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.briefing import Briefing, BriefingItem
from app.models.case import Case
from app.models.company import Company
from app.models.document import WorkerDocument
from app.models.evidence import EvidenceEvent
from app.models.worker import Worker
from app.services.briefing_service import generate_daily_briefing

REF = "2026-07-17"


@pytest.fixture()
def seeded_company(db: Session) -> str:
    company = Company(id="cmp_brf_test", name="브리핑테스트제조", case_seq=0, evidence_seq=0)
    db.add(company)
    db.add(
        Worker(
            id="wrk_high",
            company_id="cmp_brf_test",
            display_name="Nguyen Van A",
            nationality="베트남",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 8, 6),  # D-20 → HIGH
            contract_ends_at=dt.date(2027, 1, 1),  # 비자보다 늦게 끝남 → conflict
        )
    )
    db.add(
        Worker(
            id="wrk_low",
            company_id="cmp_brf_test",
            display_name="Batbayar",
            nationality="몽골",
            visa_type="E-9",
            stay_expires_at=dt.date(2027, 7, 1),  # 여유 → LOW
        )
    )
    db.flush()
    db.add(
        WorkerDocument(
            id="doc_missing",
            company_id="cmp_brf_test",
            worker_id="wrk_high",
            doc_type="passport_copy",
            status="missing",
            due_date=dt.date(2026, 7, 22),  # D-5 → HIGH
        )
    )
    db.flush()
    return "cmp_brf_test"


def _findings_count(db: Session, company_id: str) -> int:
    from app.services.context_service import build_context_snapshot

    snapshot = build_context_snapshot(
        db, company_id=company_id, required_context=[], reference_date=REF
    )
    return len(snapshot.rule_findings)


def test_generate_creates_briefing_and_items_ranked_by_severity(
    db: Session, seeded_company: str
) -> None:
    expected_count = _findings_count(db, seeded_company)
    assert expected_count == 5  # visa_expiry x2 + contract_visa_conflict + missing_document + quota_review

    briefing = generate_daily_briefing(db, company_id=seeded_company, reference_date=REF)

    assert briefing.company_id == seeded_company
    assert briefing.briefing_date == dt.date(2026, 7, 17)
    assert briefing.rerun_count == 0

    items = (
        db.execute(
            select(BriefingItem)
            .where(BriefingItem.briefing_id == briefing.id)
            .order_by(BriefingItem.rank)
        )
        .scalars()
        .all()
    )
    assert len(items) == expected_count
    assert [item.rank for item in items] == list(range(1, expected_count + 1))

    cases = {
        case.id: case
        for case in db.execute(
            select(Case).where(Case.id.in_([item.case_id for item in items]))
        ).scalars()
    }
    severities = [cases[item.case_id].severity for item in items]
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    assert severities == sorted(severities, key=lambda s: order[s])
    # hero(rank=1)는 HIGH 중에서도 risk_type 우선순위가 가장 앞선 contract_visa_conflict
    assert cases[items[0].case_id].case_type == "contract_visa_conflict"
    assert cases[items[0].case_id].worker_id == "wrk_high"


def test_generate_cases_satisfy_schema_constraints_and_carry_no_worker_name(
    db: Session, seeded_company: str
) -> None:
    briefing = generate_daily_briefing(db, company_id=seeded_company, reference_date=REF)
    items = db.execute(select(BriefingItem).where(BriefingItem.briefing_id == briefing.id)).scalars().all()
    cases = db.execute(select(Case).where(Case.id.in_([i.case_id for i in items]))).scalars().all()

    assert len(cases) == 5
    for case in cases:
        assert case.case_type in {
            "visa_expiry",
            "missing_document",
            "contract_visa_conflict",
            "reporting_deadline",
            "quota_review",
        }
        assert case.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        assert case.prepared_by == "rule"
        assert case.case_code.startswith("case_")
        # DDL 주석 "title: 업무 단위 명칭(근로자명 미포함)" — 원문 이름이 새면 안 된다.
        assert "Nguyen" not in case.title and "Batbayar" not in case.title
        assert "Nguyen" not in (case.summary or "") and "Batbayar" not in (case.summary or "")

    quota_case = next(c for c in cases if c.case_type == "quota_review")
    assert quota_case.worker_id is None


def test_generate_records_risk_flagged_evidence_linked_to_cases(
    db: Session, seeded_company: str
) -> None:
    briefing = generate_daily_briefing(db, company_id=seeded_company, reference_date=REF)
    items = db.execute(select(BriefingItem).where(BriefingItem.briefing_id == briefing.id)).scalars().all()

    events = (
        db.execute(select(EvidenceEvent).where(EvidenceEvent.company_id == seeded_company))
        .scalars()
        .all()
    )
    risk_events = [e for e in events if e.type == "risk_flagged"]
    assert len(risk_events) == len(items)
    assert {e.case_id for e in risk_events} == {item.case_id for item in items}
    assert all(e.actor_type == "system" for e in risk_events)
    assert all("Nguyen" not in e.summary and "Batbayar" not in e.summary for e in risk_events)


def test_generate_is_idempotent_on_rerun_same_day(db: Session, seeded_company: str) -> None:
    first = generate_daily_briefing(db, company_id=seeded_company, reference_date=REF)
    first_items = db.execute(
        select(BriefingItem).where(BriefingItem.briefing_id == first.id)
    ).scalars().all()
    first_case_ids = {item.case_id for item in first_items}
    first_case_codes = {
        case.id: case.case_code
        for case in db.execute(select(Case).where(Case.id.in_(first_case_ids))).scalars()
    }

    second = generate_daily_briefing(db, company_id=seeded_company, reference_date=REF)

    assert second.id == first.id  # 같은 날 재실행 → 같은 briefing 행 갱신(UNIQUE company_id, briefing_date)
    assert second.rerun_count == 1

    second_items = db.execute(
        select(BriefingItem).where(BriefingItem.briefing_id == second.id)
    ).scalars().all()
    assert len(second_items) == len(first_items)  # 중복 생성 없음(delete-then-insert)

    second_case_ids = {item.case_id for item in second_items}
    assert second_case_ids == first_case_ids  # case가 재사용됨(같은 결정론적 id)
    for case_id, code in first_case_codes.items():
        reloaded = db.get(Case, case_id)
        assert reloaded.case_code == code  # case_code 카운터가 재실행마다 재발급되지 않음

    briefings = db.execute(
        select(Briefing).where(Briefing.company_id == seeded_company)
    ).scalars().all()
    assert len(briefings) == 1  # UNIQUE(company_id, briefing_date) 위반 없이 upsert됨


def test_generate_with_no_workers_yields_empty_briefing(db: Session) -> None:
    db.add(Company(id="cmp_empty", name="워커없는회사"))
    db.flush()

    briefing = generate_daily_briefing(db, company_id="cmp_empty", reference_date=REF)

    items = db.execute(select(BriefingItem).where(BriefingItem.briefing_id == briefing.id)).scalars().all()
    assert items == []
