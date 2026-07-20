"""GET /api/v1/notifications, POST /api/v1/notifications/{id}/read — R5.4.

생성 경로(N01/N06/N03 훅)는 test_notifications_service.py가 서비스 계층에서 검증한다 — 여기서는
이 두 엔드포인트의 계약(인증·테넌트/수신자 격리·읽음 처리 멱등성)만 본다. 시드에서 바로
POST /api/v1/approvals를 호출해 N01 알림을 실제로 만든 뒤 조회/읽음 처리를 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_base(db):
    db.execute(
        text(
            """
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사1'), ('cmp2','테스트 회사2');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_manager','010-0000-0002','박주임', now()),
          ('u_other','010-0000-0003','다른회사담당', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active'),
          ('m_other','cmp2','u_other','manager','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','체류 만료 임박','HIGH','risk_review','2026-08-09');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) VALUES
          ('act1','cmp1','cs1','approve','send_message','승인하기', true);
    """
        )
    )
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


PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_manager": "010-0000-0002", "u_other": "010-0000-0003"}


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str = "u_owner") -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def _request_approval(client: TestClient) -> None:
    resp = client.post("/api/v1/approvals", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 201, resp.text


def test_list_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 401, resp.text


def test_owner_sees_the_n01_notification_from_approval_request(client):
    _request_approval(client)
    resp = client.get("/api/v1/notifications", headers=_auth_headers(client, "u_owner"))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "N01"
    assert data[0]["case_id"] == "cs1"
    assert data[0]["status"] == "queued"
    assert data[0]["read_at"] is None


def test_requester_does_not_see_their_own_request_notification(client):
    """N01 수신자는 승인 권한자(owner)이지 요청자(manager) 본인이 아니다."""
    _request_approval(client)
    resp = client.get("/api/v1/notifications", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_other_company_member_does_not_see_it(client):
    _request_approval(client)
    resp = client.get("/api/v1/notifications", headers=_auth_headers(client, "u_other"))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_mark_read_updates_read_at(client):
    _request_approval(client)
    headers = _auth_headers(client, "u_owner")
    notification_id = client.get("/api/v1/notifications", headers=headers).json()[0]["id"]

    resp = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["read_at"] is not None

    listed = client.get("/api/v1/notifications", headers=headers).json()
    assert listed[0]["read_at"] is not None


def test_mark_read_is_idempotent(client):
    _request_approval(client)
    headers = _auth_headers(client, "u_owner")
    notification_id = client.get("/api/v1/notifications", headers=headers).json()[0]["id"]

    first = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers).json()
    second = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers).json()
    assert first["read_at"] == second["read_at"]


def test_mark_read_on_unknown_id_is_not_found(client):
    resp = client.post("/api/v1/notifications/nope/read", headers=_auth_headers(client, "u_owner"))
    assert resp.status_code == 404, resp.text


def test_mark_read_on_other_recipients_notification_is_not_found(client):
    """수신자가 아닌 사람이 남의 알림 id를 알아도 읽음 처리할 수 없다(존재 비노출)."""
    _request_approval(client)
    owner_headers = _auth_headers(client, "u_owner")
    notification_id = client.get("/api/v1/notifications", headers=owner_headers).json()[0]["id"]

    other_headers = _auth_headers(client, "u_other")
    resp = client.post(f"/api/v1/notifications/{notification_id}/read", headers=other_headers)
    assert resp.status_code == 404, resp.text
