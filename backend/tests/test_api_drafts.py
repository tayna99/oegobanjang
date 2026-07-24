"""GET /api/v1/cases/{case_id}/draft — 초안 읽기(SD-5). plans/SEED_DESIGN_2026-07-20.md Part B5(b).

test_api_cases.py와 동일한 전용 테스트 앱(cases_router만) + 세션 부트스트랩 관례를 따른다 —
초안 엔드포인트가 그 라우터에 함께 등록돼 있다.
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
        INSERT INTO cases
          (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, prepared_by)
        VALUES
          ('cs1','cmp1','case_001','w1','visa_expiry','비자 만료 D-30','HIGH','approval_pending','2026-08-09','rule'),
          ('cs_nodraft','cmp1','case_002','w1','visa_expiry','서류 없는 케이스','LOW','draft', NULL,'rule');
        INSERT INTO cases (id, company_id, case_code, case_type, title, severity, state, prepared_by)
        VALUES ('cs_other','cmp2','case_101','other','다른 회사 케이스','LOW','draft','rule');
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


def test_get_case_draft_returns_draft_with_ordered_langs(client, seeded):
    seeded.execute(text("""
        INSERT INTO drafts (id, company_id, case_id, channel, purpose, status)
        VALUES ('drf1','cmp1','cs1','Zalo','서류 요청 메시지','draft');
        INSERT INTO draft_variants (id, company_id, draft_id, lang, text, is_revised, created_at) VALUES
          ('dv1','cmp1','drf1','ko','한국어 원문', false, now()),
          ('dv2','cmp1','drf1','vi','베트남어 원문', false, now() + interval '1 second');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs1/draft", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["draft_id"] == "drf1"
    assert data["channel"] == "Zalo"
    assert data["purpose"] == "서류 요청 메시지"
    assert data["status"] == "draft"
    assert [item["lang"] for item in data["langs"]] == ["ko", "vi"]
    assert data["langs"][0] == {"lang": "ko", "text": "한국어 원문", "is_revised": False}


def test_get_case_draft_prefers_most_recent_non_terminal_draft(client, seeded):
    # db/schema.sql trg_draft_variants_editable_parent: draft_variants는 부모가 편집 가능
    # (draft/revision_requested)할 때만 붙을 수 있다 — 그래서 'draft'로 만든 뒤 변형을 넣고
    # 나서야 'superseded'로 전이한다(trg_drafts_approval_state_insert가 직접 rejected INSERT도
    # 막는다 — 이 종결 상태 필터링 테스트는 직접 삽입 가능한 'superseded'로 검증한다).
    seeded.execute(text("""
        INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, created_at) VALUES
          ('drf_old','cmp1','cs1','Zalo','대체된 초안','draft', now() - interval '1 day'),
          ('drf_new','cmp1','cs1','Zalo','재작성 초안','draft', now());
        INSERT INTO draft_variants (id, company_id, draft_id, lang, text, is_revised) VALUES
          ('dv_old','cmp1','drf_old','ko','옛 초안 문구', false),
          ('dv_new','cmp1','drf_new','ko','새 초안 문구', false);
        UPDATE drafts SET status = 'superseded' WHERE id = 'drf_old';
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs1/draft", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    assert resp.json()["draft_id"] == "drf_new"


def test_get_case_draft_falls_back_to_most_recent_when_all_terminal(client, seeded):
    seeded.execute(text("""
        INSERT INTO drafts (id, company_id, case_id, channel, purpose, status, created_at) VALUES
          ('drf_a','cmp1','cs1','Zalo','초안 A','draft', now() - interval '1 day'),
          ('drf_b','cmp1','cs1','Zalo','초안 B','draft', now());
        INSERT INTO draft_variants (id, company_id, draft_id, lang, text, is_revised) VALUES
          ('dv_b','cmp1','drf_b','ko','최근 종결 초안 문구', false);
        UPDATE drafts SET status = 'superseded' WHERE id IN ('drf_a','drf_b');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs1/draft", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    assert resp.json()["draft_id"] == "drf_b"


def test_get_case_draft_includes_revised_variant_flag(client, seeded):
    seeded.execute(text("""
        INSERT INTO drafts (id, company_id, case_id, channel, purpose, status)
        VALUES ('drf1','cmp1','cs1','Zalo','서류 요청 메시지','draft');
        INSERT INTO draft_variants (id, company_id, draft_id, lang, text, is_revised, created_at) VALUES
          ('dv1','cmp1','drf1','ko','원문', false, now()),
          ('dv2','cmp1','drf1','ko','수정본', true, now() + interval '1 second');
    """))
    seeded.flush()

    resp = client.get("/api/v1/cases/cs1/draft", headers=_auth_header(seeded))
    assert resp.status_code == 200, resp.text
    langs = resp.json()["langs"]
    assert langs == [
        {"lang": "ko", "text": "원문", "is_revised": False},
        {"lang": "ko", "text": "수정본", "is_revised": True},
    ]


def test_get_case_draft_without_any_draft_is_not_found(client, seeded):
    resp = client.get("/api/v1/cases/cs_nodraft/draft", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_case_draft_for_other_company_case_is_not_found(client, seeded):
    resp = client.get("/api/v1/cases/cs_other/draft", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_case_draft_missing_case_is_not_found(client, seeded):
    resp = client.get("/api/v1/cases/no-such-case/draft", headers=_auth_header(seeded))
    assert resp.status_code == 404, resp.text


def test_get_case_draft_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/cases/cs1/draft")
    assert resp.status_code == 401, resp.text
