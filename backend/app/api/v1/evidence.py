"""판단 기록(evidence_events) 일반 기록/조회 엔드포인트 — POST/GET /api/v1/evidence(R2.5).

approval_decided 등 도메인 전용 이벤트는 각자의 도메인 트랜잭션(services/approvals.py 등)이
직접 기록한다 — 이 엔드포인트는 그 외 화면(RBAC·해석 확인·발송 실행 등)이 개별 도메인
엔드포인트 없이도 감사 기록을 남길 수 있게 하는 범용 통로다. 무인증 패키지 링크 이벤트
(package_link_issued/viewed, package_reply)는 여기서 받지 않는다 — api/v1/packages.py 참조.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.domain.evidence_exceptions import (
    EvidenceCaseNotFoundError,
    EvidenceError,
    EvidenceInvalidTypeError,
    EvidenceReasonContainsPiiError,
)
from app.models.membership import Membership
from app.schemas.evidence import EvidenceEventCreate, EvidenceEventOut
from app.services.evidence import create_evidence_event, list_evidence_events

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])

_ERROR_STATUS: dict[type[EvidenceError], int] = {
    EvidenceInvalidTypeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EvidenceReasonContainsPiiError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EvidenceCaseNotFoundError: status.HTTP_404_NOT_FOUND,
}


@router.post("", response_model=EvidenceEventOut, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceEventCreate,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> EvidenceEventOut:
    try:
        event = create_evidence_event(db, membership, payload)
    except EvidenceError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return EvidenceEventOut.model_validate(event)


@router.get("", response_model=list[EvidenceEventOut])
def list_evidence(
    case_id: str | None = None,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[EvidenceEventOut]:
    events = list_evidence_events(db, membership.company_id, case_id)
    return [EvidenceEventOut.model_validate(e) for e in events]
