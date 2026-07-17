"""GET /api/v1/threads(목록) · GET /api/v1/threads/{thread_id}(상세) — 컨택 스레드 읽기 API.

plans/NEXT_ROADMAP_2026-07-16.md §R2.3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.thread import ThreadDetailOut, ThreadOut
from app.services.threads import get_thread_detail_out, list_threads_out

router = APIRouter(prefix="/api/v1/threads", tags=["threads"])


@router.get("", response_model=list[ThreadOut])
def list_threads(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[ThreadOut]:
    return list_threads_out(db, membership.company_id)


@router.get("/{thread_id}", response_model=ThreadDetailOut)
def get_thread_detail(
    thread_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> ThreadDetailOut:
    detail = get_thread_detail_out(db, membership.company_id, thread_id)
    if detail is None:
        # 다른 회사 소속 스레드도 동일한 404 — 존재 여부를 노출하지 않는다.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "스레드를 찾을 수 없습니다")
    return detail
