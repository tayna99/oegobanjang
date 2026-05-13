# Housing Consent Workflow Design

## Summary

숙식비 동의서는 `/dashboard`의 상시 Daily Briefing 업무가 아니라, 급여월 또는 분쟁 방어가 필요한 시점에 담당자가 꺼내 쓰는 보조 워크플로우로 설계한다.

MVP의 목표는 담당자가 PC Dashboard에서 입력한 월급, 숙박비, 식비를 기준으로 공제율을 계산하고, 다국어 동의서 초안을 만들고, 대표 승인 후 근로자 모바일 서명을 받아 Evidence Log에 남기는 것이다. 실제 외부 발송, 자동 메시지 발송, 법률/노무 판단, 정부 제출은 하지 않는다.

## Scope

### In Scope

- PC Dashboard에서 `숙식비 동의서 만들기` 수동 진입점을 제공한다.
- `POST /api/v1/agent/run`은 `housing_deduction` intent의 생성 트리거로 사용한다.
- 전용 `housing_consent_service`가 계산, 초안 저장, 상태 전이, 토큰 생성, 서명 처리를 담당한다.
- `HousingConsentDraft` 모델과 `housing_consent_drafts` 테이블을 추가한다.
- `Approval.target_type = "housing_consent_draft"`를 기존 approval 흐름에 추가한다.
- 대표 승인 후에도 자동 발송하지 않고, 모바일 서명 링크/QR을 준비 상태로만 제공한다.
- 근로자 모바일 공개 화면은 token 기반으로 접근하며 `worker_id`를 노출하지 않는다.
- 서명 완료 시 `signed_at`을 기록하고 Evidence Log 이벤트를 남긴다.

### Out of Scope

- 급여 시스템 연동
- 실제 Zalo, 카카오톡, 문자, 이메일 자동 발송
- 공제 가능 여부 확정 또는 법률/노무 자문
- Daily Briefing 자동 승격 전체 구현
- PDF export 또는 대외 제출용 문서 생성

## User Flow

```txt
담당자 (PC Dashboard)
  │
  ├─ 숙식비 동의서 만들기
  │   근로자 선택 + 급여월 + 월급 + 숙박비 + 식비 입력
  ▼
POST /api/v1/agent/run
  intent_hint: housing_deduction
  worker_id, pay_period, monthly_wage, housing_fee, meal_fee
  ▼
Intent Router
  intent: housing_deduction
  ▼
LangChain v1 / housing consent agent
  ├─ calculate_housing_deduction()
  └─ generate_housing_consent_draft()
        housing_consent_drafts 저장
        Approval(target_type="housing_consent_draft") 생성
        approval_required=true 반환
  ▼
PC Dashboard
  계산 결과 + 동의서 초안 + 대표 승인 버튼
  ▼
POST /api/v1/approvals/{approval_id}/approve
  자동 발송 없음
  signature link/QR 준비
  ▼
근로자 모바일 공개 링크
  token 기반 모국어 동의서 화면
  ▼
POST /api/v1/public/housing-consent/{token}/sign
  signed_at 업데이트
  Evidence Log 기록
```

## State Model

`housing_consent_drafts.status`는 다음 상태를 사용한다.

```txt
DRAFT_CREATED
-> PENDING_APPROVAL
-> APPROVED
-> PENDING_WORKER_SIGNATURE
-> SIGNED
```

예외 상태:

```txt
REJECTED
REVISION_REQUESTED
EXPIRED
```

상태 전이 원칙:

- 초안 생성 직후에는 `PENDING_APPROVAL`로 둔다.
- 대표 승인 전에는 모바일 서명 링크를 활성화하지 않는다.
- 대표 승인 후에는 `PENDING_WORKER_SIGNATURE`로 전이하고, 자동 발송은 하지 않는다.
- 근로자 서명 완료 시 `SIGNED`로 전이한다.
- 반려 또는 수정 요청 시 기존 초안을 덮어쓰지 않고 새 초안 생성을 유도한다.

## Data Model

`HousingConsentDraft` 핵심 필드:

- `id`
- `company_id`
- `worker_id`
- `masked_worker_id`
- `pay_period`, 예: `2026-06`
- `monthly_wage`
- `housing_fee`
- `meal_fee`
- `total_deduction`
- `deduction_rate_pct`
- `within_limit`
- `language_code`
- `consent_draft_text`
- `status`
- `approval_required`
- `approval_id`
- `signed_at`
- `risk_flags`
- `created_by`
- `created_at`
- `updated_at`
- `signature_token_hash`
- `signature_token_expires_at`

모바일 공개 링크에는 `worker_id`를 포함하지 않는다. 공개 API는 `token`을 기준으로 동의서를 조회하고 서명을 처리한다.

## Calculation Rules

MVP에서는 CSV seed와 일치하게 `20% 상한`만 hard rule로 사용한다.

- `total_deduction = housing_fee + meal_fee`
- `deduction_rate_pct = total_deduction / monthly_wage * 100`
- `deduction_rate_pct > 20`이면 `within_limit=false`
- 20% 초과 시 `risk_flags`에 상한 초과를 기록한다.

8%는 하한 또는 확정 rule로 사용하지 않는다. 화면에는 필요하면 안내 문구로만 표시하고, 승인/서명을 차단하는 기준으로 쓰지 않는다.

화면 문구는 다음 표현을 사용한다.

- `입력값 기준 공제율 계산`
- `20% 상한 초과 여부 표시`
- `담당자 확인 필요`
- `대표 승인 후 근로자 서명 요청 가능`
- `실제 발송 아님 / demo 또는 수동 전달 대기`

금지 표현:

- `공제 가능 확정`
- `법적으로 문제 없음`
- `자동 발송 완료`
- `근로자에게 발송됨`

## API Design

PC 내부 API:

```txt
POST /api/v1/housing-consent/drafts/calculate
POST /api/v1/housing-consent/drafts
GET  /api/v1/housing-consent/drafts/{draft_id}
POST /api/v1/housing-consent/drafts/{draft_id}/signature-link
```

기존 approval API 재사용:

```txt
POST /api/v1/approvals/{approval_id}/approve
POST /api/v1/approvals/{approval_id}/request-revision
POST /api/v1/approvals/{approval_id}/reject
```

모바일 공개 API:

```txt
GET  /api/v1/public/housing-consent/{token}
POST /api/v1/public/housing-consent/{token}/sign
```

`/sign`은 approval API가 아니다. 대표 승인 이후 근로자 본인이 동의서에 서명하는 별도 이벤트다.

## Agent Integration

`POST /api/v1/agent/run`은 다음 두 방식 모두 허용한다.

자연어:

```json
{
  "message": "홍길동 숙식비 동의서 만들어줘. 월급 230만원, 숙박비 18만원, 식비 12만원.",
  "company_id": "demo-company-01"
}
```

PC form:

```json
{
  "message": "숙식비 동의서 초안 생성",
  "intent_hint": "housing_deduction",
  "company_id": "demo-company-01",
  "worker_id": "worker_001",
  "pay_period": "2026-06",
  "monthly_wage": 2300000,
  "housing_fee": 180000,
  "meal_fee": 120000
}
```

폼 입력은 자연어 파싱보다 안정적이므로 MVP 기본 경로로 사용한다. 자연어는 demo chat 진입 보조 경로로 둔다.

## Frontend Design

`/dashboard`는 계속 `DashboardShell -> DailyBriefingPanel` 흐름을 유지한다.

DailyBriefingPanel에 큰 상시 업무 카드로 넣지 않고, 우측 액션 또는 drawer 진입점으로 제공한다.

PC drawer 단계:

1. 근로자 선택
2. 급여월 선택
3. 월급, 숙박비, 식비 입력
4. 공제율 계산
5. 동의서 초안 미리보기
6. 대표 승인 요청
7. 승인 후 모바일 서명 링크/QR 표시
8. 서명 상태 확인

모바일 화면:

- 공개 token으로 진입한다.
- 모국어 동의서 내용을 보여준다.
- 월급, 숙박비, 식비, 총 공제액, 공제율을 표시한다.
- `입력값 기준`, `담당자 확인 필요`, `서명 전 확인` 문구를 표시한다.
- 서명 완료 후 PC Dashboard에는 `SIGNED` 상태가 반영된다.

## Daily Briefing Relationship

MVP 1차에서는 Daily Briefing 자동 승격을 구현하지 않는다.

2차에서 다음 조건일 때만 Daily Briefing item으로 승격한다.

- 급여월인데 해당 근로자 동의서가 없음
- 기존 동의서 이후 숙식비 금액이 변경됨
- `within_limit=false`
- `PENDING_WORKER_SIGNATURE` 상태가 오래 지속됨
- 분쟁/이의제기 대비 Evidence가 필요한 케이스

Daily Briefing은 모든 동의서 생성 화면이 아니라 위험과 누락을 알려주는 관제실 역할만 한다.

## Evidence And Safety

필수 Evidence Log 이벤트:

- `housing_deduction_calculated`
- `housing_consent_draft_created`
- `approval_requested`
- `housing_consent_draft_approved`
- `signature_link_prepared`
- `housing_consent_signed`

Evidence Log에는 민감정보 원문을 저장하지 않는다. `worker_id`는 내부 DB 필드로만 쓰고, 공개 URL과 공개 응답에는 `masked_worker_id` 또는 표시용 이름만 사용한다.

대표 승인 후에도 실제 발송은 수행하지 않는다. outbox가 필요하면 `PENDING_MANUAL_DISPATCH` 또는 `MOCK_DISPATCH_READY` 상태만 남긴다.

## Implementation Slices

### Slice 1: Backend Core

- `HousingConsentDraft` 모델과 migration 추가
- `housing_consent_service` 추가
- 계산 함수와 draft 생성 함수 추가
- approval target type 연결
- Evidence Log 생성

### Slice 2: Agent Run Entry

- `housing_deduction` intent 인식
- `calculate_housing_deduction` tool 추가
- `generate_housing_consent_draft` tool 추가
- `agent/run` 응답에 draft preview와 approval id 포함

### Slice 3: PC Dashboard

- DailyBriefingPanel 보조 액션/drawer 추가
- form 입력 -> agent/run 호출
- 계산 결과와 draft preview 표시
- 대표 승인 버튼 연결
- 서명 링크/QR 준비 상태 표시

### Slice 4: Mobile Signature

- token 기반 공개 조회 API
- 모바일 서명 화면
- 서명 완료 API
- PC status refresh

### Slice 5: Daily Briefing Escalation

- 미서명, 금액 변경, 20% 초과 건만 Daily Briefing item으로 승격
- 이 slice는 MVP 1차 이후 진행한다.

## Test Plan

Backend:

- 20% 이하 계산은 `within_limit=true`
- 20% 초과 계산은 `within_limit=false`와 risk flag 기록
- draft 생성 시 approval 생성
- approval approve 시 자동 발송 없이 `PENDING_WORKER_SIGNATURE` 전이
- 공개 token 조회는 `worker_id`를 노출하지 않음
- sign API는 `SIGNED`, `signed_at`, Evidence Log를 기록

Frontend:

- `/dashboard`는 `DashboardShell -> DailyBriefingPanel` 유지
- drawer에서 form 입력 후 계산 결과 표시
- 20% 초과 시 경고 표시
- 대표 승인 후 서명 링크/QR 표시
- 모바일 서명 완료 후 PC 상태가 갱신됨

Safety:

- 실제 발송 없음
- 공개 링크에 `worker_id` 없음
- UI가 공제 가능 여부를 확정하지 않음
- Evidence Log에 민감정보 원문 없음

