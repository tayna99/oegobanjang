# Daily Briefing LLM Planner And Operations Backlog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the post-MVP work needed to make Daily Briefing citation refresh, natural-language planning, provider integrations, and production controls safe for pilot and operations.

**Architecture:** Keep the MVP thin slice safe by default. Production hardening should add allowlists, review states, quality gates, and provider boundaries without letting LLMs or background jobs execute external submissions or sends directly.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Chroma, PyMuPDF, deterministic Daily Briefing service, Next.js dashboard, mock headers plus Bearer JWT scope.

---

## Status

Daily Briefing MVP thin slice is implemented with a deterministic structured planner. Official citation refresh now has a real worker boundary:

- fetch official `source_url` content over HTTP/HTTPS/file source
- parse HTML/text/PDF content
- update `daily_briefing_source_citations`
- write refreshed chunks JSONL
- write chroma-ready JSONL
- upsert a local Chroma collection with deterministic embeddings
- record refresh queue status and EvidenceEvent

The items below are intentionally not implemented in the current slice.

## Queue Item 1: Citation Refresh Production Hardening

**Status:** Next best operational hardening step after the real fetch/parse/reindex worker.

**Why this matters:** The current worker can fetch and reindex official source content. Production needs a review gate so broken HTML/PDF parsing or wrong source URLs do not immediately become trusted evidence.

**Files:**

- Modify: `backend/app/config.py`
- Modify: `backend/app/models/daily_briefing.py`
- Modify: `backend/app/api/v1/citations.py`
- Modify: `backend/app/services/citation_refresh_worker.py`
- Modify: `backend/migrations/versions/<new_revision>_citation_refresh_production_hardening.py`
- Modify: `frontend/features/admin/`
- Test: `backend/tests/test_citation_official_fetch_worker.py`
- Test: `backend/tests/test_daily_briefing_api.py`

### Task 1.1: Source URL Allowlist

- [ ] Add config `DAILY_BRIEFING_OFFICIAL_FETCH_ALLOWED_DOMAINS=hikorea.go.kr,eps.go.kr,law.go.kr,gov.kr,kosha.or.kr`.
- [ ] Add a failing test: `https://evil.example.test/file.pdf` returns `409 SOURCE_DOMAIN_NOT_ALLOWED`.
- [ ] Implement domain validation before `urllib.request.urlopen`.
- [ ] Record blocked attempt as `citation_refresh_failed` EvidenceEvent with `external_fetch_performed=false`.
- [ ] Run `uv run pytest backend/tests/test_citation_official_fetch_worker.py backend/tests/test_daily_briefing_api.py::test_official_citation_refresh_uses_source_url_when_feature_flag_enabled`.

### Task 1.2: Fetched But Inactive Review State

- [ ] Add `review_status` to `daily_briefing_source_citations`: `active | fetched_pending_review | rejected`.
- [ ] Change `official_source_fetch` to write refreshed citation rows as `fetched_pending_review` by default.
- [ ] Add `POST /api/v1/citations/{citation_id}/activate-refresh` for admin-only activation.
- [ ] Ensure Daily Briefing uses only active citations for strong official evidence.
- [ ] Add tests proving pending citations are visible in admin review but not used as validated evidence.

### Task 1.3: Diff View Before Activation

- [ ] Store `previous_source_hash`, `new_source_hash`, `previous_excerpt`, and `new_excerpt` in refresh queue payload.
- [ ] Add `GET /api/v1/citations/refresh-queue/{queue_id}/diff`.
- [ ] Return a redacted text diff summary: added lines, removed lines, old hash, new hash, chunk count delta.
- [ ] Add admin UI panel showing old/new excerpt and hash before activation.
- [ ] Add tests proving raw PII is not included in the diff response.

### Task 1.4: Quality Gate

- [ ] Add quality checks: minimum extracted text length 200 chars, maximum empty page ratio 30%, required source hash, required chunk count >= 1.
- [ ] Add PDF-specific quality fields: `page_count`, `empty_page_count`, `extracted_char_count`.
- [ ] If quality fails, set queue status `failed` and do not upsert active citation.
- [ ] Add tests for empty PDF, tiny HTML, oversized body, unsupported content type, and successful normal source.

### Task 1.5: Scheduled Refresh Candidate Generation

- [ ] Add `GET /api/v1/citations/admin/refresh-candidates?stale_days=180`.
- [ ] Return active official citations whose `ingest_at` is older than the threshold and have allowed source URLs.
- [ ] Add optional scheduler task that creates queue rows only; it must not process/fetch automatically by default.
- [ ] Add tests proving scheduled candidate generation does not fetch external URLs.

### Task 1.6: Operational Runbook

- [ ] Add `docs/runbooks/citation-refresh-production.md`.
- [ ] Document env flags, allowlist, queue creation, process command/API, review/activate flow, rollback procedure, and failure states.
- [ ] Include the explicit statement: citation refresh never submits government forms, sends messages, or replaces expert review.

### Acceptance Criteria

- Official source refresh cannot fetch non-allowlisted domains.
- Fetched citation content is inactive until admin activation.
- Admin can compare old/new source before activation.
- Broken PDF/HTML extraction fails closed.
- Scheduler can create refresh candidates without fetching external URLs.
- EvidenceEvent records every blocked, failed, fetched, activated, and rejected refresh path.
- `uv run pytest backend/tests` passes.

## Queue Item 2: LLM Structured Planner Provider

**Goal:** Let users ask broader natural-language questions while keeping Router bounded and execution deterministic.

**Principle:**

```txt
User natural language
-> Input Guard
-> Bounded Intent Router
-> LLM Structured Planner
-> State Loader
-> Deterministic Daily Briefing service
-> Aggregator/Risk
-> Human Approval
-> Evidence Log
```

The LLM must only produce a schema. It must not call tools, mutate DB state, send messages, submit government forms, or approve actions.

### Target Schema

```json
{
  "intent": "visa_expiry",
  "plan_steps": [
    "resolve_worker_reference",
    "load_worker_state",
    "evaluate_visa_expiry",
    "create_pending_next_actions"
  ],
  "required_context": ["company", "workers", "documents", "citations"],
  "entities": {
    "worker_ref": "Nguyen",
    "date_range": "this_month"
  },
  "blocked_actions": ["send_message_without_approval"],
  "approval_required": true,
  "execution_allowed": true,
  "target_service": "daily_briefing"
}
```

### Implementation Plan

- [ ] Add `DailyBriefingStructuredPlan` schema with strict enum fields.
- [ ] Add `LLMDailyBriefingPlannerProvider` behind `DAILY_BRIEFING_LLM_PLANNER_ENABLED=false`.
- [ ] Keep deterministic planner as fallback and default.
- [ ] Add guardrail validation: unknown/forbidden intents cannot execute.
- [ ] Add parser validation: malformed LLM output falls back to deterministic planner.
- [ ] Add EvidenceEvent `plan_created` with redacted input hash and structured plan summary.
- [ ] Add tests for free-form Korean requests, malformed LLM output, forbidden government submission, and fallback behavior.
- [ ] Run `uv run pytest backend/tests/test_daily_briefing_natural_language.py backend/tests/test_daily_briefing_api.py`.

### Acceptance Criteria

- Natural-language request can be converted to a strict plan schema.
- LLM output cannot expand allowed actions beyond known intents.
- Government portal submission remains forbidden.
- Message send/handoff delivery remains approval-required.
- If LLM fails, deterministic planner still handles supported MVP cases.

## Queue Item 3: Real External Delivery Providers

**Status:** Waiting for credentials and operating policy.

- [ ] Kakao Biz provider adapter.
- [ ] SMTP/email provider adapter.
- [ ] Admin-office handoff delivery adapter.
- [ ] Provider-specific retry/backoff and failure audit.
- [ ] No government portal submission.

## Queue Item 4: Production Auth/RBAC

**Status:** Waiting for auth provider decision.

- [ ] Replace mock headers with production auth mode.
- [ ] Keep Bearer JWT company scope.
- [ ] Add role/permission persistence.
- [ ] Require real identity for approval/export/dispatch.

## Queue Item 5: Provider Audit Event Expansion

**Status:** Ready after first real provider adapter.

- [ ] Add provider response code/ref/hash.
- [ ] Store raw provider payload outside EvidenceEvent.
- [ ] Keep EvidenceEvent redacted and hash/reference based.

## Queue Item 6: Citation Source Quality Review

**Status:** After official fetch worker has pilot data.

- [ ] Add admin review status for fetched citations.
- [ ] Add stale/fresh transition dashboard.
- [ ] Add source text diff view between refreshes.
- [ ] Add manual approval before citation is used as strong official evidence if needed.
