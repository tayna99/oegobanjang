# Backend

외고반장 backend는 FastAPI 기반 서버입니다.

---

## 역할

backend는 다음을 담당합니다.

- 사용자/관리자 인증
- 사업장 정보 관리
- 외국인 근로자 정보 관리
- 채용 요청 관리
- 비자/체류 정보 관리
- 서류 제출/누락 상태 관리
- 다국어 메시지 초안 관리
- 관리자 승인 관리
- Evidence Log 저장
- Agent Runtime 실행

---

## 실행

루트에서 가상환경을 만든 뒤 실행합니다.

```bash
uv venv
.venv\Scripts\activate
uv sync
```

backend 실행:

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

---

## 주요 구조

```txt
backend/app/api
- HTTP API 라우터

backend/app/core
- 보안, 예외, 공통 응답, 로깅

backend/app/db
- SQLAlchemy 세션, Base 설정

backend/app/models
- ORM 모델

backend/app/schemas
- Pydantic 요청/응답 스키마

backend/app/services
- 비즈니스 로직

backend/app/agent_runtime
- LangGraph, Agent, Tool, RAG 실행 모듈

backend/tasks
- 예약/백그라운드 작업

backend/tests
- 테스트
```

---

## Agent Runtime

Agent Runtime은 아래 경로에서 관리합니다.

```txt
backend/app/agent_runtime/
```

주요 역할:

- Intent Router
- Planner
- Agent Execution
- Approval Gate
- Evidence Logger
- RAG Retrieval
- Tool Orchestration

---

## 테스트

```bash
bash scripts/run_backend_tests.sh
bash scripts/run_agent_tests.sh
```

---

## 주의사항

- AI는 비자 가능 여부를 확정하지 않는다.
- AI는 법률·노무 자문을 하지 않는다.
- 외부 발송, 제출, 전달은 반드시 승인 이후에만 가능하다.
- 민감정보 원문은 로그에 저장하지 않는다.