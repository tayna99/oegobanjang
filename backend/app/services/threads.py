"""threads 도메인 읽기 서비스 — 회사 스코프 스레드 목록·상세 조립. plans/NEXT_ROADMAP_2026-07-16.md §R2.3.

읽기 전용(조회만) — 상태 전이·트랜잭션 관심사가 없어 approvals.py 같은 커밋 경계는 없다.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.interpretation import Interpretation
from app.models.thread import Thread, ThreadMessage
from app.models.worker import Worker
from app.schemas.thread import (
    InterpretationOut,
    MessageOut,
    ThreadDetailOut,
    ThreadOut,
    ThreadWorkerOut,
)


def _worker_out(worker: Worker | None) -> ThreadWorkerOut | None:
    return ThreadWorkerOut.model_validate(worker) if worker is not None else None


def list_threads_out(db: Session, company_id: str) -> list[ThreadOut]:
    """company_id로 스코프된 스레드 전체를 last_message_at 내림차순으로 조회한다."""
    threads = db.execute(
        select(Thread).where(Thread.company_id == company_id).order_by(Thread.last_message_at.desc())
    ).scalars().all()
    if not threads:
        return []

    worker_ids = {t.worker_id for t in threads}
    workers_by_id = {
        w.id: w
        for w in db.execute(
            select(Worker).where(Worker.company_id == company_id, Worker.id.in_(worker_ids))
        ).scalars().all()
    }

    thread_ids = [t.id for t in threads]
    counts_by_thread_id = dict(
        db.execute(
            select(ThreadMessage.thread_id, func.count(ThreadMessage.id))
            .where(ThreadMessage.company_id == company_id, ThreadMessage.thread_id.in_(thread_ids))
            .group_by(ThreadMessage.thread_id)
        ).all()
    )
    latest_status_by_thread_id = _latest_interpretation_status_by_thread_id(db, company_id, thread_ids)

    return [
        ThreadOut(
            id=thread.id,
            worker=_worker_out(workers_by_id.get(thread.worker_id)),
            channel=thread.channel,
            last_message_at=thread.last_message_at,
            message_count=counts_by_thread_id.get(thread.id, 0),
            latest_interpretation_status=latest_status_by_thread_id.get(thread.id),
        )
        for thread in threads
    ]


def _latest_interpretation_status_by_thread_id(
    db: Session, company_id: str, thread_ids: list[str]
) -> dict[str, str]:
    """스레드별 "가장 최근 메시지에 달린 해석"의 status 1건 — 목록(ThreadOut)의 배지·정렬
    근거(코드리뷰 지적: 목록이 interpretation_status를 안 내려 real 모드에서 응답 도착 배지·
    정렬이 항상 죽어 있었다). get_thread_detail_out의 프론트 대응 로직(threads.ts
    toThreadDetail — 메시지 역순 순회로 해석 있는 첫 메시지를 찾음)과 동일한 우선순위를
    서버에서 재현한다: 메시지 최신순, 동일 메시지에 재해석이 여러 건이면 그중 최신 해석.
    """
    if not thread_ids:
        return {}
    ranked = (
        select(
            ThreadMessage.thread_id,
            Interpretation.status,
            func.row_number()
            .over(
                partition_by=ThreadMessage.thread_id,
                order_by=(ThreadMessage.created_at.desc(), Interpretation.created_at.desc()),
            )
            .label("rn"),
        )
        .join(Interpretation, Interpretation.thread_message_id == ThreadMessage.id)
        .where(ThreadMessage.company_id == company_id, ThreadMessage.thread_id.in_(thread_ids))
        .subquery()
    )
    rows = db.execute(select(ranked.c.thread_id, ranked.c.status).where(ranked.c.rn == 1)).all()
    return dict(rows)


def get_thread_detail_out(db: Session, company_id: str, thread_id: str) -> ThreadDetailOut | None:
    """company_id+thread_id로 스레드 1건을 조회한다. 없으면(다른 회사 소속 포함) None —
    호출부(라우터)가 존재 여부를 노출하지 않도록 404로 변환한다."""
    thread = db.execute(
        select(Thread).where(Thread.company_id == company_id, Thread.id == thread_id)
    ).scalar_one_or_none()
    if thread is None:
        return None

    worker = db.execute(
        select(Worker).where(Worker.company_id == company_id, Worker.id == thread.worker_id)
    ).scalar_one_or_none()

    messages = db.execute(
        select(ThreadMessage)
        .where(ThreadMessage.company_id == company_id, ThreadMessage.thread_id == thread_id)
        .order_by(ThreadMessage.created_at)
    ).scalars().all()

    interpretations_by_message_id: dict[str, Interpretation] = {}
    if messages:
        message_ids = [m.id for m in messages]
        for interpretation in db.execute(
            select(Interpretation)
            .where(
                Interpretation.company_id == company_id,
                Interpretation.thread_message_id.in_(message_ids),
            )
            .order_by(Interpretation.created_at)
        ).scalars().all():
            # 메시지당 해석이 여러 건이면(재해석 등) 가장 최근 것을 남긴다(created_at 오름차순 순회).
            interpretations_by_message_id[interpretation.thread_message_id] = interpretation

    message_outs = [
        MessageOut(
            id=message.id,
            direction=message.direction,
            channel=thread.channel,
            lang=message.lang,
            body_original=message.body_original,
            body_ko=message.body_ko,
            received_at=message.received_at,
            created_at=message.created_at,
            interpretation=(
                InterpretationOut.model_validate(interpretations_by_message_id[message.id])
                if message.id in interpretations_by_message_id
                else None
            ),
        )
        for message in messages
    ]

    return ThreadDetailOut(
        id=thread.id,
        worker=_worker_out(worker),
        channel=thread.channel,
        messages=message_outs,
    )
