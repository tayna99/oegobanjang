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

현재 PR/브랜치의 운영 대상은 두 갈래다 — 프론트 MVP(`src/`)와 신규 백엔드 접속점(`backend/`, 2026-07-12부터).

```txt
src/
= 현재 제품 UI, 라우팅, 화면 상태, 데모 런 엔진

backend/
= 신규 서비스 API — FastAPI + SQLAlchemy + Alembic. docs/DB_SCHEMA.md가 스키마 설계 정본

docs/, plans/, rules/
= 프론트 MVP + 백엔드의 사양, 로드맵, 작업 규칙

legacy/
= 이전 FastAPI 백엔드, 데이터 파이프라인, Agent Runtime, eval, 기존 문서 보관 영역
```

**`backend/`는 `legacy/backend/`의 부활이 아니라 신규 구현이다.** `docs/DB_SCHEMA.md`(§10 P1/P2/P3 단계 도입)를 정본으로 처음부터 다시 설계했고, 레거시 결함 20건(`docs/DB_SCHEMA.md` §12 — 런타임 `ALTER TABLE`, ORM relationship 부재, `create_all()` 산재 등)을 의도적으로 피한다. 현재는 **P1 코어 18테이블**(모델·유일한 Alembic 리비전·가드레일 테스트)까지 있고, API 라우터는 화면이 백엔드에 붙는 순서대로 점진 추가한다(진행 상황은 `backend/README.md` + `plans/HANDOFF.md`). **Agent Runtime은 아직 신규 `backend/`로 이관되지 않았다** — 계속 `legacy/backend/app/agent_runtime/`에만 있으며, 이관은 별도 mission의 몫이다.

```txt
legacy/backend/app/agent_runtime/
├─ langchain_v1/
├─ legacy_graph/
├─ agents/
├─ rag/
├─ tools/
└─ schemas/
```

Agent Runtime 또는 기존 legacy 백엔드 복구/이관 mission이 명시된 경우에만 `legacy/backend/`를 수정한다. 신규 `backend/`(서비스 API) 작업은 이 조건과 무관하게 항상 유효한 대상이다 — `legacy/backend/`와 완전히 별개 트리로 취급한다. 그 외 일반 MVP 화면 작업은 `src/`, `docs/`, `plans/`, `rules/`를 중심으로 진행한다.

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

신규 `backend/` 작업자는 추가로 아래 문서를 확인한다.

```txt
docs/DB_SCHEMA.md        # 스키마 설계 정본 — §4 테이블 정의, §5 가드레일, §8 프론트 계약 매핑
backend/README.md        # 세팅·마이그레이션·테스트 방법, 알려진 스코프 경계
db/README.md             # DBeaver로 스키마를 직접 열어볼 때
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

신규 `backend/` 작업 중에는 아래 영역을 중심으로 수정한다.

```txt
backend/app/
backend/migrations/
backend/tests/
docs/DB_SCHEMA.md   # 스키마를 바꾸면 모델·마이그레이션과 같은 PR에서 함께 갱신
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

신규 `backend/`를 수정한 경우 아래 명령을 사용한다.

```bash
cd backend && uv run pytest
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
