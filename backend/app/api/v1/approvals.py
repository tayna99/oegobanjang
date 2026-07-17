"""승인 결정·요청 엔드포인트 — 케이스(액션) 단위 단건 처리만 존재한다.

일괄 승인 API는 만들지 않는다(GOTCHAS §3, PC §3a 각주 비준) — 이 라우터에
batch/bulk 계열 엔드포인트를 추가하지 않는 것 자체가 그 규칙의 집행이다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.domain.exceptions import (
    ApprovalActionNotRequestableError,
    ApprovalAlreadyDecidedError,
    ApprovalAlreadyPendingError,
    ApprovalBlockedByEvidenceError,
    ApprovalChecklistIncompleteError,
    ApprovalDelegationInvalidError,
    ApprovalError,
    ApprovalForbiddenError,
    ApprovalIdempotencyKeyReusedError,
    ApprovalIdentityRequiredError,
    ApprovalNotFoundError,
    ApprovalPinInvalidError,
    ApprovalReasonContainsPiiError,
    ApprovalReasonRequiredError,
    CaseTransitionError,
)
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalOut,
    ApprovalRequestCreate,
)
from app.services.approvals import decide_approval, request_approval

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

_ERROR_STATUS: dict[type[ApprovalError], int] = {
    ApprovalNotFoundError: status.HTTP_404_NOT_FOUND,
    ApprovalAlreadyDecidedError: status.HTTP_409_CONFLICT,
    ApprovalAlreadyPendingError: status.HTTP_409_CONFLICT,
    ApprovalIdempotencyKeyReusedError: status.HTTP_409_CONFLICT,
    CaseTransitionError: status.HTTP_409_CONFLICT,
    ApprovalForbiddenError: status.HTTP_403_FORBIDDEN,
    ApprovalDelegationInvalidError: status.HTTP_403_FORBIDDEN,
    ApprovalActionNotRequestableError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalBlockedByEvidenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalChecklistIncompleteError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalIdentityRequiredError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalPinInvalidError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalReasonRequiredError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalReasonContainsPiiError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _run_decision(
    db: Session, approval_id: str, decision: str, payload: ApprovalDecisionRequest, decided_by_user_id: str
) -> ApprovalDecisionResponse:
    try:
        approval, case_state = decide_approval(db, approval_id, decision, payload, decided_by_user_id)
    except ApprovalError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return ApprovalDecisionResponse(approval=ApprovalOut.model_validate(approval), case_state=case_state)


@router.post("", response_model=ApprovalDecisionResponse, status_code=status.HTTP_201_CREATED)
def create_approval_request(
    payload: ApprovalRequestCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    try:
        approval, case_state = request_approval(db, payload.action_id, current_user_id)
    except ApprovalError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return ApprovalDecisionResponse(approval=ApprovalOut.model_validate(approval), case_state=case_state)


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
def approve_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    return _run_decision(db, approval_id, "approved", payload, current_user_id)


@router.post("/{approval_id}/reject", response_model=ApprovalDecisionResponse)
def reject_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    return _run_decision(db, approval_id, "rejected", payload, current_user_id)
