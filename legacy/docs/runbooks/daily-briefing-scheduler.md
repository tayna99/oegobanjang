# Daily Briefing Scheduler Runbook

## 목적

Daily Briefing scheduler는 회사별 외국인 고용 운영 리스크를 매일 생성하는 내부 작업이다. 이 작업은 메시지 발송, 행정사 전달, 정부 포털 제출을 실행하지 않는다.

## 환경 변수

```env
DAILY_BRIEFING_SCHEDULER_ENABLED=true
DAILY_BRIEFING_SCHEDULER_RUN_ON_STARTUP=false
DAILY_BRIEFING_SCHEDULER_INTERVAL_SECONDS=86400
DAILY_BRIEFING_SCHEDULER_TIMEZONE=Asia/Seoul
DAILY_BRIEFING_SCHEDULER_COMPANY_IDS=company_001,company_002
```

## 운영 확인 API

```http
GET /api/v1/daily-briefings/scheduler/status
X-User-Role: admin
```

확인할 값:

- `enabled`: scheduler 활성화 여부
- `running`: 현재 background thread 실행 여부
- `timezone`: D-day 계산 기준 timezone
- `configured_company_ids`: 자동 생성 대상 회사 목록
- `last_run`: 마지막 실행 결과

## 수동 실행 API

```http
POST /api/v1/daily-briefings/scheduled-run
X-User-Role: admin
Content-Type: application/json

{
  "company_ids": ["company_001"],
  "date": "2026-05-08"
}
```

## 안전 원칙

- scheduler는 briefing, pending action, evidence event만 생성한다.
- scheduler는 외부 메시지, 이메일, 카카오, 행정사 전달을 실행하지 않는다.
- 외부 provider 연동은 승인된 action과 별도 dispatch endpoint를 통과해야 한다.
- MVP에서는 `mock_webhook` provider만 허용하며 실제 외부 전송은 수행하지 않는다.

## 장애 대응

- `status=partial_failure`: 일부 회사만 실패했다. `errors[]`의 `company_id`와 `error_code`를 확인한다.
- `COMPANY_NOT_FOUND`: source company row가 없거나 company id가 잘못됐다.
- `STATE_SAVE_FAILED`: DB 저장 실패 가능성이 있으므로 같은 company/date 재실행 전 DB 상태를 확인한다.
- `missing_evidence_count > 0`: citation admin view에서 stale/synthetic/missing evidence를 확인하고 공식문서를 재수집한다.
