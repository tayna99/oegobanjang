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
| 화면 컴포넌트 | `src/features/<도메인>/` — 화면 코드는 전부 features 아래. 예: `src/features/briefing/`(M1) — `BriefingScreen`(5상태 프레젠테이션) + `BriefingHomePage`(caseStore·threadStore 시딩 컨테이너) 분리 패턴, M2~M9도 이걸 따른다. `src/features/case/`(M2) — `CaseReviewPage`(2b 사례 검토, citation 0건 승인 잠금, caseStore.docUpdates 오버레이) + `CaseHistoryPage`(2d 승인 이력). `src/features/approve/ApprovePage.tsx`(2c, M2.6.3) — 체크리스트 4/4 + citation-lock + PIN 게이트, 결정은 `lib/approval.ts`의 `useApprovalActions`(approve/reject) 공유 유닛이 수행. `src/features/run/`(M9, 1.5) — `StepTimeline`(RunStep 리스트, guardrail만 경고 톤) + `RunScreen`(5상태 프레젠테이션, mode='approval'\|'command'\|'replay') + `RunPage`(`/run/:runId` 전용 — RUN_CONFIGS를 runKey로 조회, mode 무관 단일 라우트. 케이스 최종 승인(`/case/:id/approve`)과는 별개 화면·별개 결정 경로다). `src/features/messages/`(2.2, 메시지 탭) — 모바일은 `MessagesScreen`(default/empty 프레젠테이션, `sortThreads`로 응답 도착 스레드 최상단 고정) + `MessagesPage`(threadStore 시딩 컨테이너, lg+에서는 `MessagesWorkbench`(PC 4c, 독립 mock `mocks/messages.ts` 사용)로 분기). `src/features/thread/`(2.2, M6) — `ThreadScreen`(5상태, `default` 안에 `interpretation`(M6 해석 확인)/`timeline`(대화+확정 카드) 2모드) + `InterpretationCard`(surface 카드, 유일한 파랑 CTA "상태 반영 확인") + `ThreadPage`(threadStore 조회 + confirmInterpretation→caseStore.applyInterpretationUpdates→evidenceStore.append 오케스트레이션, 승인 대기 초안 스레드는 `<Navigate>`로 M3 직행). (`src/screens/`는 도메인 화면이 아직 없는 라우트를 덮는 공용 `PlaceholderScreen` 전용) |
| 데이터 타입 | `src/types.ts` — CaseCard·NextActionRef·Approval·EvidenceEvent (1단계 스펙 §0.4), Message·MessageThread·Interpretation(2.2, 스펙 원본은 `docs/MESSAGING_CHANNELS.md` §4), CompanyMember·DelegationConfig·ApprovalPolicy·Tenant·ExpertAccount·ExpertMembership(7단계 RBAC·행정사 화이트라벨) |
| DB 설계 계약 | `docs/DB_SCHEMA.md` — PostgreSQL 16+ 서비스 DB의 데이터 계약 정본. 실행 DDL·데모 시드·160개 회귀 검증은 `db/`(`db/schema.sql`, `db/seed_demo.sql`, `db/validate.py`)에 있으며, backend 이식은 별도 PR 범위 |
| 상태 | `src/stores/` — caseStore(docUpdates 포함), approvalStore, evidenceStore, citationStore, roleStore, companyStore, threadStore(2.2 — `upsert`/`confirmInterpretation`. 발송 함수 없음: 승인은 `interpretationStatus`를 `confirmed`로 옮길 뿐, 실제 채널 발송은 approvalStore.dispatch 몫) |
| 디자인 토큰 | `src/styles/tokens.css` + `tailwind.config` theme |
| mock 데이터 | `src/mocks/` — `fixtures.ts`(CASE_CARDS·CASE_SHEETS, 6인 로스터: Batbayar·Nguyen·Siti·Tran·Rahmat·Oyunaa) · `drafts.ts`(DRAFT) · `runs.ts`(RUN_CONFIGS — command/replay 포함) · `evidence.ts`(EVIDENCE_SEED) · `threads.ts`(2.2 — `THREADS` 스레드·해석 픽스처 + `threadIdForCase` caseId→threadId 매핑, 셀렉터는 `src/lib/threads.ts`의 `sortThreads`/`threadBadge`/`countArrivedResponses`/`formatClockTime`/`formatDateCaption`/`latestInboundMessage`) · `messages.ts`(MessagesWorkbench 전용 독립 mock, threadStore와 별개) · `packages.ts`(행정사 패키지, M2.4) |

## 3. 화면 ↔ 라우트 ↔ 스펙

| 라우트 | 화면 | 스펙 원본 |
|---|---|---|
| `/` | M1 브리핑 홈 | 1단계 M1, 탭별기획 §1 |
| `/cases` `?filter=` | M7 케이스 목록 (+M2 시트) | 1단계 M2·M7, 탭별기획 §2 |
| `/case/:caseId` (bare) | 2b 사례 검토 전면 페이지(모바일) / PC 워크벤치 선택 상태(lg+) — M2.6.2에서 바텀시트 대체 | 2단계 딥링크맵 §3 (N03 등), Mobile.dc.html §2b |
| `/case/:id/draft` | M3 초안 | 1단계 M3 |
| `/case/:id/approve` | 2c 최종 승인 체크리스트(필수 4/4 게이트 + 반려 사유) — M2.6.3에서 런 화면 대체, 에이전트 런은 /run/:runId 전용 | Mobile.dc.html §2c |
| `/case/:id/history` | 2d 승인 이력(생애 타임라인, 사람 결정만 primary) — M2.6.4 신설 | Mobile.dc.html §2d, 탭별기획 §4.2 |
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
- **구현(1.5):** `src/lib/runEngine.ts`의 `executeRun(config, onStep, onDone)`이 React 비의존 순수 함수로 위 계약을 구현 — approval/command는 `430ms * (index+1)` 간격 스텝 emit, replay는 지연 없이 전체 즉시 emit. `src/lib/useRunEngine.ts`가 React 훅으로 감싸 `{steps, status, currentIndex}`를 노출. M2.6.3부터 M4 케이스 최종 승인(`/case/:id/approve`)은 `ApprovePage`(체크리스트 4/4 + citation-lock + PIN 게이트, `lib/approval.ts`의 `useApprovalActions`로 결정)가 전담하고, `RunPage`/`RunScreen`은 M9(`/run/:runId`) 전용이다(§2). 1.6부터 approval mode 승인 버튼은 approvalStore.decide() → caseStore.transition(..., 'human_approved') → evidenceStore.append('approval_decided') → `/case/:id/history`(2d)로 이어진다.

## 6. 의존 방향 (위반 금지)

```
app → features → components, stores, mocks
components ↛ features (공용 컴포넌트는 도메인을 모른다)
stores ↛ features
```

## 7. 흐름도 — 승인 해피패스 (M2.6, Mobile.dc.html §2a~2d)

```
M1 카드 [검토]
→ router: /case/nguyen (2b 사례 검토) → "검토 계속"
→ router: /case/nguyen/approve (2c 최종 승인)
→ ApprovePage: 체크리스트 필수 4/4 + citation-lock 해제 → [승인하기] → 본인확인 PIN 확인
→ useApprovalActions.approve(): approvalStore.decide(approved, idempotencyKey)
→ caseStore 전이(approval_pending→human_approved)
→ evidenceStore.append(approval_decided)
→ router: /case/nguyen/history (2d 승인 이력) → 복귀 시 M1 카드 상태 반영
```
