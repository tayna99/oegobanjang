"""행정사 화이트라벨 v1 서비스(R5.1) — 위탁(Grant) 생애주기 + 사무소 구성원 CRUD +
email+OTP 세션 로그인. spec: reference/specs/7-1_행정사_화이트라벨_v1.md §3/§5/§7.

패키지 조회(3중 체크 + PackageViewLog 기록)는 이 파일이 아니라 services/packages.py에
있다 — spec §4.2가 다루는 대상이 HandoffPackage 도메인이라 그 파일의 기존 관례(승인
게이트·evidence 통합)를 따르는 것이 "재발명 금지"에 맞다(task 지시 — packages.py를
확장하되 중복 구현하지 않는다).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.auth_tokens import generate_otp_code, generate_session_token, hash_secret, secrets_match
from app.domain.expert_exceptions import (
    ExpertGrantForbiddenError,
    ExpertGrantInvalidTransitionError,
    ExpertGrantNotFoundError,
    ExpertGrantUnboundedError,
    ExpertMemberNotRegisteredError,
    ExpertMemberSuspendedError,
    ExpertOfficeMemberForbiddenError,
    ExpertOfficeMemberNotFoundError,
    ExpertOtpAttemptsExceededError,
    ExpertOtpCodeMismatchError,
    ExpertOtpExpiredError,
    ExpertOtpNotFoundError,
    ExpertSessionInvalidError,
)
from app.models.evidence import EvidenceEvent
from app.models.expert import (
    ExpertAccount,
    ExpertGrant,
    ExpertLoginOtp,
    ExpertOfficeMember,
    ExpertSession,
)
from app.models.membership import Membership
from app.models.user import User
from app.schemas.expert import ExpertGrantIssueRequest, ExpertOfficeMemberCreateRequest, ExpertOfficeMemberUpdateRequest
from app.services.evidence import next_event_no

ISSUER_ROLES = ("owner", "manager")
GRANT_TERMINAL_STATUSES = ("expired", "revoked")
GRANT_LIVE_STATUSES = ("invited", "company_authorized", "active")

OTP_TTL = dt.timedelta(minutes=5)
OTP_REQUEST_COOLDOWN = dt.timedelta(seconds=30)
MAX_OTP_ATTEMPTS = 5
SESSION_TTL = dt.timedelta(hours=12)  # 화이트라벨 세션 — 내부 세션(30일)보다 짧게(spec §3.3 idle 취지)


def _company_scoped(db: Session, company_id: str, grant_id: str) -> ExpertGrant:
    grant = db.execute(
        select(ExpertGrant).where(ExpertGrant.tenant_id == company_id, ExpertGrant.id == grant_id)
    ).scalar_one_or_none()
    if grant is None:
        raise ExpertGrantNotFoundError(grant_id)
    return grant


def _emit_grant_evidence(db: Session, grant: ExpertGrant, actor_display: str, summary: str, event_type: str) -> None:
    event_no = next_event_no(db, grant.tenant_id)
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=grant.tenant_id,
            event_no=event_no,
            type=event_type,
            at=dt.datetime.now(dt.timezone.utc),
            actor_type="user",
            actor_display=actor_display,
            summary=summary,
        )
    )


def issue_grant(db: Session, membership: Membership, payload: ExpertGrantIssueRequest) -> ExpertGrant:
    """POST /api/v1/expert/grants — spec §5.1 invited 단계 + §7.2 사무소 검색/신규 등록.

    business_registration_no가 기존 사무소와 일치하면 재사용(동명 사무소 오초대 방지,
    spec §2.2 UX #15), 없으면 신규 ExpertAccount + 최초 ExpertOfficeMember(담당자,
    isOfficeAdmin=true)를 함께 만든다(spec §3.2 "사무소 담당자 이메일 입력").
    """
    if membership.role not in ISSUER_ROLES:
        raise ExpertGrantForbiddenError()

    from_date = payload.from_ or dt.date.today()
    if payload.until <= from_date:
        raise ExpertGrantUnboundedError()

    account: ExpertAccount | None = None
    if payload.business_registration_no:
        account = db.execute(
            select(ExpertAccount).where(ExpertAccount.business_registration_no == payload.business_registration_no)
        ).scalar_one_or_none()

    if account is None:
        account = ExpertAccount(
            id=new_id(),
            office_name=payload.office_name,
            brand_initial=payload.brand_initial,
            brand_color=payload.brand_color,
            business_registration_no=payload.business_registration_no,
        )
        db.add(account)
        db.flush()
        db.add(
            ExpertOfficeMember(
                id=new_id(),
                expert_account_id=account.id,
                name=payload.office_contact_name,
                email=payload.office_contact_email,
                is_office_admin=True,
            )
        )

    grant = ExpertGrant(
        id=new_id(),
        status="invited",
        expert_account_id=account.id,
        tenant_id=membership.company_id,
        granted_by=membership.user_id,
        from_date=from_date,
        until_date=payload.until,
        review_interval_days=payload.review_interval_days or 365,
    )
    db.add(grant)
    db.flush()

    granter = db.get(User, membership.user_id)
    _emit_grant_evidence(
        db,
        grant,
        actor_display=f"{granter.name if granter else membership.user_id} → {account.office_name} 위탁 초대",
        summary=f"행정사 위탁 초대 · {account.office_name}",
        event_type="expert_access_granted",
    )
    db.commit()
    db.refresh(grant)
    return grant


def authorize_grant(db: Session, membership: Membership, grant_id: str) -> ExpertGrant:
    """spec §5.1 company_authorized 단계 — 위탁계약 근거 확인(체크박스, v1 최소구현)."""
    if membership.role not in ISSUER_ROLES:
        raise ExpertGrantForbiddenError()
    grant = _company_scoped(db, membership.company_id, grant_id)
    if grant.status != "invited":
        raise ExpertGrantInvalidTransitionError(f"invited 상태에서만 승인 확인할 수 있습니다(현재: {grant.status})")

    grant.status = "company_authorized"
    db.flush()
    account = db.get(ExpertAccount, grant.expert_account_id)
    granter = db.get(User, membership.user_id)
    _emit_grant_evidence(
        db,
        grant,
        actor_display=f"{granter.name if granter else membership.user_id} (위탁계약 근거 확인)",
        summary=f"위탁계약 근거 확인 · {account.office_name if account else grant.expert_account_id}",
        event_type="expert_access_granted",
    )
    db.commit()
    db.refresh(grant)
    return grant


def revoke_grant(db: Session, membership: Membership, grant_id: str) -> ExpertGrant:
    """spec §7.2 "owner만 철회 가능, manager는 초대까지만" — 내부 구성원 초대 매트릭스와 동일 원칙."""
    if membership.role != "owner":
        raise ExpertGrantForbiddenError("위탁 철회는 대표만 할 수 있습니다")
    grant = _company_scoped(db, membership.company_id, grant_id)
    if grant.status in GRANT_TERMINAL_STATUSES:
        raise ExpertGrantInvalidTransitionError(f"이미 종료된 위탁입니다(현재: {grant.status})")

    grant.status = "revoked"
    grant.revoked_reason = "manual"
    db.flush()
    account = db.get(ExpertAccount, grant.expert_account_id)
    granter = db.get(User, membership.user_id)
    _emit_grant_evidence(
        db,
        grant,
        actor_display=f"{granter.name if granter else membership.user_id} (위탁 철회)",
        summary=f"위탁 철회 · {account.office_name if account else grant.expert_account_id}",
        event_type="expert_access_revoked",
    )
    db.commit()
    db.refresh(grant)
    return grant


def _expire_due_grants(db: Session, *, tenant_id: str | None = None, expert_account_id: str | None = None) -> int:
    """until_date 도달 시 자동 expired 전이(spec §5.1). 배치 잡이 아니라 조회 경로에서
    지연 평가한다 — 이 함수를 부르는 list_grants/resolve_expert_allowed_tenant_ids가
    항상 먼저 호출되므로, 배치가 아직 안 돌았어도 만료된 grant가 접근권을 주는 창은
    생기지 않는다(§10 후속 "실제 배치 구현"과는 별개로, 접근 통제 자체는 이미 안전하다)."""
    today = dt.date.today()
    stmt = select(ExpertGrant).where(ExpertGrant.status.in_(GRANT_LIVE_STATUSES), ExpertGrant.until_date < today)
    if tenant_id is not None:
        stmt = stmt.where(ExpertGrant.tenant_id == tenant_id)
    if expert_account_id is not None:
        stmt = stmt.where(ExpertGrant.expert_account_id == expert_account_id)
    due = db.execute(stmt).scalars().all()
    for grant in due:
        grant.status = "expired"
        grant.revoked_reason = "expired"
        db.flush()
        account = db.get(ExpertAccount, grant.expert_account_id)
        _emit_grant_evidence(
            db,
            grant,
            actor_display="시스템 (위탁 기간 만료)",
            summary=f"위탁 기간 만료 · {account.office_name if account else grant.expert_account_id}",
            event_type="expert_access_revoked",
        )
    if due:
        db.commit()
    return len(due)


def list_grants(db: Session, membership: Membership) -> list[ExpertGrant]:
    if membership.role not in ISSUER_ROLES:
        raise ExpertGrantForbiddenError()
    _expire_due_grants(db, tenant_id=membership.company_id)
    return list(
        db.execute(
            select(ExpertGrant).where(ExpertGrant.tenant_id == membership.company_id).order_by(ExpertGrant.created_at.desc())
        ).scalars()
    )


# ---------------------------------------------------------------------------
# 사무소 직원 관리(spec §5.6) — 오너십은 사무소(isOfficeAdmin) 쪽에 있다. 고객사는
# ExpertGrant만 관리한다(위).
# ---------------------------------------------------------------------------


def list_office_members(db: Session, actor: ExpertOfficeMember) -> list[ExpertOfficeMember]:
    return list(
        db.execute(
            select(ExpertOfficeMember)
            .where(ExpertOfficeMember.expert_account_id == actor.expert_account_id)
            .order_by(ExpertOfficeMember.created_at)
        ).scalars()
    )


def create_office_member(db: Session, actor: ExpertOfficeMember, payload: ExpertOfficeMemberCreateRequest) -> ExpertOfficeMember:
    if not actor.is_office_admin:
        raise ExpertOfficeMemberForbiddenError()

    existing = db.execute(
        select(ExpertOfficeMember).where(
            ExpertOfficeMember.expert_account_id == actor.expert_account_id,
            ExpertOfficeMember.email == payload.email,
        )
    ).scalar_one_or_none()
    if existing is not None:
        # 이메일 일치 시 기존 구성원 재사용(spec §3.2/§3.3 "다른 회사로 재초대" 원칙과
        # 동일 사상 — 계정 중복 생성 금지). 정지 상태였다면 재활성화한다.
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return existing

    member = ExpertOfficeMember(
        id=new_id(),
        expert_account_id=actor.expert_account_id,
        name=payload.name,
        email=payload.email,
        is_office_admin=payload.is_office_admin,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_office_member(
    db: Session, actor: ExpertOfficeMember, member_id: str, payload: ExpertOfficeMemberUpdateRequest
) -> ExpertOfficeMember:
    if not actor.is_office_admin:
        raise ExpertOfficeMemberForbiddenError()
    target = db.execute(
        select(ExpertOfficeMember).where(
            ExpertOfficeMember.expert_account_id == actor.expert_account_id, ExpertOfficeMember.id == member_id
        )
    ).scalar_one_or_none()
    if target is None:
        raise ExpertOfficeMemberNotFoundError()

    if payload.status is not None:
        target.status = payload.status
    if payload.is_office_admin is not None:
        target.is_office_admin = payload.is_office_admin
    db.commit()
    db.refresh(target)
    return target


# ---------------------------------------------------------------------------
# 화이트라벨 세션 로그인(spec §3) — email+OTP. docs/DB_SCHEMA.md §4.8-1 편차 노트:
# legacy JWT 계보 대신 이 저장소의 phone+OTP+불투명 세션 패턴을 email 축으로 특수화한다.
# ---------------------------------------------------------------------------


def request_expert_otp(db: Session, email: str) -> tuple[str | None, int]:
    now = dt.datetime.now(dt.timezone.utc)
    active = db.execute(
        select(ExpertLoginOtp)
        .where(ExpertLoginOtp.email == email, ExpertLoginOtp.consumed_at.is_(None), ExpertLoginOtp.expires_at > now)
        .order_by(ExpertLoginOtp.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active is not None and active.created_at > now - OTP_REQUEST_COOLDOWN:
        return None, max(int((active.expires_at - now).total_seconds()), 0)

    code = generate_otp_code()
    db.add(ExpertLoginOtp(id=new_id(), email=email, code_hash=hash_secret(code), expires_at=now + OTP_TTL))
    db.commit()
    return code, int(OTP_TTL.total_seconds())


def _activate_due_grants_on_login(db: Session, expert_account_id: str) -> None:
    """spec §5.1 "ExpertOfficeMember 최초 로그인 성공 → active" — 이 사무소의
    company_authorized grant 전부를 active로 전이한다(개인이 아니라 사무소 전체가
    grant를 공유하는 v1 scope 고정, spec §10)."""
    due = db.execute(
        select(ExpertGrant).where(
            ExpertGrant.expert_account_id == expert_account_id, ExpertGrant.status == "company_authorized"
        )
    ).scalars().all()
    for grant in due:
        grant.status = "active"
        db.flush()
        account = db.get(ExpertAccount, expert_account_id)
        _emit_grant_evidence(
            db,
            grant,
            actor_display=f"{account.office_name if account else expert_account_id} (최초 로그인)",
            summary=f"위탁 활성화 · {account.office_name if account else expert_account_id}",
            event_type="expert_access_granted",
        )


def verify_expert_otp_and_login(db: Session, email: str, code: str) -> tuple[str, ExpertOfficeMember, dt.datetime]:
    """검증 + 세션 발급을 한 함수로 묶는다(services/auth.py의 verify_otp와 동일 관례)."""
    otp = db.execute(
        select(ExpertLoginOtp)
        .where(ExpertLoginOtp.email == email, ExpertLoginOtp.consumed_at.is_(None))
        .order_by(ExpertLoginOtp.created_at.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()
    if otp is None:
        raise ExpertOtpNotFoundError()

    now = dt.datetime.now(dt.timezone.utc)
    if otp.expires_at < now:
        raise ExpertOtpExpiredError()
    if otp.attempt_count >= MAX_OTP_ATTEMPTS:
        raise ExpertOtpAttemptsExceededError()
    if not secrets_match(code, otp.code_hash):
        otp.attempt_count += 1
        db.commit()
        raise ExpertOtpCodeMismatchError()

    otp.consumed_at = now
    db.flush()

    member = db.execute(select(ExpertOfficeMember).where(ExpertOfficeMember.email == email)).scalars().first()
    if member is None:
        db.rollback()
        raise ExpertMemberNotRegisteredError()
    if member.status != "active":
        db.rollback()
        raise ExpertMemberSuspendedError()

    _activate_due_grants_on_login(db, member.expert_account_id)

    raw_token = generate_session_token()
    session_expires_at = now + SESSION_TTL
    db.add(
        ExpertSession(
            id=new_id(), expert_office_member_id=member.id, token_hash=hash_secret(raw_token), expires_at=session_expires_at
        )
    )
    db.commit()
    db.refresh(member)
    return raw_token, member, session_expires_at


def resolve_expert_session_member(db: Session, raw_token: str) -> ExpertOfficeMember:
    """세션 토큰 → 활성 ExpertOfficeMember. spec §3.3 "refresh마다 status 재조회" 취지를
    매 요청마다 그대로 적용한다(짧은 access TTL 절충 대신 매 요청 재조회 — spec이 인정한
    절충보다 더 강한 보장)."""
    now = dt.datetime.now(dt.timezone.utc)
    session = db.execute(select(ExpertSession).where(ExpertSession.token_hash == hash_secret(raw_token))).scalar_one_or_none()
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise ExpertSessionInvalidError()
    member = db.get(ExpertOfficeMember, session.expert_office_member_id)
    if member is None or member.status != "active":
        raise ExpertSessionInvalidError()
    return member


def resolve_expert_allowed_tenant_ids(db: Session, member: ExpertOfficeMember) -> list[str]:
    """패턴 특수화(spec §4.1) — resolve_daily_briefing_allowed_company_ids의 패키지 도메인
    버전. status='active'인 grant의 tenant_id만 포함한다(spec §3.1 "status: 'active'인
    tenantId만 채운다")."""
    _expire_due_grants(db, expert_account_id=member.expert_account_id)
    rows = db.execute(
        select(ExpertGrant.tenant_id).where(
            ExpertGrant.expert_account_id == member.expert_account_id, ExpertGrant.status == "active"
        )
    ).scalars()
    return list(rows)
