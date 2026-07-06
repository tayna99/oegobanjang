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

### [2026-07-06] 1.1 — 완료
- 한 일: ROADMAP 1.1(라우터+딥링크 맵+Shell) 전체 9태스크 완료. `src/lib/routes.ts`(`ROUTES`/`ROUTE_PATHS` 딥링크 경로 단일 출처), `src/lib/cn.ts`(legacy `features/pc/ui.tsx`에서 이식), `src/components/icons.tsx`(탭 아이콘 4종, `prototype_v3.html`에서 이식), `src/screens/PlaceholderScreen.tsx`(미구현 라우트 공용 자리표시자), `src/lib/deeplink.ts`(`validateIdParam` — zod 기반 loader 팩토리, `zod` 신규 의존성 4.4.3), `src/lib/nav.ts`(`useNav()` — 명명된 내비게이션 메서드 12개, 전부 `ROUTES.*` 위임), `src/Shell.tsx`(레이아웃 라우트 — <1024px 모바일 탭바/이상 PC 헤더 분기 + `useDeepLinkBackstack()` 훅, 콜드 스타트 시 히스토리를 [M1, 목적지]로 재작성), `src/router.tsx`(자식 라우트 12개로 전체 라우트 트리 완성, 그중 6개는 `validateIdParam` 기반 loader 보유). M0.1 자리표시자였던 `src/App.tsx`/`src/App.test.tsx`는 삭제(Shell로 완전 대체). 두 DoD(라우트 스냅샷 테스트, 딥링크 백스택=M1→목적지)를 `src/router.test.tsx`의 실제(비모킹) 라우터 테스트로 검증.
- 남은 일 / 중단 지점: 없음. 1.2/1.3/1.4/2.1이 의존하는 라우팅·딥링크·Shell·nav 인프라는 모두 준비 완료.
- 결정 사항:
  - `/case/:caseId`(bare, M2 케이스 바텀시트)와 `/onboarding/workers`(O1 근로자 등록)를 라우트 트리에 추가 — `ARCHITECTURE.md` 원래 라우트 표에는 없었지만 2단계 딥링크맵 스펙(N03 등은 `case/{id}`로, N21은 `onboarding/workers`로 직결)이 요구해 반영. 같은 세션에서 ARCHITECTURE.md §3 표도 갱신.
  - 계획 외 보정: 태스크 도중 `router.navigate(-1)`이 당시 vitest 3.2.6에서 throw(vitest-dev/vitest#8374 — Node 24 아래 jsdom AbortSignal 브랜드 체크 버그)하는 것을 발견. 사용자 확인 후 근본 해결을 택해 `vitest` `^3.0.0` → `^4.1.10` 업그레이드. 테스트 완화 없이 버그 자체를 제거, 이후 전체 스위트 통과.
  - 알려진 사소한 갭(차단 아님, 향후 세션 참고용): (1) `Shell.tsx`의 탭바 치수(`h-[62px]`/`text-[11px]`/`pb-[62px]`)는 탭별기획 §0.2가 지정한 정확한 값이지만 아직 `tokens.css`/`tailwind.config.js`에 이름 있는 토큰으로 등록되지 않음 — 향후 디자인 토큰 패스에서 정리 가능. (2) 라우트 스냅샷 테스트는 `path`/`hasLoader`/`children` 형태만 검사해 loader가 엉뚱한 라우트에 붙는 경우(예: `case` 라우트에 `runId` validator)는 단독으로 못 잡음 — 딥링크 백스택 테스트 2개가 부분적으로만 보완. (3) 스코프 의도적 제외(완료 아님, 착오 방지용 명시): M2 오버레이 실제 렌더링(1.4), TabBar 미확인 배지(스토어 연결 후), `filter` 쿼리 파라미터 값 검증(2.1), 딥링크 검증 실패 시 토스트 문구(Toast 컴포넌트 자체가 아직 없음 — 담당 태스크 불명확한 스펙 갭).
  - 최종 whole-branch 리뷰 반영: (1)은 이 패스에서 이미 토큰화 완료(`--tabbar-h`/`--tabbar-label-fs` + `spacing.tabbar`/`fontSize.tabbar-label`)로 해소됨. 추가로, `useDeepLinkBackstack`의 콜드 스타트 `navigate(target)` 호출(`/case/:caseId` 등)이 현재 location `state`를 싣지 않는다는 점이 발견됨 — 1.4가 M2 바텀시트를 "background location" 오버레이 패턴(시트 라우트에 배경 위치를 state로 주입)으로 구현할 때 이 훅과 조율이 필요하니 1.4 착수 시 다시 조사하지 않도록 여기 남긴다.
- verify 상태: PASS (typecheck 0, lint 0, test 12 files/57 passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` 진입점 표(라우팅·딥링크→`src/router.tsx`, 화면 셸→`src/Shell.tsx`)와 §3 라우트 표(`/case/:caseId` bare, `/onboarding/workers` 추가) 갱신.

---

### [2026-07-06] 0.5 — 완료
- 한 일: `reference/prototype_v3.html`·`reference/specs/*`(12_모바일퍼스트_재설계 사본, 기존 세션에서 이미 복사되어 diff 확인만 함)을 출처로 `src/mocks/` 4파일 이식. `fixtures.ts` — v3 CASE 레지스트리 5건(nguyen/bayar/mohammad/tranCase/hiring)을 `CaseCard[]`(§0.4)로, M2 시트용 데이터(kv·docs·citations·activity·nextWake)를 로컬 `CaseSheet` 타입으로 정규화. severity/그룹은 v3 `caseRows()`의 sev 필드(warn/crit/info/neut)로 근거를 삼아 매핑. `drafts.ts` — DRAFT 3건(nguyen/mohammad/tranReminder), KR+VN(nguyen,tranReminder)/KR+EN(mohammad) — SPEC_INDEX가 요구한 EN 포함. `runs.ts` — APPROVE 6건(nguyen/candidate/bayarPkg/mohammad/hiring/tranReminder)을 `RunConfig`/`RunStep`으로. `evidence.ts` — 초기 EV 시드 5건만(런타임 addEv 이후 항목은 향후 evidenceStore.append 몫). `src/types.ts`의 `EvidenceEvent`에 표시용 옵션 필드 3개(`summary`/`actor`/`evidenceRef`) 추가(M8 EventTimelineItem 이식, 기존 필드는 불변이라 M0.4 테스트 영향 없음).
- 남은 일 / 중단 지점: 없음. PKG(candidate/hiring 패키지 본문)·command/replay 런(#4790/#4796 draft/#4788 replay)·M7 목록 그룹핑(g 필드)은 의도적으로 제외 — 각각 M2.4·M1.5(L3)·2.1 태스크 몫. bayar는 v3 시트에 CTA가 1개뿐이라 secondaryAction('상세 보기')을 새로 만들어 채움 — M1.4에서 실제 UI 확정 시 재검토. 다음은 ROADMAP 1.1 (라우터+딥링크 맵, Shell). L2라 계획 승인 대상.
- 결정 사항:
  - Case.state 매핑(추론, v3에 명시 없음): nguyen·mohammad=approval_pending / bayar=blocked(GOTCHAS "high risk→blocked") / tranCase=risk_review / hiring=draft.
  - RunStep에 공식 5종(thinking/tool_call/guardrail/handoff/replan, GLOSSARY) 밖의 'wait'를 로컬 확장으로 추가 — v3의 "승인 대기" 스텝을 표현하려는 것으로, M9 RunStep으로 승격 시 스펙에 먼저 반영 필요.
  - CaseDocStatus는 M2 스펙의 4값(missing/requested/received/company_check) 밖에 'expiring'·'pending' 2개를 fixtures.ts 로컬 타입에 추가 — v3 라벨(만료 예정/대기)을 손실 없이 옮기기 위함.
  - EvidenceEvent 확장 필드는 모두 optional이라 evidenceStore/guardrails.test.ts 기존 계약 불변. cat(위험감지/초안생성/승인/전달) 필터 그룹은 저장하지 않고 추후 selector로 파생 예정(2.3).
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed — 신규 mocks는 순수 데이터라 별도 테스트 없음, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md`의 mock 데이터 진입점 행을 4파일 구조로 갱신.

---

### [2026-07-06] 0.4 — 완료
- 한 일: zustand 스토어 3종 — `src/stores/caseStore.ts`(GOTCHAS §2 상태머신 `transition` 검증), `approvalStore.ts`(`requestApproval`/`decide`/`dispatch`, idempotencyKey 중복 차단, 승인 없이 dispatch throw), `evidenceStore.ts`(append-only, 이벤트 Object.freeze). `src/lib/guardrail.ts`에 `GuardrailError`. `src/types.ts`에 `Approval`·`EvidenceEvent`(+ EvidenceType) 추가. 가드레일 테스트 `src/stores/guardrails.test.ts` 12개.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.5 (mocks 이식 — v3 CASE/DRAFT/APPROVE/EV → fixtures, 스펙: docs/SPEC_INDEX.md 이식표, DoD: typecheck 통과 + PII 원문 없음). L1.
- 결정 사항:
  - 3개 가드레일 테스트: (1) 승인 없이 dispatch 불가 (2) evidence append-only(수정·삭제 액션 부재 + 동결) (3) 중복 승인 차단(같은 key no-op) — 전부 통과. Case 상태 전이 보강 3개 추가.
  - 직접 발송 함수 미구현. dispatch는 approved에서만 mock 경계까지(`{dispatched:true}`), 실제 발송 없음.
  - EvidenceEvent에 원문/PII 필드 없음 — hash만 허용.
  - 스토어 경로 = `src/stores/`. 아직 App에 미연결(M1.x에서 연결) — 빌드 번들에는 미포함.
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.3 — 완료
- 한 일: `src/types.ts`에 §0.4 공용 타입 이식(Severity/CaseState/Role/ApprovalStatus/NextActionRef/WorkerRef/CaseCard/Citation). `src/lib/dday.ts`에 `calcDday(target, base)`(UTC 자정 정규화, 'YYYY-MM-DD'·'YYYY.MM.DD'·Date 입력) + `dDayLabel` + `dDayTone`(배지 색 규칙). `src/lib/mask.ts`에 `maskId`(영숫자→*, 구분자 유지). 단위 테스트 2파일(22 tests).
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.4 (스토어 3종 case/approval/evidence + 가드레일 테스트, 스펙: docs/GOTCHAS §1·2 — 아직 `docs/GOTCHAS.md`가 이 루트에 있는지 확인 필요, 없으면 `외고반장_통합/13_클로드코드_구현패키지/docs/GOTCHAS.md` 참조). L2라 계획 승인 대상.
- 결정 사항:
  - dDay 부호 규칙: 양수=남은 일수(D-N), 0=D-day, 음수=경과(D+N). tone은 토큰 색 이름(critical/warning/info/neutral)으로 반환 — 배지가 tokens와 1:1.
  - `calcDday`는 UTC 자정 기준으로 계산해 로컬 타임존·DST와 무관하게 결정적. 테스트는 기준일 주입.
  - `maskId`는 원문 digit 미보존(전체 마스킹) — safety.md "원문 금지" + 3단계 "화면에는 ***-*******만" 준수.
- verify 상태: PASS (typecheck 0, lint 0, test 22 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.2 — 완료
- 한 일: `src/styles/tokens.css`에 prototype_v3 `:root` 토큰 그대로 이식(reduced-motion 오버라이드 포함). `tailwind.config.js` theme를 토큰 `var()`에 연동(colors/radius/shadow/duration/timing + fontFamily). `src/index.css`에서 tokens + Pretendard(가변폰트 dynamic-subset) import, base layer에 `bg-canvas/text-ink/font-sans` 적용. 토큰 스냅샷 테스트 1개(`src/styles/tokens.test.ts`) — 기준 `:root` 블록만 파싱, 빈 맵 가드 포함.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.3 (`src/types.ts` + `calcDday`·`maskId` 유틸 + 단위 테스트, 스펙: reference/specs 1단계 §0.4).
- 결정 사항:
  - Pretendard는 정적 dynamic-subset(9웨이트 전부 → CSS 526kB) 대신 **가변폰트 dynamic-subset** 사용 → CSS 53.8kB. family `Pretendard Variable` 우선, `Pretendard` 폴백.
  - 토큰 단일 출처 = tokens.css. tailwind은 var() 참조만. duration도 var()라 reduced-motion 캐스케이드 유지.
  - 스냅샷 테스트는 처음에 `?raw` 임포트가 vitest에서 빈 문자열 → 거짓 통과(`{}`) 발생 → cwd 상대경로 fs 읽기 + 개수 가드로 교정.
- verify 상태: PASS (typecheck 0, lint 0, test 2 passed, build OK, CSS 53.8kB).
- 지도/규칙 갱신: 없음.

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
