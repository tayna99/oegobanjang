"""POST /api/v1/approvals — 승인 요청 생성 엔드포인트. docs/DB_SCHEMA.md §4.3, §13-11.

요청은 manager 역할의 인증된 세션만 만들 수 있다(app/services/approvals.ALLOWED_REQUEST_ROLES,
7단계 권한 매트릭스 — 케이스 진행은 manager만, owner는 조회만).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_base(db):
    db.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_manager','010-0000-0002','박주임', now()),
          ('u_viewer','010-0000-0003','최열람', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active'),
          ('m_viewer','cmp1','u_viewer','viewer','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09');
    """))
    db.flush()


def _seed_action(
    db, *, cid, aid, code, case_state="risk_review", action_type="send_message",
    requires_approval=True, next_action_state="ready", due="2026-08-09",
):
    # ux_cases_reuse UNIQUE(company_id, worker_id, case_type, due_date) — 테스트마다 due를 달리한다.
    db.execute(
        text(
            "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) "
            "VALUES (:cid,'cmp1',:code,'w1','visa_expiry','테스트 케이스','HIGH',:state,:due)"
        ),
        {"cid": cid, "code": code, "state": case_state, "due": due},
    )
    db.execute(
        text(
            "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) "
            "VALUES (:aid,'cmp1',:cid,'approve',:atype,'승인 요청', :astate, :req)"
        ),
        {"aid": aid, "cid": cid, "atype": action_type, "astate": next_action_state, "req": requires_approval},
    )
    db.flush()


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    _seed_action(db, cid="cs1", aid="act1", code="case_001")
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


def test_manager_can_request_approval(client, seeded):
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act1"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "pending"
    assert data["case_state"] == "approval_pending"
    evt = seeded.execute(
        text("SELECT type FROM evidence_events WHERE action_id='act1' ORDER BY event_no DESC LIMIT 1")
    ).scalar_one()
    assert evt == "approval_requested"


def test_request_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/approvals", json={"action_id": "act1"})
    assert resp.status_code == 401, resp.text


def test_owner_cannot_request_approval(client):
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act1"}, headers=_auth_headers(client, user="u_owner")
    )
    assert resp.status_code == 403, resp.text


def test_viewer_cannot_request_approval(client):
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act1"}, headers=_auth_headers(client, user="u_viewer")
    )
    assert resp.status_code == 403, resp.text


def test_action_not_found_returns_404(client):
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "nope"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 404, resp.text


def test_action_not_requiring_approval_is_rejected(client, seeded):
    _seed_action(seeded, cid="cs2", aid="act2", code="case_002", requires_approval=False, action_type="other",
                 due="2026-08-10")
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act2"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 422, resp.text


def test_action_not_ready_is_rejected(client, seeded):
    _seed_action(seeded, cid="cs3", aid="act3", code="case_003", next_action_state="locked", due="2026-08-11")
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act3"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 422, resp.text


def test_duplicate_request_on_same_action_is_conflict(client):
    headers = _auth_headers(client, user="u_manager")
    first = client.post("/api/v1/approvals", json={"action_id": "act1"}, headers=headers)
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/approvals", json={"action_id": "act1"}, headers=headers)
    assert second.status_code == 409, second.text


def test_case_not_in_requestable_state_is_conflict(client, seeded):
    # draft는 risk_review로만 전이한다 — approval_pending으로 직접 갈 수 없어 이 경로를 검증한다.
    # human_approved 등 후행 상태는 트리거(trg_cases_terminal_not_insertable)가 직접 시딩을 막는다.
    _seed_action(seeded, cid="cs4", aid="act4", code="case_004", case_state="draft", due="2026-08-12")
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act4"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 409, resp.text


def test_request_succeeds_from_returned_state(client, seeded):
    _seed_action(seeded, cid="cs5", aid="act5", code="case_005", case_state="returned", due="2026-08-13")
    resp = client.post(
        "/api/v1/approvals", json={"action_id": "act5"}, headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["case_state"] == "approval_pending"
