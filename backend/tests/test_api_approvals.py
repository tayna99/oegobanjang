"""POST /api/v1/approvals/{id}/approve|reject — 승인 결정 서비스의 게이트·동시성·멱등성·인증 검증.

DB 레벨 가드레일(테넌트·상태머신)은 db/validate.py가 담당한다. 이 테스트는 서비스 계층
(HTTP 상태 매핑·게이트 판정·케이스 전이·evidence append·세션 인증)을 PG 실 인스턴스에서 검증한다.
일괄(batch) 엔드포인트는 존재하지 않는다(GOTCHAS §3) — 그런 테스트가 없는 것이 의도다.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.domain.auth_tokens import hash_secret
from app.main import app


def _seed_base(db):
    # 멀티 스테이트먼트 raw SQL 블록에는 SQLAlchemy 바인드 파라미터(:name)를 쓸 수 없다
    # (psycopg 드라이버가 문장당 1회 파싱을 전제) — f-string 삽입은 pin_hash가 로컬에서
    # 계산한 16진 다이제스트뿐이라 인젝션 위험이 없다.
    pin_hash = hash_secret("1234")
    db.execute(text(f"""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at, pin_hash) VALUES
          ('u_owner','010-0000-0001','김대표', now(), '{pin_hash}'),
          ('u_manager','010-0000-0002','박주임', now(), '{pin_hash}');
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


PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_manager": "010-0000-0002"}


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req.status_code == 200, req.text
    code = req.json()["debug_code"]
    assert code is not None  # 테스트 환경(environment=local)에서만 노출됨
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    assert verify.status_code == 200, verify.text
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str = "u_owner") -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def _body(**overrides):
    body = {"idempotency_key": str(uuid.uuid4()), "identity_method": "pin", "pin": "1234"}
    body.update(overrides)
    return body


def test_approve_success_by_owner(client, seeded):
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "approved"
    assert data["case_state"] == "human_approved"
    count = seeded.execute(text("SELECT count(*) FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert count == 1


def test_approve_requires_identity_method(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(identity_method=None), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_approve_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body())
    assert resp.status_code == 401, resp.text


def test_manager_cannot_approve_when_policy_owner_only(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(), headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 403, resp.text


def test_manager_can_approve_low_severity_when_policy_allows(client, seeded):
    seeded.execute(text("UPDATE companies SET approval_policy='manager_allowed' WHERE id='cmp1'"))
    seeded.execute(text("UPDATE cases SET severity='LOW' WHERE id='cs1'"))
    seeded.flush()
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(), headers=_auth_headers(client, user="u_manager")
    )
    assert resp.status_code == 200, resp.text


def test_approve_idempotent_replay_returns_same_result(client, seeded):
    key = str(uuid.uuid4())
    headers = _auth_headers(client)
    first = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key), headers=headers)
    second = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key), headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["approval"]["status"] == second.json()["approval"]["status"] == "approved"
    count = seeded.execute(text("SELECT count(*) FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert count == 1  # replay는 evidence를 중복 생성하지 않는다


def test_replay_with_wrong_direction_is_conflict(client):
    key = str(uuid.uuid4())
    headers = _auth_headers(client)
    first = client.post("/api/v1/approvals/apv1/approve", json=_body(idempotency_key=key), headers=headers)
    assert first.status_code == 200
    # approve로 소진된 키로 reject 재호출 → 409(F2)
    second = client.post(
        "/api/v1/approvals/apv1/reject", json=_body(idempotency_key=key, reason="다시 봄"), headers=headers
    )
    assert second.status_code == 409, second.text


def test_approve_different_key_after_decided_is_conflict(client):
    headers = _auth_headers(client)
    assert client.post("/api/v1/approvals/apv1/approve", json=_body(), headers=headers).status_code == 200
    assert client.post("/api/v1/approvals/apv1/approve", json=_body(), headers=headers).status_code == 409


def test_approve_blocked_when_no_usable_citation(client, seeded):
    _seed_case_with_pending_approval(seeded, cid="cs2", aid="act2", apid="apv2", code="case_002",
                                     with_citation=False, due="2026-09-01")
    resp = client.post("/api/v1/approvals/apv2/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 422, resp.text


def test_reject_requires_reason(client):
    resp = client.post(
        "/api/v1/approvals/apv1/reject", json=_body(reason=None), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_reject_success_transitions_case_to_returned(client):
    resp = client.post(
        "/api/v1/approvals/apv1/reject", json=_body(reason="근거 확인 필요"), headers=_auth_headers(client)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "rejected"
    assert data["case_state"] == "returned"


def test_reject_reason_with_pii_is_blocked(client):
    resp = client.post(
        "/api/v1/approvals/apv1/reject",
        json=_body(reason="010-1234-5678로 연락해 확인"),
        headers=_auth_headers(client),
    )
    assert resp.status_code == 422, resp.text


def test_reject_evidence_does_not_leak_free_text_pii(client, seeded):
    """코드 리뷰 지적(PR #10): contains_pii()는 등록번호·전화번호·여권번호 패턴만 잡는다 —
    이름 같은 자유형 PII가 섞인 사유는 통과되므로, evidence_events.summary에 원문이 그대로
    남지 않고 고정 요약 + 해시로만 기록되는지 확인한다(evidence_events.summary DDL 주석
    "원문 전문 금지" 준수)."""
    reason = "김철수 전무님 확인 후 처리 요망"  # 정규식 패턴에 안 걸리는 이름 — 그래도 PII
    resp = client.post(
        "/api/v1/approvals/apv1/reject", json=_body(reason=reason), headers=_auth_headers(client)
    )
    assert resp.status_code == 200, resp.text  # 정규식 미탐지라 저장 자체는 허용됨(approvals.reason)

    row = seeded.execute(
        text("SELECT summary, output_hash FROM evidence_events WHERE approval_id='apv1'")
    ).mappings().one()
    assert "김철수" not in row["summary"]
    assert row["summary"] == "반려"
    assert row["output_hash"] == f"sha256:{hashlib.sha256(reason.encode()).hexdigest()}"

    # 원문 자체는 approvals.reason(승인 레코드 본연의 필드)에는 정상적으로 남아야 한다.
    stored_reason = seeded.execute(text("SELECT reason FROM approvals WHERE id='apv1'")).scalar_one()
    assert stored_reason == reason


def test_high_risk_blocked_case_rejects_non_handoff_action(client, seeded):
    _seed_case_with_pending_approval(seeded, cid="cs3", aid="act3", apid="apv3", code="case_003",
                                     severity="CRITICAL", state="blocked", action_type="send_message",
                                     due="2026-07-08")
    resp = client.post("/api/v1/approvals/apv3/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 403, resp.text


def test_high_risk_blocked_case_handoff_approves_but_stays_blocked(client, seeded):
    # blocked(고위험) 케이스의 handoff 승인은 승인만 확정되고 케이스는 blocked로 유지된다(행정사 이관).
    _seed_case_with_pending_approval(seeded, cid="cs4", aid="act4", apid="apv4", code="case_004",
                                     severity="CRITICAL", state="blocked", action_type="create_handoff",
                                     due="2026-07-09")
    resp = client.post("/api/v1/approvals/apv4/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "approved"
    assert data["case_state"] == "blocked"


def test_approval_not_found_returns_404(client):
    resp = client.post("/api/v1/approvals/nope/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 404


def test_reject_evidence_is_recorded_as_approval_rejected(client, seeded):
    resp = client.post(
        "/api/v1/approvals/apv1/reject", json=_body(reason="근거 확인 필요"), headers=_auth_headers(client)
    )
    assert resp.status_code == 200, resp.text
    evt_type = seeded.execute(text("SELECT type FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert evt_type == "approval_rejected"


def test_approve_mismatched_pin_is_rejected(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin="9999"), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_approve_without_pin_value_is_rejected(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin=None), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_approve_with_unregistered_pin_is_rejected(client, seeded):
    seeded.execute(text("UPDATE users SET pin_hash=NULL WHERE id='u_owner'"))
    seeded.flush()
    resp = client.post("/api/v1/approvals/apv1/approve", json=_body(), headers=_auth_headers(client))
    assert resp.status_code == 422, resp.text


def test_approve_submits_checklist_and_persists_it(client, seeded):
    checklist = [
        {"key": "risk", "label": "위험도 검토", "checked": True},
        {"key": "docs", "label": "근거 확인", "checked": True},
    ]
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(checklist=checklist), headers=_auth_headers(client)
    )
    assert resp.status_code == 200, resp.text
    stored = seeded.execute(text("SELECT checklist FROM approvals WHERE id='apv1'")).scalar_one()
    assert stored == checklist


def test_approve_rejected_when_submitted_checklist_incomplete(client):
    checklist = [{"key": "risk", "label": "위험도 검토", "checked": False}]
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(checklist=checklist), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def _seed_delegation(db, *, delegator="u_owner", delegate="u_manager", starts="2026-07-01T00:00:00Z",
                      ends="2027-01-01T00:00:00Z", revoked_at=None):
    db.execute(
        text(
            "INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, "
            "starts_at, ends_at, revoked_at) VALUES "
            "('dlg1','cmp1',:delegator,:delegate,'approval',:starts,:ends,:revoked_at)"
        ),
        {"delegator": delegator, "delegate": delegate, "starts": starts, "ends": ends, "revoked_at": revoked_at},
    )
    db.flush()


def test_manager_can_approve_on_behalf_of_owner_with_valid_delegation(client, seeded):
    _seed_delegation(seeded)
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 200, resp.text
    actor = seeded.execute(text("SELECT actor_display FROM evidence_events WHERE approval_id='apv1'")).scalar_one()
    assert "대리 승인" in actor


def test_manager_cannot_approve_on_behalf_without_delegation(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_manager_cannot_approve_on_behalf_with_expired_delegation(client, seeded):
    _seed_delegation(seeded, starts="2020-01-01T00:00:00Z", ends="2020-02-01T00:00:00Z")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_manager_cannot_approve_on_behalf_with_revoked_delegation(client, seeded):
    _seed_delegation(seeded, revoked_at="2026-07-01T00:00:00Z")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text
