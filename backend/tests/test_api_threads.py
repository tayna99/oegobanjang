"""GET /api/v1/threads · GET /api/v1/threads/{thread_id} — 컨택 스레드 읽기 API 검증.

plans/NEXT_ROADMAP_2026-07-16.md §R2.3. threads 라우터는 app/main.py에 등록되므로(다른
읽기 도메인과 함께), 이 테스트는 app.api.v1.threads의 router만 담은 전용 테스트 앱을
구성해 검증한다(test_api_cases.py·test_api_briefings.py와 동일한 패턴 — 공유
app.main.app을 모듈 임포트 시점에 변형하지 않는다).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.v1.threads import router as threads_router
from app.db.session import get_db
from app.domain.auth_tokens import hash_secret

_threads_app = FastAPI()
_threads_app.include_router(threads_router)


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
          ('w1','cmp1','Nguyen Van A','베트남','제조1팀','2026-08-09'),
          ('w2','cmp2','Tran Thi B','베트남',NULL,'2026-08-09');
    """))
    db.flush()


def _seed_session(db, *, token: str, user_id: str = "u1") -> None:
    """UserSession을 SQL로 직접 INSERT해 알려진 raw token으로 인증 헤더를 구성한다
    (test_api_auth.py의 test_session_seeded_directly_with_past_expiry_is_rejected 패턴)."""
    db.execute(
        text(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at) "
            "VALUES (:id, :uid, :hash, now() + interval '1 day')"
        ),
        {"id": f"sess_{token}", "uid": user_id, "hash": hash_secret(token)},
    )
    db.flush()


def _seed_thread_with_messages(db, *, tid: str, company_id: str, worker_id: str, channel: str = "sms") -> None:
    db.execute(
        text(
            "INSERT INTO threads (id, company_id, worker_id, channel, last_message_at) "
            "VALUES (:tid, :cid, :wid, :ch, now())"
        ),
        {"tid": tid, "cid": company_id, "wid": worker_id, "ch": channel},
    )
    db.execute(
        text(
            "INSERT INTO thread_messages "
            "(id, thread_id, company_id, direction, lang, body_original, body_ko, received_at, created_at) "
            "VALUES (:mid,:tid,:cid,'inbound','vi','xin chao','안녕하세요', now() - interval '1 hour', now() - interval '1 hour')"
        ),
        {"mid": f"{tid}_m1", "tid": tid, "cid": company_id},
    )
    db.execute(
        text(
            "INSERT INTO thread_messages "
            "(id, thread_id, company_id, direction, lang, body_original, body_ko, received_at, created_at) "
            "VALUES (:mid,:tid,:cid,'inbound','vi','toi hieu roi','이해했습니다', now(), now())"
        ),
        {"mid": f"{tid}_m2", "tid": tid, "cid": company_id},
    )
    db.execute(
        text(
            "INSERT INTO interpretations (id, company_id, thread_message_id, summary_ko, confidence, status) "
            "VALUES (:iid,:cid,:mid,'근로자가 이해했다고 응답','high','proposed')"
        ),
        {"iid": f"{tid}_i1", "cid": company_id, "mid": f"{tid}_m2"},
    )
    db.flush()


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    _threads_app.dependency_overrides[get_db] = _override
    yield TestClient(_threads_app)
    _threads_app.dependency_overrides.clear()


def _auth_headers(token: str = "raw-token-1") -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_list_threads_returns_message_count_and_worker(client, seeded):
    _seed_thread_with_messages(seeded, tid="th1", company_id="cmp1", worker_id="w1")
    _seed_session(seeded, token="raw-token-1")

    resp = client.get("/api/v1/threads", headers=_auth_headers())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "th1"
    assert data[0]["message_count"] == 2
    assert data[0]["channel"] == "sms"
    assert data[0]["worker"]["display_name"] == "Nguyen Van A"
    assert data[0]["worker"]["team"] == "제조1팀"
    # 코드리뷰 지적(PR #16 P1): 목록이 해석 상태를 안 내려주면 real 모드 목록 화면의 응답
    # 도착 배지·정렬이 항상 죽는다 — _seed_thread_with_messages가 마지막 메시지에 심어둔
    # proposed 해석이 목록 단계에서도 그대로 보여야 한다.
    assert data[0]["latest_interpretation_status"] == "proposed"


def test_list_threads_latest_interpretation_status_is_none_without_interpretation(client, seeded):
    seeded.execute(
        text(
            "INSERT INTO threads (id, company_id, worker_id, channel, last_message_at) "
            "VALUES ('th_no_interp','cmp1','w1','sms', now())"
        )
    )
    seeded.flush()
    _seed_session(seeded, token="raw-token-1")

    resp = client.get("/api/v1/threads", headers=_auth_headers())
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["latest_interpretation_status"] is None


def test_list_threads_latest_interpretation_status_follows_most_recent_message(client, seeded):
    """가장 최근 메시지가 해석이 없어도, 해석이 달린 메시지 중 가장 최근 것을 기준으로 삼는다
    (threads.ts toThreadDetail의 reverse-find와 동일한 우선순위를 서버에서 재현)."""
    seeded.execute(
        text(
            "INSERT INTO threads (id, company_id, worker_id, channel, last_message_at) "
            "VALUES ('th_order','cmp1','w1','sms', now())"
        )
    )
    seeded.execute(
        text(
            "INSERT INTO thread_messages "
            "(id, thread_id, company_id, direction, created_at) "
            "VALUES ('th_order_m1','th_order','cmp1','inbound', now() - interval '2 hour')"
        )
    )
    seeded.execute(
        text(
            "INSERT INTO thread_messages "
            "(id, thread_id, company_id, direction, created_at) "
            "VALUES ('th_order_m2','th_order','cmp1','inbound', now() - interval '1 hour')"
        )
    )
    seeded.execute(
        text(
            "INSERT INTO thread_messages "
            "(id, thread_id, company_id, direction, created_at) "
            "VALUES ('th_order_m3','th_order','cmp1','inbound', now())"
        )
    )
    seeded.execute(
        text(
            "INSERT INTO interpretations (id, company_id, thread_message_id, summary_ko, confidence, status) "
            "VALUES ('th_order_i1','cmp1','th_order_m1','오래된 해석','high','confirmed')"
        )
    )
    seeded.execute(
        text(
            "INSERT INTO interpretations (id, company_id, thread_message_id, summary_ko, confidence, status) "
            "VALUES ('th_order_i2','cmp1','th_order_m2','최근 메시지의 해석','high','proposed')"
        )
    )
    # th_order_m3(가장 최근 메시지)는 해석이 없다 — m2의 해석(proposed)이 반영돼야 한다.
    seeded.flush()
    _seed_session(seeded, token="raw-token-1")

    resp = client.get("/api/v1/threads", headers=_auth_headers())
    assert resp.status_code == 200, resp.text
    by_id = {t["id"]: t for t in resp.json()}
    assert by_id["th_order"]["latest_interpretation_status"] == "proposed"


def test_get_thread_detail_returns_messages_in_order_with_interpretation(client, seeded):
    _seed_thread_with_messages(seeded, tid="th1", company_id="cmp1", worker_id="w1")
    _seed_session(seeded, token="raw-token-1")

    resp = client.get("/api/v1/threads/th1", headers=_auth_headers())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == "th1"
    assert len(data["messages"]) == 2
    # 시간순: m1이 1시간 전, m2가 방금 — m1이 먼저 와야 한다.
    assert data["messages"][0]["id"] == "th1_m1"
    assert data["messages"][0]["interpretation"] is None
    assert data["messages"][1]["id"] == "th1_m2"
    assert data["messages"][1]["interpretation"]["summary_ko"] == "근로자가 이해했다고 응답"
    assert data["messages"][1]["interpretation"]["confidence"] == "high"


def test_threads_without_session_is_unauthorized(client):
    resp = client.get("/api/v1/threads")
    assert resp.status_code == 401, resp.text

    resp2 = client.get("/api/v1/threads/th1")
    assert resp2.status_code == 401, resp2.text


def test_other_company_thread_is_invisible_and_returns_404(client, seeded):
    _seed_thread_with_messages(seeded, tid="th1", company_id="cmp1", worker_id="w1")
    _seed_thread_with_messages(seeded, tid="th2", company_id="cmp2", worker_id="w2")
    _seed_session(seeded, token="raw-token-1")

    list_resp = client.get("/api/v1/threads", headers=_auth_headers())
    assert list_resp.status_code == 200, list_resp.text
    ids = [t["id"] for t in list_resp.json()]
    assert ids == ["th1"]  # cmp2의 th2는 섞이지 않는다

    detail_resp = client.get("/api/v1/threads/th2", headers=_auth_headers())
    assert detail_resp.status_code == 404, detail_resp.text  # 존재 여부를 노출하지 않는다


def test_unknown_thread_id_is_not_found(client, seeded):
    _seed_session(seeded, token="raw-token-1")
    resp = client.get("/api/v1/threads/nope", headers=_auth_headers())
    assert resp.status_code == 404, resp.text
