"""GET /api/v1/cases(목록, R2.3) · GET /api/v1/cases/{case_id}(상세, R2.4).

이 테스트는 app/api/v1/cases.py의 router만 담은 전용 테스트 앱을 구성해 검증한다.
DB 레벨 가드레일(테넌트 격리 등)은 db/validate.py가 담당한다 — 이 pytest는 서비스 계층
(회사 스코프 필터링·조립·세션 인증)을 PG 실 인스턴스에서 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.v1.cases import router as cases_router
from app.db.session import get_db
from app.domain.auth_tokens import hash_secret

_cases_app = FastAPI()
_cases_app.include_router(cases_router)


def _seed_base(db):
    db.execute(text("""
        INSERT INTO companies (id, name, approval_policy) VALUES
          ('cmp1','테스트1','owner_only'),
          ('cmp2','테스트2','owner_only');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u1','010-0000-0001','김대표', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m1','cmp1','u1','owner','active');
        INSERT INTO workers (id, company_id, display_name, nationality, team, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','생산1팀','2026-08-09');
    """))
    db.flush()


def _auth_header(db, user_id: str = "u1") -> dict:
    """세션 토큰을 OTP 로그인 없이 직접 발급한다 — sessions 테이블에 알려진 raw token의
    해시를 INSERT하고 그 raw token으로 Authorization 헤더를 구성한다."""
    raw_token = f"raw-token-{user_id}"
    db.execute(
        text(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at) "
            "VALUES (:id, :uid, :hash, now() + interval '30 days')"
        ),
        {"id": f"sess_{user_id}", "uid": user_id, "hash": hash_secret(raw_token)},
    )
    db.flush()
    return {"Authorization": f"Bearer {raw_token}"}


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    _cases_app.dependency_overrides[get_db] = _override
    yield TestClient(_cases_app)
    _cases_app.dependency_overrides.clear()


def test_list_cases_returns_case_with_worker_and_actions(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases
          (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, prepared_by)
        VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료 D-30','HIGH','risk_review','2026-08-09','rule');
        INSERT INTO next_actions
          (id, company_id, case_id, kind, action_type, label, state, requires_approval, slot)
        VALUES
          ('act_p','cmp1','cs1','draft','request_document','서류 요청 초안','ready',false,'primary'),
          ('act_s','cmp1','cs1','approve','send_message','메시지 승인 요청','ready',true,'secondary');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    case = data[0]
    assert case["id"] == "cs1"
    assert case["case_code"] == "case_001"
    assert case["severity"] == "HIGH"
    assert case["state"] == "risk_review"
    assert case["due_date"] == "2026-08-09"
    assert case["worker"] == {"display_name": "Nguyen Van A", "nationality": "베트남", "team": "생산1팀"}
    assert case["primary_action"]["action_id"] == "act_p"
    assert case["primary_action"]["label"] == "서류 요청 초안"
    assert case["primary_action"]["requires_approval"] is False
    assert case["secondary_action"]["action_id"] == "act_s"
    assert case["secondary_action"]["requires_approval"] is True


def test_list_cases_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 401, resp.text


def test_list_cases_excludes_other_company_cases(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases (id, company_id, case_code, case_type, title, severity, state, prepared_by)
        VALUES ('cs_other','cmp2','case_101','other','다른 회사 케이스','LOW','draft','rule');
        INSERT INTO cases
          (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, prepared_by)
        VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료 D-30','HIGH','risk_review','2026-08-09','rule');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    ids = [c["id"] for c in resp.json()]
    assert ids == ["cs1"]
    assert "cs_other" not in ids


def test_list_cases_handles_case_without_worker_or_actions(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases (id, company_id, case_code, case_type, title, severity, state, prepared_by)
        VALUES ('cs2','cmp1','case_002','other','근로자 미배정 케이스','MEDIUM','draft','rule');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    case = next(c for c in resp.json() if c["id"] == "cs2")
    assert case["worker"] is None
    assert case["primary_action"] is None
    assert case["secondary_action"] is None


# GET /api/v1/cases/{case_id} — 상세(R2.4). ApprovePage의 Blocker A+B 해소 대상.


def test_get_case_detail_includes_citation_count_guard_note_and_pending_approval(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases
          (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, prepared_by, guard_note)
        VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료 D-30','HIGH','approval_pending','2026-08-09','rule','행정사 전달 필요');
        INSERT INTO next_actions
          (id, company_id, case_id, kind, action_type, label, state, requires_approval, slot)
        VALUES
          ('act1','cmp1','cs1','approve','send_message','승인하기','ready',true,'primary');
        INSERT INTO citations (id, grade, status, title, source, ingest_at)
        VALUES ('cit_a','A','official','출입국관리법 제25조','국가법령정보센터', now());
        INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor)
        VALUES ('cmp1','cs1','cit_a','rule');
    """))
    # checklist는 JSON 콜론(":checked":false)이 SQLAlchemy text()의 바인드 파라미터 문법과
    # 충돌해 별도 파라미터 바인딩 단일 문장으로 분리한다(위 멀티 스테이트먼트 블록과 달리
    # 문장이 하나뿐이라 바인딩이 정상 동작한다).
    seeded.execute(
        text(
            "INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, "
            "requested_at, checklist) VALUES "
            "('apv1','cmp1','cs1','act1','pending','agent', now(), CAST(:checklist AS jsonb))"
        ),
        {"checklist": '[{"key":"risk","label":"위험도 검토","checked":false}]'},
    )
    seeded.flush()

    resp = client.get("/api/v1/cases/cs1", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == "cs1"
    assert data["usable_citation_count"] == 1
    assert data["guard_note"] == "행정사 전달 필요"
    assert data["pending_approval"]["id"] == "apv1"
    assert data["pending_approval"]["action_id"] == "act1"
    assert data["pending_approval"]["checklist"] == [{"key": "risk", "label": "위험도 검토", "checked": False}]


def test_get_case_detail_pending_approval_is_null_when_none(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases (id, company_id, case_code, case_type, title, severity, state, prepared_by)
        VALUES ('cs2','cmp1','case_002','other','승인 없는 케이스','LOW','draft','rule');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs2", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    assert resp.json()["pending_approval"] is None
    assert resp.json()["usable_citation_count"] == 0


def test_get_case_detail_for_other_company_case_is_not_found(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases (id, company_id, case_code, case_type, title, severity, state, prepared_by)
        VALUES ('cs_other','cmp2','case_101','other','다른 회사 케이스','LOW','draft','rule');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs_other", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_case_detail_missing_case_is_not_found(client, seeded):
    resp = client.get("/api/v1/cases/no-such-case", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_case_detail_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/cases/cs1")
    assert resp.status_code == 401, resp.text
