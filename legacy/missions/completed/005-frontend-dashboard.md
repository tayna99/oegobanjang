# Mission 005: Frontend Dashboard

## Goal

외고반장 MVP의 관리자 대시보드 화면 뼈대를 만든다.

대시보드는 담당자가 이번 달 처리해야 할 외국인 고용 업무, 비자 만료, 서류 누락, 승인 대기, Evidence Log를 한눈에 확인할 수 있어야 한다.

---

## Required Reading

```txt
README.md
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
```

---

## Target Files

```txt
frontend/app/dashboard/
frontend/app/workers/
frontend/app/hiring/
frontend/app/visa/
frontend/app/documents/
frontend/app/contacts/
frontend/app/approvals/
frontend/app/evidence/

frontend/components/
frontend/features/dashboard/
frontend/features/workers/
frontend/features/approvals/
frontend/features/evidence/

frontend/lib/api.ts
frontend/lib/constants.ts
frontend/types/
```

---

## Scope

이번 mission에서 구현할 범위는 다음과 같다.

- 기본 레이아웃
- 대시보드 카드
- 이번 달 처리 필요 업무 목록
- 비자 만료 D-day 표시
- 서류 누락 표시
- 승인 대기 목록
- Evidence Log 조회 화면 skeleton
- API client 기본 구조
- mock 데이터 기반 화면 구성

---

## Dashboard Sections

대시보드는 최소 아래 영역을 포함한다.

```txt
1. 이번 달 처리 필요 업무
2. 비자 만료 임박 근로자
3. 서류 누락 케이스
4. 신규 채용 요청
5. 승인 대기 작업
6. Evidence Log 최근 이력
```

---

## UX Rules

- 승인 필요한 작업은 명확히 표시한다.
- 실제 발송/전송 버튼은 바로 실행하지 않는다.
- 위험 작업은 확인 모달 또는 승인 화면으로 이동한다.
- Evidence Log와 근거 문서가 숨겨지지 않도록 한다.
- 민감정보는 마스킹해서 표시한다.

---

## Out of Scope

이번 mission에서 구현하지 않는다.

- 완전한 디자인 시스템
- 실제 인증 연결
- 실제 메시지 발송
- 실제 행정사 전송
- 복잡한 차트
- 모바일 최적화 완성
- 모든 API 실연동

---

## Acceptance Criteria

- dashboard route가 존재한다.
- workers/hiring/visa/documents/contacts/approvals/evidence route가 존재한다.
- 대시보드에서 mock 업무 목록을 볼 수 있다.
- 승인 대기 항목이 표시된다.
- Evidence Log 영역이 표시된다.
- 민감정보는 원문 그대로 표시하지 않는다.
- frontend lint/build가 통과한다.

---

## Verification Commands

```bash
npm run typecheck
npm run build
npm run test
```

---

## Human Review Checklist

- [x] 대시보드에서 주요 업무가 보이는가?
- [x] 승인 필요한 작업이 명확히 구분되는가?
- [x] 민감정보가 마스킹되는가?
- [x] Evidence Log 접근 경로가 있는가?
- [x] 실제 외부 발송/전송이 발생하지 않는가?

---

## 2026-05-10 Status

상태: completed

구현한 것:

- `frontend/package.json`, `tsconfig.json`, `next.config.mjs`, `app/layout.tsx`, `app/page.tsx`를 추가해 Next App Router 프로젝트로 검증 가능하게 만들었다.
- `dashboard`, `workers`, `hiring`, `visa`, `documents`, `contacts`, `approvals`, `evidence` route에 실제 `page.tsx`를 추가했다.
- `frontend/features/dashboard/mockData.ts`에 이번 달 업무, 비자 만료, 서류 누락, 신규 채용, 승인 대기, Evidence Log mock 데이터를 추가했다.
- `frontend/lib/masking.ts`로 여권번호, 외국인등록번호, 전화번호 마스킹을 추가하고 mock Evidence/서류 표시에서 원문 노출을 막았다.
- 외부 발송, 행정사 전달, 정부 제출은 화면에서 직접 실행하지 않고 승인 필요/차단 상태로만 표시했다.

검증:

- `npm run typecheck` 통과
- `npm run build` 통과
- `npm run test` 통과
