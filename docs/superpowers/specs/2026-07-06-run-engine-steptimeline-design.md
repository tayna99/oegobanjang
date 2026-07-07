# 런 엔진 + StepTimeline 설계 (ROADMAP 1.5)

> 관련: ARCHITECTURE.md §5 런 시스템, 1단계_화면상태스펙 §M9 v1.2, GOTCHAS(가드레일 노출, 승인 즉시 활성화 금지)

## 배경 / 범위

ROADMAP 1.5: "런 엔진 + StepTimeline (mode: approval/command/replay, 스텝 스트리밍)". L3(협업) 태스크.

DoD: 스트리밍 완료 전 승인 disabled 테스트, guardrail 스텝 렌더.

범위는 3개 모드(approval/command/replay)를 한 번에 다룬다 — 사용자 확인됨. 이유: ARCHITECTURE.md가 이미 3모드를 하나의 런 엔진 계약으로 정의해뒀고, 1.6(M3~M5 루프)이 M4(approval) 완성을 전제하므로 어차피 approval은 필수이며, command/replay의 UI 진입점(CommandBar, ApprovalCard 프로액티브 행)이 이미 자리만 잡힌 채 존재해 배선 비용이 크지 않다.

## 1. 엔진 코어

### `src/lib/runEngine.ts`

React에 의존하지 않는 순수 함수:

```ts
export function executeRun(
  config: RunConfig,
  onStep: (step: RunStep, index: number) => void,
  onDone: () => void,
): { cancel: () => void }
```

- `config.mode === 'replay'`일 때는 스텝을 지연 없이 모두 즉시 emit 후 `onDone()` 호출(읽기 전용 재생, 애니메이션 없음).
- 그 외(`'approval'`, `'command'`)는 `setTimeout` 기반 순차 emit, 간격은 프로토타입 v3 관례 `430ms * (i + 1)`.
- 반환된 `cancel()`은 남은 `setTimeout`을 모두 clear — 사용자가 화면을 벗어나거나 취소를 누를 때 훅의 `useEffect` cleanup에서 호출.
- 이 함수의 시그니처와 `RunConfig` 인터페이스는 이후 실 LLM 백엔드로 교체되어도 바뀌지 않아야 한다(ARCHITECTURE.md §5의 명시적 요구).

### `src/lib/useRunEngine.ts`

```ts
function useRunEngine(config: RunConfig): {
  steps: RunStep[];       // 지금까지 emit된 스텝만
  status: 'streaming' | 'done' | 'error';
  currentIndex: number;
}
```

- 내부에서 `executeRun`을 호출하고 스텝을 누적, `config`가 바뀌면(런 전환) 이전 실행을 `cancel()`하고 재시작.
- 전역 zustand 스토어는 만들지 않는다 — 런은 화면 하나가 소유하는 로컬 상태이며, caseStore/approvalStore처럼 여러 화면이 동시 구독해야 할 공유 상태가 아니다.

## 2. 데이터 모델 — `src/mocks/runs.ts` 확장

- `RunConfig.mode`는 기존 3값(`'command' | 'approval' | 'replay'`) 그대로 유지. ARCHITECTURE.md의 "M4는 이 화면의 mode='pre_approval' 특수 케이스"라는 문구는 별도 모드 값이 아니라 "M4 라우트가 이 화면(mode='approval')의 특수 사용처"라는 뜻으로 해석한다(사용자 확인).
- `mode:'command'` 신규 1건 추가: 데모 시나리오 "이번 달 급한 직원만 정리해줘"(run #4790). MVP는 자연어 파싱을 하지 않으므로, CommandBar 제출 시 항상 이 고정 config로 매핑한다(실 파싱은 백엔드 단계).
- `mode:'replay'` 신규 1건 추가: run #4788, `readOnly: true` 필드 추가(타입에 반영). ApprovalCard의 `preparedRunRef`, CaseSheet의 `activity[].runRef`가 참조하는 대상.
- `RunStepKind`는 스펙 5종(`thinking | tool_call | guardrail | handoff | replan`)만 남긴다. M0.5가 추가했던 로컬 `'wait'` kind는 현재 사용처를 확인해 guardrail로 흡수하거나 제거한다(구현 태스크에서 실사용처 grep 후 결정).

## 3. 화면 — `src/features/run/`

- `RunScreen`(프레젠테이션, 5상태) + `RunPage`(컨테이너) — M1/M2와 동일한 container/presentation 분리 패턴.
- 라우트 `/case/:caseId/approve`(M4)와 `/run/:runId`(M9) 둘 다 `RunPage`를 마운트한다. 전자는 `mode:'approval'` config로, 후자는 `mode:'command'` 또는 `mode:'replay'` config로 진입 — 어떤 config를 쓸지는 라우트 파라미터(`caseId` vs `runId`)로 `RUN_CONFIGS`에서 조회해 결정한다.
- `StepTimeline` 컴포넌트: emit된 `steps`를 리스트 렌더. `kind==='guardrail'`인 스텝은 별도 색/아이콘으로 시각적으로 구분되어야 한다(GOTCHAS: "가드레일은 숨기지 않고 스텝으로 노출 — 신뢰 자산"). 나머지 4종(`thinking/tool_call/handoff/replan`)은 기존 AgentActivityBlock 아이콘 세트를 참고해 매핑.
- 승인 버튼(`mode:'approval'`일 때만 렌더): `status !== 'done'`이면 `disabled` — 이것이 DoD의 핵심 테스트 포인트("스트리밍 완료 전 승인 disabled").
- 5상태:
  - default: 스트리밍 진행 중, pause/cancel 컨트롤 노출.
  - empty/loading: "분석 중" — 스트리밍 시작 직후 첫 스텝 emit 전 구간.
  - error: 스펙의 3가지 서브케이스(그중 "범위 밖 요청 → 행정사 검토 요청" 포함) 그대로 이식.
  - offline: 기존 `OfflineBanner` 재사용, 승인/커맨드 제출 등 요청 발신형 액션 잠금(GOTCHAS "오프라인 시 승인 차단").
- replay 모드는 승인 버튼도, pause/cancel도 렌더하지 않고 전체 스텝을 정적으로 보여주기만 한다.

## 4. 기존 진입점 배선

- `CommandBar.onSubmit`(현재 입력만 비우는 no-op): 제출 시 `mode:'command'` RunConfig(#4790 고정)를 골라 `/run/<그 config의 runId>`로 네비게이트하도록 교체.
- `ApprovalCard`의 프로액티브 행(현재 `stopPropagation`만 하는 no-op 버튼): `preparedRunRef`가 가리키는 replay config로 `/run/<runId>`(replay 모드) 네비게이트하도록 교체.
- `/case/:caseId/approve`(M4) 라우트: 기존 `PlaceholderScreen` → `RunPage`(mode=approval)로 교체.

## 5. 테스트 전략

- `useRunEngine` 단위 테스트: fake timer로 스텝이 순차 emit되는지, `cancel()` 호출 시 이후 스텝이 emit되지 않는지, replay config는 즉시 전체 emit되는지.
- `RunScreen` 컴포넌트 테스트: 스트리밍 미완료 상태에서 승인 버튼 `disabled` 속성 확인(DoD 1), `kind:'guardrail'` 스텝이 다른 스텝과 구분되는 클래스/텍스트로 렌더되는지 확인(DoD 2).
- `CommandBar`/`ApprovalCard` 통합 테스트: 제출/클릭 시 올바른 라우트로 네비게이트하는지.

## 자기 검토

- Placeholder 없음 — 모든 섹션에 구체적 파일 경로·타입·값 명시.
- 내부 일관성: §2의 모드 해석이 §1(엔진)·§3(화면)·§4(배선) 전체에서 동일하게 사용됨.
- 범위: 단일 구현 계획으로 다루기에 적절한 크기(엔진 1개 파일 쌍 + 화면 1쌍 + 기존 mock/두 컴포넌트 수정) — 별도 분해 불필요.
- 모호성 점검: "M4 특수 케이스" 문구의 두 가지 해석 가능성을 명시적으로 하나로 확정함(별도 모드 값 아님).
