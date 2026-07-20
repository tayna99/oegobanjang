"""행정사 화이트라벨 v1(R5.1) — /api/v1/expert/* 전체.

spec: reference/specs/7-1_행정사_화이트라벨_v1.md. 커버 범위:
- 위탁(ExpertGrant) 생애주기: 발급(invited)→승인확인(company_authorized)→로그인 시 자동
  활성화(active)→철회(revoked)/자동만료(expired). 무기한 위탁 금지(결정 C)는 여기서
  API 레벨로, db/validate.py에서 DB 레벨로 이중 검증한다.
- 사무소 구성원(ExpertOfficeMember) CRUD — 사무소 자체 오너십(isOfficeAdmin, spec §5.6).
- email+OTP 화이트라벨 세션 로그인.
- 패키지 조회(GET /api/v1/expert/packages/{id}) 3중 체크 + PackageViewLog 기록(spec §4.2/§6).
  **최고위험 지점**: tenant scope + 사무소(expert_account_id) 일치 + 케이스 승인 게이트 —
  셋 중 하나라도 실패하면 전부 동일한 404(존재 비노출).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.domain.auth_tokens import hash_secret
from app.main import app


def _seed_base(db):
    # pin_hash: 데모 PIN '1234' — u_owner1/u_owner2가 approvals API로 승인을 결정하는
    # 테스트(_approve)에 필요하다(test_api_approvals.py와 동일 관례).
    pin_hash = hash_secret("1234")
    db.execute(text(f"""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사1'), ('cmp2','테스트 회사2');
        INSERT INTO users (id, phone, name, terms_agreed_at, pin_hash) VALUES
          ('u_owner1','010-0000-0001','김대표', now(), '{pin_hash}'),
          ('u_manager1','010-0000-0002','박주임', now(), null),
          ('u_viewer1','010-0000-0003','최열람', now(), null),
          ('u_owner2','010-0000-0004','이대표', now(), '{pin_hash}');
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner1','cmp1','u_owner1','owner','active'),
          ('m_manager1','cmp1','u_manager1','manager','active'),
          ('m_viewer1','cmp1','u_viewer1','viewer','active'),
          ('m_owner2','cmp2','u_owner2','owner','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Batbayar E.','몽골','2026-07-04'),
          ('w2','cmp2','Le Van T.','베트남','2026-08-01');
        INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES
          ('cit_a','A','official','출입국관리법 제25조','국가법령정보센터', now());

        -- cs1(cmp1): human_approved까지 진행 — approvals API로 승인시켜 case_transitions 를 그대로 탄다.
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','케이스1','LOW','approval_pending','2026-07-04');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) VALUES
          ('act1','cmp1','cs1','approve','create_handoff','승인하기',true);
        INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp1','cs1','cit_a','rule');
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv1','cmp1','cs1','act1','pending','agent', now());

        -- cs2(cmp1): 아직 approval_pending — 승인 게이트 실패 테스트용(due_date를 cs1과
        -- 달리해 ux_cases_reuse(company_id,worker_id,case_type,due_date) 충돌을 피한다).
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs2','cmp1','case_002','w1','visa_expiry','케이스2','LOW','approval_pending','2026-09-04');

        -- cs_other(cmp2): 다른 테넌트 — cross-tenant 격리 테스트용.
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs_other','cmp2','case_001','w2','visa_expiry','케이스3','LOW','approval_pending','2026-08-01');
        INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp2','cs_other','cit_a','rule');
    """))
    db.flush()


def _approve(client: TestClient, approval_id: str, headers: dict) -> None:
    resp = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"idempotency_key": str(uuid.uuid4()), "identity_method": "pin", "pin": "1234"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


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


PHONE_BY_USER = {
    "u_owner1": "010-0000-0001",
    "u_manager1": "010-0000-0002",
    "u_viewer1": "010-0000-0003",
    "u_owner2": "010-0000-0004",
}


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str = "u_manager1") -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def _expert_login(client: TestClient, email: str) -> str:
    req = client.post("/api/v1/expert/auth/otp/request", json={"email": email})
    assert req.status_code == 200, req.text
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/expert/auth/otp/verify", json={"email": email, "code": code})
    assert verify.status_code == 200, verify.text
    return verify.json()["session_token"]


def _expert_headers(client: TestClient, email: str) -> dict:
    return {"Authorization": f"Bearer {_expert_login(client, email)}"}


def _issue_grant_body(**overrides) -> dict:
    body = {
        "office_name": "김앤리 행정사무소",
        "office_contact_email": "lee@kimlee.example",
        "office_contact_name": "이아무개",
        "brand_initial": "K",
        "brand_color": "#2f6fed",
        "until": "2027-07-20",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# 위탁(Grant) 발급/승인/철회
# ---------------------------------------------------------------------------


def test_owner_can_issue_grant_and_bootstraps_office_member(client, seeded):
    resp = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1"))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "invited"
    assert data["tenant_id"] == "cmp1"
    assert data["scope"] == "package_review"
    assert data["basis"] == "processing_agreement"

    member_count = seeded.execute(
        text("SELECT count(*) FROM expert_office_members WHERE email='lee@kimlee.example'")
    ).scalar_one()
    assert member_count == 1

    evt = seeded.execute(
        text("SELECT type FROM evidence_events WHERE company_id='cmp1' AND type='expert_access_granted'")
    ).one()
    assert evt.type == "expert_access_granted"


def test_manager_can_issue_grant(client):
    resp = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_manager1"))
    assert resp.status_code == 201, resp.text


def test_viewer_cannot_issue_grant(client):
    resp = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_viewer1"))
    assert resp.status_code == 403, resp.text


def test_issue_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/expert/grants", json=_issue_grant_body())
    assert resp.status_code == 401, resp.text


def test_issue_rejects_a_grant_that_does_not_end_after_it_starts(client):
    """결정 C — 무기한 위탁 금지. from==until(경계)도 거부한다."""
    resp = client.post(
        "/api/v1/expert/grants",
        json=_issue_grant_body(**{"from": "2026-07-20", "until": "2026-07-20"}),
        headers=_auth_headers(client, "u_owner1"),
    )
    assert resp.status_code == 422, resp.text


def test_reinviting_the_same_business_registration_no_reuses_the_expert_account(client, seeded):
    body = _issue_grant_body(business_registration_no="111-22-33333")
    first = client.post("/api/v1/expert/grants", json=body, headers=_auth_headers(client, "u_owner1"))
    second = client.post(
        "/api/v1/expert/grants",
        json={**body, "until": "2028-07-20"},
        headers=_auth_headers(client, "u_owner2"),
    )
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["expert_account_id"] == second.json()["expert_account_id"]
    account_count = seeded.execute(
        text("SELECT count(*) FROM expert_accounts WHERE business_registration_no='111-22-33333'")
    ).scalar_one()
    assert account_count == 1


def test_owner_can_authorize_invited_grant(client):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "company_authorized"


def test_authorize_a_grant_that_is_already_authorized_conflicts(client):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))
    assert resp.status_code == 409, resp.text


def test_authorize_grant_from_another_company_is_not_found(client):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner2"))
    assert resp.status_code == 404, resp.text


def test_owner_can_revoke_grant(client):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/revoke", headers=_auth_headers(client, "u_owner1"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "revoked"
    assert resp.json()["revoked_reason"] == "manual"


def test_manager_cannot_revoke_grant(client):
    """spec §7.2 "owner만 철회 가능, manager는 초대까지만" — 내부 초대 매트릭스와 동일 원칙."""
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/revoke", headers=_auth_headers(client, "u_manager1"))
    assert resp.status_code == 403, resp.text


def test_revoking_an_already_revoked_grant_conflicts(client):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    client.post(f"/api/v1/expert/grants/{issued['id']}/revoke", headers=_auth_headers(client, "u_owner1"))
    resp = client.post(f"/api/v1/expert/grants/{issued['id']}/revoke", headers=_auth_headers(client, "u_owner1"))
    assert resp.status_code == 409, resp.text


def test_list_grants_lazily_expires_due_grants(client, seeded):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    seeded.execute(
        text("UPDATE expert_grants SET from_date = CURRENT_DATE - 10, until_date = CURRENT_DATE - 1 WHERE id=:id"),
        {"id": issued["id"]},
    )
    seeded.flush()

    resp = client.get("/api/v1/expert/grants", headers=_auth_headers(client, "u_manager1"))
    assert resp.status_code == 200, resp.text
    row = next(g for g in resp.json() if g["id"] == issued["id"])
    assert row["status"] == "expired"
    assert row["revoked_reason"] == "expired"


def test_list_grants_only_shows_this_companys_grants(client, seeded):
    client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1"))
    client.post(
        "/api/v1/expert/grants",
        json=_issue_grant_body(office_contact_email="other@office.example"),
        headers=_auth_headers(client, "u_owner2"),
    )
    resp = client.get("/api/v1/expert/grants", headers=_auth_headers(client, "u_manager1"))
    assert resp.status_code == 200, resp.text
    assert all(g["tenant_id"] == "cmp1" for g in resp.json())


# ---------------------------------------------------------------------------
# 화이트라벨 세션 로그인 — 첫 로그인이 company_authorized → active를 트리거한다(spec §5.1)
# ---------------------------------------------------------------------------


def test_office_member_login_activates_authorized_grant(client, seeded):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))

    headers = _expert_headers(client, "lee@kimlee.example")
    assert "Authorization" in headers

    status_row = seeded.execute(text("SELECT status FROM expert_grants WHERE id=:id"), {"id": issued["id"]}).one()
    assert status_row.status == "active"


def test_login_with_unregistered_email_is_not_found(client):
    resp = client.post("/api/v1/expert/auth/otp/request", json={"email": "nobody@nowhere.example"})
    code = resp.json()["debug_code"]
    verify = client.post("/api/v1/expert/auth/otp/verify", json={"email": "nobody@nowhere.example", "code": code})
    assert verify.status_code == 404, verify.text


def test_login_with_suspended_member_is_forbidden(client, seeded):
    issued = client.post("/api/v1/expert/grants", json=_issue_grant_body(), headers=_auth_headers(client, "u_owner1")).json()
    client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))
    seeded.execute(text("UPDATE expert_office_members SET status='suspended' WHERE email='lee@kimlee.example'"))
    seeded.flush()

    resp = client.post("/api/v1/expert/auth/otp/request", json={"email": "lee@kimlee.example"})
    code = resp.json()["debug_code"]
    verify = client.post("/api/v1/expert/auth/otp/verify", json={"email": "lee@kimlee.example", "code": code})
    assert verify.status_code == 403, verify.text


# ---------------------------------------------------------------------------
# 사무소 구성원 CRUD — 오너십은 사무소(isOfficeAdmin) 쪽(spec §5.6)
# ---------------------------------------------------------------------------


def _bootstrap_active_office(client, seeded, *, until="2027-07-20"):
    issued = client.post(
        "/api/v1/expert/grants", json=_issue_grant_body(until=until), headers=_auth_headers(client, "u_owner1")
    ).json()
    client.post(f"/api/v1/expert/grants/{issued['id']}/authorize", headers=_auth_headers(client, "u_owner1"))
    return issued


def test_office_admin_can_create_and_list_members(client, seeded):
    _bootstrap_active_office(client, seeded)
    admin_headers = _expert_headers(client, "lee@kimlee.example")

    resp = client.post(
        "/api/v1/expert/office-members",
        json={"email": "kim2@kimlee.example", "name": "김둘째", "is_office_admin": False},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text

    listed = client.get("/api/v1/expert/office-members", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    emails = {m["email"] for m in listed.json()}
    assert {"lee@kimlee.example", "kim2@kimlee.example"} <= emails


def test_non_admin_member_cannot_create_members(client, seeded):
    _bootstrap_active_office(client, seeded)
    admin_headers = _expert_headers(client, "lee@kimlee.example")
    client.post(
        "/api/v1/expert/office-members",
        json={"email": "kim2@kimlee.example", "name": "김둘째", "is_office_admin": False},
        headers=admin_headers,
    )
    member_headers = _expert_headers(client, "kim2@kimlee.example")

    resp = client.post(
        "/api/v1/expert/office-members",
        json={"email": "kim3@kimlee.example", "name": "김셋째", "is_office_admin": False},
        headers=member_headers,
    )
    assert resp.status_code == 403, resp.text


def test_office_admin_can_suspend_a_member(client, seeded):
    _bootstrap_active_office(client, seeded)
    admin_headers = _expert_headers(client, "lee@kimlee.example")
    created = client.post(
        "/api/v1/expert/office-members",
        json={"email": "kim2@kimlee.example", "name": "김둘째", "is_office_admin": False},
        headers=admin_headers,
    ).json()

    resp = client.patch(f"/api/v1/expert/office-members/{created['id']}", json={"status": "suspended"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "suspended"


def test_office_members_endpoint_requires_expert_session(client):
    resp = client.get("/api/v1/expert/office-members")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# 패키지 조회 — 3중 체크(spec §4.2) + PackageViewLog(spec §6). 최고위험 지점.
# ---------------------------------------------------------------------------


def _seed_package(db, *, pkg_id, case_id, company_id, expert_account_id):
    db.execute(
        text(
            "INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload, expert_account_id) "
            "VALUES (:id,:cid,:case_id,'expert_review','{}',:eid)"
        ),
        {"id": pkg_id, "cid": company_id, "case_id": case_id, "eid": expert_account_id},
    )
    db.flush()


def test_active_grant_can_view_approved_package_and_logs_the_view(client, seeded):
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")  # activates the grant
    account_id = issued["expert_account_id"]

    _approve(client, "apv1", _auth_headers(client, "u_owner1"))  # cs1 -> human_approved
    _seed_package(seeded, pkg_id="hp1", case_id="cs1", company_id="cmp1", expert_account_id=account_id)

    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/hp1", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["package_id"] == "hp1"
    assert resp.json()["tenant_id"] == "cmp1"

    log_count = seeded.execute(
        text("SELECT count(*) FROM package_view_log WHERE package_id='hp1' AND expert_office_member_id="
             "(SELECT id FROM expert_office_members WHERE email='lee@kimlee.example')")
    ).scalar_one()
    assert log_count == 1


def test_view_requires_expert_session(client, seeded):
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    _approve(client, "apv1", _auth_headers(client, "u_owner1"))
    _seed_package(seeded, pkg_id="hp1", case_id="cs1", company_id="cmp1", expert_account_id=issued["expert_account_id"])

    resp = client.get("/api/v1/expert/packages/hp1")
    assert resp.status_code == 401, resp.text


def test_view_returns_404_for_a_package_belonging_to_another_tenant(client, seeded):
    """cross-tenant 격리 — cmp1에 활성 grant가 있어도 cmp2 패키지는 볼 수 없다."""
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    _approve(client, "apv1", _auth_headers(client, "u_owner1"))

    # cs_other(cmp2)를 human_approved까지 진행시키고 cmp2 패키지를 만든다.
    seeded.execute(text("""
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) VALUES
          ('act_other','cmp2','cs_other','approve','create_handoff','승인하기',true);
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv_other','cmp2','cs_other','act_other','pending','agent', now());
    """))
    seeded.flush()
    _approve(client, "apv_other", _auth_headers(client, "u_owner2"))
    _seed_package(seeded, pkg_id="hp_other", case_id="cs_other", company_id="cmp2", expert_account_id=issued["expert_account_id"])

    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/hp_other", headers=headers)
    assert resp.status_code == 404, resp.text


def test_view_returns_404_for_a_package_belonging_to_a_different_office(client, seeded):
    """spec §4.2 6번 항목 — 같은 tenant 안에서도 다른 사무소(expert_account) 앞 패키지는
    볼 수 없다(사무소 교체 등 과도기 회귀 방지, 기술 검증 #2가 지적한 지점)."""
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    _approve(client, "apv1", _auth_headers(client, "u_owner1"))

    other_office = client.post(
        "/api/v1/expert/grants",
        json=_issue_grant_body(
            office_name="다른 행정사무소",
            office_contact_email="other@office.example",
            business_registration_no="999-99-99999",
        ),
        headers=_auth_headers(client, "u_owner1"),
    ).json()

    _seed_package(seeded, pkg_id="hp1", case_id="cs1", company_id="cmp1", expert_account_id=other_office["expert_account_id"])

    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/hp1", headers=headers)
    assert resp.status_code == 404, resp.text


def test_view_returns_404_before_the_case_is_human_approved(client, seeded):
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    # cs2는 여전히 approval_pending — 승인 게이트를 통과하지 못한다.
    _seed_package(seeded, pkg_id="hp2", case_id="cs2", company_id="cmp1", expert_account_id=issued["expert_account_id"])

    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/hp2", headers=headers)
    assert resp.status_code == 404, resp.text


def test_view_returns_404_after_the_grant_is_revoked(client, seeded):
    issued = _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    _approve(client, "apv1", _auth_headers(client, "u_owner1"))
    _seed_package(seeded, pkg_id="hp1", case_id="cs1", company_id="cmp1", expert_account_id=issued["expert_account_id"])

    client.post(f"/api/v1/expert/grants/{issued['id']}/revoke", headers=_auth_headers(client, "u_owner1"))

    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/hp1", headers=headers)
    assert resp.status_code == 404, resp.text


def test_view_nonexistent_package_returns_404(client, seeded):
    _bootstrap_active_office(client, seeded)
    _expert_login(client, "lee@kimlee.example")
    headers = _expert_headers(client, "lee@kimlee.example")
    resp = client.get("/api/v1/expert/packages/no-such-package", headers=headers)
    assert resp.status_code == 404, resp.text
