"""FastAPI 공용 의존성 — 인증된 세션에서 신원·소속을 도출한다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth_exceptions import SessionInvalidError
from app.models.membership import Membership
from app.services.auth import get_active_membership, resolve_session_user_id

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
    """R2.3 — 읽기 API의 회사 스코프 근거. 활성 소속이 없으면 403(현재 시드·프론트 모두
    1인 1사 전제라 여러 건이어도 get_active_membership이 하나만 반환한다)."""
    membership = get_active_membership(db, current_user_id)
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "소속된 회사가 없습니다")
    return membership
