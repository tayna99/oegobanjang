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
from app.main import app


def _seed_base(db):
    # pin_hash 값 = hash_secret('1234')(로컬 기본 pepper 기준) — _body()의 기본 pin과 짝을 이룬다.
    db.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp1','테스트','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at, pin_hash) VALUES
          ('u_owner','010-0000-0001','김대표', now(),
           'f6069dbc9e0c0f3a844b39d21e6664b359cbdd2f1cf32b22f8afbb317f5aa86a'),
          ('u_manager','010-0000-0002','박주임', now(),
           'f6069dbc9e0c0f3a844b39d21e6664b359cbdd2f1cf32b22f8afbb317f5aa86a');
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


def _seed_delegation(db, *, delegator="u_owner", delegate="u_manager", starts_at="now() - interval '1 day'",
                      ends_at="now() + interval '1 day'", revoked=False, company="cmp1", scope="approval",
                      id_="del1"):
    db.execute(
        text(
            f"INSERT INTO delegations (id, company_id, delegator_user_id, delegate_user_id, scope, "
            f"starts_at, ends_at, revoked_at) VALUES "
            f"(:id, :company, :delegator, :delegate, :scope, {starts_at}, {ends_at}, "
            f"{'now()' if revoked else 'NULL'})"
        ),
        {"id": id_, "company": company, "delegator": delegator, "delegate": delegate, "scope": scope},
    )
    db.flush()


def test_delegated_approve_succeeds_with_active_delegation(client, seeded):
    # owner_only 정책 하에서 manager 단독으로는 승인 불가하지만, 유효한 위임이 있으면 성공한다.
    _seed_delegation(seeded)
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval"]["status"] == "approved"


def test_delegated_reject_succeeds_with_active_delegation(client, seeded):
    _seed_delegation(seeded)
    resp = client.post(
        "/api/v1/approvals/apv1/reject",
        json=_body(on_behalf_of_user_id="u_owner", reason="위임 반려 확인"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval"]["status"] == "rejected"


def test_approve_on_behalf_without_any_delegation_row_is_forbidden(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_on_behalf_with_revoked_delegation_is_forbidden(client, seeded):
    _seed_delegation(seeded, revoked=True)
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_on_behalf_with_expired_delegation_is_forbidden(client, seeded):
    _seed_delegation(seeded, starts_at="now() - interval '2 days'", ends_at="now() - interval '1 day'")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_on_behalf_with_not_yet_started_delegation_is_forbidden(client, seeded):
    _seed_delegation(seeded, starts_at="now() + interval '1 day'", ends_at="now() + interval '2 days'")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_on_behalf_with_wrong_direction_delegation_is_forbidden(client, seeded):
    # 위임은 owner(u_owner)→manager(u_manager) 방향으로 정상 존재하지만, u_owner가 반대로
    # "u_manager를 대리해" 결정하려 하면(방향이 실제 요청과 반대) 매칭되는 위임이 없어야 한다.
    _seed_delegation(seeded, delegator="u_owner", delegate="u_manager")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_manager"),
        headers=_auth_headers(client, user="u_owner"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_on_behalf_ignores_delegation_from_other_company(client, seeded):
    # 타 회사에 같은 두 사용자로 유효해 보이는 위임이 있어도(멤버십도 별도로 그 회사에
    # 존재), company_id가 다르면 이 승인(cmp1)에는 적용되지 않아야 한다(테넌트 격리).
    seeded.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES ('cmp_other','다른 회사','owner_only');
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner_other','cmp_other','u_owner','owner','active'),
          ('m_manager_other','cmp_other','u_manager','manager','active');
    """))
    seeded.flush()
    _seed_delegation(seeded, company="cmp_other")
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(on_behalf_of_user_id="u_owner"),
        headers=_auth_headers(client, user="u_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_approve_with_wrong_pin_is_rejected(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin="0000"), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_approve_with_pin_method_but_missing_pin_value_is_rejected(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin=None), headers=_auth_headers(client)
    )
    assert resp.status_code == 422, resp.text


def test_approve_with_pin_method_but_user_has_no_pin_registered_is_rejected(client, seeded):
    seeded.execute(text("UPDATE users SET pin_hash=NULL WHERE id='u_owner'"))
    seeded.flush()
    no_pin_resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin=None), headers=_auth_headers(client)
    )
    wrong_pin_resp = client.post(
        "/api/v1/approvals/apv1/approve", json=_body(pin="0000"), headers=_auth_headers(client)
    )
    assert no_pin_resp.status_code == wrong_pin_resp.status_code == 422
    # 등록 여부가 응답 메시지로 새어나가지 않는지 확인 — 오답과 동일한 메시지여야 한다.
    assert no_pin_resp.json()["detail"] == wrong_pin_resp.json()["detail"]


def test_approve_with_biometric_method_skips_pin_check(client):
    resp = client.post(
        "/api/v1/approvals/apv1/approve",
        json=_body(identity_method="biometric", pin=None),
        headers=_auth_headers(client),
    )
    assert resp.status_code == 200, resp.text


def test_reject_with_wrong_pin_is_rejected(client):
    resp = client.post(
        "/api/v1/approvals/apv1/reject",
        json=_body(pin="0000", reason="근거 확인 필요"),
        headers=_auth_headers(client),
    )
    assert resp.status_code == 422, resp.text
