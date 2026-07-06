# Mission 004: Backend Core API

## Goal

외고반장 MVP에 필요한 FastAPI 핵심 API와 기본 DB 모델을 구현한다.

이 mission은 제품 API의 뼈대를 만드는 작업이다.  
Agent의 상세 판단 로직은 Agent Runtime mission에서 다룬다.

---

## Required Reading

```txt
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/DB_SCHEMA.md
docs/SECURITY_GUARDRAILS.md
```

---

## Target Files

```txt
backend/app/main.py
backend/app/config.py

backend/app/api/v1/router.py
backend/app/api/v1/health.py
backend/app/api/v1/auth.py
backend/app/api/v1/companies.py
backend/app/api/v1/workers.py
backend/app/api/v1/hiring.py
backend/app/api/v1/visas.py
backend/app/api/v1/documents.py
backend/app/api/v1/contacts.py

backend/app/core/security.py
backend/app/core/exceptions.py
backend/app/core/responses.py
backend/app/core/logging.py

backend/app/db/session.py
backend/app/db/base.py

backend/app/models/user.py
backend/app/models/company.py
backend/app/models/worker.py
backend/app/models/hiring.py
backend/app/models/visa.py
backend/app/models/document.py
backend/app/models/contact.py

backend/app/schemas/auth.py
backend/app/schemas/company.py
backend/app/schemas/worker.py
backend/app/schemas/hiring.py
backend/app/schemas/visa.py
backend/app/schemas/document.py
backend/app/schemas/contact.py

backend/app/services/auth_service.py
backend/app/services/company_service.py
backend/app/services/worker_service.py
backend/app/services/hiring_service.py
backend/app/services/visa_service.py
backend/app/services/document_service.py
backend/app/services/contact_service.py

backend/tests/test_health.py
```

---

## Scope

이번 mission에서 구현할 범위는 다음과 같다.

- FastAPI 앱 기본 구조
- `/api/v1/health`
- 공통 응답 포맷
- 공통 예외 처리
- request_id 기반 로깅 기초
- SQLAlchemy DB session 설정
- 기본 ORM 모델 초안
- 기본 Pydantic schema 초안
- 주요 API router skeleton
- health test

---

## API Groups

```txt
/api/v1/health
/api/v1/auth
/api/v1/companies
/api/v1/workers
/api/v1/hiring
/api/v1/visas
/api/v1/documents
/api/v1/contacts
```

---

## Out of Scope

이번 mission에서 구현하지 않는다.

- 완전한 인증/인가
- 실제 로그인 보안 완성
- Agent Runtime 상세 구현
- RAG 검색
- 승인/Evidence Log 상세 구현
- 프론트 화면 구현
- 실제 메시지 발송
- 외부 API 연동

---

## Acceptance Criteria

- FastAPI 앱이 실행된다.
- `/api/v1/health`가 정상 응답한다.
- v1 router가 구성되어 있다.
- 공통 응답 포맷이 정의되어 있다.
- DB session 설정 파일이 존재한다.
- 주요 도메인 모델 초안이 존재한다.
- health test가 통과한다.

---

## Verification Commands

```bash
bash scripts/run_backend_tests.sh
```

---

## Human Review Checklist

- [ ] FastAPI 앱이 실행되는가?
- [ ] health endpoint가 정상인가?
- [ ] 공통 응답/예외 구조가 있는가?
- [ ] 도메인별 router가 분리되어 있는가?
- [ ] 민감정보를 로그에 남기지 않는 구조인가?