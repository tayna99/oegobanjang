# AI OS Design

## 1. 목적

외고반장의 AI OS는 사용자의 자연어 요청을 받아 업무 의도를 분류하고, 필요한 전문 에이전트를 실행한 뒤, 안전한 다음 행동과 근거를 생성한다.

이 시스템은 단순 챗봇이 아니라 외국인 고용 업무를 상태 기반으로 처리하는 Agentic Workflow다.

---

## 2. 전체 흐름

```txt
User Request
→ Intent Router
→ Planner
→ State Loader
→ Agent Execution
→ Risk / Human Approval
→ Evidence Log
→ Final Response
```

---

## 3. 핵심 설계 원칙

```txt
RAG = 공식 근거와 절차를 찾는 곳
SQL/DB = 현재 직원·후보자 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
LLM = 자연어 구조화, 요약, 메시지 생성, 설명을 하는 곳
Human Approval = 발송·제출·전달 전 최종 승인 지점
```

- 모든 어려운 문제를 검색 문제로 재구조화한다.
- AI는 판정자가 아니라 케이스 처리 보조자다.
- 법령·절차·서식·안전자료는 RAG에서 찾는다.
- 현재 직원 상태, 후보자 상태, 서류 보유 여부, D-day 계산은 DB/Rule Base에서 처리한다.
- 발송·제출·전달 전에는 반드시 Human Approval을 거친다.

---

## 4. Agent 구성

| 담당자 | Agent | 책임 |
|---|---|---|
| 김현욱 | Visa Document Agent | 비자, 체류, 서류, D-day, 행정사 전달 패키지 |
| 임태나 | Workforce Agent | 인력 확보, 신규 채용 요청, 후보 요건 확인 |
| 유현희 | Multilingual Contact Agent | 다국어 메시지, 응답 해석, 온보딩 안내 |

---

## 5. Visa Document Agent

### Owner

김현욱

### 책임

- 체류만료 D-day 계산
- E-9 체류 관련 리스크 탐지
- 케이스별 필수 서류 체크
- 누락 서류 계산
- 공식 근거 RAG 검색
- 행정사 전달 패키지 초안 생성
- Evidence Log 생성

### 금지

- 비자 연장 가능 여부 확정
- 법률 자문
- 서류 최종 제출
- 행정사 자동 전송
- 외국인등록번호 원문 로그 저장

---

## 6. Workforce Agent

### Owner

임태나

### 책임

- 신규 채용 의도 파악
- E-9 고용 절차 검색
- 사업장 확인 항목 정리
- 후보자 서류 준비 상태 확인
- 송출회사/행정사에게 물어볼 질문 생성
- 신규 인력 요청서 초안 생성

### 금지

- 후보자 성실도 판단
- 장기근속 가능성 예측
- 국적별 선호
- 특정 후보 자동 추천
- 최종 고용 가능 여부 확정

---

## 7. Multilingual Contact Agent

### Owner

유현희

### 책임

- 다국어 메시지 초안 생성
- 개인정보 사용 목적 안내 포함
- 제출 기한 안내 포함
- 근로자 답변 요약
- 확보된 서류와 부족한 서류 추출
- 상태 업데이트 후보 생성
- 담당자 승인 필요 여부 표시

### LangChain v1 실행 형태

현재 다국어 컨택 Agent는 LangChain v1 통합 Agent 안에서 호출 가능한 2개
`LangChain tool-callable sub-agent wrappers`로 노출한다. 독립 실행 서버나 별도
LangGraph subgraph가 아니다.

| Sub-Agent Wrapper | LangChain tool | 책임 |
|---|---|---|
| Contact Onboarding Sub-Agent | `run_contact_onboarding` | 다국어 메시지 초안 생성, RAG 근거 검색, `message_templates.csv` 기반 초안 생성, translation quality check |
| Worker Reply Interpreter Sub-Agent | `run_worker_reply_interpreter` | 근로자 답변 번역/요약, `translated_ko`, 상태 업데이트 후보, 담당자 next action 후보 생성 |

두 wrapper 모두 외부 발송, 상태 확정, 정부 제출, 전문가 자동 전달을 수행하지 않는다.
메시지 초안은 `approval_required=true`, 근로자 답변 해석은
`approval_required=true` 및 `manager_review_required=true`를 반환한다.
상태 업데이트는 후보만 생성하며 `candidate.is_final=false`를 유지한다.
Evidence Log 후보에는 메시지 전문, `worker_reply` 원문, `translated_ko` 전문을 저장하지 않는다.

### MVP 언어 범위

- 1순위: 베트남어(`vi`)는 메시지 생성, 한국어 원문 표시, 개인정보 사용 목적/제출 기한 포함, 담당자 승인 대기, 베트남어 답변 요약, 서류 상태 업데이트 후보, Evidence Log 후보 생성까지 end-to-end로 검증한다.
- 2순위: 인도네시아어(`id`)는 같은 템플릿을 사용한 메시지 생성만 시연한다.
- 다른 언어는 이번 1주 MVP 범위에 포함하지 않는다.

### 금지

- 승인 없는 자동 발송
- 차별적 표현
- 협박성 문구
- 법적 확답
- 민감정보 과다 노출

---

## 8. Agent Runtime 위치

```txt
backend/app/agent_runtime/
├─ graph/
├─ agents/
├─ rag/
├─ tools/
└─ schemas/
```

---

## 9. Agent 실행 원칙

- 모든 Agent는 결과와 함께 근거를 반환해야 한다.
- 모든 Agent는 `approval_required` 여부를 명시해야 한다.
- 모든 Agent는 Evidence Log 후보 이벤트를 생성해야 한다.
- Agent는 외부 발송, 제출, 전달을 직접 실행하지 않는다.
- 최종 저장은 backend service 계층에서 처리한다.
---

## Agent Chat 현재 구현 기준

`/api/v1/agent/chat`은 Daily Briefing 화면과 같은 운영 snapshot을 사용한다.

```txt
사용자 질문
→ RAG/semantic retrieval로 업무 후보 검색
→ LLM 또는 strict normalizer가 intent/entity/action 정규화
→ intent에 맞는 DB/Rule/RAG tool 결과 실행
→ retrieved chunk와 tool result 안에서 답변 생성
```

- RAG는 공식 정책 문서와 마스킹된 운영 snapshot을 함께 검색한다.
- DB는 현재 직원, 후보자, 서류, action, citation 상태의 source of truth다.
- Rule Base는 D-day, 누락 여부, 계약-체류 충돌, 신고기한을 계산한다.
- LLM은 자연어 정규화와 요약만 담당하며 실행 권한을 갖지 않는다.
- 발송, 제출, 전달, 완료 처리는 `approval_required=true`로 막고 담당자 승인 후 별도 단계에서만 처리한다.
- 화면 표시명은 backend의 `subject_display_name` / `subject_display_id`를 사용한다. raw PII는 API 응답, evidence log, frontend fixture에 노출하지 않는다.

`frontend-proto`는 더 이상 순수 mock 화면이 아니라 API-backed demo shell이다. backend 연결 실패 시에만 demo fixture를 fallback으로 보여주며, 이때 UI에 `데모 데이터` 배지를 표시한다.
