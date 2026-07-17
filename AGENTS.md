# AGENTS.md

## 1. 프로젝트 목적

외고반장은 외국인 고용 사업장의 체류, 고용, 서류, 다국어 소통, 비자 갱신 업무를 하나의 흐름으로 관리하는 외국인 고용 운영 OS다.

이 프로젝트는 비자 신청 대행 서비스가 아니다.  
핵심은 외국인 고용 과정에서 발생하는 운영 리스크를 줄이고, 담당자가 놓치기 쉬운 서류·기한·소통 문제를 먼저 발견하는 것이다.

---

## 2. 핵심 원칙

```txt
RAG = 공식 근거와 절차를 찾는 곳
SQL/DB = 현재 직원·후보자 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
LLM = 자연어 구조화, 요약, 메시지 생성, 설명을 하는 곳
Human Approval = 발송·제출·전달 전 최종 승인 지점
```

AI는 다음을 하지 않는다.

- 비자 가능 여부를 확정하지 않는다.
- 법률·노무 자문을 하지 않는다.
- 정부 포털 제출을 자동화하지 않는다.
- 외국인 근로자를 감시하지 않는다.
- 후보자의 성실도나 이탈 가능성을 판단하지 않는다.
- 국적별 선호 또는 차별적 추천을 하지 않는다.

---

## 3. 현재 아키텍처

현재 PR/브랜치의 운영 대상은 루트의 모바일 우선 Vite + React MVP다.

```txt
src/
= 현재 제품 UI, 라우팅, 화면 상태, 데모 런 엔진

docs/, plans/, rules/
= 현재 프론트 MVP의 사양, 로드맵, 작업 규칙

legacy/
= 이전 FastAPI 백엔드, 데이터 파이프라인, Agent Runtime, eval, 기존 문서 보관 영역
```

루트 `backend/`는 `db/schema.sql`을 그대로 적용하는 FastAPI 서비스로 이미 존재하고 동작한다(OTP 인증·세션, 승인 요청 생성 + approve/reject, pytest 스위트가 CI에 편입). 다만 프론트(`src/`)는 아직 이 backend를 한 줄도 호출하지 않는다(fetch 0건) — 배선은 `plans/ROADMAP.md` R2 범위다. `legacy/backend/`는 이전 백엔드(Agent Runtime 포함)를 보존한 별개 경로이며, 새 프론트 MVP 작업의 production import 대상이 아니다.

Agent Runtime 관련 코드는 legacy 영역에 남아 있다.

```txt
legacy/backend/app/agent_runtime/
├─ langchain_v1/
├─ legacy_graph/
├─ agents/
├─ rag/
├─ tools/
└─ schemas/
```

Agent Runtime 또는 기존 백엔드 복구/이관 mission이 명시된 경우에만 `legacy/backend/`를 수정한다. 그 외 일반 MVP 화면 작업은 `src/`, `docs/`, `plans/`, `rules/`를 중심으로 진행한다.

---

## 4. 작업 전 읽을 문서

현재 루트 MVP 작업자는 아래 문서를 먼저 확인한다.

```txt
README.md
docs/ARCHITECTURE.md
docs/SPEC_INDEX.md
docs/GOTCHAS.md
plans/ROADMAP.md
plans/HANDOFF.md
rules/design.md
rules/frontend.md
rules/safety.md
```

legacy 백엔드 또는 Agent Runtime 작업자는 추가로 아래 문서를 확인한다.

```txt
legacy/docs/*
legacy/missions/active/*.md
legacy/backend/app/agent_runtime/**
```

---

## 5. 작업 방식

1. 관련 문서 확인
2. 관련 mission 또는 roadmap 항목 확인
3. 변경 범위 확인
4. 작은 단위로 구현
5. 테스트 작성 또는 수정
6. 필요한 경우 eval 데이터 추가 또는 확인
7. Evidence Log 영향 확인
8. PR 작성

---

## 6. 작업 범위 제한

mission 또는 roadmap에 적힌 Scope 밖 작업은 하지 않는다.

프론트 MVP 작업 중에는 주로 아래 영역을 수정한다.

```txt
src/
docs/
plans/
rules/
```

legacy 백엔드/Agent 작업이 명시된 경우에는 아래 영역을 중심으로 수정한다.

```txt
legacy/backend/app/agent_runtime/
legacy/backend/tests/
legacy/evals/
legacy/missions/
legacy/docs/
```

---

## 7. 금지 작업

아래 기능은 구현하지 않는다.

- AI 단독 비자 신청 제출
- AI 단독 법률·노무 자문
- 정부 포털 직접 자동 제출
- 근로자 SNS, 단톡방, 외부 커뮤니티 감시
- 이탈 예측 모델
- 국적별 선호 또는 차별적 추천
- 사업장 공개 평판 점수
- 브로커 색출

---

## 8. 승인 필요 작업

아래 작업은 초안 생성까지만 가능하다.  
실제 실행은 담당자 승인 이후에만 가능하다.

- 외국인 근로자에게 메시지 발송
- 행정사/노무사에게 패키지 전달
- 케이스 상태 완료 처리
- 대외 제출용 문서 export
- 카톡/문자 푸시 발송

Agent 또는 UI 플로우는 이런 작업을 만나면 `approval_required=true`를 반환하거나 승인 대기 상태로 표시해야 한다.

---

## 9. Evidence Log 원칙

중요한 판단에는 Evidence Log 후보 이벤트를 남긴다.

반드시 기록해야 하는 이벤트:

- intent_classified
- plan_created
- tool_executed
- rag_retrieved
- risk_flagged
- approval_requested
- final_response_generated

민감정보 원문은 Evidence Log에 저장하지 않는다.

---

## 10. 검증 명령

현재 루트 MVP 검증은 아래 명령을 우선 사용한다.

```bash
npm run verify
```

legacy 백엔드/Agent Runtime을 수정한 경우에는 해당 legacy 검증도 함께 수행한다.

```bash
bash legacy/scripts/verify_all.sh
bash legacy/scripts/run_backend_tests.sh
bash legacy/scripts/run_agent_tests.sh
python legacy/scripts/run_evals.py --dataset safety_guardrail_cases
```

---

## 11. PR 완료 기준

- [ ] mission 또는 roadmap Acceptance Criteria를 만족했는가?
- [ ] 테스트가 통과했는가?
- [ ] 필요한 eval case를 추가했는가?
- [ ] 승인 필요한 작업을 자동 실행하지 않는가?
- [ ] Evidence Log 후보 이벤트가 생성되는가?
- [ ] 민감정보 원문이 로그에 남지 않는가?
- [ ] Scope 밖 파일을 불필요하게 수정하지 않았는가?
