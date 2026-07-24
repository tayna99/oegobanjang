"""POST /api/v1/outbox("실행 확인") · GET /api/v1/outbox(조회) — 발송 대기열. R3 stage ②.

MESSAGING_CHANNELS.md §1 각주² — 승인(human_approved)과 실행은 같은 순간이 아니다. 이
엔드포인트가 그 "실행 확인"(manager 1탭)의 실제 진입점이다. DispatchQueuePage의 real-mode
"발송 실행" 버튼이 이 엔드포인트를 호출한다(src/lib/api/outbox.ts).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, get_current_user_id
from app.db.session import get_db
from app.domain.outbox_exceptions import (
    OutboxActionNotFoundError,
    OutboxActionTypeNotSupportedError,
    OutboxAlreadyQueuedError,
    OutboxApprovalNotApprovedError,
    OutboxError,
    OutboxForbiddenError,
    OutboxNoContentError,
    OutboxNoThreadError,
    OutboxReminderCooldownError,
    OutboxResendNotEligibleError,
    OutboxWorkerMissingError,
)
from app.models.membership import Membership
from app.schemas.outbox import OutboxDispatchRequest, OutboxOut
from app.services.outbox import create_and_dispatch, list_outbox

router = APIRouter(prefix="/api/v1/outbox", tags=["outbox"])

_ERROR_STATUS: dict[type[OutboxError], int] = {
    OutboxActionNotFoundError: status.HTTP_404_NOT_FOUND,
    OutboxForbiddenError: status.HTTP_403_FORBIDDEN,
    OutboxActionTypeNotSupportedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    OutboxApprovalNotApprovedError: status.HTTP_403_FORBIDDEN,
    OutboxAlreadyQueuedError: status.HTTP_409_CONFLICT,
    OutboxWorkerMissingError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    OutboxNoThreadError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    OutboxNoContentError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    OutboxReminderCooldownError: status.HTTP_409_CONFLICT,
    OutboxResendNotEligibleError: status.HTTP_409_CONFLICT,
}


@router.post("", response_model=OutboxOut, status_code=status.HTTP_201_CREATED)
async def dispatch_outbox_item(
    payload: OutboxDispatchRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OutboxOut:
    try:
        item = await create_and_dispatch(
            db, current_user_id, payload.action_id, event_type=payload.event_type, threshold=payload.threshold
        )
    except OutboxError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return OutboxOut.model_validate(item)


@router.get("", response_model=list[OutboxOut])
def get_outbox(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[OutboxOut]:
    return [OutboxOut.model_validate(item) for item in list_outbox(db, membership.company_id)]
