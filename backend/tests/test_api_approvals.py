"""POST /api/v1/approvals/{id}/approve|reject — docs/DB_SCHEMA.md §5.3 승인 게이트
불변식이 실제 HTTP 계층에서 강제되는지 검증한다.

일괄(batch) 엔드포인트는 존재하지 않는다(GOTCHAS §3) — 이 파일에도 그런 테스트가
없는 것 자체가 의도다.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app

NOW = "2026-07-12T08:00:00+00:00"


def _seed_base(conn):
    conn.execute(
        text(
            "INSERT INTO companies (id, name, approval_policy, created_at, updated_at) "
            "VALUES ('cmp_1', '테스트 사업장', 'owner_only', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO users (id, phone, name, terms_agreed_at, created_at, updated_at) VALUES "
            "('usr_owner', '010-0000-0001', '김대표', :now, :now, :now), "
            "('usr_manager', '010-0000-0002', '박주임', :now, :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO memberships (id, company_id, user_id, role, status, created_at, updated_at) VALUES "
            "('mem_owner', 'cmp_1', 'usr_owner', 'owner', 'active', :now, :now), "
            "('mem_manager', 'cmp_1', 'usr_manager', 'manager', 'active', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at, created_at, updated_at) "
            "VALUES ('wrk_1', 'cmp_1', 'Nguyen Van A', '베트남', '2026-08-09', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO citations (id, grade, status, title, source, ingest_at, created_at, updated_at) "
            "VALUES ('cit_a', 'A', 'official', '출입국관리법 제25조', '국가법령정보센터', :now, :now, :now)"
        ),
        {"now": NOW},
    )


def _seed_case_with_pending_approval(
    conn, *, case_id, action_id, approval_id, severity="HIGH", state="approval_pending",
    action_type="send_message", with_citation=True, due_date="2026-08-09",
):
    # due_date는 호출부마다 달라야 한다 — ux_cases_reuse(company_id, worker_id, case_type,
    # due_date) 부분 유니크가 같은 근로자·유형·기한의 열린 케이스 중복을 막는다(§4.3).
    conn.execute(
        text(
            "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, created_at, updated_at) "
            "VALUES (:case_id, 'cmp_1', :case_code, 'wrk_1', 'visa_expiry', '테스트 케이스', :severity, :state, :due_date, :now, :now)"
        ),
        {"case_id": case_id, "case_code": f"case_{case_id}", "severity": severity, "state": state, "due_date": due_date, "now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, requires_approval, created_at, updated_at) "
            "VALUES (:action_id, 'cmp_1', :case_id, 'approve', :action_type, '승인하기', 1, :now, :now)"
        ),
        {"action_id": action_id, "case_id": case_id, "action_type": action_type, "now": NOW},
    )
    if with_citation:
        conn.execute(
            text("INSERT INTO case_citations (case_id, citation_id, added_by_actor, created_at) VALUES (:case_id, 'cit_a', 'rule', :now)"),
            {"case_id": case_id, "now": NOW},
        )
    conn.execute(
        text(
            "INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at, created_at) "
            "VALUES (:approval_id, 'cmp_1', :case_id, :action_id, 'pending', 'agent', :now, :now)"
        ),
        {"approval_id": approval_id, "case_id": case_id, "action_id": action_id, "now": NOW},
    )


@pytest.fixture()
def client(migrated_engine):
    session_factory = sessionmaker(bind=migrated_engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def _override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with migrated_engine.begin() as conn:
        _seed_base(conn)
        _seed_case_with_pending_approval(conn, case_id="cs_1", action_id="act_1", approval_id="apv_1")

    yield TestClient(app)
    app.dependency_overrides.clear()


def _decision_body(**overrides):
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "decided_by_user_id": "usr_owner",
        "identity_method": "pin",
    }
    body.update(overrides)
    return body


def test_approve_success_by_owner(client, migrated_engine):
    resp = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "approved"
    assert data["case_state"] == "human_approved"

    with migrated_engine.connect() as conn:
        evidence_count = conn.execute(
            text("SELECT count(*) FROM evidence_events WHERE approval_id='apv_1'")
        ).scalar_one()
    assert evidence_count == 1


def test_approve_requires_identity_method(client):
    resp = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body(identity_method=None))
    assert resp.status_code == 422, resp.text


def test_manager_cannot_approve_when_policy_owner_only(client):
    resp = client.post(
        "/api/v1/approvals/apv_1/approve",
        json=_decision_body(decided_by_user_id="usr_manager"),
    )
    assert resp.status_code == 403, resp.text


def test_manager_can_approve_low_severity_when_policy_allows(client, migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(text("UPDATE companies SET approval_policy='manager_allowed' WHERE id='cmp_1'"))
        conn.execute(text("UPDATE cases SET severity='LOW' WHERE id='cs_1'"))
    resp = client.post(
        "/api/v1/approvals/apv_1/approve",
        json=_decision_body(decided_by_user_id="usr_manager"),
    )
    assert resp.status_code == 200, resp.text


def test_approve_idempotent_replay_returns_same_result(client, migrated_engine):
    key = str(uuid.uuid4())
    first = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body(idempotency_key=key))
    second = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body(idempotency_key=key))
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["approval"]["status"] == second.json()["approval"]["status"] == "approved"

    with migrated_engine.connect() as conn:
        evidence_count = conn.execute(
            text("SELECT count(*) FROM evidence_events WHERE approval_id='apv_1'")
        ).scalar_one()
    assert evidence_count == 1  # 재처리(replay)라 evidence가 중복 생성되지 않아야 함


def test_approve_different_key_after_already_decided_is_conflict(client):
    first = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body())
    assert first.status_code == 200
    second = client.post("/api/v1/approvals/apv_1/approve", json=_decision_body())  # 새 랜덤 키
    assert second.status_code == 409


def test_approve_blocked_when_no_usable_citation(client, migrated_engine):
    with migrated_engine.begin() as conn:
        _seed_case_with_pending_approval(
            conn, case_id="cs_2", action_id="act_2", approval_id="apv_2", with_citation=False,
            due_date="2026-09-01",
        )
    resp = client.post("/api/v1/approvals/apv_2/approve", json=_decision_body())
    assert resp.status_code == 422, resp.text


def test_reject_requires_reason(client):
    resp = client.post("/api/v1/approvals/apv_1/reject", json=_decision_body(reason=None))
    assert resp.status_code == 422, resp.text


def test_reject_success_transitions_case_to_returned(client):
    resp = client.post("/api/v1/approvals/apv_1/reject", json=_decision_body(reason="근거 확인 필요"))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["approval"]["status"] == "rejected"
    assert data["case_state"] == "returned"


def test_reject_reason_with_phone_number_pattern_blocked(client):
    resp = client.post(
        "/api/v1/approvals/apv_1/reject", json=_decision_body(reason="010-1234-5678로 연락해서 확인")
    )
    assert resp.status_code == 422, resp.text


def test_high_risk_blocked_case_only_allows_handoff_action(client, migrated_engine):
    with migrated_engine.begin() as conn:
        _seed_case_with_pending_approval(
            conn,
            case_id="cs_3",
            action_id="act_3",
            approval_id="apv_3",
            severity="CRITICAL",
            state="blocked",
            action_type="send_message",
            due_date="2026-07-08",
        )
    resp = client.post("/api/v1/approvals/apv_3/approve", json=_decision_body())
    assert resp.status_code == 403, resp.text


def test_approval_not_found_returns_404(client):
    resp = client.post("/api/v1/approvals/nope/approve", json=_decision_body())
    assert resp.status_code == 404
