"""행정사 패키지 무인증 열람 링크 — POST(발급/재발급, 인증)·GET(열람, 무인증) /api/v1/packages/{case_id}/link (R2.6).

GET은 로그인 없이 접근하는 유일한 엔드포인트다(ExpertLinkPage와 동일한 무인증 전제) — 이
파일의 `view_link`만 `get_current_membership`을 거치지 않는다. 나머지 화면(패키지 문서
콘텐츠)은 여전히 프론트 mock(mocks/packages.ts)이 렌더한다 — 여기서는 링크 유효성만 다룬다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.domain.package_exceptions import (
    PackageCaseNotFoundError,
    PackageError,
    PackageForbiddenError,
    PackageLinkNotFoundError,
)
from app.models.handoff import HandoffPackage
from app.models.membership import Membership
from app.schemas.package import PackageLinkStatus
from app.services.packages import issue_package_link, view_package_link

router = APIRouter(prefix="/api/v1/packages", tags=["packages"])

_ERROR_STATUS: dict[type[PackageError], int] = {
    PackageForbiddenError: status.HTTP_403_FORBIDDEN,
    PackageCaseNotFoundError: status.HTTP_404_NOT_FOUND,
    PackageLinkNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _to_status(pkg: HandoffPackage) -> PackageLinkStatus:
    assert pkg.link_issued_at is not None and pkg.link_expires_at is not None
    return PackageLinkStatus(case_id=pkg.case_id, issued_at=pkg.link_issued_at, expires_at=pkg.link_expires_at)


@router.post("/{case_id}/link", response_model=PackageLinkStatus, status_code=status.HTTP_201_CREATED)
def issue_link(
    case_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> PackageLinkStatus:
    try:
        pkg = issue_package_link(db, membership, case_id)
    except PackageError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return _to_status(pkg)


@router.get("/{case_id}/link", response_model=PackageLinkStatus)
def view_link(case_id: str, db: Session = Depends(get_db)) -> PackageLinkStatus:
    try:
        pkg = view_package_link(db, case_id)
    except PackageError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return _to_status(pkg)
