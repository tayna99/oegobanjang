"""GET/POST /api/v1/response-link/{token} — 근로자 응답 링크(무인증). R3 stage ②.

MESSAGING_CHANNELS.md §3 수신 파이프라인: 인바운드 정규화(thread_messages, direction=
'inbound') → N02(worker_reply_received) → M6 Interpretation(proposed). 근로자 원문은
목록/요약/evidence summary에 절대 노출되지 않는다(GOTCHAS §3).
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


def _seed_response_link(db, *, expires_at: str = "2026-08-01T00:00:00Z") -> None:
    db.execute(text("""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at, preferred_language) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-01','vi');
        INSERT INTO threads (id, company_id, worker_id, channel, last_message_at) VALUES
          ('th1','cmp1','w1','sms', '2026-07-10T09:00:00Z');
    """))
    db.execute(
        text("""
            INSERT INTO thread_messages (id, thread_id, company_id, direction, lang, body_original, body_ko,
                                          received_at, response_token, response_token_expires_at)
            VALUES ('tm_out','th1','cmp1','system','vi','Hay gui ho so cua ban.','서류를 보내주세요.',
                    '2026-07-10T09:00:00Z','tok_valid', :expires_at)
        """),
        {"expires_at": expires_at},
    )
    db.flush()


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    return client


def test_get_view_returns_prompt_and_choices(db):
    _seed_response_link(db)
    client = _client(db)

    resp = client.get("/api/v1/response-link/tok_valid")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["thread_id"] == "th1"
    assert data["worker"]["display_name"] == "Nguyen Van A"
    assert data["lang"] == "vi"
    assert data["prompt"] == "Hay gui ho so cua ban."
    assert "received" in data["choices"]
    app.dependency_overrides.clear()


def test_get_view_unknown_token_is_404(db):
    _seed_response_link(db)
    client = _client(db)

    resp = client.get("/api/v1/response-link/does-not-exist")
    assert resp.status_code == 404, resp.text
    app.dependency_overrides.clear()


def test_get_view_expired_token_is_404(db):
    _seed_response_link(db, expires_at="2020-01-01T00:00:00Z")
    client = _client(db)

    resp = client.get("/api/v1/response-link/tok_valid")
    assert resp.status_code == 404, resp.text
    app.dependency_overrides.clear()


def test_post_choice_creates_high_confidence_interpretation(db):
    _seed_response_link(db)
    client = _client(db)

    resp = client.post("/api/v1/response-link/tok_valid", json={"choice": "received"})
    assert resp.status_code == 201, resp.text

    inbound = db.execute(
        text("SELECT direction, body_original FROM thread_messages WHERE thread_id='th1' AND direction='inbound'")
    ).one()
    assert inbound.direction == "inbound"
    assert "확인했습니다" in inbound.body_original

    interp = db.execute(text("SELECT confidence, status, summary_ko FROM interpretations")).one()
    assert interp.confidence == "high"
    assert interp.status == "proposed"
    assert "확인했습니다" in interp.summary_ko  # 정형 라벨은 허용 — 원문 자유입력은 아니다

    evt = db.execute(text("SELECT type, summary FROM evidence_events WHERE type='worker_reply_received'")).one()
    assert evt.type == "worker_reply_received"
    assert "확인했습니다" not in evt.summary  # evidence summary는 절대 원문/선택 라벨을 담지 않는다
    app.dependency_overrides.clear()


def test_post_free_text_only_creates_low_confidence_interpretation_without_raw_text_leaking(db):
    _seed_response_link(db)
    client = _client(db)

    secret_sentence = "제 여권은 사장님이 가지고 계세요 다음주에 받을 수 있어요"
    resp = client.post("/api/v1/response-link/tok_valid", json={"free_text": secret_sentence})
    assert resp.status_code == 201, resp.text

    inbound = db.execute(
        text("SELECT body_original FROM thread_messages WHERE thread_id='th1' AND direction='inbound'")
    ).one()
    assert inbound.body_original == secret_sentence  # 원문은 스레드 상세(body_original)에만 보관

    interp = db.execute(text("SELECT confidence, summary_ko FROM interpretations")).one()
    assert interp.confidence == "low"
    assert secret_sentence not in interp.summary_ko  # GOTCHAS §3 — 목록/요약에 원문 노출 금지

    evt = db.execute(text("SELECT summary FROM evidence_events WHERE type='worker_reply_received'")).one()
    assert secret_sentence not in evt.summary
    app.dependency_overrides.clear()


def test_post_without_choice_or_free_text_is_rejected(db):
    _seed_response_link(db)
    client = _client(db)

    resp = client.post("/api/v1/response-link/tok_valid", json={})
    assert resp.status_code == 422, resp.text
    assert db.execute(text("SELECT count(*) FROM interpretations")).scalar_one() == 0
    app.dependency_overrides.clear()


def test_post_updates_thread_last_message_at(db):
    _seed_response_link(db)
    client = _client(db)

    client.post("/api/v1/response-link/tok_valid", json={"choice": "not_yet"})

    last_message_at = db.execute(text("SELECT last_message_at FROM threads WHERE id='th1'")).scalar_one()
    assert last_message_at > dt.datetime(2026, 7, 10, 9, 0, tzinfo=dt.timezone.utc)
    app.dependency_overrides.clear()
