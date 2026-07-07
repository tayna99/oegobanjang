# 외고반장 (Oegobanjang) — 프로젝트 규칙

E-9 외국인 고용 운영 Agentic OS의 **모바일 퍼스트 프론트엔드 MVP**.
핵심 철학: **자동 제출이 아니라 자동 준비.** AI는 준비하고, 사람이 승인하고, 모든 판단은 기록된다.

## 스택

- Vite + React 18 + TypeScript + Tailwind CSS + react-router-dom
- 테스트: Vitest + @testing-library/react / E2E: Playwright
- 상태: Zustand (전역 최소화 — 케이스/승인/기록 스토어만)
- 백엔드 없음(MVP): `src/mocks/`의 fixture + 인메모리 스토어. API 계약은 스펙의 데이터 타입을 따른다

## 명령어

```bash
npm run dev          # 개발 서버
npm run test         # vitest (단위)
npm run test:e2e     # playwright (승인 플로우 스모크)
npm run lint         # eslint + prettier check
npm run typecheck    # tsc --noEmit
npm run verify       # lint + typecheck + test (커밋 전 필수)
```

## 폴더 구조 (지도는 docs/ARCHITECTURE.md)

```
src/
├── app/            라우터, 쉘(모바일 탭바/PC 헤더), 프로바이더
├── components/     공용 UI (Button, Badge, Card, BottomSheet, StepTimeline…)
├── features/
│   ├── briefing/   M1 오늘 브리핑
│   ├── cases/      M2 시트, M7 목록
│   ├── drafts/     M3 초안, 수정 요청
│   ├── runs/       M4/M9 에이전트 런, 프로액티브 재생
│   ├── approvals/  승인 게이트, M5 완료
│   ├── messages/   스레드, M6 응답 해석
│   ├── evidence/   M8 판단 기록
│   └── packages/   행정사 패키지
├── stores/         zustand 스토어 (case, approval, evidence)
├── mocks/          fixture (Nguyen/Tran/Bayar… — 프로토타입 v3 데이터 이식)
└── styles/         tokens.css (디자인 토큰 CSS 변수)
```

## 절대 규칙 (위반 = 리뷰 반려)

1. **승인 게이트**: 외부 발송성 액션은 `approval.status === 'approved'` 없이 실행 경로가 존재하면 안 된다. "발송" 함수는 만들지 않는다 — `requestApproval()`이 종착점.
2. **PII**: 외국인등록번호·여권번호 원문을 상태·로그·fixture에 저장/표시 금지. 마스킹 유틸(`maskId()`)만 사용.
3. **Evidence**: 상태를 바꾸는 모든 액션은 `evidenceStore.append()` 호출. 기록은 append-only — 수정/삭제 API 금지.
4. **표현**: UI 문구에 단정 표현("가능합니다", "완료되었습니다"의 오용), 이모지, 느낌표 금지. 문구는 스펙의 마이크로카피를 그대로 사용.
5. **디자인 토큰만 사용**: 색·radius·간격 하드코딩 금지. `styles/tokens.css` 변수 사용. 상세: `rules/design.md`
6. 나머지 도메인 함정: **`docs/GOTCHAS.md` 필독** (케이스 상태 전이, 가드레일 목록)

## 작업 방식

- 태스크는 `plans/ROADMAP.md`에서 가져온다. 태스크에 명시된 스펙 파일(`reference/specs/…`)을 **먼저 읽고** 구현한다.
- UI의 시각 기준은 `reference/prototype_v3.html` — 마크업·토큰·모션 값을 이식하되 React 컴포넌트로 재구성한다.
- 완료 선언 전 `npm run verify` 통과 + 태스크 DoD 확인. 실패 상태로 "완료" 보고 금지.
- 같은 실수를 반복하게 만든 원인은 `rules/`에 규칙으로 추가하고 같은 커밋에 포함한다.
- 코드 변경으로 `docs/ARCHITECTURE.md`가 낡으면 같은 PR에서 갱신한다.

## 상세 규칙 (필요할 때만 읽기 — Progressive Disclosure)

- 프론트 컨벤션: `rules/frontend.md`
- 디자인 토큰·UI: `rules/design.md`
- 도메인 안전 체크리스트: `rules/safety.md`
- 용어집(네이밍 사전): `docs/GLOSSARY.md`
- 스펙 문서 찾기: `docs/SPEC_INDEX.md`
