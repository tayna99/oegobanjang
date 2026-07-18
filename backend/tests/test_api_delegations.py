"""GET /api/v1/delegations/mine — 위임 조회. R2.4, docs/DB_SCHEMA.md §4.1, §13-10."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_base(db):
    db.execute(text("""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_manager','010-0000-0002','박주임', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active');
    """))
    db.flush()


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, phone: str = "010-0000-0002") -> dict:
    return {"Authorization": f"Bearer {_login(client, phone)}"}


def test_returns_null_when_no_delegation(client):
    resp = client.get("/api/v1/delegations/mine", headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_returns_valid_delegation(client, seeded):
    seeded.execute(text(
        "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, starts_at, ends_at) "
        "VALUES ('dlg1','cmp1','u_owner','u_manager','approval','2026-07-01T00:00:00Z','2027-01-01T00:00:00Z')"
    ))
    seeded.flush()

    resp = client.get("/api/v1/delegations/mine", headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["delegator_user_id"] == "u_owner"
    assert data["delegator_name"] == "김대표"


def test_returns_null_when_delegation_expired(client, seeded):
    seeded.execute(text(
        "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, starts_at, ends_at) "
        "VALUES ('dlg1','cmp1','u_owner','u_manager','approval','2020-01-01T00:00:00Z','2020-02-01T00:00:00Z')"
    ))
    seeded.flush()

    resp = client.get("/api/v1/delegations/mine", headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_returns_null_when_delegation_revoked(client, seeded):
    seeded.execute(text(
        "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, starts_at, ends_at, revoked_at) "
        "VALUES ('dlg1','cmp1','u_owner','u_manager','approval','2026-07-01T00:00:00Z','2027-01-01T00:00:00Z','2026-07-05T00:00:00Z')"
    ))
    seeded.flush()

    resp = client.get("/api/v1/delegations/mine", headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_owner_does_not_see_their_own_grant_as_a_delegation(client, seeded):
    seeded.execute(text(
        "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, starts_at, ends_at) "
        "VALUES ('dlg1','cmp1','u_owner','u_manager','approval','2026-07-01T00:00:00Z','2027-01-01T00:00:00Z')"
    ))
    seeded.flush()

    resp = client.get("/api/v1/delegations/mine", headers=_auth_headers(client, phone="010-0000-0001"))
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/delegations/mine")
    assert resp.status_code == 401, resp.text
