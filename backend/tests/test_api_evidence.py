"""POST/GET /api/v1/evidence — 일반 판단 기록 기록/조회 엔드포인트. R2.5, docs/DB_SCHEMA.md §4.5.

승인 결정 등 도메인 전용 이벤트(services/approvals.py)는 이미 별도로 테스트돼 있다 — 여기서는
이 범용 엔드포인트 자체의 계약(허용 타입·PII 차단·테넌트 격리·무인증 타입 거부)만 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_base(db):
    db.execute(text("""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사1'), ('cmp2','테스트 회사2');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u1','010-0000-0001','김담당', now()),
          ('u2','010-0000-0002','박담당', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m1','cmp1','u1','manager','active'),
          ('m2','cmp2','u2','manager','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09'),
          ('w2','cmp2','Le Van T','베트남','2026-08-09');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','케이스1','HIGH','risk_review','2026-08-09'),
          ('cs2','cmp2','case_001','w2','visa_expiry','케이스2','HIGH','risk_review','2026-08-09');
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


def _auth_headers(client: TestClient, phone: str = "010-0000-0001") -> dict:
    return {"Authorization": f"Bearer {_login(client, phone)}"}


def test_member_can_create_evidence(client, seeded):
    resp = client.post(
        "/api/v1/evidence",
        json={"type": "interpretation_confirmed", "case_id": "cs1", "summary": "해석 확인"},
        headers=_auth_headers(client),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "interpretation_confirmed"
    assert data["case_id"] == "cs1"
    assert data["company_id"] == "cmp1"
    assert data["actor_type"] == "user"
    assert data["actor_display"] == "김담당"
    assert data["event_no"] >= 1


def test_create_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/evidence", json={"type": "role_granted", "summary": "역할 부여"})
    assert resp.status_code == 401, resp.text


def test_company_level_event_without_case_id_allowed(client):
    resp = client.post(
        "/api/v1/evidence", json={"type": "plan_created", "summary": "계획 생성"}, headers=_auth_headers(client)
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["case_id"] is None


def test_invalid_type_rejected(client):
    resp = client.post(
        "/api/v1/evidence", json={"type": "not_a_real_type", "summary": "무언가"}, headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("type_", ["package_link_issued", "package_link_viewed", "package_reply"])
def test_package_link_types_rejected_on_generic_endpoint(client, type_):
    # 무인증 화면(ExpertLinkPage)에서 나오는 타입 — 이 인증 필요 엔드포인트로는 절대 못 남긴다
    # (api/v1/packages.py 전용 경로만 허용).
    resp = client.post(
        "/api/v1/evidence", json={"type": type_, "summary": "패키지 링크 관련"}, headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


# 코드리뷰 회귀(PR #20 P1): get_current_membership은 "이 회사 소속인가"만 확인하고 role은
# 안 본다 — 예전엔 ALLOWED_EVIDENCE_TYPES가 approval_decided/role_changed/dispatch_executed
# 같은 특권 결과 타입까지 그대로 받아, 아무 구성원이나 실제로 일어나지 않은 승인·역할변경·
# 발송완료를 감사 로그에 위조해 넣을 수 있었다. 이제 이런 타입은 전부 거부돼야 한다(해당
# 도메인의 실제 서버 트랜잭션 안에서만 기록 가능).
@pytest.mark.parametrize(
    "type_",
    [
        "approval_requested",
        "approval_decided",
        "approval_rejected",
        "approval_escalated",
        "role_granted",
        "role_changed",
        "member_invited",
        "member_removed",
        "delegation_granted",
        "delegation_revoked",
        "autonomy_changed",
        "worker_deleted",
        "dispatch_executed",
        "delivery_confirmed",
    ],
)
def test_privileged_types_rejected_on_generic_endpoint(client, type_):
    resp = client.post(
        "/api/v1/evidence", json={"type": type_, "summary": "위조 시도"}, headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_summary_containing_pii_rejected(client):
    resp = client.post(
        "/api/v1/evidence",
        json={"type": "plan_created", "summary": "등록번호 900101-1234567 포함"},
        headers=_auth_headers(client),
    )
    assert resp.status_code == 422, resp.text


def test_case_id_from_other_company_is_not_found(client):
    # cs2는 cmp2 소속 — cmp1 세션으로는 존재하지 않는 것과 동일하게 취급(테넌트 격리).
    resp = client.post(
        "/api/v1/evidence",
        json={"type": "interpretation_confirmed", "case_id": "cs2", "summary": "해석 확인"},
        headers=_auth_headers(client),
    )
    assert resp.status_code == 404, resp.text


def test_list_returns_only_own_company_events_sorted_by_event_no(client):
    headers1 = _auth_headers(client, "010-0000-0001")
    headers2 = _auth_headers(client, "010-0000-0002")
    client.post("/api/v1/evidence", json={"type": "plan_created", "summary": "cmp1 이벤트 1"}, headers=headers1)
    client.post("/api/v1/evidence", json={"type": "plan_created", "summary": "cmp2 이벤트"}, headers=headers2)
    client.post("/api/v1/evidence", json={"type": "plan_created", "summary": "cmp1 이벤트 2"}, headers=headers1)

    resp = client.get("/api/v1/evidence", headers=headers1)
    assert resp.status_code == 200, resp.text
    events = resp.json()
    assert [e["summary"] for e in events] == ["cmp1 이벤트 1", "cmp1 이벤트 2"]
    assert events[0]["event_no"] < events[1]["event_no"]


def test_list_filtered_by_case_id(client):
    headers = _auth_headers(client)
    client.post(
        "/api/v1/evidence",
        json={"type": "interpretation_confirmed", "case_id": "cs1", "summary": "케이스 이벤트"},
        headers=headers,
    )
    client.post("/api/v1/evidence", json={"type": "plan_created", "summary": "회사 이벤트"}, headers=headers)

    resp = client.get("/api/v1/evidence", params={"case_id": "cs1"}, headers=headers)
    assert resp.status_code == 200, resp.text
    events = resp.json()
    assert len(events) == 1
    assert events[0]["case_id"] == "cs1"
