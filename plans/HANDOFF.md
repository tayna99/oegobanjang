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

### [2026-07-06] 1.4 — 완료
- 한 일: `/case/:caseId`가 실제 M2 케이스 시트를 렌더. `src/components/BottomSheet.tsx`(공용 모달 프리미티브 — scrim/slide-up/dismissible/footer, 도메인 타입 모름). `src/features/case/CaseSheet.tsx`(1단계 §M2 5블록 고정: 요약/AI확인내용/서류체크리스트/근거/에이전트활동 + ActionBar 2개 — citation 0건이면 근거 경고 + **승인이 필요한 액션만** locked, 5개 케이스 전부 이 컴포넌트 하나로 커버·분기 없음). `src/features/case/CaseSheetPage.tsx`(`<BriefingHomePage/>`를 배경으로, `<CaseSheet/>`를 오버레이로 구성 — 2단계 딥링크맵의 "M1 위에 오버레이" 요구를 진짜 background-location 대신 M1 렌더러 재사용으로 근사). 어드버서리얼 리뷰에서 Important 1건(`activity`가 비어 있으면(mohammad/hiring) `nextWake`까지 통째로 안 뜨던 버그) 발견 후 수정.
- 남은 일 / 중단 지점: 없음. 진짜 background-location(M7 생기면 재검토), half↔full 드래그 제스처, M9 재생 뷰 연결, tranCase 확인완료 후 UI 반영은 계획 문서에 범위 밖으로 명시. Minor로 남긴 것(고치지 않음, 문제 아님): `BriefingHomePage`와 `CaseSheetPage`가 caseStore 시딩 `useEffect`를 각자 갖고 있어 중복이지만 React 마운트 순서상 안전(자식이 먼저 시드하고 부모는 가드에 걸려 스킵) — 다음에 손댈 사람은 공유 훅으로 뽑을지 고려. 존재하지 않는 caseId로 이동하면 안내 없이 조용히 M1만 보임(M7·실제 딥링크 검증 붙을 때 재검토). 다음은 ROADMAP 1.5(런 엔진, **L3** 협업 태스크 — v3의 renderRun() 각본 재생 로직 이식) 또는 2.1(M7 케이스 목록) — ROADMAP 순서상 1.5가 다음이지만 L3라 더 무거운 협의가 필요.
- 결정 사항:
  - citation 등급(A/B/C/E) 배지는 기존 `Badge` 컴포넌트를 재사용하지 않고 새 인라인 span으로 렌더 — 프로토타입 v3 `.cite .g`(18×18 정사각형)가 `Badge`의 알약형과 시각이 달라 억지로 끼워맞추지 않음(`size-[18px]`는 1.3의 `size-[22px]`와 같은 성격의 알려진 국지적 예외).
  - citation-잠금은 `card.primaryAction.requiresApproval`이 true인 액션에만 걸린다 — tranCase처럼 승인이 필요 없는 primaryAction(kind:'confirm')은 citation 0건이어도 잠기지 않는다(GOTCHAS §2가 말하는 건 "승인 게이트"지 "모든 액션 차단"이 아님).
- verify 상태: PASS (typecheck 0, lint 0, test 30 files/162 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/case/` 사례 추가.

---

### [2026-07-06] 1.3 — 완료
- 한 일: M1 오늘 브리핑 홈을 5상태 전부 구현하고 `/` 라우트에 연결(더 이상 PlaceholderScreen 아님). `src/types.ts`에 `NextActionKind`(approve/draft/detail/thread/package/confirm) 추가 + `src/mocks/fixtures.ts` CASE_CARDS 10개 액션에 kind 채움. `src/lib/actionNav.ts`(`useNextAction()` — kind→이동/인라인 액션, confirm은 risk_review→completed가 CASE_TRANSITIONS에 없어 이동 없이 evidence만 남김). `src/lib/briefing.ts`(`greetingText`/`sortCards`/`visibleCardsForRole`/`recommendReason` 순수 함수). `src/components/icons.tsx`에 IconSpark/IconWait 추가. `src/features/briefing/`: `BriefingHeader`/`SummaryStatRow`/`CommandBar`(작은 프레젠테이션), `ApprovalCard`(hero/compact, 배지 순서 고정, CTA 2개), `BriefingScreen`(5상태 전부 담은 순수 프레젠테이션 — 이번 마일스톤 DoD), `BriefingHomePage`(caseStore 시딩 + role/greeting 계산하는 컨테이너). 어드버서리얼 리뷰에서 Important 3건 발견 후 수정: (1) compact 카드도 primary(파랑) CTA를 렌더해 "화면당 파랑 1개" 위반 — compact는 secondary variant로 교정 (2) hero 추천 이유가 dead ternary로 항상 undefined — `recommendReason()` 헬퍼로 실연결 (3) `greetingText`가 테스트만 되고 실제 화면은 호칭 없이 인사문을 재구현 — `BriefingViewState`에 `greeting` 필드 추가해 실연결.
- 남은 일 / 중단 지점: 없음. 컨테이너/프레젠테이션 분리 패턴(`<Name>Screen` + `<Name>Page`)이 확립됐으니 M2~M9도 따르길 권장. role(manager 고정, 4.2 몫)·근로자수(5 고정, 3단계 몫)·실제 fetch/오프라인 감지(백엔드 접속점 이후)·Toast(스펙 갭)·CommandBar→M9 연결(1.5)·프로액티브 행→런 재생 뷰(1.5)는 계획 문서에 범위 밖으로 명시. 다음은 ROADMAP 1.4(BottomSheet + M2 케이스 시트) — L2.
- 결정 사항:
  - 실행 중 세션 사용량 한도로 워크플로우가 한 번 중단됐다(9:50pm 리셋) — task3(briefing.ts)는 이미 완성돼 있었지만 커밋 전에 끊겨 수동으로 확인 후 커밋, 나머지(4/6/7/8)는 순차 Agent 디스패치로 이어서 진행. 최종 결과물이나 커밋 이력에는 영향 없음.
  - `ApprovalCard`의 오프라인 처리는 계획 원안(카드 전체 fieldset 잠금)에서 `offlineDisabled` prop 방식으로 구현 중 조정됨 — `requiresApproval:true`인 CTA만 잠그고 읽기 액션(예: 초안 보기)은 오프라인에서도 유지(GOTCHAS §3 "초안 보기 등 읽기 액션은 캐시 범위 내 허용"과 정확히 부합, 원안보다 개선).
  - `router.test.tsx`의 잘못된 caseId 리다이렉트 테스트가 기대하는 텍스트를 `/M1 오늘 브리핑/`(옛 PlaceholderScreen 문구)에서 `/화성 1공장/`(BriefingHomePage 헤더 회사명)로 갱신 — index route 교체의 자연스러운 결과.
- verify 상태: PASS (typecheck 0, lint 0, test 27 files/148 tests passed, build OK). `router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 flake하는 기존 이슈(1.1부터)는 이번 세션에서는 재현되지 않았다.
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/briefing/`을 컨테이너/프레젠테이션 분리 패턴의 실제 사례로 추가.

---

### [2026-07-06] 1.2 — 완료
- 한 일: 공용 컴포넌트 6종 + 배지 색 규칙 매핑 모듈. `src/components/Badge.tsx`(tone 7종: critical/warning/pending/info/success/neutral/line, 프로토타입 v3 `.bdg` 그대로), `Button.tsx`(variant 3종 primary/secondary/outline + size default/sm, 네이티브 button 속성 pass-through), `Card.tsx`(variant default/hero + interactive, margin은 컴포넌트에 강제 안 함), `SafetyNotice.tsx`(props 없음 — GOTCHAS §3 고정 문구를 타입으로 강제), `OfflineBanner.tsx`(v3에 시각 참고 없어 스펙 텍스트만으로 신규 설계), `Skeleton.tsx`(bg-hairline pulse, motion-reduce 대응). `src/lib/badgeTone.ts` — `severityTone`/`approvalStatusTone`/`caseStateTone`(1단계 §0.2 표 → BadgeTone 매핑, Badge는 이 파일에서 타입만 import해 도메인 타입 격리 유지). `icons.tsx`에 `IconShield` 추가(기존 4개 아이콘 불변). `tokens.css`/`tailwind.config.js`에 이번 태스크에 필요한 토큰 전부 등록(배지 배경 틴트 4색 + 텍스트 오버라이드 2개, 배지 radius 8px, surface-press, 버튼 치수 5개, SafetyNotice 치수 2개) — 임의값 Tailwind 클래스 0건.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 1.3(M1 브리핑 홈, 5상태 전부) — 이번에 만든 6개 컴포넌트 + badgeTone이 그 화면의 기반이 됨. L2라 계획 승인 대상.
- 결정 사항:
  - 배지 radius는 rules/design.md 요약(칩·배지 14)과 달리 실제 8px(`--r-badge`) — 프로토타입 v3 `.bdg{border-radius:8px}`가 시각 기준(rules/design.md 자체 원칙)이라 프로토타입을 따름. rules/design.md 요약 문구 자체는 이번 태스크 범위 밖이라 고치지 않음(다음에 손대는 사람이 "14로 되돌리는" 실수를 하지 않도록 여기 기록).
  - Button/Card는 레이아웃(margin/flex:1)을 자체에 강제하지 않음 — 프로토타입 정적 HTML과 달리 재사용 컴포넌트라 간격은 호출부(부모 레이아웃) 책임으로 뺌.
  - 배지 텍스트 색은 종류별로 기본 토큰과 다른 값 사용(critical: 아이콘/닷 등에 쓰는 #EF4444가 아니라 배지 전용 #DC2626, warning도 마찬가지) — 프로토타입 원본 그대로, `critical-text`/`warning-text`로 별도 등록.
  - `src/router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 실패(단독 실행 시엔 항상 통과) — 이번 태스크가 만든 파일과 무관(router.tsx/Shell.tsx 무변경 확인됨), 1.1부터 있던 타이밍 이슈로 추정. 다음에 이 테스트를 만지는 사람은 참고.
- verify 상태: PASS (typecheck 0, lint 0, test 19 files/104 tests passed, build OK). router.test.tsx 간헐적 flake는 위 참고.
- 지도/규칙 갱신: 없음(ARCHITECTURE.md의 "화면 컴포넌트" 항목은 아직 `src/features/`를 가리키는데, 이번 6개는 도메인 화면이 아니라 공용 프리미티브라 `src/components/`에 그대로 있음 — 별도 갱신 불필요 판단).

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
