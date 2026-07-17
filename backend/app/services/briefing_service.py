"""데일리 브리핑 — Risk Rule Engine 결과를 briefings·briefing_items·cases로 영속화.

plans/ROADMAP.md G6(backend, rule-only·LLM 0회): context_service.build_context_snapshot()이
이미 확정한 rule_findings를 소비만 한다 — 이 모듈은 LLM을 한 번도 호출하지 않는다.
같은 날 재호출은 멱등 갱신(briefings.briefing_date UNIQUE, §4.9 DDL 주석) — briefing·case는
company_id+결정론적 키로 upsert하고, briefing_items는 매 호출마다 delete-then-insert한다
(브리핑은 스냅샷이므로 부분 병합보다 전량 재작성이 단순하고 안전하다).

case.title/summary는 db/schema.sql §4.3 DDL 주석("title: 업무 단위 명칭(근로자명 미포함)",
"summary: 마스킹 적용")을 따라 risk_type 표시 라벨 + D-day만 담고 워커 이름은 넣지 않는다
(workers.display_name은 마스킹되지 않은 원문 — case_id는 worker_id로 연결되므로 화면이
근로자 이름을 보여줄 땐 별도 조인으로 가져온다).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain import rules
from app.models.briefing import Briefing, BriefingItem
from app.models.case import Case
from app.models.company import Company
from app.models.evidence import EvidenceEvent
from app.services import context_service
from app.services.context_service import ContextSnapshot, RuleFinding


def generate_daily_briefing(
    db: Session,
    *,
    company_id: str,
    reference_date: str | None = None,
) -> Briefing:
    """스냅샷 조립(룰 실행 포함) → briefing/case/briefing_item upsert → risk_flagged evidence."""
    snapshot = context_service.build_context_snapshot(
        db, company_id=company_id, required_context=[], reference_date=reference_date
    )
    briefing = _upsert_briefing(db, snapshot)

    db.execute(
        delete(BriefingItem).where(
            BriefingItem.company_id == company_id, BriefingItem.briefing_id == briefing.id
        )
    )

    now = dt.datetime.now(dt.UTC)
    for rank, finding in enumerate(snapshot.rule_findings, start=1):
        case = _upsert_case(
            db, company_id=company_id, reference_date=snapshot.reference_date, finding=finding
        )
        db.add(
            BriefingItem(
                id=new_id(),
                company_id=company_id,
                briefing_id=briefing.id,
                case_id=case.id,
                rank=rank,
            )
        )
        _record_risk_flagged(db, company_id=company_id, case_id=case.id, finding=finding, at=now)

    db.commit()
    db.refresh(briefing)
    return briefing


def _upsert_briefing(db: Session, snapshot: ContextSnapshot) -> Briefing:
    company_id = snapshot.company.company_id
    briefing_id = rules.stable_id("brf", company_id, snapshot.reference_date)
    now = dt.datetime.now(dt.UTC)
    source_hash = rules.short_hash(snapshot.model_dump_json(), length=64)

    stmt = (
        pg_insert(Briefing)
        .values(
            id=briefing_id,
            company_id=company_id,
            briefing_date=dt.date.fromisoformat(snapshot.reference_date),
            generated_at=now,
            source_snapshot_hash=source_hash,
            rerun_count=0,
            last_refreshed_at=now,
        )
        .on_conflict_do_update(
            index_elements=[Briefing.company_id, Briefing.briefing_date],
            set_={
                "generated_at": now,
                "source_snapshot_hash": source_hash,
                "rerun_count": Briefing.rerun_count + 1,
                "last_refreshed_at": now,
            },
        )
    )
    db.execute(stmt)
    db.flush()
    return db.execute(select(Briefing).where(Briefing.id == briefing_id)).scalar_one()


def _upsert_case(
    db: Session,
    *,
    company_id: str,
    reference_date: str,
    finding: RuleFinding,
) -> Case:
    subject_key = finding.worker_id or "company"
    case_id = rules.stable_id("case", company_id, subject_key, finding.risk_type)
    due_date = _finding_due_date(reference_date, finding)
    summary = f"{finding.display_label} — {_risk_timing_label(finding)}"
    guard_note = _guard_note(finding.severity)
    now = dt.datetime.now(dt.UTC)

    existing = db.get(Case, case_id)
    if existing is not None:
        existing.severity = finding.severity
        existing.summary = summary
        existing.due_date = dt.date.fromisoformat(due_date) if due_date else None
        existing.guard_note = guard_note
        existing.updated_at = now
        db.flush()
        return existing

    case = Case(
        id=case_id,
        company_id=company_id,
        case_code=f"case_{_next_case_seq(db, company_id):03d}",
        worker_id=finding.worker_id,
        case_type=finding.risk_type,
        title=finding.display_label,
        summary=summary,
        severity=finding.severity,
        due_date=dt.date.fromisoformat(due_date) if due_date else None,
        guard_note=guard_note,
        prepared_by="rule",
    )
    db.add(case)
    db.flush()
    return case


def _finding_due_date(reference_date: str, finding: RuleFinding) -> str | None:
    """RuleFinding은 원본 만료일 대신 d_day/days_overdue만 들고 있으므로 역산한다
    (rules.evaluate_* 함수들이 reference_date 기준으로 뺀 것의 역연산이라 정확하다)."""
    ref = rules.parse_iso_date(reference_date)
    if finding.expired and finding.days_overdue is not None:
        return (ref - dt.timedelta(days=finding.days_overdue)).isoformat()
    if finding.d_day is not None:
        return (ref + dt.timedelta(days=finding.d_day)).isoformat()
    return None


def _risk_timing_label(finding: RuleFinding) -> str:
    if finding.expired:
        if finding.days_overdue is not None:
            return f"만료 후 {finding.days_overdue}일 경과"
        return "기한 경과"
    if finding.d_day is not None:
        return f"D-{finding.d_day}"
    return "기한 확인 필요"


def _guard_note(severity: str) -> str | None:
    if severity == "CRITICAL":
        return "즉시 조치가 필요합니다 — 기한이 지났거나 임박했습니다"
    if severity == "HIGH":
        return "빠른 시일 내 조치가 필요합니다"
    return None


def _next_case_seq(db: Session, company_id: str) -> int:
    """companies.case_seq를 원자적으로 증가시킨다 — app/services/approvals._next_event_no와
    동일 계약(단문 UPDATE...RETURNING, §9 case_code 발급 카운터)."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(case_seq=Company.case_seq + 1)
        .returning(Company.case_seq)
    ).scalar_one()


def _next_event_no(db: Session, company_id: str) -> int:
    """app/services/approvals.py·evidence_ingest.py의 _next_event_no와 동일 계약."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(evidence_seq=Company.evidence_seq + 1)
        .returning(Company.evidence_seq)
    ).scalar_one()


def _record_risk_flagged(
    db: Session,
    *,
    company_id: str,
    case_id: str,
    finding: RuleFinding,
    at: dt.datetime,
) -> None:
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=company_id,
            event_no=_next_event_no(db, company_id),
            type="risk_flagged",
            at=at,
            case_id=case_id,
            actor_type="system",
            actor_display="Risk Rule Engine",
            summary=f"{finding.display_label} — {finding.severity} ({_risk_timing_label(finding)})",
        )
    )
