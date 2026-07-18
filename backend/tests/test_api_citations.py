"""GET /api/v1/citations — 근거 라이브러리 조회(전역 official + 회사 internal, F등급 제외, 테넌트 인가)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app

PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_other": "010-0000-0009"}


@pytest.fixture()
def seeded(db):
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
        INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) VALUES
          ('cit_global_a', NULL, 'A', 'official', '출입국관리법 제25조', '국가법령정보센터', now()),
          ('cit_cmp1_e', 'cmp1', 'E', 'internal', 'cmp1 전용 템플릿', 'internal', now()),
          ('cit_cmp2_e', 'cmp2', 'E', 'internal', 'cmp2 전용 템플릿', 'internal', now()),
          ('cit_f_synthetic', NULL, 'F', 'official', '합성 데이터', 'synthetic', now());
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


def test_returns_global_official_and_own_company_internal_citations(client: TestClient) -> None:
    response = client.get(
        "/api/v1/citations", params={"company_id": "cmp1"}, headers=_auth_headers(client, "u_owner")
    )

    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert ids == {"cit_global_a", "cit_cmp1_e"}


def test_does_not_leak_other_company_internal_citations(client: TestClient) -> None:
    response = client.get(
        "/api/v1/citations", params={"company_id": "cmp1"}, headers=_auth_headers(client, "u_owner")
    )

    ids = {row["id"] for row in response.json()}
    assert "cit_cmp2_e" not in ids


def test_never_returns_f_grade_synthetic_citations(client: TestClient) -> None:
    response = client.get(
        "/api/v1/citations", params={"company_id": "cmp1"}, headers=_auth_headers(client, "u_owner")
    )

    grades = {row["grade"] for row in response.json()}
    assert "F" not in grades


def test_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/citations", params={"company_id": "cmp1"})

    assert response.status_code == 401


def test_rejects_access_to_company_without_membership(client: TestClient) -> None:
    response = client.get(
        "/api/v1/citations", params={"company_id": "cmp1"}, headers=_auth_headers(client, "u_other")
    )

    assert response.status_code == 403
