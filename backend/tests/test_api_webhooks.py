"""POST /api/v1/webhooks/zalo — Zalo OA 인바운드 webhook. R3 stage ④.

MESSAGING_CHANNELS.md §3: "Zalo OA webhook은 붙는 시점부터 같은 정규화 지점에 합류한다."
자격 증명(공유 시크릿) 미설정 시 503으로 항상 거부 — 발신 어댑터의 credential-gating 원칙을
인바운드에도 동일 적용한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _seed(db) -> None:
    db.execute(text("""
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트 회사');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at, preferred_language) VALUES
          ('w1','cmp1','Tran Thi H.','베트남','2026-09-01','vi');
        INSERT INTO threads (id, company_id, worker_id, channel) VALUES ('th1','cmp1','w1','zalo');
    """))
    db.flush()


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def test_webhook_rejects_when_secret_unset(db, monkeypatch):
    monkeypatch.delenv("ZALO_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()
    _seed(db)
    client = _client(db)

    resp = client.post(
        "/api/v1/webhooks/zalo",
        json={"thread_id": "th1", "text": "Da nhan duoc, cam on."},
        headers={"X-Webhook-Secret": "anything"},
    )
    assert resp.status_code == 503, resp.text
    assert db.execute(text("SELECT count(*) FROM thread_messages")).scalar_one() == 0
    app.dependency_overrides.clear()


def test_webhook_rejects_wrong_secret(db, monkeypatch):
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "correct-secret")
    get_settings.cache_clear()
    _seed(db)
    client = _client(db)

    resp = client.post(
        "/api/v1/webhooks/zalo",
        json={"thread_id": "th1", "text": "Da nhan duoc, cam on."},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert resp.status_code == 401, resp.text
    app.dependency_overrides.clear()


def test_webhook_rejects_missing_secret_header(db, monkeypatch):
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "correct-secret")
    get_settings.cache_clear()
    _seed(db)
    client = _client(db)

    resp = client.post("/api/v1/webhooks/zalo", json={"thread_id": "th1", "text": "hi"})
    assert resp.status_code == 401, resp.text
    app.dependency_overrides.clear()


def test_webhook_ingests_reply_into_same_normalization_pipeline(db, monkeypatch):
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "correct-secret")
    get_settings.cache_clear()
    _seed(db)
    client = _client(db)

    resp = client.post(
        "/api/v1/webhooks/zalo",
        json={"thread_id": "th1", "text": "Da nhan duoc, cam on."},
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert resp.status_code == 204, resp.text

    inbound = db.execute(
        text("SELECT direction, lang, body_original FROM thread_messages WHERE thread_id='th1'")
    ).one()
    assert inbound.direction == "inbound"
    assert inbound.lang == "vi"
    assert inbound.body_original == "Da nhan duoc, cam on."

    interp = db.execute(text("SELECT confidence, status FROM interpretations")).one()
    assert interp.confidence == "low"  # webhook은 항상 자유 입력(버튼 선택 없음)
    assert interp.status == "proposed"

    evt = db.execute(text("SELECT type, summary FROM evidence_events WHERE type='worker_reply_received'")).one()
    assert "Da nhan duoc" not in evt.summary  # 원문 미노출(GOTCHAS §3)
    app.dependency_overrides.clear()


def test_webhook_unknown_thread_is_404(db, monkeypatch):
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "correct-secret")
    get_settings.cache_clear()
    _seed(db)
    client = _client(db)

    resp = client.post(
        "/api/v1/webhooks/zalo",
        json={"thread_id": "does-not-exist", "text": "hi"},
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert resp.status_code == 404, resp.text
    app.dependency_overrides.clear()
