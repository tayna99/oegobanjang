"""FastAPI 공용 의존성 — 인증된 세션에서 신원을 도출한다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth_exceptions import SessionInvalidError
from app.models.membership import Membership
from app.services.auth import resolve_session_user_id

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증이 필요합니다")
    try:
        return resolve_session_user_id(db, credentials.credentials)
    except SessionInvalidError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc


def get_current_membership(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Membership:
    """읽기 API의 테넌트 해석(§13-13) — 세션 사용자의 active membership이 정확히 1개면 그
    회사로 스코프한다. 0개면 소속 없음(403), 2개 이상이면 멀티 회사 선택 미구현(400,
    MVP 한계 — 회사 선택 UI는 후속). 모든 active 역할(viewer 포함)이 읽기를 통과한다."""
    memberships = db.execute(
        select(Membership).where(Membership.user_id == current_user_id, Membership.status == "active")
    ).scalars().all()
    if not memberships:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "소속된 회사가 없습니다")
    if len(memberships) > 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "다중 회사 소속은 아직 지원하지 않습니다")
    return memberships[0]
