"""POST /api/v1/auth/otp/request|verify — phone+OTP 로그인. docs/DB_SCHEMA.md §13-11."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


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
    def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


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


# R2.2 — GET /api/v1/auth/me: 프론트 roleStore가 세션에서 역할을 파생시키는 근거 엔드포인트.
def test_me_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


def test_me_returns_user_and_active_membership(client, seeded):
    seeded.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m1','cmp1','u1','manager','active');
    """))
    seeded.flush()

    req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    token = verify.json()["session_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["id"] == "u1"
    assert data["membership"] == {"company_id": "cmp1", "role": "manager"}
    assert data["delegated_by"] == []


def test_me_exposes_active_delegations(client, seeded):
    """R2.4 — 로그인 사용자(u1, manager)가 대리 승인할 수 있는 owner가 delegated_by에 나온다."""
    seeded.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES ('u_owner','010-2222-0001','김대표', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m1','cmp1','u1','manager','active'),
          ('m2','cmp1','u_owner','owner','active');
        INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, starts_at, ends_at)
        VALUES ('del1','cmp1','u_owner','u1','approval', now() - interval '1 day', now() + interval '1 day');
    """))
    seeded.flush()

    req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    token = verify.json()["session_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["delegated_by"] == [{"user_id": "u_owner", "name": "김대표"}]


def test_me_without_membership_returns_null(client):
    req = client.post("/api/v1/auth/otp/request", json={"phone": "010-1111-0001"})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "010-1111-0001", "code": code})
    token = verify.json()["session_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["membership"] is None


def test_settings_rejects_default_pepper_outside_local():
    import pytest as _pytest
    from pydantic import ValidationError

    from app.config import Settings

    with _pytest.raises(ValidationError):
        Settings(environment="production")

    # local은 기본 pepper를 허용한다(개발 편의) — 회귀 방지.
    Settings(environment="local")
