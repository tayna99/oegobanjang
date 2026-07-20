"""app/services/notifications.py — 생성 훅(N01·N06·N03)·dedupe·조회/읽음 처리. R5.4.

승인 요청/결정은 services/approvals.py 함수를 직접 호출한다(엔드포인트 배선은
test_api_approval_requests.py/test_api_approvals.py가 이미 검증) — 여기서는 그 트랜잭션이
notifications 행을 정확히 남기는지만 본다. 데일리 브리핑(N03)은 test_briefing_service.py와
동일한 PG 테스트 하니스를 쓴다.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.auth_tokens import hash_secret
from app.models.briefing import BriefingItem
from app.models.company import Company
from app.models.document import WorkerDocument
from app.models.notification import Notification
from app.models.worker import Worker
from app.schemas.approval import ApprovalDecisionRequest
from app.services.approvals import decide_approval, request_approval
from app.services.briefing_service import generate_daily_briefing
from app.services.notifications import list_notifications, mark_notification_read


# ---------------------------------------------------------------------------
# N01/N06 — 승인 요청/결정 훅 (services/approvals.py 직접 호출)
# ---------------------------------------------------------------------------


def _seed_approval_world(db: Session) -> None:
    pin_hash = hash_secret("1234")
    db.execute(
        text(
            f"""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at, pin_hash) VALUES
          ('u_owner','010-0000-0001','김대표', now(), '{pin_hash}'),
          ('u_manager','010-0000-0002','박주임', now(), '{pin_hash}'),
          ('u_viewer','010-0000-0003','최열람', now(), NULL);
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active'),
          ('m_viewer','cmp1','u_viewer','viewer','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09');
        INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES
          ('cit_a','A','official','출입국관리법 제25조','국가법령정보센터', now());
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','체류 만료 임박','HIGH','risk_review','2026-08-09');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) VALUES
          ('act1','cmp1','cs1','approve','send_message','승인하기', true);
        INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES
          ('cmp1','cs1','cit_a','rule');
    """
        )
    )
    db.flush()


@pytest.fixture()
def approval_world(db: Session) -> Session:
    _seed_approval_world(db)
    return db


def _by_recipient(notifications: list[Notification]) -> dict[str, list[Notification]]:
    out: dict[str, list[Notification]] = {}
    for n in notifications:
        out.setdefault(n.recipient_user_id, []).append(n)
    return out


def test_request_approval_notifies_approvers_excluding_requester(approval_world: Session) -> None:
    approval, _ = request_approval(approval_world, "act1", "u_manager")

    all_notifications = list(approval_world.execute(select(Notification)).scalars())
    by_recipient = _by_recipient(all_notifications)

    # 승인 권한자(owner+manager)만 — 요청자 본인(u_manager)은 제외, viewer도 제외.
    assert set(by_recipient) == {"u_owner"}
    n01 = by_recipient["u_owner"][0]
    assert n01.type == "N01"
    assert n01.priority == "P1"
    assert n01.case_id == "cs1"
    assert n01.deeplink_path == "case/cs1/approve"
    assert n01.dedupe_key == f"cs1:N01:{approval.id}:u_owner"
    assert n01.channel == "push"
    assert n01.status == "queued"  # §13-7 — sent/delivered 아님


def test_request_approval_notification_masks_worker_name(approval_world: Session) -> None:
    """case.title(근로자 이름 미포함)만 쓴다 — DDL 주석 "title: 업무 단위 명칭(근로자명
    미포함)"을 알림 title/body도 그대로 지켜야 한다."""
    request_approval(approval_world, "act1", "u_manager")
    notification = approval_world.execute(select(Notification)).scalar_one()
    assert "Nguyen" not in notification.title
    assert "Nguyen" not in notification.body


def _approve_body(**overrides) -> ApprovalDecisionRequest:
    base = {"idempotency_key": str(uuid.uuid4()), "identity_method": "pin", "pin": "1234"}
    base.update(overrides)
    return ApprovalDecisionRequest(**base)


def test_decide_approval_notifies_only_the_original_requester(approval_world: Session) -> None:
    approval, _ = request_approval(approval_world, "act1", "u_manager")
    decide_approval(approval_world, approval.id, "approved", _approve_body(), "u_owner")

    all_notifications = list(approval_world.execute(select(Notification)).scalars())
    by_recipient = _by_recipient(all_notifications)

    # N01(owner 수신) + N06(요청자 manager 수신) — 결정자(u_owner) 본인은 N06 수신자가 아니다.
    assert set(by_recipient) == {"u_owner", "u_manager"}
    n01_types = {n.type for n in by_recipient["u_owner"]}
    n06_types = {n.type for n in by_recipient["u_manager"]}
    assert n01_types == {"N01"}
    assert n06_types == {"N06"}
    n06 = by_recipient["u_manager"][0]
    assert n06.title == "승인 완료"
    assert n06.deeplink_path == "case/cs1"


def test_decide_approval_reject_notifies_requester_with_rejection_title(approval_world: Session) -> None:
    approval, _ = request_approval(approval_world, "act1", "u_manager")
    decide_approval(
        approval_world, approval.id, "rejected", _approve_body(reason="근거 확인 필요"), "u_owner"
    )
    n06 = approval_world.execute(
        select(Notification).where(Notification.recipient_user_id == "u_manager", Notification.type == "N06")
    ).scalar_one()
    assert n06.title == "반려"


def test_idempotent_approval_replay_does_not_duplicate_notifications(approval_world: Session) -> None:
    """멱등 replay(같은 idempotency_key)는 approvals.py가 조기 반환한다 — 알림도 중복 생성되면
    안 된다."""
    key = str(uuid.uuid4())
    approval, _ = request_approval(approval_world, "act1", "u_manager")
    decide_approval(approval_world, approval.id, "approved", _approve_body(idempotency_key=key), "u_owner")
    decide_approval(approval_world, approval.id, "approved", _approve_body(idempotency_key=key), "u_owner")

    n06_count = approval_world.execute(
        select(Notification).where(Notification.recipient_user_id == "u_manager", Notification.type == "N06")
    ).scalars().all()
    assert len(n06_count) == 1


# ---------------------------------------------------------------------------
# N03 — risk_flagged(CRITICAL)만 실시간 알림 (briefing_service.generate_daily_briefing)
# ---------------------------------------------------------------------------

REF = "2026-07-17"


@pytest.fixture()
def briefing_company(db: Session) -> str:
    company_id = "cmp_notif_brf"
    db.add(Company(id=company_id, name="알림테스트제조", case_seq=0, evidence_seq=0))
    db.flush()  # 아래 raw SQL의 FK(memberships.company_id)가 참조하기 전에 반영해야 한다
    db.execute(
        text(
            f"""
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner2','010-0000-0011','김대표2', now()),
          ('u_manager2','010-0000-0012','박주임2', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner2','{company_id}','u_owner2','owner','active'),
          ('m_manager2','{company_id}','u_manager2','manager','active');
    """
        )
    )
    db.add(
        Worker(
            id="wrk_critical",
            company_id=company_id,
            display_name="Batbayar E.",
            nationality="몽골",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 7, 10),  # REF보다 과거 → 만료(CRITICAL)
        )
    )
    db.add(
        Worker(
            id="wrk_high",
            company_id=company_id,
            display_name="Tran Thi H.",
            nationality="베트남",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 8, 6),  # D-20 → HIGH(N03 대상 아님)
        )
    )
    db.flush()
    return company_id


def test_generate_daily_briefing_notifies_owner_and_manager_for_critical_only(
    db: Session, briefing_company: str
) -> None:
    generate_daily_briefing(db, company_id=briefing_company, reference_date=REF)

    notifications = list(
        db.execute(select(Notification).where(Notification.company_id == briefing_company)).scalars()
    )
    n03 = [n for n in notifications if n.type == "N03"]
    # CRITICAL(만료) 케이스 1건 × 수신자(owner+manager) 2인 = 2건. HIGH 케이스는 N03을 만들지 않는다.
    assert len(n03) == 2
    assert {n.recipient_user_id for n in n03} == {"u_owner2", "u_manager2"}
    assert all(n.priority == "P1" for n in n03)
    assert all("Batbayar" not in n.title and "Batbayar" not in n.body for n in n03)

    critical_case_ids = {
        item.case_id
        for item in db.execute(
            select(BriefingItem).where(BriefingItem.company_id == briefing_company)
        ).scalars()
    }
    assert all(n.case_id in critical_case_ids for n in n03)


def test_generate_daily_briefing_rerun_same_day_does_not_duplicate_n03(
    db: Session, briefing_company: str
) -> None:
    generate_daily_briefing(db, company_id=briefing_company, reference_date=REF)
    generate_daily_briefing(db, company_id=briefing_company, reference_date=REF)

    n03 = list(
        db.execute(
            select(Notification).where(Notification.company_id == briefing_company, Notification.type == "N03")
        ).scalars()
    )
    assert len(n03) == 2  # dedupe_key(case+threshold) 충돌로 재실행은 아무 것도 추가하지 않는다


def test_high_severity_worker_produces_no_n03(db: Session, briefing_company: str) -> None:
    generate_daily_briefing(db, company_id=briefing_company, reference_date=REF)
    n03_case_ids = {
        n.case_id
        for n in db.execute(
            select(Notification).where(Notification.company_id == briefing_company, Notification.type == "N03")
        ).scalars()
    }
    high_case = db.execute(
        select(BriefingItem).where(BriefingItem.company_id == briefing_company)
    ).scalars().all()
    # wrk_high의 케이스는 어느 것도 N03 수신 대상에 없어야 한다(HIGH는 다이제스트 몫).
    from app.models.case import Case

    high_case_ids = {
        c.id
        for c in db.execute(select(Case).where(Case.company_id == briefing_company, Case.worker_id == "wrk_high"))
        .scalars()
    }
    assert not (high_case_ids & n03_case_ids)
    assert len(high_case) >= 1  # sanity — 브리핑 자체는 두 워커 다 케이스를 만든다


# ---------------------------------------------------------------------------
# 조회/읽음 처리 — list_notifications/mark_notification_read (라우터는 test_api_notifications.py)
# ---------------------------------------------------------------------------


def test_list_and_mark_read_service_functions(approval_world: Session) -> None:
    request_approval(approval_world, "act1", "u_manager")
    notifications = list_notifications(approval_world, company_id="cmp1", recipient_user_id="u_owner")
    assert len(notifications) == 1
    assert notifications[0].read_at is None

    marked = mark_notification_read(
        approval_world, company_id="cmp1", recipient_user_id="u_owner", notification_id=notifications[0].id
    )
    assert marked is not None
    assert marked.read_at is not None

    # 다른 수신자·다른 회사 스코프로는 조회/읽음 처리가 안 된다(404에 해당하는 None).
    assert (
        mark_notification_read(
            approval_world, company_id="cmp1", recipient_user_id="u_manager", notification_id=notifications[0].id
        )
        is None
    )


def test_mark_read_is_idempotent_and_preserves_first_read_at(approval_world: Session) -> None:
    request_approval(approval_world, "act1", "u_manager")
    notification_id = list_notifications(approval_world, company_id="cmp1", recipient_user_id="u_owner")[0].id

    first = mark_notification_read(
        approval_world, company_id="cmp1", recipient_user_id="u_owner", notification_id=notification_id
    )
    second = mark_notification_read(
        approval_world, company_id="cmp1", recipient_user_id="u_owner", notification_id=notification_id
    )
    assert first is not None and second is not None
    assert first.read_at == second.read_at
