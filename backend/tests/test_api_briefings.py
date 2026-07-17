"""POST /api/v1/briefings/generate — 테넌트 인가 + 응답 계약 (G6)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app

PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_other": "010-0000-0009"}


@pytest.fixture()
def seeded(db: Session) -> Session:
    db.execute(
        text(
            """
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트제조'), ('cmp2','다른회사');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_other','010-0000-0009','타사대표', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_other','cmp2','u_other','owner','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-06');
    """
        )
    )
    db.flush()
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


def _auth_headers(client: TestClient, user: str) -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def test_generate_returns_ranked_items_for_authorized_member(client: TestClient) -> None:
    response = client.post(
        "/api/v1/briefings/generate",
        json={"company_id": "cmp1", "reference_date": "2026-07-17"},
        headers=_auth_headers(client, "u_owner"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company_id"] == "cmp1"
    assert body["briefing_date"] == "2026-07-17"
    assert len(body["items"]) >= 1
    assert body["items"][0]["rank"] == 1
    assert "case_code" in body["items"][0]


def test_generate_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/briefings/generate", json={"company_id": "cmp1", "reference_date": "2026-07-17"}
    )

    assert response.status_code == 401


def test_generate_rejects_company_without_membership(client: TestClient) -> None:
    response = client.post(
        "/api/v1/briefings/generate",
        json={"company_id": "cmp1", "reference_date": "2026-07-17"},
        headers=_auth_headers(client, "u_other"),
    )

    assert response.status_code == 403
