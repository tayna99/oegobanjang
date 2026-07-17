"""POST/GET /api/v1/packages/{case_id}/link — 행정사 패키지 무인증 열람 링크. R2.6, docs/DB_SCHEMA.md §4.8.

POST(발급/재발급)는 manager/owner 인증 필요, GET(열람)은 무인증 — ExpertLinkPage와 동일한
신뢰 모델(case_id 자체가 비밀 링크). 만료·미발급·대상 없음은 모두 같은 404(존재 비노출).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_base(db):
    db.execute(text("""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_manager','010-0000-0002','박주임', now()),
          ('u_viewer','010-0000-0003','최열람', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active'),
          ('m_viewer','cmp1','u_viewer','viewer','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Batbayar E.','몽골','2026-07-04');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','케이스1','CRITICAL','blocked','2026-07-04');
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


PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_manager": "010-0000-0002", "u_viewer": "010-0000-0003"}


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str = "u_manager") -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def test_manager_can_issue_link(client, seeded):
    resp = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["case_id"] == "cs1"
    assert data["issued_at"] < data["expires_at"]

    evt = seeded.execute(
        text("SELECT type, actor_display FROM evidence_events WHERE case_id='cs1' AND type='package_link_issued'")
    ).one()
    assert evt.type == "package_link_issued"
    assert evt.actor_display == "박주임"

    pkg_count = seeded.execute(text("SELECT count(*) FROM handoff_packages WHERE case_id='cs1'")).scalar_one()
    assert pkg_count == 1


def test_owner_can_issue_link(client):
    resp = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client, "u_owner"))
    assert resp.status_code == 201, resp.text


def test_viewer_cannot_issue_link(client):
    resp = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client, "u_viewer"))
    assert resp.status_code == 403, resp.text


def test_issue_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/packages/cs1/link")
    assert resp.status_code == 401, resp.text


def test_issue_for_nonexistent_case_is_not_found(client):
    resp = client.post("/api/v1/packages/no-such-case/link", headers=_auth_headers(client))
    assert resp.status_code == 404, resp.text


def test_reissue_updates_same_row_not_a_duplicate(client, seeded):
    headers = _auth_headers(client)
    first = client.post("/api/v1/packages/cs1/link", headers=headers)
    second = client.post("/api/v1/packages/cs1/link", headers=headers)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["expires_at"] <= second.json()["expires_at"]

    pkg_count = seeded.execute(text("SELECT count(*) FROM handoff_packages WHERE case_id='cs1'")).scalar_one()
    assert pkg_count == 1

    reissue_events = seeded.execute(
        text("SELECT count(*) FROM evidence_events WHERE case_id='cs1' AND type='package_link_issued'")
    ).scalar_one()
    assert reissue_events == 2


def test_view_valid_link_returns_200_without_auth_and_logs_evidence(client, seeded):
    client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client))

    resp = client.get("/api/v1/packages/cs1/link")
    assert resp.status_code == 200, resp.text
    assert resp.json()["case_id"] == "cs1"

    evt = seeded.execute(
        text("SELECT type, actor_type FROM evidence_events WHERE case_id='cs1' AND type='package_link_viewed'")
    ).one()
    assert evt.actor_type == "system"


def test_view_before_issue_returns_404(client):
    resp = client.get("/api/v1/packages/cs1/link")
    assert resp.status_code == 404, resp.text


def test_view_nonexistent_case_returns_404(client):
    resp = client.get("/api/v1/packages/no-such-case/link")
    assert resp.status_code == 404, resp.text


def test_view_expired_link_returns_404(client, seeded):
    client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client))
    seeded.execute(text("UPDATE handoff_packages SET link_expires_at = now() - interval '1 day' WHERE case_id='cs1'"))
    seeded.flush()

    resp = client.get("/api/v1/packages/cs1/link")
    assert resp.status_code == 404, resp.text


def test_generic_evidence_endpoint_cannot_forge_package_link_viewed(client):
    # api/v1/evidence.py 쪽에서도 동일 계약을 검증하지만, 여기서도 "이 라우터가 유일한
    # package_link_viewed 발행처"라는 전제를 한 번 더 못박는다.
    resp = client.post(
        "/api/v1/evidence",
        json={"type": "package_link_viewed", "case_id": "cs1", "summary": "위조 시도"},
        headers=_auth_headers(client),
    )
    assert resp.status_code == 422, resp.text
