"""알림 생성/큐잉 — R5.4. docs/DB_SCHEMA.md §4.10, reference/specs/2단계_알림카탈로그_딥링크맵_v1.md.

`notifications` ORM 모델(app/models/notification.py)은 이 서비스가 생기기 전까지 어떤
서비스·라우터에서도 쓰이지 않았다 — 이 파일이 그 생성 경로다. evidence_events와 동일 원칙
(app/services/evidence.py PRIVILEGED_EVIDENCE_TYPES 참조)을 따른다: 알림도 "실제로 그 이벤트가
일어난 서버 트랜잭션 안"에서만 생성해야 위조 알림을 막을 수 있으므로, 범용 POST 엔드포인트를
두지 않는다 — 이 모듈의 함수를 이벤트 발생 지점(services/approvals.py·briefing_service.py)이
자기 트랜잭션 안에서 직접 호출한다(별도 db.commit() 없음 — 호출부의 커밋에 얹힌다).

이번 세션이 배선한 이벤트는 서버가 이미 감지하는 3종뿐이다(카탈로그 §4.1 P1 즉시 발송):
- N01 `approval_requested` — 승인 권한자(활성 owner+manager, 요청자 본인 제외)
- N06 `approval_decided`/`approval_rejected` — 요청을 만든 담당자 1인
- N03 `risk_flagged`(CRITICAL만) — 담당자+대표(활성 owner+manager)
N02(worker_replied)는 인바운드 쓰기 API가 아직 없어(A3, R3 몫) 소스 자체가 없고, N04/N05(런
상태 전이)·N10~N14(아침 다이제스트 스케줄러)·N20~N22(주간 묶음)는 이번 범위 밖(후속) —
docs/DB_SCHEMA.md §4.10 R5.4 노트 참조.

MVP 불변식(§13-7, GOTCHAS): notifications는 발신 "의도" 큐일 뿐이다. status는
queued/held/suppressed만 허용되고 sent/delivered/failed는 DB CHECK가 구조적으로 차단한다
(db/validate.py "notification sent status is blocked"). 이 서비스는 그 큐에 행을 적재만
한다 — 실제 발신 확인은 어디에도 기록하지 않는다.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.models.membership import Membership
from app.models.notification import Notification
from app.services.push_adapter import send_push

APPROVAL_ROLES = ("owner", "manager")


def _active_recipients(db: Session, company_id: str, *, roles: tuple[str, ...], exclude_user_id: str | None = None) -> list[str]:
    """카탈로그 수신자 규칙(§1 "승인 권한자(대표 또는 담당자)" 등)의 공통 구현 — 활성
    멤버십만, exclude_user_id는 "이미 알고 있는 행위자 본인은 자기 행위 알림을 받지
    않는다"는 관례(승인 요청자가 자기 요청 알림을 또 받을 필요는 없다)."""
    stmt = select(Membership.user_id).where(
        Membership.company_id == company_id,
        Membership.status == "active",
        Membership.role.in_(roles),
        Membership.user_id.is_not(None),
    )
    if exclude_user_id is not None:
        stmt = stmt.where(Membership.user_id != exclude_user_id)
    return [uid for uid in db.execute(stmt).scalars() if uid is not None]


def _create_notification(
    db: Session,
    *,
    company_id: str,
    recipient_user_id: str,
    type_code: str,
    priority: str,
    title: str,
    body: str,
    deeplink_path: str,
    dedupe_key: str,
    channel: str = "push",
    case_id: str | None = None,
    run_id: str | None = None,
) -> Notification | None:
    """UNIQUE(company_id, dedupe_key) 충돌 시 조용히 건너뛴다(idempotent — 2단계 §5.2
    "같은 case + 같은 event_type + 같은 임계값은 1회만"). title/body는 호출부가 이미 마스킹된
    값(case.title/summary 등)으로만 조립해야 한다 — 이 함수는 그 값을 그대로 저장할 뿐 별도
    마스킹을 하지 않는다(evidence_events.summary와 동일 계약, 책임은 호출부)."""
    stmt = (
        pg_insert(Notification)
        .values(
            id=new_id(),
            company_id=company_id,
            recipient_user_id=recipient_user_id,
            type=type_code,
            priority=priority,
            title=title,
            body=body,
            deeplink_path=deeplink_path,
            dedupe_key=dedupe_key,
            channel=channel,
            case_id=case_id,
            run_id=run_id,
        )
        .on_conflict_do_nothing(index_elements=["company_id", "dedupe_key"])
        .returning(Notification.id)
    )
    new_row_id = db.execute(stmt).scalar_one_or_none()
    if new_row_id is None:
        return None
    notification = db.get(Notification, new_row_id)
    assert notification is not None
    send_push(notification)  # 자격증명 게이트 스텁 — notifications 행에는 아무 것도 쓰지 않는다
    return notification


def notify_approval_requested(
    db: Session,
    *,
    company_id: str,
    case_id: str,
    case_title: str,
    approval_id: str,
    requested_by_user_id: str,
    at: dt.datetime,
) -> list[Notification]:
    """N01 `approval_requested` — 승인 권한자(활성 owner+manager, 요청자 본인 제외)에게.

    dedupe_key는 승인 건(approval_id) + 수신자 단위다 — UNIQUE 제약이 (company_id, dedupe_key)
    전체(수신자별이 아님)라, 승인 권한자가 2인 이상이면 recipient_id를 키에 포함하지 않을 경우
    두 번째 이후 수신자의 INSERT가 첫 수신자 행과 dedupe_key가 겹쳐 on_conflict_do_nothing에
    조용히 먹힌다(발견한 회귀 — test_notifications_service.py가 고정). 같은 액션에 pending
    승인은 항상 최대 1건이므로(ux_approvals_one_pending) approval_id 자체는 여전히 안정적인
    자연키다.
    """
    recipients = _active_recipients(db, company_id, roles=APPROVAL_ROLES, exclude_user_id=requested_by_user_id)
    created: list[Notification] = []
    for recipient_id in recipients:
        notification = _create_notification(
            db,
            company_id=company_id,
            recipient_user_id=recipient_id,
            type_code="N01",
            priority="P1",
            title="승인 요청 1건",
            body=f"{case_title} · 승인 전에는 외부로 발송되지 않습니다",
            deeplink_path=f"case/{case_id}/approve",
            dedupe_key=f"{case_id}:N01:{approval_id}:{recipient_id}",
            case_id=case_id,
        )
        if notification is not None:
            created.append(notification)
    return created


def notify_approval_decided(
    db: Session,
    *,
    company_id: str,
    case_id: str,
    case_title: str,
    approval_id: str,
    requested_by_user_id: str | None,
    decision: str,
    at: dt.datetime,
) -> Notification | None:
    """N06 `approval_decided` — 승인/반려 결정을 요청을 만든 담당자 1인에게 알린다.

    프론트가 아니라 agent/rule이 만든 요청(requested_by_user_id NULL)은 수신자가 없으므로
    조용히 스킵한다 — approvals.py.request_approval은 현재 requested_by_actor='user'만
    다루므로 실제로는 항상 값이 있다(서비스 docstring 참조).
    """
    if requested_by_user_id is None:
        return None
    verb = "승인 완료" if decision == "approved" else "반려"
    return _create_notification(
        db,
        company_id=company_id,
        recipient_user_id=requested_by_user_id,
        type_code="N06",
        priority="P1",
        title=verb,
        body=f"{case_title} · {verb}",
        deeplink_path=f"case/{case_id}",
        dedupe_key=f"{case_id}:N06:{approval_id}",
        case_id=case_id,
    )


def notify_risk_flagged_critical(
    db: Session,
    *,
    company_id: str,
    case_id: str,
    case_title: str,
    severity: str,
    threshold_key: str,
    at: dt.datetime,
) -> list[Notification]:
    """N03 `risk_flagged(CRITICAL)` — 담당자+대표(활성 owner+manager)에게.

    카탈로그(§2)는 CRITICAL만 실시간 P1이고 HIGH 이하는 아침 다이제스트(N11, P2)로 합산된다
    — 다이제스트 스케줄러는 이번 범위 밖이라 여기서는 CRITICAL만 다룬다(호출부가 그 필터를
    건다). threshold_key는 "같은 임계값은 1회만"(§5.2) idempotency 키 재료 — days_overdue/
    d_day처럼 판단 근거가 바뀌면 자연히 새 알림이 정당하게 남는다. dedupe_key에 recipient_id를
    포함하는 이유는 notify_approval_requested 문서화 참조(수신자 2인 이상일 때 두 번째부터
    UNIQUE 충돌로 조용히 스킵되는 것을 막는다).
    """
    if severity != "CRITICAL":
        return []
    recipients = _active_recipients(db, company_id, roles=APPROVAL_ROLES)
    created: list[Notification] = []
    for recipient_id in recipients:
        notification = _create_notification(
            db,
            company_id=company_id,
            recipient_user_id=recipient_id,
            type_code="N03",
            priority="P1",
            title="즉시 확인 필요",
            body=f"{case_title} · 확인이 필요합니다",
            deeplink_path=f"case/{case_id}",
            dedupe_key=f"{case_id}:N03:{threshold_key}:{recipient_id}",
            case_id=case_id,
        )
        if notification is not None:
            created.append(notification)
    return created


def list_notifications(db: Session, *, company_id: str, recipient_user_id: str) -> list[Notification]:
    return list(
        db.execute(
            select(Notification)
            .where(
                Notification.company_id == company_id,
                Notification.recipient_user_id == recipient_user_id,
            )
            .order_by(Notification.created_at.desc())
        )
        .scalars()
        .all()
    )


def mark_notification_read(
    db: Session, *, company_id: str, recipient_user_id: str, notification_id: str
) -> Notification | None:
    """본인 수신함의 알림만 읽음 처리할 수 있다(company_id+recipient_user_id 스코프) — 다른
    사람 수신함 항목은 조회조차 안 된다(존재 비노출, 404). 이미 읽은 알림을 다시 눌러도
    read_at을 덮어쓰지 않는다(최초 열람 시각 보존, 멱등)."""
    notification = db.execute(
        select(Notification).where(
            Notification.company_id == company_id,
            Notification.id == notification_id,
            Notification.recipient_user_id == recipient_user_id,
        )
    ).scalar_one_or_none()
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification
