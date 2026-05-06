# Decisions

이 문서는 외고반장 프로젝트의 주요 기술/제품 의사결정을 기록한다.

---

## Decision 001: 초기 구조는 backend 중심으로 간다

### Date

TBD

### Context

API 서버와 Agent 실행 서버를 분리하는 구조도 고려했다.  
하지만 초기 MVP 단계에서 서버를 여러 개 운영하면 로컬 개발, 환경변수 관리, 포트 관리, CI 관리가 복잡해질 수 있다.

### Decision

초기 구조는 FastAPI backend 중심으로 구성한다.

Agent Runtime은 아래 경로에서 관리한다.

```txt
backend/app/agent_runtime/
```

### Consequence

장점:

- 로컬 실행이 단순하다.
- API와 Agent 상태 관리가 쉽다.
- 승인과 Evidence Log 저장 흐름이 단순하다.
- 팀원들이 같은 서버 기준으로 개발할 수 있다.

단점:

- Agent 실행이 무거워지면 backend 부하가 커질 수 있다.
- 추후 독립 배포가 필요해지면 분리 작업이 필요하다.

---

## Decision 002: AI는 판정자가 아니라 케이스 처리 보조자다

### Date

TBD

### Context

비자, 체류, 고용변동, 노무 이슈는 법적 책임이 발생할 수 있다.

### Decision

AI는 비자 가능 여부를 확정하지 않는다.  
공식 근거와 현재 상태를 바탕으로 확인할 항목, 누락 서류, 다음 안전 행동, 전문가 검토 지점을 제안한다.

### Consequence

- Safety Guardrail이 필수다.
- Human Approval이 필수다.
- Evidence Log가 필수다.

---

## Decision 003: RAG와 DB/Rule Base를 분리한다

### Date

TBD

### Context

RAG는 공식 근거 검색에는 강하지만 현재 직원 상태 관리에는 적합하지 않다.

### Decision

- 법령·절차·서식·안전자료는 RAG에 넣는다.
- 직원 상태·후보 상태·서류 보유 여부·D-day 계산은 DB/Rule Base에서 처리한다.

### Consequence

- `document_requirements.csv`가 중요하다.
- RAG는 “왜 필요한지”를 설명하는 근거 역할을 한다.

---

## Decision 004: 다국어 Contact Agent 저장은 초안과 후보 상태로 제한한다

### Date

TBD

### Context

다국어 Contact Agent는 메시지 초안, 근로자 답변 요약, 상태 업데이트 후보, Evidence Log 후보 이벤트를 생성한다.

이 결과를 운영 DB에 저장해야 담당자 승인, 반려, 수정, 감사 추적이 가능하다.
다만 외국인 근로자 메시지와 답변에는 개인정보 또는 민감한 상황 설명이 포함될 수 있다.

### Decision

- 다국어 메시지 초안 전문은 `contact_messages.korean_text`, `contact_messages.translated_text`에 저장한다.
- 초안 생성 시 `contact_messages.status=PENDING_APPROVAL`, `approval_required=true`, `sent_at=null`로 관리한다.
- Evidence Log에는 메시지 전문과 `worker_reply` 원문을 저장하지 않는다.
- Evidence Log에는 원문 없는 요약, source_id 목록, risk_flags, 승인 필요 여부만 저장한다.
- 상태 업데이트는 `status_update_candidates`에 후보로만 저장한다.
- 실제 발송과 실제 상태 반영은 approval 이후 별도 단계에서만 가능하다.

### Consequence

장점:

- 담당자가 메시지 초안을 검토하고 승인/반려할 수 있다.
- 감사 로그에는 필요한 근거와 요약만 남아 개인정보 노출 위험이 줄어든다.
- 근로자 서류 상태가 AI 응답만으로 확정 변경되지 않는다.

주의:

- `contact_messages`는 메시지 전문을 저장하므로 접근 권한과 보관 정책이 필요하다.
- `evidence_logs.summary`에는 개인정보 원문을 넣지 않도록 service 계층에서 추가 검증이 필요하다.
