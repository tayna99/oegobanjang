import { useLiveRunStore } from '@/stores/liveRunStore';
import type { RunEngineStatus, UseRunEngineResult } from './useRunEngine';

// SD-4 — 실시간 커맨드 런(POST /runs/stream) 전용 훅. useRunEngine과 반환 계약이 완전히
// 동일해(steps/status/currentIndex) RunScreen·StepTimeline은 무수정으로 재사용된다. 차이는
// 스텝의 출처뿐이다 — executeRun의 setTimeout 재생 대신, liveRunStore가 이미 받아 두었거나
// (또는 지금 이 순간에도 계속 받고 있는) 프레임을 그대로 구독한다. 스트림 자체는 여기서
// 열지 않는다(그건 CommandBar가 시작한 liveRunStore.startCommandRun 몫) — 이 훅을 쓰는
// 컴포넌트가 마운트/언마운트돼도 스트림 소비 자체는 끊기지 않는다(핸드오프 설계,
// plans/SEED_DESIGN_2026-07-20.md Part C SD-4).
export function useLiveRunEngine(runId: string): UseRunEngineResult {
  const run = useLiveRunStore((s) => s.runs[runId]);
  const steps = run?.steps ?? [];
  const status: RunEngineStatus = run?.status === 'streaming' ? 'streaming' : 'done';
  return { steps, status, currentIndex: steps.length - 1 };
}
