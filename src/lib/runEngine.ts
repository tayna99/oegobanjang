import type { RunConfig, RunStep } from '@/mocks/runs';

// 스텝 스트리밍 간격 — 프로토타입 v3 관례(430ms * (index + 1)),
// HANDOFF에 이미 기록된 "MVP의 런은 각본 기반" 규칙을 그대로 구현한다.
const STEP_INTERVAL_MS = 430;

export interface RunEngineHandle {
  cancel: () => void;
}

// React를 모르는 순수 함수 — 이 시그니처와 RunConfig 인터페이스는 실 LLM 백엔드로
// 교체되어도 바뀌지 않아야 한다(ARCHITECTURE.md §5).
export function executeRun(
  config: RunConfig,
  onStep: (step: RunStep, index: number) => void,
  onDone: () => void,
): RunEngineHandle {
  if (config.mode === 'replay') {
    config.steps.forEach((step, index) => onStep(step, index));
    onDone();
    return { cancel: () => {} };
  }

  if (config.steps.length === 0) {
    onDone();
    return { cancel: () => {} };
  }

  const timers = config.steps.map((step, index) =>
    setTimeout(
      () => {
        onStep(step, index);
        if (index === config.steps.length - 1) onDone();
      },
      STEP_INTERVAL_MS * (index + 1),
    ),
  );

  return {
    cancel: () => timers.forEach(clearTimeout),
  };
}
