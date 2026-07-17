"""GET /api/v1/briefings/latest — 최신 브리핑 조회. plans/NEXT_ROADMAP_2026-07-16.md §R2.3.

이 라우터는 아직 app/main.py에 등록되지 않으므로(여러 도메인 동시 작업 충돌 방지),
이 테스트는 app/api/v1/briefings.py의 router만 담은 전용 테스트 앱을 구성해 검증한다.
DB 레벨 가드레일(테넌트 격리 등)은 db/validate.py가 담당한다 — 이 pytest는 서비스 계층
(회사 스코프 필터링·조립·rank 순서·세션 인증)을 PG 실 인스턴스에서 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.v1.briefings import router as briefings_router
from app.db.session import get_db
from app.domain.auth_tokens import hash_secret

_briefings_app = FastAPI()
_briefings_app.include_router(briefings_router)


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

    _briefings_app.dependency_overrides[get_db] = _override
    yield TestClient(_briefings_app)
    _briefings_app.dependency_overrides.clear()


def _seed_case(db, company_id: str, case_id: str, case_code: str, title: str):
    """worker 배정 없는 최소 케이스 1건을 심는다 — 다른 회사(cmp2)에는 workers 시드가 없어
    worker_id FK를 걸 수 없으므로 일부러 NULL로 둔다."""
    db.execute(
        text(
            "INSERT INTO cases (id, company_id, case_code, case_type, title, severity, "
            "state, due_date, prepared_by) VALUES "
            "(:id, :cmp, :code, 'visa_expiry', :title, 'HIGH', 'risk_review', '2026-08-09', 'rule')"
        ),
        {"id": case_id, "cmp": company_id, "code": case_code, "title": title},
    )
    db.flush()


def test_get_latest_briefing_returns_cases_in_rank_order(client, seeded):
    seeded.execute(text("""
        INSERT INTO cases
          (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, prepared_by)
        VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료 D-30','HIGH','risk_review','2026-08-09','rule'),
          ('cs2','cmp1','case_002','w1','visa_expiry','비자 만료 D-10','CRITICAL','risk_review','2026-07-27','rule');
        INSERT INTO next_actions
          (id, company_id, case_id, kind, action_type, label, state, requires_approval, slot)
        VALUES
          ('act_p','cmp1','cs1','draft','request_document','서류 요청 초안','ready',false,'primary');
        INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash)
        VALUES ('br1','cmp1','2026-07-17', now(), 'hash1');
        INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank)
        VALUES
          ('bi1','cmp1','br1','cs2',1),
          ('bi2','cmp1','br1','cs1',2);
    """))
    seeded.flush()

    resp = client.get("/api/v1/briefings/latest", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == "br1"
    assert data["briefing_date"] == "2026-07-17"
    assert len(data["cases"]) == 2
    # rank 순서 그대로: cs2(rank=1)가 먼저, cs1(rank=2)가 다음.
    assert data["cases"][0]["id"] == "cs2"
    assert data["cases"][0]["case_code"] == "case_002"
    assert data["cases"][0]["severity"] == "CRITICAL"
    assert data["cases"][1]["id"] == "cs1"
    assert data["cases"][1]["case_code"] == "case_001"
    # CaseOut 필드(worker·primary_action)도 cases 서비스 조립 그대로 채워진다.
    assert data["cases"][1]["worker"] == {"display_name": "Nguyen Van A", "nationality": "베트남", "team": "생산1팀"}
    assert data["cases"][1]["primary_action"]["action_id"] == "act_p"
    assert data["cases"][0]["primary_action"] is None


def test_get_latest_briefing_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/briefings/latest")
    assert resp.status_code == 401, resp.text


def test_get_latest_briefing_without_any_briefing_is_not_found(client, seeded):
    resp = client.get("/api/v1/briefings/latest", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_latest_briefing_does_not_leak_other_company_briefing(client, seeded):
    # cmp1(로그인 회사)에 브리핑이 아예 없어도, cmp2(다른 회사)에 최신 브리핑이 있다는 이유로
    # 그 데이터가 새어 나오면 안 된다 — 404여야 한다.
    _seed_case(seeded, "cmp2", "cs_other", "case_101", "다른 회사 케이스")
    seeded.execute(text("""
        INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash)
        VALUES ('br_other','cmp2','2026-07-17', now(), 'hash_other');
        INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank)
        VALUES ('bi_other','cmp2','br_other','cs_other',1);
    """))
    seeded.flush()

    resp = client.get("/api/v1/briefings/latest", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_latest_briefing_scopes_cases_to_own_company_when_both_have_briefings(client, seeded):
    # 두 회사 모두 최신 브리핑이 있을 때, cmp1 로그인 사용자는 cmp1 케이스만 받아야 한다
    # (cmp2의 케이스가 섞여 들어오면 안 된다).
    _seed_case(seeded, "cmp1", "cs1", "case_001", "우리 회사 케이스")
    _seed_case(seeded, "cmp2", "cs_other", "case_101", "다른 회사 케이스")
    seeded.execute(text("""
        INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash)
        VALUES
          ('br1','cmp1','2026-07-17', now(), 'hash1'),
          ('br_other','cmp2','2026-07-17', now(), 'hash_other');
        INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank)
        VALUES
          ('bi1','cmp1','br1','cs1',1),
          ('bi_other','cmp2','br_other','cs_other',1);
    """))
    seeded.flush()

    resp = client.get("/api/v1/briefings/latest", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == "br1"
    ids = [c["id"] for c in data["cases"]]
    assert ids == ["cs1"]
    assert "cs_other" not in ids
