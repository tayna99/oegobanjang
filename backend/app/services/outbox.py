"""발송 대기열(outbox) 서비스 — MESSAGING_CHANNELS.md §2. `Approval → Outbox → ChannelAdapter`.

manager의 "실행 확인"(§1 각주² — 승인=상태 전이, 실행은 manager의 별도 확인)이 `create_and_dispatch`를
호출한다. next_actions.action_type='send_message'가 이미 승인된 액션에만 정확히 1개의 outbox
행을 만들고(사건 idempotency는 `dedupe_key` UNIQUE 제약이 구조적으로 강제, db/schema.sql
`outbox` §2), 발송 창(21:00~08:30, CRITICAL만 22:00까지 허용)에 걸리지 않으면 즉시
ChannelAdapter를 호출해 처리한다. 알림톡 실패는 SMS로 1회만 대체 발송한다("채널 중복 금지" —
fallback이지 중복 발송이 아니다, 2단계_알림카탈로그_딥링크맵_v1.md §5.2와 동일 원칙).

발송된 메시지는 thread_messages(direction='system')로도 기록되고, 응답 링크(§3)를 위한
`response_token`을 그 자리에서 발급한다 — 인바운드는 이 서비스가 아니라
`app/services/response_link.py`·`app/services/webhooks.py`가 담당한다(발신/수신 분리, §1).
"""

from __future__ import annotations

import datetime as dt
import secrets
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.outbox_exceptions import (
    OutboxActionNotFoundError,
    OutboxActionTypeNotSupportedError,
    OutboxAlreadyQueuedError,
    OutboxApprovalNotApprovedError,
    OutboxForbiddenError,
    OutboxNoContentError,
    OutboxNoThreadError,
    OutboxReminderCooldownError,
    OutboxResendNotEligibleError,
    OutboxWorkerMissingError,
)
from app.models.approval import Approval
from app.models.case import Case, NextAction
from app.models.company import Company
from app.models.draft import Draft, DraftVariant
from app.models.evidence import EvidenceEvent
from app.models.membership import Membership
from app.models.outbox import Outbox
from app.models.thread import Thread, ThreadMessage
from app.models.worker import Worker
from app.services.channels import WORKER_CHANNEL_ADAPTERS
from app.services.evidence import next_event_no

DISPATCHER_ROLES = ("manager",)  # 7단계 §2 각주² — owner는 승인만, 실행은 manager
SEND_MESSAGE_ACTION_TYPE = "send_message"

NIGHT_HOLD_HOUR = 21  # 일반 알림 보류 시작 시각
CRITICAL_HOLD_HOUR = 22  # CRITICAL(N03)만 이 시각까지 허용
RESUME_TIME = dt.time(8, 30)  # 다이제스트 합류 시각(2단계 §5.1)

REMINDER_COOLDOWN = dt.timedelta(hours=24)  # 2단계 §5.2
RESEND_MIN_AGE = dt.timedelta(hours=48)  # 2단계 §5.2
RESPONSE_LINK_VALIDITY = dt.timedelta(days=14)  # handoff_packages(7일)보다 근로자 응답 유예를 넉넉히 둔다


def compute_send_window(now_local: dt.datetime, *, is_critical: bool) -> dt.datetime | None:
    """발송 창 판정(§2 표). 즉시 발송 가능하면 None, 아니면 보류 해제 시각(당일/익일 08:30)."""
    hold_hour = CRITICAL_HOLD_HOUR if is_critical else NIGHT_HOLD_HOUR
    current = now_local.time()
    if RESUME_TIME <= current < dt.time(hold_hour, 0):
        return None
    resume_date = now_local.date() if current < RESUME_TIME else now_local.date() + dt.timedelta(days=1)
    return dt.datetime.combine(resume_date, RESUME_TIME, tzinfo=now_local.tzinfo)


def _dedupe_key(case_id: str, event_type: str, threshold: str) -> str:
    return f"{case_id}:{event_type}:{threshold}"


def _masked_recipient_ref(worker_id: str) -> str:
    # 이 스키마엔 근로자 연락처 원문 컬럼이 없다(§7 PII 최소화) — 표시용 참조만 남긴다.
    return f"worker:{worker_id}"


def _load_dispatcher_membership(db: Session, company_id: str, user_id: str) -> Membership | None:
    return db.execute(
        select(Membership).where(
            Membership.company_id == company_id, Membership.user_id == user_id, Membership.status == "active"
        )
    ).scalar_one_or_none()


def _approved_approval(db: Session, company_id: str, action_id: str) -> Approval | None:
    return db.execute(
        select(Approval)
        .where(Approval.company_id == company_id, Approval.action_id == action_id, Approval.status == "approved")
        .order_by(Approval.decided_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _thread_for_worker(db: Session, company_id: str, worker_id: str) -> Thread | None:
    return db.execute(
        select(Thread).where(Thread.company_id == company_id, Thread.worker_id == worker_id)
    ).scalar_one_or_none()


def _approved_draft_variant(
    db: Session, company_id: str, approval_id: str, lang: str
) -> tuple[Draft, DraftVariant] | None:
    draft = db.execute(
        select(Draft).where(Draft.company_id == company_id, Draft.approval_id == approval_id)
    ).scalar_one_or_none()
    if draft is None:
        return None
    variants = list(
        db.execute(
            select(DraftVariant).where(DraftVariant.company_id == company_id, DraftVariant.draft_id == draft.id)
        ).scalars()
    )
    if not variants:
        return None
    chosen = (
        next((v for v in variants if v.lang == lang), None)
        or next((v for v in variants if v.lang == "ko"), None)
        or variants[0]
    )
    return draft, chosen


def _company_timezone(db: Session, company_id: str) -> ZoneInfo:
    tz_name = db.execute(select(Company.timezone).where(Company.id == company_id)).scalar_one_or_none()
    return ZoneInfo(tz_name or "Asia/Seoul")


def _existing_outbox(db: Session, company_id: str, dedupe_key: str) -> Outbox | None:
    return db.execute(
        select(Outbox).where(Outbox.company_id == company_id, Outbox.dedupe_key == dedupe_key)
    ).scalar_one_or_none()


def _check_reminder_cooldown(db: Session, company_id: str, case_id: str, now: dt.datetime) -> None:
    recent = db.execute(
        select(Outbox.id).where(
            Outbox.company_id == company_id,
            Outbox.case_id == case_id,
            Outbox.event_type == "reminder",
            Outbox.created_at > now - REMINDER_COOLDOWN,
        ).limit(1)
    ).scalar_one_or_none()
    if recent is not None:
        raise OutboxReminderCooldownError()


def _check_resend_eligible(db: Session, company_id: str, case_id: str, action_id: str, now: dt.datetime) -> None:
    """48시간 미응답 재발송 전제: 원 dispatch가 실제로 sent됐고, sent 이후 48h가 지났으며,
    그 사이 스레드에 근로자 응답(inbound)이 없어야 한다."""
    original = db.execute(
        select(Outbox).where(
            Outbox.company_id == company_id,
            Outbox.case_id == case_id,
            Outbox.action_id == action_id,
            Outbox.event_type == "dispatch",
            Outbox.status == "sent",
        )
    ).scalar_one_or_none()
    if original is None or original.sent_at is None or now - original.sent_at < RESEND_MIN_AGE:
        raise OutboxResendNotEligibleError()
    if original.thread_id is not None:
        replied = db.execute(
            select(ThreadMessage.id).where(
                ThreadMessage.company_id == company_id,
                ThreadMessage.thread_id == original.thread_id,
                ThreadMessage.direction == "inbound",
                ThreadMessage.created_at > original.sent_at,
            ).limit(1)
        ).scalar_one_or_none()
        if replied is not None:
            raise OutboxResendNotEligibleError()


async def _process_item(db: Session, item: Outbox, *, now: dt.datetime | None = None) -> None:
    """어댑터를 호출해 outbox 행을 갱신하고, 성공 시 thread_messages(system) + evidence를 남긴다.

    `now`는 호출부(create_and_dispatch)가 받은 시각을 그대로 전달한다 — 여기서 새로
    `dt.datetime.now()`를 부르면 테스트가 주입한 시각과 어긋나 리마인드 쿨다운·48h 재발송
    판정이 실제 벽시계에 좌우된다."""
    adapter = WORKER_CHANNEL_ADAPTERS[item.channel]
    result = await adapter.send(to=item.recipient_ref or "", body=item.body, lang=item.lang)
    now = now if now is not None else dt.datetime.now(dt.timezone.utc)
    item.attempt_count += 1
    if result.status == "sent":
        item.status = "sent"
        item.external_id = result.external_id
        item.sent_at = now
    else:
        item.status = "failed"
        item.failed_reason = result.detail
    db.flush()

    if item.status != "sent":
        return

    response_token = secrets.token_urlsafe(32)
    thread_message = ThreadMessage(
        id=new_id(),
        thread_id=item.thread_id,
        company_id=item.company_id,
        direction="system",
        lang=item.lang,
        body_original=item.body,
        body_ko=item.body if item.lang == "ko" else None,
        received_at=now,
        created_at=now,
        response_token=response_token,
        response_token_expires_at=now + RESPONSE_LINK_VALIDITY,
    )
    db.add(thread_message)
    if item.thread_id is not None:
        thread = db.get(Thread, item.thread_id)
        if thread is not None:
            thread.last_message_at = now

    event_no = next_event_no(db, item.company_id)
    stub_note = "(스텁 — 자격 증명 없음)" if result.is_stub else ""
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=item.company_id,
            event_no=event_no,
            type="dispatch_executed",
            at=now,
            case_id=item.case_id,
            action_id=item.action_id,
            approval_id=item.approval_id,
            actor_type="user",
            actor_user_id=item.requested_by_user_id,
            summary=f"발송 실행 · {item.channel} {stub_note}".strip(),
        )
    )
    db.flush()


async def _create_and_process_sms_fallback(
    db: Session, original: Outbox, *, now: dt.datetime | None = None
) -> Outbox:
    """알림톡 실패 후 SMS로 1회만 대체 발송("채널 중복 금지" — fallback, 중복 발송 아님)."""
    fallback_dedupe_key = f"{original.dedupe_key}:sms_fallback"
    if _existing_outbox(db, original.company_id, fallback_dedupe_key) is not None:
        return original
    now = now if now is not None else dt.datetime.now(dt.timezone.utc)
    fallback = Outbox(
        id=new_id(),
        company_id=original.company_id,
        case_id=original.case_id,
        action_id=original.action_id,
        approval_id=original.approval_id,
        thread_id=original.thread_id,
        channel="sms",
        event_type=original.event_type,
        dedupe_key=fallback_dedupe_key,
        body=original.body,
        lang=original.lang,
        recipient_ref=original.recipient_ref,
        status="queued",
        fallback_from_id=original.id,
        requested_by_user_id=original.requested_by_user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(fallback)
    db.flush()
    await _process_item(db, fallback, now=now)
    return fallback


async def create_and_dispatch(
    db: Session,
    dispatcher_user_id: str,
    action_id: str,
    *,
    event_type: str = "dispatch",
    threshold: str | None = None,
    now: dt.datetime | None = None,
) -> Outbox:
    """"실행 확인" — MESSAGING_CHANNELS.md §1 각주²가 명시한, 승인과는 분리된 별도 이벤트.

    `now`는 테스트에서 발송 창(§2 표) 경계값을 결정적으로 검증하기 위한 주입 지점이다 —
    생략하면 실제 현재 시각을 쓴다(운영 경로는 항상 기본값)."""
    next_action = db.get(NextAction, action_id)
    if next_action is None:
        raise OutboxActionNotFoundError(action_id)

    membership = _load_dispatcher_membership(db, next_action.company_id, dispatcher_user_id)
    if membership is None or membership.role not in DISPATCHER_ROLES:
        raise OutboxForbiddenError()

    if next_action.action_type != SEND_MESSAGE_ACTION_TYPE:
        raise OutboxActionTypeNotSupportedError(next_action.action_type)

    approval = _approved_approval(db, next_action.company_id, action_id)
    if approval is None:
        raise OutboxApprovalNotApprovedError(action_id)

    case = db.get(Case, next_action.case_id)
    if case is None or case.worker_id is None:
        raise OutboxWorkerMissingError()
    worker = db.get(Worker, case.worker_id)
    if worker is None:
        raise OutboxWorkerMissingError()

    thread = _thread_for_worker(db, next_action.company_id, worker.id)
    if thread is None or thread.channel not in WORKER_CHANNEL_ADAPTERS:
        raise OutboxNoThreadError()

    lang = worker.preferred_language or "ko"
    found = _approved_draft_variant(db, next_action.company_id, approval.id, lang)
    if found is None:
        raise OutboxNoContentError()
    _draft, variant = found

    now = now if now is not None else dt.datetime.now(dt.timezone.utc)
    if event_type == "reminder":
        _check_reminder_cooldown(db, next_action.company_id, case.id, now)
    if event_type == "resend":
        _check_resend_eligible(db, next_action.company_id, case.id, action_id, now)

    dedupe_key = _dedupe_key(case.id, event_type, threshold or action_id)
    if _existing_outbox(db, next_action.company_id, dedupe_key) is not None:
        raise OutboxAlreadyQueuedError(dedupe_key)

    tz = _company_timezone(db, next_action.company_id)
    scheduled_for = compute_send_window(now.astimezone(tz), is_critical=(case.severity == "CRITICAL"))

    item = Outbox(
        id=new_id(),
        company_id=next_action.company_id,
        case_id=case.id,
        action_id=action_id,
        approval_id=approval.id,
        thread_id=thread.id,
        channel=thread.channel,
        event_type=event_type,
        dedupe_key=dedupe_key,
        body=variant.text,
        lang=lang,
        recipient_ref=_masked_recipient_ref(worker.id),
        status="queued",
        scheduled_for=scheduled_for,
        requested_by_user_id=dispatcher_user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise OutboxAlreadyQueuedError(dedupe_key) from exc

    if scheduled_for is None:
        await _process_item(db, item, now=now)
        if item.channel == "alimtalk" and item.status == "failed":
            await _create_and_process_sms_fallback(db, item, now=now)

    db.commit()
    db.refresh(item)
    return item


def list_outbox(db: Session, company_id: str) -> list[Outbox]:
    return list(
        db.execute(
            select(Outbox).where(Outbox.company_id == company_id).order_by(Outbox.created_at.desc())
        ).scalars()
    )
