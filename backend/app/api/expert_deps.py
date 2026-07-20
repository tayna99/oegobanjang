"""화이트라벨 세션 의존성 — app/api/deps.py(get_current_membership)의 expert 대칭.

내부 세션(Bearer <session_token> → users/memberships)과 별개 스킴이다 — 같은 Authorization
헤더 형태를 쓰지만 토큰 네임스페이스가 다르다(expert_sessions.token_hash). 한 요청이 두
스킴을 섞어 쓸 수 없다(각 라우터가 자기 스킴의 의존성만 문다).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.expert_exceptions import ExpertSessionInvalidError
from app.models.expert import ExpertOfficeMember
from app.services.expert import resolve_expert_session_member

_expert_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_expert_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(_expert_bearer_scheme),
    db: Session = Depends(get_db),
) -> ExpertOfficeMember:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증이 필요합니다")
    try:
        return resolve_expert_session_member(db, credentials.credentials)
    except ExpertSessionInvalidError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
