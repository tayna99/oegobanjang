# 외고반장

외고반장은 외국인 고용 사업장의 체류, 고용, 서류, 다국어 소통, 비자 갱신 업무를 하나의 흐름으로 관리하는 **외국인 고용 운영 OS**입니다.

이 프로젝트는 비자 신청을 대행하거나 법률 판단을 자동화하는 서비스가 아닙니다.  
공식 규정, 직원 상태, 누락 정보, 메시지 초안, 행정사 전달 패키지를 정리해 담당자와 전문가가 안전하게 판단할 수 있도록 돕는 것이 목표입니다.

---

## 프로젝트 한 줄 정의

E-9 외국인 근로자를 고용하는 제조업 중소기업이 비자 만료, 서류 누락, 고용변동 신고, 다국어 소통 리스크를 놓치지 않도록 돕는 AI 기반 운영 관리 시스템입니다.

---

## 현재 리포 구성

현행 운영 대상은 루트의 **모바일 우선 Vite + React MVP**입니다. 이전 FastAPI 백엔드 단계의 산출물은 전부 `legacy/`로 이관되었습니다(아래 "레거시 백엔드" 절 참조).

```txt
src/            제품 UI — 화면(features), 공용 컴포넌트, 스토어(zustand), mock 데이터, 런 엔진
docs/           현행 MVP 문서 — ARCHITECTURE(코드 지도), SPEC_INDEX(스펙↔구현 매핑), GOTCHAS(주의사항)
plans/          ROADMAP(마일스톤·태스크·DoD), HANDOFF(세션 인수인계 기록)
rules/          design(디자인 시스템 v2 규칙), frontend(프론트 컨벤션), safety(안전 체크리스트)
reference/      스펙 원본 사본, 디자인 시스템 고정 사본, 프로토타입 v3
legacy/         이전 FastAPI 백엔드·데이터 파이프라인·Agent Runtime·evals·missions·설계 문서 보관
외고반장_통합/   기획 원자료 아카이브
현욱/           팀원 작업 노트 아카이브
.claude/        Claude Code 서브에이전트(ui-matcher·verifier)와 설정
```

작업 규칙의 정본은 `AGENTS.md`입니다.

---

## 실행 방법

Node.js 20 이상이 필요합니다. 현행 MVP는 브라우저 mock 데이터로 동작하므로 환경변수, DB, Docker 없이 실행됩니다.

```bash
npm install
npm run dev
```

### 검증

```bash
npm run verify
```

`verify`는 typecheck → lint → 테스트(vitest) → 프로덕션 빌드를 순서대로 실행합니다.  
개별 실행: `npm run typecheck`, `npm run lint`, `npm run test`(watch) / `npm run test:run`, `npm run build`

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

## 현재 MVP 범위와 흐름

```txt
알림 → 오늘 브리핑(M1) → 케이스 시트(M2) → 초안(M3) → 승인(M4) → 완료(M5)
```

이 루프가 제품의 본체입니다. 에이전트 런(M9)과 프로액티브 런이 준비물(초안·근거·패키지)을 만들고, 사람은 승인만 합니다. 모든 판단은 판단 기록(M8, Evidence)에 남습니다.

- 현재 런은 **각본 기반**(mock fixtures 재생)입니다. 실제 LLM·백엔드 연결은 이후 단계에서 RunConfig 인터페이스를 유지한 채 교체합니다(`plans/ROADMAP.md`의 "백엔드 접속점" 절).
- 발송 도구는 존재하지 않습니다. 발송·제출·전달 성격의 작업은 초안 생성까지만 가능하고, 실행은 담당자 승인 이후에만 가능합니다.

화면↔라우트↔스펙 매핑과 데이터 흐름은 `docs/ARCHITECTURE.md`, 마일스톤별 태스크와 DoD는 `plans/ROADMAP.md`를 참조합니다.

---

## 레거시 백엔드 — `legacy/` 이관됨

이전 단계의 FastAPI 백엔드(일반 API + LangGraph/RAG/Agent Runtime + Evidence Log), 데이터 파이프라인, eval 하네스, mission 문서, 설계 문서(PROJECT_BRIEF, AI_OS_DESIGN, RAG_STRATEGY, TOOL_CONTRACT, SECURITY_GUARDRAILS, EVAL_HARNESS 등)는 전부 `legacy/`에 보관되어 있습니다.

- 구조·실행 방법 상세: `legacy/FOLDER_STRUCTURE.md`와 `legacy/docs/`
- `legacy/`는 새 프론트 MVP의 production import 대상이 아니며, 복구/이관 mission이 명시된 경우에만 수정합니다(`AGENTS.md` §3 참조).
