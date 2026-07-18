"""POST /api/v1/packages/{case_id}/link(발급/재발급) · GET /api/v1/packages/link/{link_token}
(열람) — 행정사 패키지 무인증 열람 링크. R2.6, docs/DB_SCHEMA.md §4.8.

POST는 manager/owner 인증 + 케이스의 create_handoff 승인 완료가 필요(코드리뷰 지적, PR #20
P1 — AGENTS.md §8 "행정사/노무사에게 패키지 전달"은 승인 필요 작업). GET은 무인증이지만
회전하는 link_token으로만 조회한다(코드리뷰 지적, PR #20 P1 — case_id는 불변이라 비밀로
쓰면 재발급으로 기존 유출 링크를 회수할 수 없다). 만료·미발급·대상 없음은 모두 같은
404(존재 비노출).
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
          ('w1','cmp1','Batbayar E.','몽골','2026-07-04'),
          ('w2','cmp1','Le Van T.','베트남','2026-08-01');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','케이스1','CRITICAL','blocked','2026-07-04'),
          ('cs2','cmp1','case_002','w2','visa_expiry','케이스2','HIGH','risk_review','2026-08-01');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval, slot) VALUES
          ('act_cs1_handoff','cmp1','cs1','approve','create_handoff','행정사 검토 자료 만들기','ready',true,'primary'),
          ('act_cs2_handoff','cmp1','cs2','approve','create_handoff','행정사 검토 자료 만들기','ready',true,'primary');
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv_cs1_handoff','cmp1','cs1','act_cs1_handoff','pending','user', now());
        UPDATE approvals SET status='approved', decided_by_user_id='u_owner', identity_method='pin', decided_at=now()
          WHERE id='apv_cs1_handoff';
    """))
    # cs2는 의도적으로 승인이 없다(요청조차 없음) — 승인 전 링크 발급 차단 테스트용.
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


def test_manager_can_issue_link_for_approved_case(client, seeded):
    resp = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["case_id"] == "cs1"
    assert data["link_token"]
    assert data["issued_at"] < data["expires_at"]

    evt = seeded.execute(
        text("SELECT type, actor_display FROM evidence_events WHERE case_id='cs1' AND type='package_link_issued'")
    ).one()
    assert evt.type == "package_link_issued"
    assert evt.actor_display == "박주임"

    pkg_count = seeded.execute(text("SELECT count(*) FROM handoff_packages WHERE case_id='cs1'")).scalar_one()
    assert pkg_count == 1


def test_owner_can_issue_link_for_approved_case(client):
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


# 코드리뷰 지적(PR #20 P1): 승인 없이는(요청조차 없어도) 절대 링크가 발급돼선 안 된다
# (AGENTS.md §8 "행정사/노무사에게 패키지 전달"은 승인 필요 작업).
def test_issue_without_approved_handoff_is_forbidden(client, seeded):
    resp = client.post("/api/v1/packages/cs2/link", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 403, resp.text

    pkg_count = seeded.execute(text("SELECT count(*) FROM handoff_packages WHERE case_id='cs2'")).scalar_one()
    assert pkg_count == 0


def test_issue_with_pending_approval_is_still_forbidden(client, seeded):
    # 승인 "요청"만 있고 아직 결정(approved)되지 않은 경우도 마찬가지로 막혀야 한다.
    seeded.execute(
        text(
            "INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) "
            "VALUES ('apv_cs2_pending','cmp1','cs2','act_cs2_handoff','pending','user', now())"
        )
    )
    seeded.flush()

    resp = client.post("/api/v1/packages/cs2/link", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 403, resp.text


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


# 코드리뷰 지적(PR #20 P1) 핵심 회귀 테스트: 재발급은 case_id가 아니라 link_token을
# 회전시켜야 한다 — 그렇지 않으면 이전에 유출된 링크를 회수할 방법이 없다.
def test_reissue_rotates_link_token_and_invalidates_the_old_one(client, seeded):
    headers = _auth_headers(client)
    first = client.post("/api/v1/packages/cs1/link", headers=headers).json()
    old_token = first["link_token"]

    # 재발급 전: 옛 토큰으로 열람 가능.
    assert client.get(f"/api/v1/packages/link/{old_token}").status_code == 200

    second = client.post("/api/v1/packages/cs1/link", headers=headers).json()
    new_token = second["link_token"]

    assert new_token != old_token
    # 재발급 후: 옛 토큰은 더 이상 통하지 않는다(회수 완료) — 새 토큰만 유효.
    assert client.get(f"/api/v1/packages/link/{old_token}").status_code == 404
    assert client.get(f"/api/v1/packages/link/{new_token}").status_code == 200


def test_view_valid_link_returns_200_without_auth_and_logs_evidence(client, seeded):
    issued = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client)).json()

    resp = client.get(f"/api/v1/packages/link/{issued['link_token']}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["case_id"] == "cs1"

    evt = seeded.execute(
        text("SELECT type, actor_type FROM evidence_events WHERE case_id='cs1' AND type='package_link_viewed'")
    ).one()
    assert evt.actor_type == "system"


def test_view_before_issue_returns_404(client):
    resp = client.get("/api/v1/packages/link/never-issued")
    assert resp.status_code == 404, resp.text


def test_view_unknown_token_returns_404(client):
    resp = client.get("/api/v1/packages/link/no-such-token")
    assert resp.status_code == 404, resp.text


def test_view_expired_link_returns_404(client, seeded):
    issued = client.post("/api/v1/packages/cs1/link", headers=_auth_headers(client)).json()
    seeded.execute(text("UPDATE handoff_packages SET link_expires_at = now() - interval '1 day' WHERE case_id='cs1'"))
    seeded.flush()

    resp = client.get(f"/api/v1/packages/link/{issued['link_token']}")
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
