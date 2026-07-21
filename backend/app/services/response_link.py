"""응답 링크(response link) — MESSAGING_CHANNELS.md §3 수신 파이프라인.

SMS에는 수신 API가 없고 Zalo OA 승인 전에도 동작해야 하므로, 1차 실연동은 "응답 링크" 패턴이다
(§3): outbox가 발송한 direction='system' thread_messages 행에 심어둔 만료형 토큰으로 근로자가
자체 호스팅 무인증 페이지에서 버튼 선택 + 자유입력으로 응답한다. 응답은 인바운드 정규화
(thread_messages, direction='inbound') → N02(worker_reply_received) 이벤트 → M6
Interpretation(status='proposed')로 이어진다. Zalo OA webhook(stage ④, app/services/webhooks.py)도
같은 `_ingest_inbound_reply`를 거쳐 이 정규화 지점에 합류한다(§3 "인바운드 소스가 응답 링크든
webhook이든 그 다음 단계는 동일하다").

근로자 원문 응답은 summary_ko에 절대 포함하지 않는다(GOTCHAS §3, 목록·요약 노출 금지 — 원문은
thread_messages.body_original에만, 스레드 상세 전용).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.response_link_exceptions import (
    ResponseLinkAlreadySubmittedError,
    ResponseLinkExpiredError,
    ResponseLinkInvalidChoiceError,
    ResponseLinkNoContentError,
)
from app.models.evidence import EvidenceEvent
from app.models.interpretation import Interpretation
from app.models.outbox import Outbox
from app.models.thread import Thread, ThreadMessage
from app.models.worker import Worker
from app.services.evidence import next_event_no

# 미리 정의된 버튼 선택지 — 모국어 번역/해석 파이프라인(LLM 필요)은 R4(에이전트 런타임
# 실연결) 몫으로 명시적으로 남긴다. 이 태스크는 "버튼 선택 + 자유입력" 정규화 경로 자체를
# 만드는 것이 범위이지, 다국어 콘텐츠 생성은 범위 밖이다.
RESPONSE_CHOICES: dict[str, str] = {
    "received": "확인했습니다 (서류 준비 완료)",
    "not_yet": "아직 준비 중입니다",
    "question": "질문이 있어요",
}


def _find_outbound_message(db: Session, token: str) -> ThreadMessage | None:
    return db.execute(select(ThreadMessage).where(ThreadMessage.response_token == token)).scalar_one_or_none()


def _lock_outbound_message(db: Session, token: str) -> ThreadMessage | None:
    """Lock one response token so concurrent browser retries cannot both consume it."""
    return db.execute(
        select(ThreadMessage).where(ThreadMessage.response_token == token).with_for_update()
    ).scalar_one_or_none()


def _resolve_case_id(db: Session, company_id: str, thread_id: str | None) -> str | None:
    """스레드=근로자 단위, 케이스=업무 단위라 1:1이 아니다(GLOSSARY D2) — 그 스레드로 가장 최근
    발송된 outbox 항목의 case_id를 "현재 연결"로 근사한다(있으면). 없으면 None(정상 — 케이스
    미연결 스레드도 존재, MESSAGING_CHANNELS.md §4 Message.caseId 주석과 동일 원칙)."""
    if thread_id is None:
        return None
    return db.execute(
        select(Outbox.case_id)
        .where(Outbox.company_id == company_id, Outbox.thread_id == thread_id)
        .order_by(Outbox.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


class ResponseLinkView:
    def __init__(self, *, thread_id: str, worker: Worker | None, lang: str | None, prompt: str) -> None:
        self.thread_id = thread_id
        self.worker = worker
        self.lang = lang
        self.prompt = prompt


def get_response_link(db: Session, token: str) -> ResponseLinkView:
    message = _find_outbound_message(db, token)
    now = dt.datetime.now(dt.timezone.utc)
    if (
        message is None
        or message.response_token_expires_at is None
        or message.response_token_expires_at < now
        or message.response_token_consumed_at is not None
    ):
        raise ResponseLinkExpiredError()
    thread = db.get(Thread, message.thread_id) if message.thread_id else None
    worker = db.get(Worker, thread.worker_id) if thread is not None else None
    prompt = message.body_original or message.body_ko or ""
    return ResponseLinkView(thread_id=message.thread_id, worker=worker, lang=message.lang, prompt=prompt)


def ingest_inbound_reply(
    db: Session,
    *,
    company_id: str,
    thread_id: str,
    lang: str | None,
    body_original: str,
    confidence: str,
    summary_ko: str,
    source: str,
    case_id: str | None = None,
    resolve_case_from_thread: bool = True,
) -> Interpretation:
    """인바운드 정규화의 단일 지점 — 응답 링크·Zalo webhook(stage ④) 모두 이 함수로 합류한다
    (§3 "인바운드 소스가 응답 링크든 webhook이든 그 다음 단계는 동일하다"). thread_messages
    (direction='inbound') 생성 → N02(worker_reply_received) → M6 Interpretation(proposed)까지
    한 트랜잭션으로 커밋한다. `summary_ko`/evidence summary는 호출부가 이미 원문을 제외하고
    구성해서 넘겨야 한다(GOTCHAS §3 — 이 함수는 원문을 재검사하지 않는다)."""
    now = dt.datetime.now(dt.timezone.utc)
    thread = db.get(Thread, thread_id)

    inbound = ThreadMessage(
        id=new_id(),
        thread_id=thread_id,
        company_id=company_id,
        direction="inbound",
        case_id=case_id,
        lang=lang,
        body_original=body_original,
        received_at=now,
    )
    db.add(inbound)
    if thread is not None:
        thread.last_message_at = now
    db.flush()

    resolved_case_id = case_id
    if resolved_case_id is None and resolve_case_from_thread:
        resolved_case_id = _resolve_case_id(db, company_id, thread_id)
        inbound.case_id = resolved_case_id
    interpretation = Interpretation(
        id=new_id(),
        company_id=company_id,
        thread_message_id=inbound.id,
        case_id=resolved_case_id,
        summary_ko=summary_ko,
        confidence=confidence,
        status="proposed",
    )
    db.add(interpretation)
    db.flush()

    event_no = next_event_no(db, company_id)
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=company_id,
            event_no=event_no,
            type="worker_reply_received",
            at=now,
            case_id=resolved_case_id,
            actor_type="system",
            actor_display=f"근로자 응답({source})",
            summary=f"근로자 응답 수신 · {source}",
        )
    )
    db.commit()
    db.refresh(interpretation)
    return interpretation


def submit_response(db: Session, token: str, *, choice: str | None, free_text: str | None) -> Interpretation:
    free_text = free_text.strip() if free_text else None
    if not choice and not free_text:
        raise ResponseLinkNoContentError()
    if choice and choice not in RESPONSE_CHOICES:
        raise ResponseLinkInvalidChoiceError()

    message = _lock_outbound_message(db, token)
    now = dt.datetime.now(dt.timezone.utc)
    if message is None or message.response_token_expires_at is None or message.response_token_expires_at < now:
        raise ResponseLinkExpiredError()
    if message.response_token_consumed_at is not None:
        raise ResponseLinkAlreadySubmittedError()
    if message.thread_id is None:
        raise ResponseLinkExpiredError()

    # This update and the inbound/evidence write below share one transaction.  The
    # row lock makes a second concurrent POST observe the committed consumption.
    message.response_token_consumed_at = now

    thread = db.get(Thread, message.thread_id)
    worker = db.get(Worker, thread.worker_id) if thread is not None else None
    lang = (worker.preferred_language if worker else None) or message.lang

    choice_label = RESPONSE_CHOICES.get(choice) if choice else None
    # 원문은 스레드 상세 전용(body_original) — evidence·summary에는 절대 복사하지 않는다(§3, GOTCHAS §3).
    body_original = " / ".join(part for part in (choice_label, free_text) if part)
    # confidence: 버튼 선택(구조화 응답)은 high, 자유 입력만 있으면 low(1단계 M6 원칙 — 해석이
    # 불확실하면 low로 두고 "원문을 확인해주세요" 안내를 프론트가 붙인다).
    confidence = "high" if choice_label else "low"
    summary_ko = (
        f"근로자 응답 수신 · {choice_label}"
        if choice_label
        else "근로자 응답 수신 · 자유 입력(원문은 스레드에서 확인)"
    )

    return ingest_inbound_reply(
        db,
        company_id=message.company_id,
        thread_id=message.thread_id,
        lang=lang,
        body_original=body_original,
        confidence=confidence,
        summary_ko=summary_ko,
        source="응답 링크",
        case_id=message.case_id,
        # Older outbound rows may not carry case_id.  Do not guess from a newer
        # outbox row and misattribute that historical reply.
        resolve_case_from_thread=False,
    )
