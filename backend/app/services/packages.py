"""행정사 패키지 무인증 열람 링크 — 발급/재발급/열람 검증. R2.6, docs/DB_SCHEMA.md §4.8.

패키지 문서 콘텐츠(검토 요청서 본문·항목 토글 등)는 이 범위에 없다 — 프론트가 기존 mock
콘텐츠(mocks/packages.ts)를 그대로 렌더하고, 여기서는 "링크가 살아있는가"만 서버가
검증하고 발급/열람을 evidence로 남긴다(§4.5 R2.5 노트 — 무인증 이벤트는 여기서 직접 기록,
services/evidence.py의 일반 엔드포인트를 거치지 않는다).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.package_exceptions import (
    PackageCaseNotFoundError,
    PackageForbiddenError,
    PackageLinkNotFoundError,
)
from app.models.case import Case
from app.models.evidence import EvidenceEvent
from app.models.handoff import HandoffPackage
from app.models.membership import Membership
from app.models.user import User
from app.services.evidence import next_event_no

LINK_VALIDITY = dt.timedelta(days=7)  # 7단계 §4 "만료형(기본 7일)" — src/lib/packageLink.ts와 동일
ISSUER_ROLES = ("owner", "manager")


def _latest_package_for_case(db: Session, case_id: str) -> HandoffPackage | None:
    return db.execute(
        select(HandoffPackage).where(HandoffPackage.case_id == case_id).order_by(HandoffPackage.created_at.desc())
    ).scalars().first()


def issue_package_link(db: Session, membership: Membership, case_id: str) -> HandoffPackage:
    """get-or-create + 발급/재발급(같은 엔드포인트가 둘 다 처리 — 항상 유효기간을 새로 연다)."""
    if membership.role not in ISSUER_ROLES:
        raise PackageForbiddenError()

    case = db.execute(
        select(Case).where(Case.company_id == membership.company_id, Case.id == case_id)
    ).scalar_one_or_none()
    if case is None:
        raise PackageCaseNotFoundError(case_id)

    pkg = _latest_package_for_case(db, case_id)
    is_reissue = pkg is not None
    now = dt.datetime.now(dt.timezone.utc)

    if pkg is None:
        # 문서 콘텐츠를 만들지 않는다 — masked_payload는 NOT NULL 제약만 충족하는 최소 레코드.
        # status는 반드시 'draft'(+approval_id NULL)로 시작해야 한다(trg_handoff_approval_state_insert) —
        # 이 패키지는 내부 승인·PDF 내보내기 플로우(PackagePage)와 무관하게 링크 발급 전용이라
        # approved/exported로 승격할 근거(승인된 create_handoff)가 없다.
        pkg = HandoffPackage(
            id=new_id(),
            company_id=membership.company_id,
            case_id=case_id,
            package_type="expert_review",
            masked_payload={"case_id": case_id},
            status="draft",
        )
        db.add(pkg)

    pkg.link_issued_at = now
    pkg.link_expires_at = now + LINK_VALIDITY
    db.flush()

    user = db.get(User, membership.user_id)
    event_no = next_event_no(db, membership.company_id)
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=membership.company_id,
            event_no=event_no,
            type="package_link_issued",
            at=now,
            case_id=case_id,
            actor_type="user",
            actor_user_id=membership.user_id,
            actor_display=user.name if user else None,
            summary="행정사 패키지 링크 재발급" if is_reissue else "행정사 패키지 링크 발급",
        )
    )

    db.commit()
    db.refresh(pkg)
    return pkg


def view_package_link(db: Session, case_id: str) -> HandoffPackage:
    """무인증 — case_id 자체가 비밀 링크(cases.id는 PK라 전역 유일, R2.3 cases.py와 동일
    신뢰 모델). 존재하지 않거나 만료됐으면 둘 다 같은 404(존재 비노출)."""
    pkg = _latest_package_for_case(db, case_id)
    now = dt.datetime.now(dt.timezone.utc)
    if pkg is None or pkg.link_expires_at is None or pkg.link_expires_at < now:
        raise PackageLinkNotFoundError()

    event_no = next_event_no(db, pkg.company_id)
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=pkg.company_id,
            event_no=event_no,
            type="package_link_viewed",
            at=now,
            case_id=case_id,
            actor_type="system",
            actor_display="외부 열람(행정사)",
            summary="외부 열람 · 행정사 패키지 링크",
        )
    )

    db.commit()
    db.refresh(pkg)
    return pkg
