"""행정사 패키지 무인증 열람 링크 — 발급/재발급/열람 검증. R2.6, docs/DB_SCHEMA.md §4.8.

패키지 문서 콘텐츠(검토 요청서 본문·항목 토글 등)는 이 범위에 없다 — 프론트가 기존 mock
콘텐츠(mocks/packages.ts)를 그대로 렌더하고, 여기서는 "링크가 살아있는가"만 서버가
검증하고 발급/열람을 evidence로 남긴다(§4.5 R2.5 노트 — 무인증 이벤트는 여기서 직접 기록,
services/evidence.py의 일반 엔드포인트를 거치지 않는다).
"""

from __future__ import annotations

import datetime as dt
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.expert_exceptions import ExpertPackageNotFoundError
from app.domain.package_exceptions import (
    PackageCaseNotFoundError,
    PackageForbiddenError,
    PackageLinkNotFoundError,
    PackageNotApprovedError,
)
from app.models.approval import Approval
from app.models.case import Case, NextAction
from app.models.evidence import EvidenceEvent
from app.models.expert import ExpertOfficeMember, PackageViewLog
from app.models.handoff import HandoffPackage
from app.models.membership import Membership
from app.models.user import User
from app.services.evidence import next_event_no
from app.services.expert import resolve_expert_allowed_tenant_ids

LINK_VALIDITY = dt.timedelta(days=7)  # 7단계 §4 "만료형(기본 7일)" — src/lib/packageLink.ts와 동일
ISSUER_ROLES = ("owner", "manager")
HANDOFF_ACTION_TYPE = "create_handoff"

# R5.1 — 화이트라벨 세션 뷰(spec §4.2)의 승인 게이트. GOTCHAS.md §2 상태머신:
# draft → risk_review → approval_pending → human_approved → completed. "human_approved
# 이상"만 허용 — 그 앞 단계는 아직 외부 노출 승인이 나지 않은 상태다.
_EXPERT_VIEW_ALLOWED_CASE_STATES = ("human_approved", "completed")


def _latest_package_for_case(db: Session, case_id: str) -> HandoffPackage | None:
    return db.execute(
        select(HandoffPackage).where(HandoffPackage.case_id == case_id).order_by(HandoffPackage.created_at.desc())
    ).scalars().first()


def _has_approved_handoff(db: Session, company_id: str, case_id: str) -> bool:
    """코드리뷰 지적(PR #20 P1): 링크 발급은 "행정사/노무사에게 패키지 전달"에 해당하는
    승인 필요 작업(AGENTS.md §8)인데, 서버가 케이스의 승인 상태를 전혀 확인하지 않아
    승인 전에도(심지어 승인 요청조차 없어도) 외부 열람 링크가 발급됐다. handoff_packages
    상태 트리거(db/schema.sql trg_handoff_approval_state_update)가 이미 "approved/exported는
    승인된 create_handoff가 있어야 한다"는 계약을 강제하고 있으므로, 같은 조건을 링크
    발급 전제조건으로 재사용한다."""
    return (
        db.execute(
            select(Approval.id)
            .join(NextAction, NextAction.id == Approval.action_id)
            .where(
                Approval.company_id == company_id,
                Approval.case_id == case_id,
                Approval.status == "approved",
                NextAction.action_type == HANDOFF_ACTION_TYPE,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _generate_link_token() -> str:
    # 코드리뷰 지적(PR #20 P1): case_id(cases.id, PK)를 공개 링크의 비밀값으로 쓰면 값이
    # 영구 불변이라 재발급으로도 기존 유출 링크를 회수할 수 없었다 — 발급/재발급마다 새로
    # 회전하는, case_id와 무관한 무작위 토큰을 대신 발급한다.
    return secrets.token_urlsafe(32)


def issue_package_link(db: Session, membership: Membership, case_id: str) -> HandoffPackage:
    """get-or-create + 발급/재발급(같은 엔드포인트가 둘 다 처리 — 항상 유효기간을 새로 연다)."""
    if membership.role not in ISSUER_ROLES:
        raise PackageForbiddenError()

    case = db.execute(
        select(Case).where(Case.company_id == membership.company_id, Case.id == case_id)
    ).scalar_one_or_none()
    if case is None:
        raise PackageCaseNotFoundError(case_id)

    # 코드리뷰 지적(PR #20 P1): 링크 발급은 "행정사에게 패키지 전달"이라 AGENTS.md §8이
    # 요구하는 사전 승인 없이는 절대 실행돼선 안 되는 작업이다 — 케이스가 아직 create_handoff
    # 승인을 받지 못했으면(요청조차 없어도) 여기서 막는다.
    if not _has_approved_handoff(db, membership.company_id, case_id):
        raise PackageNotApprovedError(case_id)

    pkg = _latest_package_for_case(db, case_id)
    is_reissue = pkg is not None
    now = dt.datetime.now(dt.timezone.utc)

    if pkg is None:
        # 문서 콘텐츠를 만들지 않는다 — masked_payload는 NOT NULL 제약만 충족하는 최소 레코드.
        # status는 반드시 'draft'(+approval_id NULL)로 시작해야 한다(trg_handoff_approval_state_insert) —
        # 이 북키핑 레코드 자체는 내부 승인·PDF 내보내기 플로우(PackagePage)의 상태 머신과
        # 별개로 유지한다(위 _has_approved_handoff가 "승인된 create_handoff가 존재하는가"를
        # 별도로 보증하므로, 이 레코드를 굳이 그 승인에 묶어 approved로 승격시킬 필요가 없다).
        pkg = HandoffPackage(
            id=new_id(),
            company_id=membership.company_id,
            case_id=case_id,
            package_type="expert_review",
            masked_payload={"case_id": case_id},
            status="draft",
        )
        db.add(pkg)

    pkg.link_token = _generate_link_token()
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


def view_expert_package(db: Session, member: ExpertOfficeMember, package_id: str) -> tuple[HandoffPackage, dt.datetime]:
    """GET /api/v1/expert/packages/{package_id} — 화이트라벨 세션 뷰(R5.1, spec §4.2).

    무인증 단발 링크(위 view_package_link)와는 별개 경로다 — 이쪽은 로그인한
    ExpertOfficeMember의 상시 셀프서비스 조회이고, 열람 감사 로그는 evidence_events가
    아니라 PackageViewLog에 남긴다(spec §6.1/§6.2 — "이 사람이 봤다"까지 추적해야 하는
    목적이 다르므로 테이블도 분리). 3중 체크(scope + 사무소 일치 + 승인 게이트) 중 하나라도
    실패하면 전부 동일한 404 하나로 응답한다(존재 비노출 원칙).

    문서 콘텐츠는 반환하지 않는다 — view_package_link와 동일한 R2.6 스코프 경계(§4.5 노트):
    여기서는 "조회 자격이 있는가"만 서버가 확정하고 기록한다.
    """
    allowed_tenant_ids = resolve_expert_allowed_tenant_ids(db, member)

    pkg = db.get(HandoffPackage, package_id)
    if pkg is None:
        raise ExpertPackageNotFoundError()
    if pkg.company_id not in allowed_tenant_ids:
        raise ExpertPackageNotFoundError()
    if pkg.expert_account_id is None or pkg.expert_account_id != member.expert_account_id:
        raise ExpertPackageNotFoundError()

    case = db.execute(
        select(Case).where(Case.company_id == pkg.company_id, Case.id == pkg.case_id)
    ).scalar_one_or_none()
    if case is None or case.state not in _EXPERT_VIEW_ALLOWED_CASE_STATES:
        raise ExpertPackageNotFoundError()

    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        PackageViewLog(
            id=new_id(),
            package_id=pkg.id,
            tenant_id=pkg.company_id,
            expert_office_member_id=member.id,
            viewed_at=now,
        )
    )
    db.commit()
    db.refresh(pkg)
    return pkg, now


def view_package_link(db: Session, link_token: str) -> HandoffPackage:
    """무인증 — link_token(발급/재발급마다 회전하는 무작위 값)이 유일한 자격 증명이다.
    코드리뷰 지적(PR #20 P1): 이전엔 case_id(PK, 불변)를 비밀로 썼는데, 재발급이 이 값을
    바꾸지 않아 한 번 유출된 링크를 영구히 회수할 수 없었다 — 이제 재발급마다 새 토큰이
    발급되므로 이전 토큰은 즉시 무효(아래 조회가 실패)가 된다. 존재하지 않거나 만료됐으면
    둘 다 같은 404(존재 비노출)."""
    pkg = db.execute(select(HandoffPackage).where(HandoffPackage.link_token == link_token)).scalar_one_or_none()
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
            case_id=pkg.case_id,
            actor_type="system",
            actor_display="외부 열람(행정사)",
            summary="외부 열람 · 행정사 패키지 링크",
        )
    )

    db.commit()
    db.refresh(pkg)
    return pkg
