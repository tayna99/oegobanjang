# 외고반장

외고반장은 외국인 고용 사업장의 체류, 고용, 서류, 다국어 소통, 비자 갱신 업무를 하나의 흐름으로 관리하는 **외국인 고용 운영 OS**입니다.

이 프로젝트는 비자 신청을 대행하거나 법률 판단을 자동화하는 서비스가 아닙니다.  
공식 규정, 직원 상태, 누락 정보, 메시지 초안, 행정사 전달 패키지를 정리해 담당자와 전문가가 안전하게 판단할 수 있도록 돕는 것이 목표입니다.

---

## 프로젝트 초기 세팅

### 1. Python 가상환경 생성

```bash
uv venv
```

### 2. 가상환경 활성화

Windows 기준:

```bash
.venv\Scripts\activate
```

macOS / Linux 기준:

```bash
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
uv sync
```

---

## 로컬 실행 흐름

### 1. 환경변수 파일 준비

`.env.example`을 복사해서 `.env`를 만듭니다.

```bash
cp .env.example .env
```

Windows PowerShell 기준:

```powershell
copy .env.example .env
```

`.env`에는 실제 API Key, DB 접속 정보 등을 작성합니다.  
`.env`는 Git에 올리지 않습니다.

현재 MVP의 service DB는 SQLite입니다.
backend 폴더 실행 기준 기본 DB URL은 아래와 같습니다.

```bash
DATABASE_URL=sqlite:///./data/oegobanjang.sqlite3
```

---

### 2. 로컬 인프라 실행

현재 MVP의 service DB는 SQLite를 사용합니다.
DB 파일은 backend 실행 기준 `backend/data/oegobanjang.sqlite3`에 생성됩니다.
Chroma는 RAG/vector search용 저장소이며 SQLite service DB와 별도입니다.
필요한 로컬 인프라가 있을 때 Docker로 실행합니다.

```bash
docker compose up -d
```

실행 확인:

```bash
docker ps
```

---

### 3. 백엔드 실행

FastAPI 백엔드 서버 하나 안에서 일반 API와 LangGraph/RAG/Agent Runtime을 함께 실행합니다.

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

---

### 4. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

---

## 프로젝트 한 줄 정의

E-9 외국인 근로자를 고용하는 제조업 중소기업이 비자 만료, 서류 누락, 고용변동 신고, 다국어 소통 리스크를 놓치지 않도록 돕는 AI 기반 운영 관리 시스템입니다.

---

## 핵심 원칙

```txt
RAG = 공식 근거와 절차를 찾는 곳
SQL/DB = 현재 직원·후보자 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
LLM = 자연어 구조화, 요약, 메시지 생성, 설명을 하는 곳
Human Approval = 발송·제출·전달 전 최종 승인 지점
```

외고반장의 AI는 다음을 하지 않습니다.

- 비자 가능 여부를 확정하지 않음
- 법률·노무 자문을 하지 않음
- 정부 포털 제출을 자동화하지 않음
- 외국인 근로자를 감시하지 않음
- 후보자의 성실도나 이탈 가능성을 판단하지 않음
- 국적별 선호 또는 차별적 추천을 하지 않음

---

## 주요 기능

### MVP 범위

- 직원 CSV 업로드
- 체류만료 D-day 계산
- 서류 누락 체크
- 공식 규정 RAG 검색
- 다음 안전 행동 추천
- 다국어 메시지 초안 생성
- 행정사 전달 패키지 초안 생성
- 관리자 승인
- Evidence Log 저장

---

## 에이전트 구성

외고반장은 3개 Agent로 구성된다.

- Visa Document Agent
- Workforce Agent
- Multilingual Contact Agent

상세 역할은 `docs/AI_OS_DESIGN.md`를 참고한다.

---

## 전체 흐름

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

## 기술 구조

초기 MVP에서는 서버를 하나만 띄웁니다.

```txt
backend/
= FastAPI 단일 서버
= 일반 API + DB + Agent Runtime + RAG + Evidence Log

frontend/
= Next.js 또는 React 기반 관리자 화면

data-pipeline/
= 공식 문서 수집, 전처리, chunk 생성, Vector DB 적재

docs/
= 설계 문서와 하네스 문서

missions/
= 팀원/AI에게 줄 작업 단위

evals/
= 에이전트 평가 데이터셋
```

---

## 주요 폴더

```txt
backend/app/api
- HTTP API 라우터

backend/app/models
- SQLAlchemy ORM 모델

backend/app/schemas
- Pydantic 요청/응답 스키마

backend/app/services
- 비즈니스 로직

backend/app/agent_runtime
- LangGraph, Agent, Tool, RAG 실행 모듈

data-pipeline
- RAG 데이터 수집/전처리

docs
- 프로젝트 설계 문서

missions
- 작업 지시서

evals
- 평가 데이터셋

.claude
- Claude Code 팀원용 작업 지침

scripts
- 테스트, 평가, 문서 적재 실행 스크립트
```

---
