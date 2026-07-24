"""POST /api/v1/outbox("실행 확인") · GET /api/v1/outbox — 발송 대기열. R3 stage ②.

MESSAGING_CHANNELS.md §1 각주²(승인≠실행) + §2(발신 파이프라인 4대 검사: 이벤트
idempotency·리마인드 쿨다운·48h 재발송·발송 창).
"""

from __future__ import annotations

import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_db
from app.domain.outbox_exceptions import OutboxAlreadyQueuedError, OutboxReminderCooldownError, OutboxResendNotEligibleError
from app.main import app
from app.services import outbox as outbox_service
from app.services.channels.base import AdapterResult
from app.services.outbox import compute_send_window, create_and_dispatch


def _seed_base(db) -> None:
    db.execute(text("""
        INSERT INTO companies (id, name, timezone) VALUES ('cmp1','테스트 회사','Asia/Seoul');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_manager','010-0000-0002','박주임', now()),
          ('u_viewer','010-0000-0003','최열람', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_manager','cmp1','u_manager','manager','active'),
          ('m_viewer','cmp1','u_viewer','viewer','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at, preferred_language) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-01','vi');
        INSERT INTO threads (id, company_id, worker_id, channel) VALUES ('th1','cmp1','w1','sms');
        INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state) VALUES
          ('cs1','cmp1','case_001','w1','reporting_deadline','케이스1','LOW','approval_pending');
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval, slot) VALUES
          ('act1','cmp1','cs1','approve','send_message','서류요청 발송','ready',true,'primary');
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv1','cmp1','cs1','act1','pending','user', now());
        -- 초안은 draft(편집 가능) 상태에서 variants를 받은 뒤 pending_approval로 넘어가고,
        -- 승인 결정이 approvals_sync_linked_drafts 트리거로 approved까지 자동 동기화한다
        -- (db/seed_demo.sql drf_nguyen과 동일한 순서 — 직접 approved로 INSERT하거나 승인된
        -- 초안의 variants를 건드리면 각각 drafts_approval_state_insert·
        -- draft_variants_editable_parent 트리거가 막는다).
        INSERT INTO drafts (id, company_id, case_id, channel, purpose, status) VALUES
          ('drf1','cmp1','cs1','sms','서류 요청','draft');
        INSERT INTO draft_variants (id, company_id, draft_id, lang, text) VALUES
          ('dv1_vi','cmp1','drf1','vi','Xin chao, vui long gui ho so.'),
          ('dv1_ko','cmp1','drf1','ko','서류를 보내주세요.');
        UPDATE drafts SET status='pending_approval', approval_id='apv1' WHERE id='drf1';
        UPDATE approvals SET status='approved', decided_by_user_id='u_owner', identity_method='pin', decided_at=now()
          WHERE id='apv1';
    """))
    db.flush()


@pytest.fixture()
def seeded(db):
    _seed_base(db)
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch):
    monkeypatch.setenv(
        "WORKER_CHANNEL_RECIPIENTS",
        json.dumps({"w1": {"sms": "01011112222", "alimtalk": "01011112222", "zalo": "zalo-user-1"}}),
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_manager": "010-0000-0002", "u_viewer": "010-0000-0003"}


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str = "u_manager") -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


# --- happy path --------------------------------------------------------------------------


def test_manager_can_dispatch_and_it_records_thread_message_and_evidence(client, seeded):
    resp = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["channel"] == "sms"
    assert data["status"] == "sent"
    assert data["external_id"].startswith("stub:sms:")  # 자격 증명 없음(dev 기본값) — 스텁 구분

    tm = seeded.execute(
        text("SELECT direction, lang, body_original, response_token, case_id FROM thread_messages WHERE thread_id='th1'")
    ).one()
    assert tm.direction == "system"
    assert tm.lang == "vi"
    assert tm.body_original == "Xin chao, vui long gui ho so."
    assert tm.response_token is not None
    assert tm.case_id == "cs1"

    evt = seeded.execute(
        text("SELECT type, case_id, action_id, approval_id FROM evidence_events WHERE type='dispatch_executed'")
    ).one()
    assert evt.case_id == "cs1" and evt.action_id == "act1" and evt.approval_id == "apv1"


@pytest.mark.asyncio
async def test_dispatch_resolves_the_secret_recipient_not_the_display_reference(seeded, monkeypatch):
    monkeypatch.setenv("WORKER_CHANNEL_RECIPIENTS", json.dumps({"w1": {"sms": "01011112222"}}))
    get_settings.cache_clear()
    destinations: list[str] = []

    class _CapturingAdapter:
        channel = "sms"

        async def send(self, *, to, body, lang=None):
            destinations.append(to)
            return AdapterResult(status="sent", external_id="provider-message-1")

    monkeypatch.setitem(outbox_service.WORKER_CHANNEL_ADAPTERS, "sms", _CapturingAdapter())

    item = await create_and_dispatch(seeded, "u_manager", "act1")

    assert item.recipient_ref == "worker:w1"
    assert destinations == ["01011112222"]


@pytest.mark.asyncio
async def test_dispatch_fails_closed_without_a_secret_recipient(seeded, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_PEPPER", "test-only-pepper")
    monkeypatch.delenv("WORKER_CHANNEL_RECIPIENTS", raising=False)
    get_settings.cache_clear()
    calls: list[str] = []

    class _CapturingAdapter:
        channel = "sms"

        async def send(self, *, to, body, lang=None):
            calls.append(to)
            return AdapterResult(status="sent", external_id="provider-message-should-not-exist")

    monkeypatch.setitem(outbox_service.WORKER_CHANNEL_ADAPTERS, "sms", _CapturingAdapter())

    item = await create_and_dispatch(seeded, "u_manager", "act1")

    assert item.status == "failed"
    assert item.failed_reason == "delivery recipient is not configured"
    assert calls == []


@pytest.mark.asyncio
async def test_dispatch_claim_is_persisted_before_adapter_call(seeded, monkeypatch):
    observed: list[tuple[str, int]] = []

    class _ClaimInspectingAdapter:
        channel = "sms"

        async def send(self, *, to, body, lang=None):
            row = seeded.execute(text("SELECT status, attempt_count FROM outbox WHERE action_id='act1'")).one()
            observed.append((row.status, row.attempt_count))
            return AdapterResult(status="sent", external_id="provider-message-1")

    monkeypatch.setitem(outbox_service.WORKER_CHANNEL_ADAPTERS, "sms", _ClaimInspectingAdapter())

    await create_and_dispatch(seeded, "u_manager", "act1")

    assert observed == [("dispatching", 1)]


def test_owner_cannot_dispatch(client, seeded):
    resp = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_owner"))
    assert resp.status_code == 403, resp.text
    assert seeded.execute(text("SELECT count(*) FROM outbox")).scalar_one() == 0


def test_viewer_cannot_dispatch(client, seeded):
    resp = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_viewer"))
    assert resp.status_code == 403, resp.text


def test_dispatch_without_session_is_unauthorized(client):
    resp = client.post("/api/v1/outbox", json={"action_id": "act1"})
    assert resp.status_code == 401, resp.text


# --- structural authorization trail (approval gate) ---------------------------------------


def test_dispatch_without_approved_approval_is_forbidden(client, seeded):
    seeded.execute(text("""
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
          ('act2','cmp1','cs1','approve','send_message','2차 발송','ready',true);
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv2','cmp1','cs1','act2','pending','user', now());
    """))
    seeded.flush()

    resp = client.post("/api/v1/outbox", json={"action_id": "act2"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 403, resp.text
    assert seeded.execute(text("SELECT count(*) FROM outbox WHERE action_id='act2'")).scalar_one() == 0


def test_dispatch_rejects_non_send_message_action_type(client, seeded):
    seeded.execute(text("""
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
          ('act_handoff','cmp1','cs1','approve','create_handoff','핸드오프','ready',true);
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv_handoff','cmp1','cs1','act_handoff','pending','user', now());
        UPDATE approvals SET status='approved', decided_by_user_id='u_owner', identity_method='pin', decided_at=now()
          WHERE id='apv_handoff';
    """))
    seeded.flush()

    resp = client.post("/api/v1/outbox", json={"action_id": "act_handoff"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 422, resp.text


# --- idempotency (structural — dedupe_key UNIQUE) ------------------------------------------


def test_dispatch_twice_is_idempotent_not_duplicated(client, seeded):
    first = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))
    assert first.status_code == 201, first.text

    second = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))
    assert second.status_code == 409, second.text

    assert seeded.execute(text("SELECT count(*) FROM outbox WHERE action_id='act1'")).scalar_one() == 1
    assert seeded.execute(text("SELECT count(*) FROM evidence_events WHERE type='dispatch_executed'")).scalar_one() == 1


# --- missing thread / missing content ------------------------------------------------------


def test_dispatch_without_thread_is_unprocessable(client, seeded):
    seeded.execute(text("DELETE FROM threads WHERE id='th1'"))
    seeded.flush()

    resp = client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 422, resp.text


def test_dispatch_without_approved_draft_is_unprocessable(client, seeded):
    # drf1을 지우는 대신(승인된 초안은 트리거가 편집/삭제를 막는다 — draft_variants_editable_parent),
    # 애초에 초안이 없는 별도의 승인된 send_message 액션을 새로 만든다.
    seeded.execute(text("""
        INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state, requires_approval) VALUES
          ('act_no_draft','cmp1','cs1','approve','send_message','초안 없는 발송','ready',true);
        INSERT INTO approvals (id, company_id, case_id, action_id, status, requested_by_actor, requested_at) VALUES
          ('apv_no_draft','cmp1','cs1','act_no_draft','pending','user', now());
        UPDATE approvals SET status='approved', decided_by_user_id='u_owner', identity_method='pin', decided_at=now()
          WHERE id='apv_no_draft';
    """))
    seeded.flush()

    resp = client.post("/api/v1/outbox", json={"action_id": "act_no_draft"}, headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 422, resp.text


# --- alimtalk 실패 → SMS fallback ("채널 중복 금지" — fallback, 중복 발송 아님) -----------------


@pytest.mark.asyncio
async def test_alimtalk_failure_triggers_single_sms_fallback(seeded, monkeypatch):
    seeded.execute(text("UPDATE threads SET channel='alimtalk' WHERE id='th1'"))
    seeded.flush()

    class _FailingAdapter:
        channel = "alimtalk"

        async def send(self, *, to, body, lang=None):
            return AdapterResult(status="failed", external_id=None, detail="template rejected")

    monkeypatch.setitem(outbox_service.WORKER_CHANNEL_ADAPTERS, "alimtalk", _FailingAdapter())

    item = await create_and_dispatch(seeded, "u_manager", "act1")

    assert item.channel == "alimtalk"
    assert item.status == "failed"

    fallback = seeded.execute(
        text("SELECT channel, status, fallback_from_id FROM outbox WHERE fallback_from_id=:id"), {"id": item.id}
    ).one()
    assert fallback.channel == "sms"
    assert fallback.status == "sent"
    assert fallback.fallback_from_id == item.id

    # 재실행해도 fallback이 한 번 더 생기지 않는다("채널 중복 금지").
    from app.services.outbox import _create_and_process_sms_fallback

    await _create_and_process_sms_fallback(seeded, item)
    seeded.commit()
    count = seeded.execute(text("SELECT count(*) FROM outbox WHERE fallback_from_id=:id"), {"id": item.id}).scalar_one()
    assert count == 1


# --- 발송 창(21:00~08:30, CRITICAL은 22:00까지) ---------------------------------------------


def test_compute_send_window_is_sendable_during_business_hours():
    now_local = dt.datetime(2026, 7, 20, 14, 0, tzinfo=dt.timezone.utc)
    assert compute_send_window(now_local, is_critical=False) is None


def test_compute_send_window_holds_after_21_for_normal():
    now_local = dt.datetime(2026, 7, 20, 21, 30, tzinfo=dt.timezone.utc)
    resume = compute_send_window(now_local, is_critical=False)
    assert resume == dt.datetime(2026, 7, 21, 8, 30, tzinfo=dt.timezone.utc)


def test_compute_send_window_allows_critical_until_22():
    now_local = dt.datetime(2026, 7, 20, 21, 30, tzinfo=dt.timezone.utc)
    assert compute_send_window(now_local, is_critical=True) is None


def test_compute_send_window_holds_critical_after_22():
    now_local = dt.datetime(2026, 7, 20, 22, 15, tzinfo=dt.timezone.utc)
    resume = compute_send_window(now_local, is_critical=True)
    assert resume == dt.datetime(2026, 7, 21, 8, 30, tzinfo=dt.timezone.utc)


def test_compute_send_window_holds_before_0830():
    now_local = dt.datetime(2026, 7, 20, 5, 0, tzinfo=dt.timezone.utc)
    resume = compute_send_window(now_local, is_critical=False)
    assert resume == dt.datetime(2026, 7, 20, 8, 30, tzinfo=dt.timezone.utc)


@pytest.mark.asyncio
async def test_dispatch_at_night_is_held_not_sent(seeded):
    night = dt.datetime(2026, 7, 20, 13, 0, tzinfo=dt.timezone.utc)  # Asia/Seoul 22:00 — 발송 보류 시간대

    item = await create_and_dispatch(seeded, "u_manager", "act1", now=night)

    assert item.status == "queued"
    assert item.scheduled_for is not None
    assert item.external_id is None
    assert seeded.execute(text("SELECT count(*) FROM thread_messages WHERE thread_id='th1'")).scalar_one() == 0
    assert seeded.execute(text("SELECT count(*) FROM evidence_events WHERE type='dispatch_executed'")).scalar_one() == 0


# --- 리마인드 쿨다운(24h) --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reminder_cooldown_blocks_second_reminder_within_24h(seeded):
    now = dt.datetime(2026, 7, 20, 10, 0, tzinfo=dt.timezone.utc)
    await create_and_dispatch(seeded, "u_manager", "act1", event_type="reminder", threshold="d3", now=now)

    with pytest.raises(OutboxReminderCooldownError):
        await create_and_dispatch(
            seeded, "u_manager", "act1", event_type="reminder", threshold="d2",
            now=now + dt.timedelta(hours=12),
        )


@pytest.mark.asyncio
async def test_reminder_allowed_after_24h_cooldown(seeded):
    now = dt.datetime(2026, 7, 20, 10, 0, tzinfo=dt.timezone.utc)
    await create_and_dispatch(seeded, "u_manager", "act1", event_type="reminder", threshold="d3", now=now)

    second = await create_and_dispatch(
        seeded, "u_manager", "act1", event_type="reminder", threshold="d2",
        now=now + dt.timedelta(hours=25),
    )
    assert second.status == "sent"


# --- 48h 미응답 재발송(1회) -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resend_rejected_before_48h(seeded):
    now = dt.datetime(2026, 7, 20, 10, 0, tzinfo=dt.timezone.utc)
    await create_and_dispatch(seeded, "u_manager", "act1", now=now)

    with pytest.raises(OutboxResendNotEligibleError):
        await create_and_dispatch(seeded, "u_manager", "act1", event_type="resend", now=now + dt.timedelta(hours=10))


@pytest.mark.asyncio
async def test_resend_rejected_if_worker_already_replied(seeded):
    now = dt.datetime(2026, 7, 20, 10, 0, tzinfo=dt.timezone.utc)
    await create_and_dispatch(seeded, "u_manager", "act1", now=now)
    seeded.execute(text(
        "INSERT INTO thread_messages (id, thread_id, company_id, direction, received_at, created_at) "
        "VALUES ('tm_reply','th1','cmp1','inbound', :at, :at)"
    ), {"at": now + dt.timedelta(hours=20)})
    seeded.flush()

    with pytest.raises(OutboxResendNotEligibleError):
        await create_and_dispatch(seeded, "u_manager", "act1", event_type="resend", now=now + dt.timedelta(hours=49))


@pytest.mark.asyncio
async def test_resend_allowed_once_after_48h_with_no_reply(seeded):
    now = dt.datetime(2026, 7, 20, 10, 0, tzinfo=dt.timezone.utc)
    await create_and_dispatch(seeded, "u_manager", "act1", now=now)

    resend = await create_and_dispatch(
        seeded, "u_manager", "act1", event_type="resend", now=now + dt.timedelta(hours=49)
    )
    assert resend.status == "sent"
    assert resend.event_type == "resend"

    with pytest.raises(OutboxAlreadyQueuedError):
        await create_and_dispatch(seeded, "u_manager", "act1", event_type="resend", now=now + dt.timedelta(hours=100))


# --- GET -----------------------------------------------------------------------------------


def test_get_outbox_lists_company_scoped_items(client, seeded):
    client.post("/api/v1/outbox", json={"action_id": "act1"}, headers=_auth_headers(client, "u_manager"))

    resp = client.get("/api/v1/outbox", headers=_auth_headers(client, "u_manager"))
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 1
    assert items[0]["action_id"] == "act1"
