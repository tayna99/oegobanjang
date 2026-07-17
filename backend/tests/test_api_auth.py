"""POST /api/v1/auth/otp/request|verify — phone+OTP 로그인. docs/DB_SCHEMA.md §13-11."""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


@contextmanager
def _client_for(session):
    """코드리뷰 재사용 지적: client/client_with_membership 두 픽스처와 테스트 하나가 각자
    dependency_overrides 세팅→TestClient 생성→teardown을 그대로 복제하고 있었다 — 세션
    하나만 받으면 되므로 이 컨텍스트매니저 하나로 통일한다."""

    def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db):
    db.execute(text("""
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u1', '010-1111-0001', '테스트유저', now());
    """))
    db.flush()
    return db


@pytest.fixture()
def client(seeded):
    with _client_for(seeded) as c:
        yield c


def test_request_otp_returns_debug_code_in_local_env(client):
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["requested"] is True
    assert data["debug_code"] is not None
    assert len(data["debug_code"]) == 6


def test_request_otp_does_not_reveal_account_existence(client):
    known = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    unknown = client.post("/api/v1/auth/otp/request", json={"phone": "010-9999-9999"})
    assert known.status_code == unknown.status_code == 200


def test_verify_otp_success_issues_session(client):
    req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = req.json()["debug_code"]
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["session_token"]
    assert data["user"]["id"] == "u1"


def test_verify_otp_wrong_code_is_unauthorized(client):
    client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": "000000"})
    assert resp.status_code == 401, resp.text


def test_verify_otp_exceeded_attempts_is_rate_limited(client):
    client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    for _ in range(5):
        resp = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": "000000"})
        assert resp.status_code == 401
    over_limit = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": "000000"})
    assert over_limit.status_code == 429, over_limit.text


def test_verify_otp_unknown_phone_is_not_found(client):
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "010-9999-9999"})
    code = resp.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-9999-9999", "code": code})
    assert verify.status_code == 404, verify.text


def test_verify_otp_without_prior_request_is_not_found(client):
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": "123456"})
    assert resp.status_code == 404, resp.text


def test_session_seeded_directly_with_past_expiry_is_rejected(client, seeded):
    from app.domain.auth_tokens import hash_secret

    seeded.execute(
        text(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at) "
            "VALUES ('sess_expired', 'u1', :hash, now() - interval '1 day', now() - interval '31 days')"
        ),
        {"hash": hash_secret("expired-raw-token")},
    )
    seeded.flush()
    resp = client.post(
        "/api/v1/approvals/nope/approve",
        json={"idempotency_key": "k1"},
        headers={"Authorization": "Bearer expired-raw-token"},
    )
    assert resp.status_code == 401, resp.text


def test_repeated_otp_request_within_cooldown_does_not_invalidate_pending_code(client):
    """어드버서리얼 보안 리뷰 F1: 반복 /otp/request로 정상 발급된 코드를 새 코드가 가려버려
    실사용자가 로그인 못 하게 되는 방해 공격을 쿨다운으로 막았는지 확인한다."""
    first = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = first.json()["debug_code"]
    assert code is not None

    # 공격자가 같은 번호로 즉시 재요청 — 새 코드를 발급하지 않아야 한다(원래 코드가 계속 유효).
    flood = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    assert flood.status_code == 200, flood.text
    assert flood.json()["debug_code"] is None

    # 실사용자가 처음 받은 코드로 로그인할 수 있어야 한다 — 방해 공격이 성립하지 않는다.
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    assert resp.status_code == 200, resp.text


def test_logout_revokes_session(client):
    req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    token = verify.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204, logout.text

    resp = client.post("/api/v1/approvals/nope/approve", json={"idempotency_key": "k1"}, headers=headers)
    assert resp.status_code == 401, resp.text


def test_logout_without_session_is_a_noop(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204, resp.text


@pytest.fixture()
def seeded_with_membership(seeded):
    # `seeded`가 이미 u1(010-1111-0001)을 넣어 뒀다 — 그 위에 회사·멤버십만 얹는다
    # (코드리뷰 재사용 지적: 이전엔 유저 INSERT를 이 픽스처가 통째로 다시 썼다).
    seeded.execute(text("INSERT INTO companies (id, name) VALUES ('cmp_test', '테스트 회사')"))
    seeded.execute(text("""
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('mem_u1', 'cmp_test', 'u1', 'manager', 'active');
    """))
    seeded.flush()
    return seeded


@pytest.fixture()
def client_with_membership(seeded_with_membership):
    with _client_for(seeded_with_membership) as c:
        yield c


def _login(client, phone="010-1111-0001"):
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def test_me_returns_user_and_active_memberships(client_with_membership):
    token = _login(client_with_membership)
    resp = client_with_membership.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["id"] == "u1"
    assert data["memberships"] == [{"company_id": "cmp_test", "role": "manager"}]


def test_me_excludes_inactive_memberships(db):
    db.execute(text("""
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u2', '010-1111-0002', '테스트유저2', now());
    """))
    db.execute(text("INSERT INTO companies (id, name) VALUES ('cmp_test2', '테스트 회사2')"))
    db.execute(text("""
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('mem_u2_removed', 'cmp_test2', 'u2', 'manager', 'removed');
    """))
    db.flush()

    with _client_for(db) as client:
        token = _login(client, phone="010-1111-0002")
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["memberships"] == []


def test_verify_otp_includes_active_memberships(seeded_with_membership):
    """코드리뷰 효율 지적: verify 응답에 멤버십을 실어 프론트가 로그인 직후 /me를 또
    부르지 않아도 되게 한다."""
    with _client_for(seeded_with_membership) as client:
        req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
        code = req.json()["debug_code"]
        verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
        assert verify.status_code == 200, verify.text
        assert verify.json()["memberships"] == [{"company_id": "cmp_test", "role": "manager"}]


def test_me_with_resolved_identity_but_missing_user_row_is_unauthorized_not_500(db):
    """코드리뷰 지적: get_current_user_id는 세션만 검증하고 users 테이블은 보지 않는다 —
    세션이 가리키는 사용자 행이 없으면 이전엔 처리되지 않은 500이 났다.
    _load_user_with_memberships가 이제 401로 걸러낸다.

    `sessions.user_id`엔 실제로 `REFERENCES users(id)`(ON DELETE 미지정 — DB가 FK로 막음)가
    있어 세션 테이블에 직접 고아 행을 넣을 수는 없다 — 그래서 get_current_user_id 의존성
    자체를 오버라이드해 "세션 검증은 통과했지만 그 user_id가 users에 없는" 상태를 재현한다.
    """
    from app.api.deps import get_current_user_id

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_id] = lambda: "no-such-user"
    try:
        resp = TestClient(app).get("/api/v1/auth/me")
        assert resp.status_code == 401, resp.text
    finally:
        app.dependency_overrides.clear()


def test_me_without_session_is_unauthorized(client_with_membership):
    resp = client_with_membership.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


def test_settings_rejects_default_pepper_outside_local():
    import pytest as _pytest
    from pydantic import ValidationError

    from app.config import Settings

    with _pytest.raises(ValidationError):
        Settings(environment="production")

    # local은 기본 pepper를 허용한다(개발 편의) — 회귀 방지.
    Settings(environment="local")
