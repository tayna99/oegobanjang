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

```txt
backend/
= FastAPI 기반 제품 API + DB + Agent Runtime + RAG + Evidence Log
```

Agent 관련 코드는 아래 경로에서 관리한다.

```txt
backend/app/agent_runtime/
├─ langchain_v1/
├─ legacy_graph/
├─ agents/
├─ rag/
├─ tools/
└─ schemas/
```

현재 production Agent Runtime은 LangChain 1.0 `create_agent(response_format=...)` 중심의
`langchain_v1/` 경로를 우선한다. `legacy_graph/`는 legacy/custom LangGraph 경로이며,
production import 대상이 아니다. LangGraph 패키지 의존성은 `create_agent` 내부 실행을 위해 유지한다.

---

## 4. 작업 전 읽을 문서

```txt
README.md
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/AI_OS_DESIGN.md
docs/RAG_STRATEGY.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
docs/EVAL_HARNESS.md
```

Agent Runtime 작업자는 추가로 아래 문서를 확인한다.

```txt
docs/GRAPH_STATE.md
docs/EVIDENCE_LOG_SCHEMA.md
missions/active/*.md
```

---

## 5. 작업 방식

1. 관련 문서 확인
2. 관련 mission 확인
3. 변경 범위 확인
4. 작은 단위로 구현
5. 테스트 작성 또는 수정
6. eval 데이터 추가 또는 확인
7. Evidence Log 영향 확인
8. PR 작성

---

## 6. 작업 범위 제한

mission에 적힌 Scope 밖 작업은 하지 않는다.

예를 들어 비자·서류 Agent 작업 중에는 아래 영역을 중심으로 수정한다.

```txt
backend/app/agent_runtime/agents/visa_agent.py
backend/app/agent_runtime/tools/visa_risk_tool.py
backend/app/agent_runtime/tools/document_check_tool.py
backend/tests/test_visa_document_agent.py
evals/datasets/document_gap_cases.jsonl
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

Agent는 이런 작업을 만나면 `approval_required=true`를 반환해야 한다.

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

```bash
bash scripts/verify_all.sh
bash scripts/run_backend_tests.sh
bash scripts/run_agent_tests.sh
bash scripts/run_frontend_tests.sh
python scripts/run_evals.py --dataset safety_guardrail_cases
```

---

## 11. PR 완료 기준

- [ ] mission의 Acceptance Criteria를 만족했는가?
- [ ] 테스트가 통과했는가?
- [ ] 필요한 eval case를 추가했는가?
- [ ] 승인 필요한 작업을 자동 실행하지 않는가?
- [ ] Evidence Log 후보 이벤트가 생성되는가?
- [ ] 민감정보 원문이 로그에 남지 않는가?
- [ ] Scope 밖 파일을 불필요하게 수정하지 않았는가?
