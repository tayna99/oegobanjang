# Daily Briefing Provider Integration Backlog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the gap between the implemented Daily Briefing dispatch/export/citation infrastructure and the later real-provider integrations that require production credentials and approval policy.

**Architecture:** Sprint 1 has implemented the safe integration boundary: approved actions create outbox jobs, mock dispatch records audit events, handoff PDF downloads record export artifacts, and citation viewers expose chunk/source metadata. The backlog below keeps real Kakao, SMTP/email, admin-office delivery, and production auth separate so MVP safety does not regress.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Next.js, header/mock auth plus Bearer JWT company scope, Daily Briefing repository/service layer.

---

## Current Implementation Status

These items are implemented and verified in the current branch. They are not only empty route shells; they connect API routes to service logic, repository persistence, migration tables, frontend helpers, and tests.

- Bearer JWT company scope is implemented in `backend/app/services/daily_briefing_service.py` through `decode_daily_briefing_bearer_token`, `resolve_daily_briefing_allowed_company_ids`, `daily_briefing_role_from_request`, and `daily_briefing_user_id_from_request`.
- PDF export and export history are implemented through `GET /api/v1/actions/{action_id}/handoff-export.pdf` and `GET /api/v1/actions/{action_id}/handoff-exports`.
- External delivery job creation and dispatch are implemented through `POST /api/v1/actions/{action_id}/external-delivery-jobs` and `POST /api/v1/external-delivery-jobs/{job_id}/dispatch`.
- Dispatch is intentionally limited to the safe `mock_webhook` provider. Approved jobs can be marked `mock_dispatched`, `external_send_performed=false` is preserved, and an audit event is recorded. Real Kakao/email/admin-office transmission is not enabled.
- Citation chunk/source document viewers are implemented through `GET /api/v1/citations/{citation_id}/chunk` and `GET /api/v1/citations/{citation_id}/source-document`.
- Alembic migration `backend/migrations/versions/20260508_0005_daily_briefing_tables.py` includes Daily Briefing export, external delivery, citation source, and source document tables.
- Frontend API helpers are implemented in `frontend/lib/api.ts` for export history, dispatch, citation chunk, and citation source document calls.

## Fresh Verification Evidence

Run on 2026-05-08:

- `uv run pytest backend/tests` -> `232 passed`
- `npm run build` from `C:\WorkBridge\frontend` -> build passed

## Decision

Do not open real external delivery providers inside the MVP until production credentials, user-facing confirmation copy, failure handling, and provider-specific audit fields are available.

The current MVP should continue to state:

```txt
승인 후 mock_webhook dispatch로 통합 경로와 audit trail까지 검증합니다. 실제 외부 전송은 수행하지 않습니다.
실제 카카오/메일/행정사 전송은 provider credentials와 운영 승인 정책이 들어온 뒤 provider adapter로 연결합니다.
```

---

## Backlog Queue

### Queue Item 0: Sprint v3 Pilot Operations Polish

**Status:** Partially completed in the current branch.

Completed:

- Admin CSV UI expanded beyond companies/workers to documents, citations, candidates, candidate documents, reporting events, and user company access.
- Citation admin view supports missing evidence, stale evidence, and synthetic-only filter toggles.
- Scheduler environment variables are documented in `.env.example`.
- Metrics snapshot decision is recorded: MVP computes metrics live from briefing/approval/export/mock dispatch rows.

Deferred:

- Multipart CSV file upload. Current MVP uses CSV text payloads and textarea-based admin input.
- Metrics snapshot table. Add this only after pilot reporting needs fixed historical cuts by day/week/company.
- Auto-loading admin dashboard on page entry. Current MVP keeps explicit refresh to avoid accidental API fan-out during demos.

### Queue Item 1: Kakao Provider Adapter

**Status:** Waiting for credentials and provider contract.

**Files:**
- Modify: `backend/app/services/daily_briefing_service.py`
- Modify: `backend/app/api/v1/external_delivery.py`
- Test: `backend/tests/test_daily_briefing_api.py`

- [ ] **Step 1: Add a failing test for approved Kakao dispatch**

Add a test that creates an approved `external_delivery_job` with `provider="kakao_biz"` and asserts dispatch is blocked when credentials are missing.

```python
def test_kakao_provider_dispatch_requires_credentials(client):
    job = _create_approved_external_delivery_job(client, provider="kakao_biz")

    response = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "PROVIDER_NOT_CONFIGURED"
```

- [ ] **Step 2: Run the focused test and verify it fails before implementation**

Run:

```powershell
uv run pytest backend/tests/test_daily_briefing_api.py::test_kakao_provider_dispatch_requires_credentials
```

Expected before implementation: fail because the provider branch is not implemented or the helper does not exist.

- [ ] **Step 3: Add provider credential config**

Add explicit settings names. Do not infer credentials from unrelated environment variables.

```python
kakao_biz_api_key: str | None = None
kakao_biz_sender_key: str | None = None
```

- [ ] **Step 4: Implement blocked Kakao adapter boundary**

In `dispatch_external_delivery_job`, keep real send disabled unless both Kakao credentials exist. Missing credentials must raise `PermissionError("PROVIDER_NOT_CONFIGURED")`.

```python
if job.provider == "kakao_biz":
    settings = get_settings()
    if not settings.kakao_biz_api_key or not settings.kakao_biz_sender_key:
        raise PermissionError("PROVIDER_NOT_CONFIGURED")
```

- [ ] **Step 5: Run focused backend tests**

Run:

```powershell
uv run pytest backend/tests/test_daily_briefing_api.py backend/tests/test_tenant_scope.py
```

Expected: all selected tests pass.

### Queue Item 2: SMTP Email Provider Adapter

**Status:** Waiting for SMTP host, sender, auth, and approved email copy.

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/daily_briefing_service.py`
- Test: `backend/tests/test_daily_briefing_api.py`

- [ ] **Step 1: Add a failing test for SMTP dispatch without credentials**

```python
def test_smtp_provider_dispatch_requires_credentials(client):
    job = _create_approved_external_delivery_job(client, provider="smtp_email")

    response = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "PROVIDER_NOT_CONFIGURED"
```

- [ ] **Step 2: Add SMTP settings**

```python
smtp_host: str | None = None
smtp_port: int | None = None
smtp_username: str | None = None
smtp_password: str | None = None
smtp_from_email: str | None = None
```

- [ ] **Step 3: Add provider branch that blocks safely until configured**

```python
if job.provider == "smtp_email":
    settings = get_settings()
    if not all(
        [
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        ]
    ):
        raise PermissionError("PROVIDER_NOT_CONFIGURED")
```

- [ ] **Step 4: Run focused backend tests**

Run:

```powershell
uv run pytest backend/tests/test_daily_briefing_api.py
```

Expected: all selected tests pass.

### Queue Item 3: Admin-Office Delivery Adapter

**Status:** Waiting for target system contract. This must not submit to a government portal or replace expert review.

**Files:**
- Modify: `backend/app/services/daily_briefing_service.py`
- Modify: `backend/app/api/v1/external_delivery.py`
- Test: `backend/tests/test_daily_briefing_api.py`

- [ ] **Step 1: Add a failing test for unsupported admin-office provider**

```python
def test_admin_office_provider_is_blocked_without_contract(client):
    job = _create_approved_external_delivery_job(client, provider="admin_office_api")

    response = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "PROVIDER_NOT_CONFIGURED"
```

- [ ] **Step 2: Keep delivery limited to handoff draft transfer only**

The adapter must transfer only an approved handoff draft. It must not submit visa applications, government forms, or legal filings.

```python
if job.provider == "admin_office_api":
    raise PermissionError("PROVIDER_NOT_CONFIGURED")
```

- [ ] **Step 3: Add acceptance copy to API error**

The API error message should be explicit:

```txt
Admin-office delivery provider is not configured. No external transfer was performed.
```

- [ ] **Step 4: Run focused backend tests**

Run:

```powershell
uv run pytest backend/tests/test_daily_briefing_api.py backend/tests/test_handoff_api.py
```

Expected: all selected tests pass.

### Queue Item 4: Production Auth/RBAC Integration

**Status:** Waiting for auth provider decision.

**Files:**
- Modify: `backend/app/services/daily_briefing_service.py`
- Modify: `backend/app/api/v1/actions.py`
- Modify: `backend/app/api/v1/external_delivery.py`
- Test: `backend/tests/test_tenant_scope.py`

- [ ] **Step 1: Add a failing test for missing user identity on dispatch**

```python
def test_dispatch_requires_user_identity_when_mock_headers_are_disabled(client):
    job = _create_approved_external_delivery_job(client, provider="mock_webhook")

    response = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )

    assert response.status_code in {401, 403}
```

- [ ] **Step 2: Introduce an auth mode setting**

```python
daily_briefing_auth_mode: str = "mock"
```

- [ ] **Step 3: Keep mock mode as Sprint 1 default**

When `daily_briefing_auth_mode == "mock"`, keep accepting `X-Company-Id`, `X-User-Role`, and `X-User-Id`.

- [ ] **Step 4: Require Bearer JWT in production mode**

When `daily_briefing_auth_mode == "jwt"`, reject requests without a valid Bearer JWT.

```python
if settings.daily_briefing_auth_mode == "jwt" and token_payload is None:
    raise PermissionError("INVALID_TOKEN")
```

- [ ] **Step 5: Run tenant scope tests**

Run:

```powershell
uv run pytest backend/tests/test_tenant_scope.py backend/tests/test_daily_briefing_api.py
```

Expected: all selected tests pass in mock mode.

### Queue Item 5: Provider Audit Event Expansion

**Status:** Ready after the first real provider adapter is introduced.

**Files:**
- Modify: `backend/app/services/daily_briefing_service.py`
- Modify: `backend/app/models/daily_briefing.py`
- Modify: `backend/migrations/versions/<new_revision>_daily_briefing_provider_audit_fields.py`
- Test: `backend/tests/test_daily_briefing_api.py`

- [ ] **Step 1: Add a failing test for provider response metadata**

```python
def test_external_delivery_dispatch_records_provider_response_metadata(client):
    job = _create_approved_external_delivery_job(client, provider="mock_webhook")

    response = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock_webhook"
    assert body["external_send_performed"] is False
    assert body["status"] == "mock_dispatched"
```

- [ ] **Step 2: Add nullable provider response fields**

```python
provider_response_code: str | None = None
provider_response_ref: str | None = None
provider_response_hash: str | None = None
```

- [ ] **Step 3: Keep raw provider payload out of EvidenceEvent**

Store a hash or reference only. Do not store raw contact details, passport numbers, alien registration numbers, or full provider response bodies in EvidenceEvent.

- [ ] **Step 4: Run backend tests**

Run:

```powershell
uv run pytest backend/tests
```

Expected: all backend tests pass.

---

## Out Of Scope Until Credentials Exist

- Real Kakao Biz message sending
- Real SMTP/email sending
- Real admin-office API transfer
- Government portal submission
- Automatic legal or labor judgment
- Candidate recommendation, nationality preference, or suitability scoring

## Completion Criteria For This Backlog

- Each real provider has a blocked-without-credentials test.
- Each real provider has explicit settings names.
- Dispatch remains impossible without an approved action.
- Dispatch remains impossible outside tenant scope.
- Every provider dispatch attempt records an audit event or a safe error.
- No raw PII is written to EvidenceEvent.
- `uv run pytest backend/tests` passes after each provider adapter task.
