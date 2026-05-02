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