# HANDOFF — 세션 인수인계 기록

> 규칙: 태스크를 끝내거나 컨텍스트 40%에 도달해 세션을 넘길 때, 에이전트가 아래 형식으로 **맨 위에** 추가한다.
> 새 세션의 첫 행동: 이 파일의 최신 항목 1개 + ROADMAP의 다음 태스크를 읽는 것. (전체 히스토리 로드 금지)

---

## 형식

```
### [날짜] 태스크 번호 — 상태 (완료/중단)
- 한 일:
- 남은 일 / 중단 지점:
- 결정 사항 (다음 세션이 알아야 할 것):
- verify 상태: PASS/FAIL(원인)
- 지도/규칙 갱신: (했으면 무엇을)
```

---

### [2026-07-06] 0.1 — 완료
- 한 일: 루트에 Vite6+React19+TS5.7+Tailwind3.4+react-router-dom7+zustand5 스캐폴드. `npm run verify`(typecheck→lint→test:run→build) 구성. 빈 셸(`src/App.tsx` = `외고반장` h1) + 라우터(`src/router.tsx`) + 렌더 테스트 1개(`src/App.test.tsx`). ESLint flat config는 앱 트리(root `src`)만 대상 — legacy/외고반장_통합 등 비앱 트리는 ignore.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.2 (tokens.css + tailwind theme, v3 `:root` 이식).
- 결정 사항:
  - 프로젝트 레퍼런스(tsconfig.node.json) 제거 → 단일 tsconfig(`src` + `vite.config.ts`), `@types/node` 추가. `tsc -b` composite 충돌 회피.
  - vitest는 v3 사용(v2.1은 vite6와 nested-vite 타입 충돌). `defineConfig`는 `vitest/config`에서 import.
  - 스토어/토큰/mocks는 범위 밖이라 미포함(0.2·0.4·0.5).
- verify 상태: PASS (typecheck 0, lint 0, test 1 passed, build OK). dev 서버 부팅 확인(localhost:5173).
- 지도/규칙 갱신: 없음.

---

(아직 기록 없음 — M0.1부터 시작)
