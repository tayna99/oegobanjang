# 외고반장 E-9 운영 리스크 MVP Thin Slice 구현 계획 v11

## Summary
Sprint 1 목표는 전체 Agentic OS가 아니라, `Daily Briefing` 기반 얇은 end-to-end 흐름을 완성하는 것이다.

핵심 데모 흐름:

`회사 선택 -> 오늘 위험 브리핑 생성 -> D-30 체류만료 HIGH -> 만료 CRITICAL -> 누락서류 표시 -> citation 표시 -> request_document/create_handoff 액션 생성 -> approval pending -> EvidenceEvent 저장 -> Handoff preview 보기 -> 같은 날짜 재실행 시 중복 없음`

Sprint 1에서는 실제 메시지 발송, 행정사 전달, 정부 포털 제출, scheduler, full RBAC/SSO, strong citation validation, full audit UI는 하지 않는다.

## Core Contracts
- `Case`는 하나 이상의 `NextAction`을 가진다.
- `NextAction`은 Sprint 1에서 하나의 `Approval`을 가진다.
- `DailyBriefingItem.next_action_ids`는 top-level `recommended_actions[].action_id`를 참조한다.
- `briefing_run_id`는 `brf_{slug_company_id}_{YYYY-MM-DD}`를 기본으로 하고, slug-safe하지 않으면 `brf_{sha256(company_id + ":" + date)[:16]}`를 쓴다.

```text
Case
- case_id
- company_id
- worker_id: str | None
- risk_type: visa_expiry | missing_document
- status: open | in_review | approval_pending | resolved | blocked
- due_date: str | None
- risk_level: CRITICAL | HIGH | MEDIUM | LOW
- created_at
- updated_at
```

```text
NextAction
- action_id
- action_type: request_document | create_handoff
- status: pending_approval | approved | blocked | completed | cancelled
- subject_id
- label
- approval_required: true
- blocked_until_approved: true
- evidence_required: true
- citation_ids
- approved_at: str | None
```

```text
Approval
- approval_id
- case_id
- action_id
- status: pending | approved | rejected | revision_requested
- approver_id: str | None
- rejection_reason: str | None
- revision_reason: str | None
- created_at
- updated_at
```

Sprint 1은 `pending -> approved`만 구현한다. `rejected`와 `revision_requested`는 Sprint 2에서 활성화한다.

```text
EvidenceEvent v1
- event_id
- event_version: v1
- trace_id
- case_id: str | None
- request_id: str | None
- event_type: input_received | state_loaded | risk_flagged | approval_requested | handoff_preview_generated | approval_approved
- actor_type: system | user | agent | approver
- node_name
- summary
- citation_ids
- redacted_input_hash: str | None
- redacted_output_hash: str | None
- hash_algorithm: sha256
- payload_ref: str | None
- created_at
```

```text
HandoffPreview
- preview_id
- case_id
- action_id
- content_redacted: dict | str
- citation_ids
- warning_flags
- created_at
```

Sprint 1에서는 별도 테이블 또는 repository entity로 저장하되, 최소한 `action_id` 기준 조회가 가능해야 한다.

## Daily Briefing Output
```text
DailyBriefingResult
- briefing_run_id
- company_id
- date
- generated_at
- timezone
- source_snapshot_hash
- rerun_count
- last_refreshed_at
- items: list[DailyBriefingItem]
- risk_summary: RiskSummary
- recommended_actions: list[NextAction]
- citation_summaries: list[CitationSummary]
- evidence_event_ids: list[str]
- approval_required: bool
```

```text
DailyBriefingItem
- item_id
- case_id
- subject_type: worker | company | case
- subject_id
- risk_type: visa_expiry | missing_document
- severity: CRITICAL | HIGH | MEDIUM | LOW
- d_day: int | None
- expired: bool
- days_overdue: int | None
- missing_documents: list[str]
- citation_ids: list[str]
- next_action_ids: list[str]
```

```text
RiskSummary
- total_count
- critical_count
- high_count
- medium_count
- low_count
- by_risk_type
```

`CitationSummary`는 Sprint 1에서 response에 embed한다. 별도 `GET /api/v1/citations/{citation_id}`는 Sprint 2로 미룬다.

## Sprint 1A: Backend Thin Slice
1. Core schema와 fixtures를 추가한다.
2. `DailyBriefingResult`, `Case`, `NextAction`, `Approval`, `EvidenceEvent`, `HandoffPreview` repository를 만든다.
3. `Case`, `NextAction`, `Approval`, `EvidenceEvent`, `HandoffPreview` 저장은 하나의 transaction으로 처리한다.
4. transaction 실패 시 partial row를 남기지 않고 `STATE_SAVE_FAILED`를 반환한다.
5. `source_snapshot_hash`는 정규화된 non-PII operational fields만 사용한다.
6. 같은 `company_id/date` 재실행 시 `briefing_run_id`는 유지한다.
7. source data가 같으면 동일 결과를 반환하고, hash가 바뀌면 기존 briefing을 업데이트한다.
8. pending approval action은 중복 생성하지 않는다.
9. no-risk briefing은 `items=[]`, `approval_required=false`로 반환하고 `input_received/state_loaded` 이벤트는 남긴다.

Risk rules:

```text
D-day
- 모든 D-day는 API input date 기준
- date가 없으면 company_timezone 기준 today
- 만료일이 지났으면 expired=true, days_overdue=N
```

```text
visa_expiry
- already expired: CRITICAL
- D-30 이하: HIGH
- D-31~D-60: MEDIUM
- D-61~D-90: LOW
```

```text
missing_document
- required document missing + due_date already passed: CRITICAL
- required document missing + due_date D-7 이하: HIGH
- required document missing + no due_date: MEDIUM
- optional document missing: LOW
```

Tenant/auth assumption:

```text
- Sprint 1은 full login/SSO를 구현하지 않는다.
- API/test는 seed user 또는 X-Company-Id, X-User-Role header를 사용한다.
- 요청 company_id가 allowed_company_ids 밖이면 TENANT_SCOPE_VIOLATION.
- worker.company_id가 요청 company_id와 다르면 TENANT_SCOPE_VIOLATION.
```

## Sprint 1B: Product Thin Slice
1. `request_document`와 `create_handoff` `NextAction`을 생성한다.
2. 모든 external action은 `approval_required=true`, `blocked_until_approved=true`로 둔다.
3. approve API는 `manager/admin`만 허용한다.
4. approve 성공 시 `Approval.status=approved`, `NextAction.status=approved`, `approved_at` 저장, `approval_approved` EvidenceEvent 생성.
5. approve 이후에도 실제 메시지 발송, 행정사 전달, export는 실행하지 않는다.
6. `create_handoff` action이 있는 경우에만 `HandoffPreview`를 생성한다.
7. `missing_evidence=true`면 preview는 만들되 warning을 표시한다.
8. PII redaction 실패 또는 tenant scope 위반이면 preview를 생성하지 않는다.

Sprint 1 API:

```text
POST /api/v1/daily-briefings/run
GET /api/v1/daily-briefings/{briefing_run_id}
POST /api/v1/approvals/{approval_id}/approve
GET /api/v1/cases/{case_id}/evidence-events
```

Minimum error response:

```json
{
  "error_code": "TENANT_SCOPE_VIOLATION",
  "message": "Requested company is outside the allowed company scope.",
  "trace_id": "trace_001"
}
```

Simple UI:

```text
- severity
- masked worker name
- risk type
- D-day / expired
- missing documents
- citation summary
- recommended action
- approve button
- Handoff preview
- Evidence Log link
```

## Example Responses
Daily briefing response는 count와 item 수가 맞아야 한다.

```json
{
  "briefing_run_id": "brf_company_001_2026-05-08",
  "company_id": "company_001",
  "date": "2026-05-08",
  "risk_summary": {
    "total_count": 2,
    "critical_count": 1,
    "high_count": 1,
    "medium_count": 0,
    "low_count": 0,
    "by_risk_type": {
      "visa_expiry": 1,
      "missing_document": 1
    }
  },
  "items": [
    {
      "item_id": "item_001",
      "case_id": "case_001",
      "subject_type": "worker",
      "subject_id": "worker_001",
      "risk_type": "visa_expiry",
      "severity": "HIGH",
      "d_day": 30,
      "expired": false,
      "days_overdue": null,
      "missing_documents": [],
      "citation_ids": ["cit_001"],
      "next_action_ids": ["action_001"]
    },
    {
      "item_id": "item_002",
      "case_id": "case_002",
      "subject_type": "worker",
      "subject_id": "worker_002",
      "risk_type": "missing_document",
      "severity": "CRITICAL",
      "d_day": null,
      "expired": true,
      "days_overdue": 3,
      "missing_documents": ["passport_copy"],
      "citation_ids": ["cit_002"],
      "next_action_ids": ["action_002", "action_003"]
    }
  ],
  "approval_required": true
}
```

Approve response:

```json
{
  "approval_id": "approval_001",
  "action_id": "action_001",
  "status": "approved",
  "approved_at": "2026-05-08T08:10:00+09:00",
  "evidence_event_id": "evt_approval_001"
}
```

## Test Plan
Required tests:

```text
backend/tests/test_daily_briefing_schema.py
backend/tests/test_source_snapshot_hash.py
backend/tests/test_risk_rule_engine.py
backend/tests/test_evidence_event_minimal.py
backend/tests/test_daily_briefing_service.py
backend/tests/test_daily_briefing_idempotency.py
backend/tests/test_next_action_approval_pending.py
backend/tests/test_handoff_preview.py
backend/tests/test_tenant_scope.py
backend/tests/test_daily_briefing_api.py
```

Key scenarios:

```text
- D-30 visa expiry -> HIGH
- expired visa -> CRITICAL
- required missing document with overdue due_date -> CRITICAL
- required missing document D-7 이하 -> HIGH
- required missing document without due_date -> MEDIUM
- same company/date rerun does not duplicate case/action/approval
- changed source_snapshot_hash updates same briefing_run_id
- viewer/auditor cannot approve
- manager/admin can approve
- raw PII is not stored in EvidenceEvent
- HandoffPreview is blocked on PII redaction failure
- tenant scope violation returns standard error shape
```

Verification commands:

```powershell
uv run pytest backend/tests/test_risk_rule_engine.py
uv run pytest backend/tests/test_daily_briefing_service.py
uv run pytest backend/tests/test_daily_briefing_idempotency.py
uv run pytest backend/tests/test_next_action_approval_pending.py
uv run pytest backend/tests/test_handoff_preview.py
uv run pytest backend/tests/test_daily_briefing_api.py
uv run pytest backend/tests
```

## Implementation Order
1. Core schema + fixtures
2. Repository/storage + transaction
3. `source_snapshot_hash`
4. Risk rule engine
5. Minimal EvidenceEvent service
6. Daily Briefing service
7. Idempotency/case reuse
8. NextAction + Approval pending
9. HandoffPreview
10. API
11. Simple UI

## Sprint 1 Demo Completion
Sprint 1 is complete when this demo works:

1. Select `company_with_5_workers`.
2. Click `오늘 위험 브리핑 생성`.
3. `worker_visa_expiring_d30` appears as HIGH.
4. `worker_visa_expired` appears as CRITICAL.
5. `worker_missing_required_documents` appears as missing_document.
6. Citation summary is visible.
7. `request_document/create_handoff` actions are pending approval.
8. Handoff preview opens internally.
9. Evidence Log shows `risk_flagged` and `approval_requested`.
10. Running the same date again creates no duplicate action.
