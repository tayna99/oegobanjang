"""GET /api/v1/cases · GET /api/v1/approvals — 읽기 API 테넌트 격리·기준일 주입(§13-13, §13-14).

decide 계열과 달리 모든 active 역할(viewer 포함)이 통과한다. company_id는 세션 사용자의
실제 membership에서만 도출한다 — 어떤 쿼리 파라미터로도 다른 회사를 조회할 수 없다(보안
리뷰 F1 비차단 권고 — 교차 테넌트 회귀를 여기서 명시적으로 검증한다).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed(db):
    db.execute(text("""
        INSERT INTO companies (id, name, timezone) VALUES
          ('cmp1','테스트1','Asia/Seoul'),
          ('cmp2','테스트2','Asia/Seoul');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u1','010-0000-0001','김담당', now()),
          ('u_viewer','010-0000-0002','최열람', now()),
          ('u_none','010-0000-0003','무소속', now()),
          ('u_other','010-0000-0004','타사담당', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m1','cmp1','u1','manager','active'),
          ('m2','cmp1','u_viewer','viewer','active'),
          ('m3','cmp2','u_other','owner','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09'),
          ('w2','cmp2','Other Worker','필리핀','2026-09-01');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료','HIGH','risk_review','2026-08-09'),
          ('cs2','cmp1','case_002','w1','other','기한 없음','LOW','draft', NULL),
          ('cs_other','cmp2','case_101','w2','visa_expiry','타사 케이스','HIGH','risk_review','2026-09-01');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) VALUES
          ('act1','cmp1','cs1','approve','send_message','승인하기', true);
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv1','cmp1','cs1','act1','pending','agent', now());
    """))
    db.flush()


PHONE_BY_USER = {
    "u1": "010-0000-0001",
    "u_viewer": "010-0000-0002",
    "u_none": "010-0000-0003",
    "u_other": "010-0000-0004",
}


@pytest.fixture()
def seeded(db):
    _seed(db)
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


def test_list_cases_without_session_is_unauthorized(client):
    assert client.get("/api/v1/cases").status_code == 401


def test_list_cases_without_membership_is_forbidden(client):
    resp = client.get("/api/v1/cases", headers=_auth_headers(client, "u_none"))
    assert resp.status_code == 403, resp.text


def test_viewer_can_list_cases(client):
    resp = client.get("/api/v1/cases", headers=_auth_headers(client, "u_viewer"))
    assert resp.status_code == 200, resp.text


def test_list_cases_scopes_to_own_company_only(client):
    resp = client.get("/api/v1/cases", headers=_auth_headers(client, "u1"))
    assert resp.status_code == 200, resp.text
    ids = {c["id"] for c in resp.json()["cases"]}
    assert ids == {"cs1", "cs2"}
    assert "cs_other" not in ids  # 타사 케이스는 절대 안 보여야 한다


def test_list_cases_d_day_uses_injected_base_date(client):
    resp = client.get(
        "/api/v1/cases", params={"base_date": "2026-07-10"}, headers=_auth_headers(client, "u1")
    )
    assert resp.status_code == 200, resp.text
    by_id = {c["id"]: c for c in resp.json()["cases"]}
    assert by_id["cs1"]["d_day"] == 30  # 2026-08-09 - 2026-07-10
    assert by_id["cs2"]["d_day"] is None  # due_date 없음
    assert resp.json()["base_date"] == "2026-07-10"


def test_list_cases_defaults_base_date_to_company_timezone_today(client):
    resp = client.get("/api/v1/cases", headers=_auth_headers(client, "u1"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["base_date"] is not None  # 미지정 시에도 항상 채워짐(회사 timezone 오늘)


def test_list_approvals_scopes_to_own_company_and_filters(client):
    resp = client.get(
        "/api/v1/approvals", params={"status": "pending"}, headers=_auth_headers(client, "u1")
    )
    assert resp.status_code == 200, resp.text
    ids = {a["id"] for a in resp.json()["approvals"]}
    assert ids == {"apv1"}


def test_list_approvals_cross_tenant_is_invisible(client):
    resp = client.get("/api/v1/approvals", headers=_auth_headers(client, "u_other"))
    assert resp.status_code == 200, resp.text
    ids = {a["id"] for a in resp.json()["approvals"]}
    assert "apv1" not in ids


def test_list_approvals_case_id_filter(client):
    resp = client.get("/api/v1/approvals", params={"case_id": "cs1"}, headers=_auth_headers(client, "u1"))
    assert resp.status_code == 200, resp.text
    assert {a["id"] for a in resp.json()["approvals"]} == {"apv1"}
