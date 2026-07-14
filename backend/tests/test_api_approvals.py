"""POST /api/v1/approvals/{id}/approve|reject — 승인 결정 서비스의 게이트·동시성·멱등성 검증.

DB 레벨 가드레일(테넌트·상태머신 145건)은 db/validate.py가 담당한다. 이 테스트는 서비스 계층
(HTTP 상태 매핑·게이트 판정·케이스 전이·evidence append)을 PG 실 인스턴스에서 검증한다.
일괄(batch) 엔드포인트는 존재하지 않는다(GOTCHAS §3) — 그런 테스트가 없는 것이 의도다.
"""

from __future__ import annotations

import uuid

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
          ('u_manager','010-0000-0002','박주임', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-09');
        INSERT INTO citations (id, grade, status, title, source, ingest_at) VALUES
          ('cit_a','A','official','출입국관리법 제25조','국가법령정보센터', now());
    """))
    db.flush()


def _seed_case_with_pending_approval(
    db, *, cid, aid, apid, code, severity="HIGH", state="approval_pending",
    action_type="send_message", with_citation=True, due="2026-08-09",
):
    db.execute(
        text(
            "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date) "
            "VALUES (:cid,'cmp1',:code,'w1','visa_expiry','테스트 케이스',:sev,:state,:due)"
        ),
        {"cid": cid, "code": code, "sev": severity, "state": state, "due": due},
    )
    db.execute(
        text(
            "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval) "
            "VALUES (:aid,'cmp1',:cid,'approve',:atype,'승인하기',true)"
        ),
        {"aid": aid, "cid": cid, "atype": action_type},
    )
    if with_citation:
        db.execute(
            text("INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor) VALUES ('cmp1',:cid,'cit_a','rule')"),
            {"cid": cid},
        )
    db.execute(
        text(
            "INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) "
            "VALUES (:apid,'cmp1',:cid,:aid,'pending','agent', now())"
        ),
        {"apid": apid, "cid": cid, "aid": aid},
    )
    db.flush()


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    _seed_case_with_pending_approval(db, cid="cs1", aid="act1", apid="apv1", code="case_001")
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _body(**overrides):
    body = {"idempotency_key": str(uuid.uuid4()), "decided_by_user_id": "u_owner", "identity_method": "pin"}
    body.update(overrides)
    return body


def test_approve_success_by_owner(client, seeded):
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "approved"
    assert data["case_state"] == "human_approved"
    count = seeded.execute(text("SELECT count(*) FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert count == 1


def test_approve_requires_identity_method(client):
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body(identity_method=None))
    assert resp.status_code == 422, resp.text


def test_manager_cannot_approve_when_policy_owner_only(client):
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body(decided_by_user_id="u_manager"))
    assert resp.status_code == 403, resp.text


def test_manager_can_approve_low_severity_when_policy_allows(client, seeded):
    seeded.execute(text("UPDATE companies SET approval_policy='manager_allowed' WHERE id='cmp1'"))
    seeded.execute(text("UPDATE cases SET severity='LOW' WHERE id='cs1'"))
    seeded.flush()
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body(decided_by_user_id="u_manager"))
    assert resp.status_code == 200, resp.text


def test_approve_idempotent_replay_returns_same_result(client, seeded):
    key = str(uuid.uuid4())
    first = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key))
    second = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["approval"]["status"] == second.json()["approval"]["status"] == "approved"
    count = seeded.execute(text("SELECT count(*) FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert count == 1  # replay는 evidence를 중복 생성하지 않는다


def test_replay_with_wrong_direction_is_conflict(client):
    key = str(uuid.uuid4())
    first = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key))
    assert first.status_code == 200
    # approve로 소진된 키로 reject 재호출 → 409(F2)
    second = client.post("/api/v1/approvals/apv1/reject", json=_body(idempotency_key=key, reason="다시 봄"))
    assert second.status_code == 409, second.text


def test_approve_different_key_after_decided_is_conflict(client):
    assert client.post("/api/v1/approvals/apv1/approve", json=_body()).status_code == 200
    assert client.post("/api/v1/approvals/apv1/approve", json=_body()).status_code == 409


def test_approve_blocked_when_no_usable_citation(client, seeded):
    _seed_case_with_pending_approval(seeded, cid="cs2", aid="act2", apid="apv2", code="case_002",
                                     with_citation=False, due="2026-09-01")
    resp = client.post("/api/v1/approvals/apv2/approve", json=_body())
    assert resp.status_code == 422, resp.text


def test_reject_requires_reason(client):
    resp = client.post("/api/v1/approvals/apv1/reject", json=_body(reason=None))
    assert resp.status_code == 422, resp.text


def test_reject_success_transitions_case_to_returned(client):
    resp = client.post("/api/v1/approvals/apv1/reject", json=_body(reason="근거 확인 필요"))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "rejected"
    assert data["case_state"] == "returned"


def test_reject_reason_with_pii_is_blocked(client):
    resp = client.post("/api/v1/approvals/apv1/reject", json=_body(reason="010-1234-5678로 연락해 확인"))
    assert resp.status_code == 422, resp.text


def test_high_risk_blocked_case_rejects_non_handoff_action(client, seeded):
    _seed_case_with_pending_approval(seeded, cid="cs3", aid="act3", apid="apv3", code="case_003",
                                     severity="CRITICAL", state="blocked", action_type="send_message",
                                     due="2026-07-08")
    resp = client.post("/api/v1/approvals/apv3/approve", json=_body())
    assert resp.status_code == 403, resp.text


def test_high_risk_blocked_case_handoff_approves_but_stays_blocked(client, seeded):
    # blocked(고위험) 케이스의 handoff 승인은 승인만 확정되고 케이스는 blocked로 유지된다(행정사 이관).
    _seed_case_with_pending_approval(seeded, cid="cs4", aid="act4", apid="apv4", code="case_004",
                                     severity="CRITICAL", state="blocked", action_type="create_handoff",
                                     due="2026-07-09")
    resp = client.post("/api/v1/approvals/apv4/approve", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "approved"
    assert data["case_state"] == "blocked"


def test_approval_not_found_returns_404(client):
    assert client.post("/api/v1/approvals/nope/approve", json=_body()).status_code == 404
