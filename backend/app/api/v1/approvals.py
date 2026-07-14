"""승인 결정 엔드포인트 — 케이스(액션) 단위 단건 처리만 존재한다.

일괄 승인 API는 만들지 않는다(GOTCHAS §3, PC §3a 각주 비준) — 이 라우터에
batch/bulk 계열 엔드포인트를 추가하지 않는 것 자체가 그 규칙의 집행이다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.exceptions import (
    ApprovalAlreadyDecidedError,
    ApprovalBlockedByEvidenceError,
    ApprovalChecklistIncompleteError,
    ApprovalError,
    ApprovalForbiddenError,
    ApprovalIdempotencyKeyReusedError,
    ApprovalIdentityRequiredError,
    ApprovalNotFoundError,
    ApprovalReasonContainsPiiError,
    ApprovalReasonRequiredError,
    CaseTransitionError,
)
from app.schemas.approval import ApprovalDecisionRequest, ApprovalDecisionResponse, ApprovalOut
from app.services.approvals import decide_approval

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

_ERROR_STATUS: dict[type[ApprovalError], int] = {
    ApprovalNotFoundError: status.HTTP_404_NOT_FOUND,
    ApprovalAlreadyDecidedError: status.HTTP_409_CONFLICT,
    ApprovalIdempotencyKeyReusedError: status.HTTP_409_CONFLICT,
    CaseTransitionError: status.HTTP_409_CONFLICT,
    ApprovalForbiddenError: status.HTTP_403_FORBIDDEN,
    ApprovalBlockedByEvidenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalChecklistIncompleteError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalIdentityRequiredError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalReasonRequiredError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ApprovalReasonContainsPiiError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _run_decision(
    db: Session, approval_id: str, decision: str, payload: ApprovalDecisionRequest
) -> ApprovalDecisionResponse:
    try:
        approval, case_state = decide_approval(db, approval_id, decision, payload)
    except ApprovalError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return ApprovalDecisionResponse(approval=ApprovalOut.model_validate(approval), case_state=case_state)


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
def approve_approval(
    approval_id: str, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)
) -> ApprovalDecisionResponse:
    return _run_decision(db, approval_id, "approved", payload)


@router.post("/{approval_id}/reject", response_model=ApprovalDecisionResponse)
def reject_approval(
    approval_id: str, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)
) -> ApprovalDecisionResponse:
    return _run_decision(db, approval_id, "rejected", payload)
