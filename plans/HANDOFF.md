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
