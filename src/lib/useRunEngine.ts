import { useEffect, useState } from 'react';
import { executeRun } from './runEngine';
import type { RunConfig, RunStep } from '@/mocks/runs';

export type RunEngineStatus = 'streaming' | 'done';

export interface UseRunEngineResult {
  steps: RunStep[];
  status: RunEngineStatus;
  currentIndex: number;
}

// config는 참조 동일성이 유지되는 객체여야 한다(예: RUN_CONFIGS 배열 원소) — 매 렌더
// 새로 만들어진 객체 리터럴을 넘기면 스트리밍이 계속 재시작된다.
export function useRunEngine(config: RunConfig): UseRunEngineResult {
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [status, setStatus] = useState<RunEngineStatus>('streaming');

  useEffect(() => {
    setSteps([]);
    setStatus('streaming');
    const handle = executeRun(
      config,
      (step) => setSteps((prev) => [...prev, step]),
      () => setStatus('done'),
    );
    return () => handle.cancel();
  }, [config]);

  return { steps, status, currentIndex: steps.length - 1 };
}
