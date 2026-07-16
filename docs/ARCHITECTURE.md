# ARCHITECTURE — 에이전트용 지도

> 목적: 코드를 읽기 전에 이 파일로 위치를 잡는다. 코드 변경으로 이 지도가 낡으면 **같은 PR에서 갱신**한다.

## 1. 제품 한 줄

알림 → 오늘 브리핑(M1) → 케이스 시트(M2) → 초안(M3) → 승인(M4) → 완료(M5) 루프가 본체.
에이전트 런(M9)과 프로액티브 런이 준비물을 만들고, 사람은 승인만 한다. 모든 판단은 Evidence(M8)에 남는다.

## 2. 진입점

| 무엇을 찾을 때 | 여기서 시작 |
|---|---|
| 라우팅·딥링크 | `src/router.tsx` — 딥링크 맵은 스펙 `2단계_알림카탈로그` §3과 1:1 |
| 화면 셸(탭바/헤더) | `src/Shell.tsx` — <1024px 모바일 탭바, 이상 PC 헤더 |
| 화면 컴포넌트 | `src/features/<도메인>/` — 화면 코드는 전부 features 아래. 예: `src/features/briefing/`(M1) — `BriefingScreen`(5상태 프레젠테이션) + `BriefingHomePage`(caseStore 시딩 컨테이너) 분리 패턴, M2~M9도 이걸 따른다. `src/features/case/`(M2) — `CaseSheet`(5블록+ActionBar, citation 0건 승인 잠금) + `CaseSheetPage`(BriefingHomePage를 배경으로 재사용하는 오버레이 근사 — 진짜 background-location은 M7(2.1) 이후 재검토). `src/features/run/`(M4/M9, 1.5) — `StepTimeline`(RunStep 리스트, guardrail만 경고 톤) + `RunScreen`(5상태 프레젠테이션, mode='approval'|'command'|'replay') + `RunPage`(컨테이너 — `/case/:caseId/approve`·`/run/:runId` 두 라우트를 이 하나로 공유, caseId면 approval config를, runId면 runKey로 조회). `src/features/messages/`(2.2, 메시지 탭) — `MessagesScreen`(default/empty 프레젠테이션, `sortThreads`로 응답 도착 스레드 최상단 고정) + `MessagesPage`(threadStore 시딩 컨테이너 — Page+Screen 분리 패턴의 또 다른 실사례). `src/features/thread/`(2.2, M6 포함) — `ThreadScreen`(5상태, `default` 안에 `interpretation`(M6 해석 확인)/`timeline`(대화+확정 카드) 2모드) + `InterpretationCard`(surface 카드, 유일한 파랑 CTA "상태 반영 확인") + `ThreadPage`(threadStore 조회 + confirmInterpretation→caseStore.applyInterpretationUpdates→evidenceStore.append 오케스트레이션, 승인 대기 초안 스레드는 `<Navigate>`로 M3 직행). (`src/screens/`는 도메인 화면이 아직 없는 라우트를 덮는 공용 `PlaceholderScreen` 전용) |
| 데이터 타입 | `src/types.ts` — CaseCard·NextActionRef·Approval·EvidenceEvent (1단계 스펙 §0.4), Message·MessageThread·Interpretation(2.2, 스펙 원본은 `docs/MESSAGING_CHANNELS.md` §4) |
| DB 설계 계약 | `docs/DB_SCHEMA.md` — PostgreSQL 16+ 서비스 DB의 데이터 계약 정본. 실행 DDL·데모 시드·160개 회귀 검증은 `db/`(`db/schema.sql`, `db/seed_demo.sql`, `db/validate.py`)에 있으며, backend 이식은 별도 PR 범위 |
| 상태 | `src/stores/` — caseStore, approvalStore, evidenceStore, threadStore(2.2 — `upsert`/`confirmInterpretation`. 발송 함수 없음: 승인은 `interpretationStatus`를 `confirmed`로 옮길 뿐, 실제 채널 발송은 approvalStore.dispatch 몫) |
| 디자인 토큰 | `src/styles/tokens.css` + `tailwind.config` theme |
| mock 데이터 | `src/mocks/` — `fixtures.ts`(CASE_CARDS·CASE_SHEETS) · `drafts.ts`(DRAFT) · `runs.ts`(RUN_CONFIGS — 1.5부터 command/replay 포함 8건) · `evidence.ts`(EVIDENCE_SEED) · `threads.ts`(2.2 — `THREADS` 스레드·해석 픽스처 + `threadIdForCase` caseId→threadId 매핑, 셀렉터는 `src/lib/threads.ts`의 `sortThreads`/`threadBadge`/`countArrivedResponses`/`formatClockTime`/`formatDateCaption`/`latestInboundMessage`). Nguyen/Tran/Bayar/Mohammad/채용. Candidate는 PKG 전용(M2.4) |

## 3. 화면 ↔ 라우트 ↔ 스펙

| 라우트 | 화면 | 스펙 원본 |
|---|---|---|
| `/` | M1 브리핑 홈 | 1단계 M1, 탭별기획 §1 |
| `/cases` `?filter=` | M7 케이스 목록 (+M2 시트) | 1단계 M2·M7, 탭별기획 §2 |
| `/case/:caseId` (bare) | M2 케이스 바텀시트 (M1 위에 오버레이) | 2단계 딥링크맵 §3 (N03 등) |
| `/case/:id/draft` | M3 초안 | 1단계 M3 |
| `/case/:id/approve` | M4 승인 직전 (런 화면 mode=approval) | 1단계 M4 |
| `/run/:id` | M9 런 / 재생 | 1단계 M9 (v1.2) |
| `/messages` `/thread/:id` | 메시지 탭(스레드 리스트) · M6 응답 해석(스레드 대화 뷰, interpretation/timeline 2모드) — 구현 완료(2.2) | 1단계 M6, 탭별기획 §3 |
| `/evidence` `?ref=` | M8 판단 기록 | 1단계 M8, 탭별기획 §4 |
| `/package/:id` | 행정사 패키지 | 프로토타입 v3 pkg 화면 |
| `/done` | M5 완료 (라우트보다 push 화면) | 1단계 M5 |
| `/onboarding/workers` | O1 근로자 등록 (3단계 온보딩) | 2단계 딥링크맵 §3 (N21) |

## 4. 데이터 흐름 (단방향)

```
mocks/fixtures, mocks/threads ──▶ stores (zustand)
                     │ caseStore: 케이스·NextAction 상태 전이
                     │ approvalStore: 승인 요청/결정 (idempotency key)
                     │ evidenceStore: append-only 이벤트 로그
                     │ threadStore: 스레드·해석 상태 (upsert / confirmInterpretation, 2.2)
                     ▼
               features/* 화면 (구독) ──액션──▶ stores 갱신 ──▶ evidenceStore.append (항상)
```

- 규칙: 화면은 store를 직접 mutate하지 않는다 — store의 액션 함수만 호출
- 승인만 예외적으로 "서버 확정 후 반영" 패턴 (MVP에선 mockApi.approve()가 서버 역할)

## 5. 런 시스템 (에이전틱 코어)

```
runEngine.execute(config: RunConfig)
  ├─ mode: 'command'(M9) | 'approval'(M4) | 'replay'(#4788)
  ├─ steps: RunStep[] (thinking|tool_call|guardrail|handoff|replan)
  ├─ 스트리밍: 스텝 순차 emit → UI StepTimeline 렌더
  └─ 종료: ResultBlock | requestApproval() — 발송 도구는 존재하지 않음
```

- MVP의 런은 **각본 기반**(fixtures의 step 배열 재생). 실 LLM 연결은 백엔드 단계 — 인터페이스(RunConfig)를 바꾸지 않고 교체 가능해야 한다
- 프로액티브 런 = `startedBy:'event'` + 도구 화이트리스트(읽기+초안) + 종착점 승인 요청
- **구현(1.5):** `src/lib/runEngine.ts`의 `executeRun(config, onStep, onDone)`이 React 비의존 순수 함수로 위 계약을 구현 — approval/command는 `430ms * (index+1)` 간격 스텝 emit, replay는 지연 없이 전체 즉시 emit. `src/lib/useRunEngine.ts`가 React 훅으로 감싸 `{steps, status, currentIndex}`를 노출. M4(`/case/:caseId/approve`)와 M9(`/run/:runId`)는 같은 `RunPage`/`RunScreen`을 공유(§2). 1.6부터 approval mode 승인 버튼은 pprovalStore.decide() → caseStore.transition(..., 'human_approved') → evidenceStore.append('approval_decided') → /done으로 이어진다.

## 6. 의존 방향 (위반 금지)

```
app → features → components, stores, mocks
components ↛ features (공용 컴포넌트는 도메인을 모른다)
stores ↛ features
```

## 7. 흐름도 — 승인 해피패스

```
M1 카드 [보내기 승인]
→ router: /case/nguyen/approve
→ runEngine(mode:approval) 스트리밍 → 완료 후 승인 버튼 enable
→ approvalStore.decide(approved, idempotencyKey)
→ caseStore 전이(approval_pending→human_approved)
→ evidenceStore.append(approval_decided)
→ M5 push-in → 복귀 시 M1 카드 상태 반영
```
