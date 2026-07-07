
# Docs

이 폴더는 외고반장 프로젝트의 설계 문서와 하네스 문서를 관리한다.

문서의 목적은 팀원과 AI Agent가 같은 기준으로 작업하도록 만드는 것이다.  
각 문서는 역할이 다르므로 같은 내용을 여러 문서에 반복해서 적지 않는다.

---

## 1. 문서 읽는 순서

처음 프로젝트에 참여하는 사람은 아래 순서로 읽는다.

```txt
1. PROJECT_BRIEF.md
2. ARCHITECTURE.md
3. AI_OS_DESIGN.md
4. RAG_STRATEGY.md
5. TOOL_CONTRACT.md
6. SECURITY_GUARDRAILS.md
7. EVAL_HARNESS.md
```

Agent Runtime 또는 LangGraph 작업자는 추가로 아래 문서를 읽는다.

```txt
8. GRAPH_STATE.md
9. EVIDENCE_LOG_SCHEMA.md
```

API, DB, 운영 로그를 작업하는 사람은 아래 문서를 함께 읽는다.

```txt
10. API_CONTRACT.md
11. DB_SCHEMA.md
12. OBSERVABILITY.md
```

---

## 2. 문서 역할

| 문서 | 역할 |
|---|---|
| `PROJECT_BRIEF.md` | 프로젝트 정의, 문제, 사용자, MVP 범위, 제외 범위 |
| `ARCHITECTURE.md` | 전체 시스템 구조와 서버/DB/Agent Runtime 구성 |
| `AI_OS_DESIGN.md` | Agent 구조, LangGraph 흐름, Agent별 책임 |
| `GRAPH_STATE.md` | LangGraph State 필드와 상태 변경 규칙 |
| `TOOL_CONTRACT.md` | Tool 등급, Tool 응답 형식, 승인 필요 작업 |
| `RAG_STRATEGY.md` | 데이터 수집, chunking, metadata, 검색 전략 |
| `SECURITY_GUARDRAILS.md` | 개인정보, 법적 책임, 금지 작업, 승인 필요 작업 |
| `EVIDENCE_LOG_SCHEMA.md` | Evidence Log 이벤트와 DB 스키마 |
| `OBSERVABILITY.md` | request_id 기반 로그, 메트릭, 추적 기준 |
| `EVAL_HARNESS.md` | 평가 데이터셋, 통과 기준, safety eval 기준 |
| `API_CONTRACT.md` | 프론트엔드와 백엔드 API 계약 |
| `DB_SCHEMA.md` | SQLite MVP service DB와 planned table 정리 |
| `DECISIONS.md` | 중요한 기술/제품 의사결정 기록 |
| `HANDOFF.md` | 팀원 또는 AI Agent에게 넘길 인수인계 내용 |

---

## 3. 문서별 원칙

### `PROJECT_BRIEF.md`

프로젝트의 “무엇을 만들 것인가”를 정의한다.

포함할 내용:

- 프로젝트 한 줄 정의
- 해결하려는 문제
- 사용자
- MVP 범위
- 제외 범위
- 성공 기준

---

### `ARCHITECTURE.md`

시스템의 “어떻게 구성할 것인가”를 정의한다.

포함할 내용:

- frontend
- backend
- Agent Runtime
- data-pipeline
- SQLite service DB
- Chroma
- Redis 사용 여부
- 요청 흐름
- 확장 기준

아키텍처 결정 이유는 `DECISIONS.md`에도 함께 남긴다.

---

### `AI_OS_DESIGN.md`

Agent 설계의 기준 문서다.

Agent별 담당자, 책임, 입력, 출력, 금지 범위는 이 문서에만 상세히 적는다.  
다른 문서에서는 담당 업무를 반복하지 않고 이 문서를 참고한다.

---

### `RAG_STRATEGY.md`

데이터 수집과 RAG 설계 기준 문서다.

포함할 내용:

- 어떤 데이터를 RAG에 넣는지
- 어떤 데이터를 DB/Rule Base로 관리하는지
- 공식 문서 수집 대상
- chunking 전략
- metadata schema
- evidence grade
- 검색 실패 처리

---

### `TOOL_CONTRACT.md`

Agent가 사용할 Tool의 계약 문서다.

포함할 내용:

- SAFE_READ
- SAFE_CALCULATE
- SAFE_DRAFT
- APPROVAL_REQUIRED
- FORBIDDEN
- Tool 공통 응답 형식
- 승인 필요 작업 처리 방식

---

### `SECURITY_GUARDRAILS.md`

보안과 안전 기준 문서다.

포함할 내용:

- 개인정보 처리 원칙
- 마스킹 규칙
- 금지 작업
- 승인 필요 작업
- 법적 책임 분리
- 감시·차별 금지

---

### `EVAL_HARNESS.md`

AI Agent가 안전하고 정확하게 동작하는지 검증하는 기준 문서다.

포함할 내용:

- Intent Router 평가
- RAG Retrieval 평가
- Document Gap 평가
- Message Generation 평가
- Safety Guardrail 평가
- Workflow E2E 평가

---

## 4. 문서 중복 방지 규칙

같은 내용을 여러 문서에 반복해서 쓰지 않는다.

기준은 아래와 같다.

```txt
프로젝트 목적과 MVP 범위
→ PROJECT_BRIEF.md

전체 구조와 확장 기준
→ ARCHITECTURE.md

Agent 역할과 담당자
→ AI_OS_DESIGN.md

RAG와 데이터 수집
→ RAG_STRATEGY.md

Tool 등급과 실행 규칙
→ TOOL_CONTRACT.md

보안, 금지, 승인 필요 작업
→ SECURITY_GUARDRAILS.md

Evidence Log
→ EVIDENCE_LOG_SCHEMA.md

평가 기준
→ EVAL_HARNESS.md

결정 이유
→ DECISIONS.md
```

다른 문서에서는 필요한 경우 링크나 문서명만 참조한다.

예시:

```txt
Agent별 상세 책임은 AI_OS_DESIGN.md를 따른다.
```

---

## 5. 문서 작성 스타일

문서는 아래 원칙을 따른다.

- 짧고 명확하게 작성한다.
- 구현자가 바로 참고할 수 있게 쓴다.
- 추상적인 설명보다 입력/출력/금지 범위를 우선한다.
- 표와 목록을 적극적으로 사용한다.
- 코드나 API가 바뀌면 관련 문서를 함께 수정한다.
- 중요한 결정은 `DECISIONS.md`에 이유와 함께 남긴다.

---

## 6. 팀원 작업 시 참고 문서

### 비자·서류 Agent 작업

```txt
PROJECT_BRIEF.md
AI_OS_DESIGN.md
RAG_STRATEGY.md
TOOL_CONTRACT.md
SECURITY_GUARDRAILS.md
EVIDENCE_LOG_SCHEMA.md
missions/active/003-visa-document-agent.md
```

### 인력 확보 Agent 작업

```txt
PROJECT_BRIEF.md
AI_OS_DESIGN.md
RAG_STRATEGY.md
TOOL_CONTRACT.md
SECURITY_GUARDRAILS.md
missions/active/004-workforce-agent.md
```

### 다국어 Agent 작업

```txt
PROJECT_BRIEF.md
AI_OS_DESIGN.md
RAG_STRATEGY.md
TOOL_CONTRACT.md
SECURITY_GUARDRAILS.md
missions/active/005-multilingual-contact-agent.md
```

### RAG/Data Pipeline 작업

```txt
RAG_STRATEGY.md
EVAL_HARNESS.md
SECURITY_GUARDRAILS.md
missions/active/002-rag-indexing.md
```

---

## 7. 문서 변경 체크리스트

문서를 수정할 때 아래를 확인한다.

- [ ] 같은 내용이 다른 문서에 중복되어 있지 않은가?
- [ ] 담당자/Agent 역할은 `AI_OS_DESIGN.md`에만 상세히 있는가?
- [ ] 금지 작업과 승인 필요 작업이 `SECURITY_GUARDRAILS.md`와 충돌하지 않는가?
- [ ] Tool 관련 내용이 `TOOL_CONTRACT.md`와 일치하는가?
- [ ] RAG 관련 내용이 `RAG_STRATEGY.md`와 일치하는가?
- [ ] 중요한 결정이라면 `DECISIONS.md`에 이유를 남겼는가?
