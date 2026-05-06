oegobanjang
├─ AGENTS.md                         # 모든 AI/사람 개발자가 공통으로 따라야 하는 작업 규칙
├─ CLAUDE.md                         # Claude Code 사용자가 가장 먼저 읽는 루트 지침
├─ README.md                         # 프로젝트 소개, 실행 방법, 전체 구조 설명
├─ FOLDER_STRUCTURE.md               # 실제 프로젝트 폴더/파일 구조 문서
├─ .gitignore                        # Git에 올리지 않을 파일/폴더 목록
├─ .python-version                   # 로컬 Python 버전 고정
├─ .env                              # 실제 로컬 환경변수 파일, Git에 올리면 안 됨
├─ .env.example                      # 팀원이 참고할 환경변수 예시 파일, Git에 올림
├─ pyproject.toml                    # Python 프로젝트 설정, 의존성, formatter/test 설정
├─ uv.lock                           # uv 의존성 lockfile
├─ docker-compose.yml                # 로컬 개발용 Postgres, Chroma, Redis 등 인프라 실행 설정
├─ DATA_GENERATION_REPORT.md         # 더미 운영 데이터 생성 결과 리포트
│
├─ backend/                          # FastAPI 단일 백엔드 서버: 제품 API + Agent Runtime 통합
│  ├─ README.md                      # 백엔드 실행 방법, 구조, 테스트 방법 설명
│  ├─ alembic.ini                    # Alembic DB 마이그레이션 설정
│  │
│  ├─ app/
│  │  ├─ main.py                     # FastAPI 앱 진입점, 라우터 등록, health check 등록
│  │  ├─ config.py                   # 환경변수, DB, Chroma, LLM 설정 로딩
│  │  │
│  │  ├─ api/                        # HTTP API 라우터 영역
│  │  │  └─ v1/
│  │  │     ├─ router.py             # v1 API 라우터 통합
│  │  │     ├─ health.py             # 서버 상태 확인 API
│  │  │     ├─ auth.py               # 로그인, 회원가입, 토큰 발급 API
│  │  │     ├─ companies.py          # 사업장 정보 API
│  │  │     ├─ workers.py            # 외국인 근로자 정보 API
│  │  │     ├─ hiring.py             # 신규 채용 요청, 쿼터 확인 API
│  │  │     ├─ visas.py              # 체류자격, 만료일, 비자 리스크 API
│  │  │     ├─ documents.py          # 서류 체크리스트, 제출/누락 서류 API
│  │  │     ├─ contacts.py           # 다국어 메시지 초안, 응답 이력 API
│  │  │     ├─ approvals.py          # 관리자 승인 대기, 승인/거절 API
│  │  │     ├─ evidence.py           # Evidence Log 조회 API
│  │  │     └─ agent.py              # LangGraph Agent 실행 API
│  │  │
│  │  ├─ core/                       # 백엔드 공통 핵심 모듈
│  │  │  ├─ security.py              # JWT, 비밀번호 해시, 권한 검사
│  │  │  ├─ exceptions.py            # 커스텀 예외, 예외 코드 정의
│  │  │  ├─ responses.py             # 공통 API 응답 포맷
│  │  │  └─ logging.py               # request_id, 구조화 로그, 감사 로그 연동
│  │  │
│  │  ├─ db/                         # DB 연결 영역
│  │  │  ├─ session.py               # SQLAlchemy DB 세션 생성
│  │  │  └─ base.py                  # SQLAlchemy Base 및 모델 import 관리
│  │  │
│  │  ├─ models/                     # SQLAlchemy ORM 모델
│  │  │  ├─ user.py                  # 사용자/관리자 계정 테이블
│  │  │  ├─ company.py               # 사업장 정보 테이블
│  │  │  ├─ worker.py                # 외국인 근로자 정보 테이블
│  │  │  ├─ hiring.py                # 채용 요청, 쿼터 계산 결과 테이블
│  │  │  ├─ visa.py                  # 체류자격, 만료일, 갱신 상태 테이블
│  │  │  ├─ document.py              # 서류 제출/누락 상태 테이블
│  │  │  ├─ contact.py               # 다국어 메시지, 응답 이력 테이블
│  │  │  ├─ approval.py              # 관리자 승인 요청/결과 테이블
│  │  │  └─ evidence.py              # Evidence Log 테이블
│  │  │
│  │  ├─ schemas/                    # Pydantic 요청/응답 스키마
│  │  │  ├─ auth.py                  # 인증 요청/응답 스키마
│  │  │  ├─ company.py               # 사업장 API 스키마
│  │  │  ├─ worker.py                # 근로자 API 스키마
│  │  │  ├─ hiring.py                # 채용/쿼터 API 스키마
│  │  │  ├─ visa.py                  # 비자/체류 API 스키마
│  │  │  ├─ document.py              # 서류 API 스키마
│  │  │  ├─ contact.py               # 다국어 메시지 API 스키마
│  │  │  ├─ approval.py              # 승인 API 스키마
│  │  │  ├─ evidence.py              # Evidence Log API 스키마
│  │  │  └─ agent.py                 # Agent 실행 요청/응답 스키마
│  │  │
│  │  ├─ services/                   # 일반 백엔드 비즈니스 로직
│  │  │  ├─ auth_service.py          # 인증/토큰 관련 로직
│  │  │  ├─ company_service.py       # 사업장 관리 로직
│  │  │  ├─ worker_service.py        # 근로자 관리 로직
│  │  │  ├─ hiring_service.py        # 채용 요청/쿼터 결과 저장 로직
│  │  │  ├─ visa_service.py          # 체류만료, D-day, 리스크 조회 로직
│  │  │  ├─ document_service.py      # 서류 체크리스트/누락 상태 관리 로직
│  │  │  ├─ contact_service.py       # 메시지 초안/응답 이력 관리 로직
│  │  │  ├─ approval_service.py      # 승인 요청 생성, 승인/거절 처리 로직
│  │  │  ├─ evidence_service.py      # Evidence Log 저장/조회 로직
│  │  │  └─ agent_service.py         # Agent Runtime 호출 및 결과 저장 조율
│  │  │
│  │  ├─ agent_runtime/              # AI 실행 모듈
│  │  │  ├─ README.md                # Agent Runtime 구조와 실행 흐름 설명
│  │  │  │
│  │  │  ├─ graph/                   # LangGraph 상태 머신 구성 영역
│  │  │  │  ├─ state.py              # Graph State 정의, 요청/계획/결과/근거 상태 관리
│  │  │  │  ├─ workflow.py           # 전체 LangGraph 그래프 연결
│  │  │  │  └─ nodes/
│  │  │  │     ├─ intent_router.py   # 사용자 요청 의도 분류
│  │  │  │     ├─ planner.py         # 실행 계획 수립
│  │  │  │     ├─ executor.py        # Agent/Tool 실행 제어
│  │  │  │     ├─ approval_gate.py   # 승인 필요 여부 판단
│  │  │  │     ├─ evidence_logger.py # Evidence Log 후보 이벤트 생성
│  │  │  │     └─ final_response.py  # 최종 응답 생성
│  │  │  │
│  │  │  ├─ agents/                  # 업무별 전문 AI Agent
│  │  │  │  ├─ hiring_agent.py       # 인력 확보, 쿼터 판단, 채용 요청 처리
│  │  │  │  ├─ contact_agent.py      # 다국어 메시지 생성, 응답 해석
│  │  │  │  └─ visa_agent.py         # 비자/체류/서류 리스크 관리
│  │  │  │
│  │  │  ├─ rag/                     # RAG 검색 관련 모듈
│  │  │  │  ├─ retriever.py          # 문서 검색 로직
│  │  │  │  ├─ embeddings.py         # 임베딩 모델 설정
│  │  │  │  ├─ vector_store.py       # Chroma 등 Vector DB 연결
│  │  │  │  ├─ citation.py           # 검색 근거 citation 생성
│  │  │  │  └─ chunking.py           # 문서 chunk 분할 전략
│  │  │  │
│  │  │  ├─ tools/                   # Agent가 호출하는 기능 도구
│  │  │  │  ├─ quota_tool.py         # 고용 가능 인원/쿼터 계산
│  │  │  │  ├─ document_check_tool.py# 필수 서류 누락 확인
│  │  │  │  ├─ translation_tool.py   # 다국어 번역/메시지 초안 생성
│  │  │  │  ├─ visa_risk_tool.py     # 체류 만료일, 리스크 수준 판단
│  │  │  │  └─ handoff_package_tool.py# 행정사/노무사 전달 패키지 초안 생성
│  │  │  │
│  │  │  └─ schemas/                 # Agent 내부 데이터 스키마
│  │  │     ├─ state.py              # Agent State 세부 타입
│  │  │     ├─ tool.py               # Tool 실행 결과 스키마
│  │  │     └─ evidence.py           # Evidence 후보 이벤트 스키마
│  │  │
│  │  └─ tasks/                      # 백그라운드/예약 작업 영역
│  │     ├─ visa_alert_task.py       # 비자 만료 D-day 알림 작업
│  │     ├─ rag_ingest_task.py       # RAG 문서 인덱싱 작업
│  │     └─ cleanup_task.py          # 임시 파일/오래된 작업 정리
│  │
│  ├─ tests/                         # 백엔드 전체 테스트
│  │  ├─ test_health.py              # 서버 health API 테스트
│  │  ├─ test_agent_workflow.py      # Agent Runtime 전체 흐름 테스트
│  │  ├─ test_guardrails.py          # 금지/승인 필요 작업 가드레일 테스트
│  │  ├─ test_approvals.py           # 승인 생성/처리 테스트
│  │  └─ test_evidence.py            # Evidence Log 저장/조회 테스트
│  │
│  └─ migrations/                    # Alembic DB 마이그레이션
│     ├─ env.py                      # Alembic 실행 환경 설정
│     └─ script.py.mako              # 마이그레이션 파일 템플릿
│
├─ frontend/                         # Next.js / React 프론트엔드
│  ├─ app/                           # Next.js App Router 라우트
│  │  ├─ dashboard/                  # 이번 달 처리 필요 업무, 알림, 요약 화면
│  │  ├─ workers/                    # 외국인 근로자 목록/상세 화면
│  │  ├─ hiring/                     # 신규 채용 요청, 쿼터 확인 화면
│  │  ├─ visa/                       # 비자 만료, 체류 리스크 관리 화면
│  │  ├─ documents/                  # 서류 체크리스트, 누락 서류 화면
│  │  ├─ contacts/                   # 다국어 메시지 초안/응답 관리 화면
│  │  ├─ approvals/                  # 관리자 승인 대기/승인/거절 화면
│  │  └─ evidence/                   # 감사 로그, 판단 근거 조회 화면
│  │
│  ├─ components/                    # 공통 UI 컴포넌트
│  ├─ features/                      # 도메인별 프론트 기능 모듈
│  │  ├─ dashboard/                  # 대시보드 관련 컴포넌트/로직
│  │  ├─ workers/                    # 근로자 관리 관련 컴포넌트/로직
│  │  ├─ approvals/                  # 승인 처리 관련 컴포넌트/로직
│  │  └─ evidence/                   # Evidence Log 관련 컴포넌트/로직
│  ├─ lib/
│  │  ├─ api.ts                      # 백엔드 API 호출 클라이언트
│  │  └─ constants.ts                # 공통 상수
│  └─ types/                         # 프론트엔드 TypeScript 타입 정의
│
├─ data-pipeline/                    # RAG 데이터 수집/전처리 파이프라인
│  ├─ crawlers/
│  │  ├─ eps_crawler.py              # EPS 고용허가제 자료 수집
│  │  ├─ hrd_crawler.py              # HRD Korea 자료 수집
│  │  ├─ gov24_crawler.py            # 정부24 체류/민원 안내 수집
│  │  └─ law_crawler.py              # 국가법령정보센터 법령/서식 수집
│  │
│  ├─ loaders/                       # PDF, HTML, CSV 등 원천 문서 로더
│  ├─ splitters/                     # 문서 chunk 분할 로직
│  ├─ normalizers/                   # 텍스트 정제, 메타데이터 표준화
│  ├─ metadata/
│  │  └─ multilingual_source_registry.jsonl # 다국어 데이터 수집 소스 레지스트리, MVP 대상 vi/id
│  ├─ seed/
│  │  ├─ companies.csv               # 샘플 사업장 데이터
│  │  ├─ counseling_centers.csv      # 상담센터 안내 seed, MVP 대상 vi/id
│  │  ├─ country_lookup.csv          # MVP 언어/국가 lookup: vi end-to-end, id message-only
│  │  ├─ document_requirements.csv   # 비자/상태별 필요 서류 데이터
│  │  ├─ interview_case_patterns.jsonl # 인터뷰 기반 내부 운영 패턴 placeholder
│  │  ├─ message_templates.jsonl     # 다국어 메시지 템플릿 legacy seed, vi/id 중심
│  │  ├─ message_templates.csv       # target language 기준 메시지 템플릿 seed, vi/id
│  │  ├─ public_case_patterns.jsonl  # 공개 상담 사례 원문이 아닌 패턴 요약
│  │  ├─ sample_policy_docs.jsonl    # 샘플 정책 문서 데이터
│  │  ├─ sample_required_docs.jsonl  # 샘플 필수 서류 데이터
│  │  ├─ synthetic_cases.jsonl       # 데모/평가용 합성 케이스
│  │  ├─ visa_lookup.csv             # 비자 유형 lookup
│  │  ├─ visas.csv                   # 샘플 비자/체류 상태 데이터
│  │  ├─ worker_documents.csv        # 샘플 근로자 서류 상태 데이터
│  │  └─ workers.csv                 # 샘플 근로자 데이터
│  ├─ raw/                           # 원본 문서 저장 위치, 대용량 파일은 Git 제외 권장
│  │  ├─ safety/
│  │  │  ├─ kosha_multilingual/      # 안전보건 다국어 안내 수집 위치
│  │  │  ├─ safety_signs/            # 안전표지 데이터 수집 위치
│  │  │  └─ safety_training/         # 안전교육 안내 수집 위치
│  │  ├─ life_guides/
│  │  │  ├─ counseling_centers/      # 상담센터 안내 데이터 수집 위치
│  │  │  ├─ hiring_guides/           # 사업주·인력확보 Agent용 고용허가제 신청절차, 접수 안내, 제출서류, FAQ, 문의처 등 고용지원 자료 저장 위치
│  │  │  ├─ housing/                 # 생활/숙소 안내 데이터 수집 위치
│  │  │  ├─ medical/                 # 의료 안내 데이터 수집 위치
│  │  │  ├─ banking_telecom/         # 은행/통신 안내 데이터 수집 위치
│  │  │  └─ transportation/          # 교통 안내 데이터 수집 위치
│  │  ├─ templates/
│  │  │  ├─ messages/
│  │  │  │  ├─ vi/                   # 베트남어 메시지 생성, 응답 해석, 상태 업데이트 검증
│  │  │  │  └─ id/                   # 인도네시아어 메시지 생성, 응답 해석, 상태 업데이트 검증
│  │  │  └─ worker_replies/
│  │  │     └─ vi/                   # 베트남어 근로자 응답 해석, 상태 업데이트 후보 검증
│  │  │     └─ id/                   # 인도네시아어 근로자 응답 해석, 상태 업데이트 후보 검증
│  │  ├─ public_cases/               # 공개 상담 사례 패턴 수집 위치
│  │  └─ synthetic_cases/            # 합성 케이스 수집 위치
│  ├─ processed/                     # 전처리된 문서 저장 위치, Git 제외 권장
│  └─ ingest.py                      # 전처리 문서를 Vector DB에 적재하는 실행 스크립트
│
├─ docs/                             # 프로젝트 설계/하네스 문서
│  ├─ README.md                      # docs 폴더 문서 목차
│  ├─ PROJECT_BRIEF.md               # 프로젝트 한 줄 정의, 문제, 목표, 사용자
│  ├─ ARCHITECTURE.md                # 전체 시스템 아키텍처 설명
│  ├─ AI_OS_DESIGN.md                # AI Operating System 설계
│  ├─ GRAPH_STATE.md                 # LangGraph State 계약 문서
│  ├─ TOOL_CONTRACT.md               # Agent Tool 계약, Tool 등급, 응답 형식
│  ├─ RAG_STRATEGY.md                # RAG 문서 수집/검색/인용 전략
│  ├─ SECURITY_GUARDRAILS.md         # 개인정보, 법적 판단, 금지 작업 기준
│  ├─ EVIDENCE_LOG_SCHEMA.md         # Evidence Log DB/이벤트 스키마
│  ├─ OBSERVABILITY.md               # 로그, 메트릭, 추적, 모니터링 설계
│  ├─ EVAL_HARNESS.md                # 평가 하네스, 테스트셋, 통과 기준
│  ├─ API_CONTRACT.md                # 프론트-백엔드 API 계약
│  ├─ DB_SCHEMA.md                   # 주요 DB 테이블 설계
│  ├─ DECISIONS.md                   # 기술/제품 의사결정 기록
│  └─ HANDOFF.md                     # 팀원/AI 에이전트에게 넘길 작업 인수인계 문서
│
├─ missions/                         # AI/팀원에게 줄 작업 단위
│  ├─ README.md                      # mission 작성 규칙, active/completed 사용법
│  ├─ active/                        # 현재 진행할 작업 지시서
│  │  ├─ 001-agent-runtime-skeleton.md# Agent Runtime 뼈대 구현 미션
│  │  ├─ 002-rag-indexing.md         # RAG 인덱싱 파이프라인 구현 미션
│  │  ├─ 003-approval-evidence-log.md# 승인/Evidence Log 구현 미션
│  │  ├─ 004-backend-core-api.md     # FastAPI 핵심 API 구현 미션
│  │  └─ 005-frontend-dashboard.md   # 프론트 대시보드 구현 미션
│  └─ completed/                     # 완료된 mission 보관
│
├─ evals/                            # 하네스 평가 데이터
│  ├─ datasets/
│  │  ├─ intent_router_cases.jsonl   # 의도 분류 평가 데이터
│  │  ├─ rag_retrieval_cases.jsonl   # RAG 검색 정확도 평가 데이터
│  │  ├─ safety_guardrail_cases.jsonl# 금지/승인 필요 작업 평가 데이터
│  │  └─ workflow_e2e_cases.jsonl    # 전체 워크플로우 E2E 평가 데이터
│  ├─ expected/                      # 기대 출력값 저장
│  ├─ reports/                       # 평가 실행 결과 리포트 저장
│  └─ README.md                      # eval 실행 방법과 평가 기준 설명
│
├─ .claude/                          # Claude 팀원용 작업 지침
│  ├─ CLAUDE.md                      # Claude Code 상세 작업 규칙
│  ├─ commands/
│  │  ├─ plan-feature.md             # Claude에게 기능 계획을 시킬 때 쓰는 명령 템플릿
│  │  ├─ implement-feature.md        # Claude에게 기능 구현을 시킬 때 쓰는 명령 템플릿
│  │  ├─ verify-feature.md           # Claude에게 검증을 시킬 때 쓰는 명령 템플릿
│  │  └─ review-pr.md                # Claude에게 PR 리뷰를 시킬 때 쓰는 명령 템플릿
│  └─ prompts/
│     ├─ backend-agent.md            # 백엔드/FastAPI 작업용 Claude 프롬프트
│     ├─ frontend-agent.md           # 프론트 작업용 Claude 프롬프트
│     ├─ agent-runtime-agent.md      # LangGraph Agent Runtime 작업용 Claude 프롬프트
│     ├─ rag-agent.md                # RAG 작업용 Claude 프롬프트
│     ├─ qa-agent.md                 # 테스트/검증 작업용 Claude 프롬프트
│     └─ reviewer-agent.md           # 리뷰어 역할 Claude 프롬프트
│
├─ scripts/
│  ├─ verify_all.sh                  # 전체 검증 스크립트
│  ├─ run_backend_tests.sh           # FastAPI 백엔드 전체 테스트 실행
│  ├─ run_agent_tests.sh             # backend/app/agent_runtime 전용 테스트 실행
│  ├─ run_frontend_tests.sh          # 프론트 lint/build/test 실행
│  ├─ run_evals.py                   # evals 데이터셋 기반 평가 실행
│  └─ ingest_rag_docs.py             # RAG 문서 적재 실행 스크립트
│
├─ infra/
│  ├─ nginx/                         # Nginx reverse proxy 설정
│  ├─ postgres/                      # PostgreSQL 초기화/운영 설정
│  ├─ chroma/                        # Chroma Vector DB 설정
│  └─ monitoring/                    # Prometheus, Grafana 등 모니터링 설정
│
└─ .github/
   ├─ pull_request_template.md       # PR 작성 시 체크리스트 템플릿
   └─ workflows/
      ├─ backend-ci.yml              # FastAPI 백엔드 + Agent Runtime CI
      ├─ frontend-ci.yml             # 프론트엔드 CI
      └─ harness-ci.yml              # evals, docs, scripts 검증 CI
