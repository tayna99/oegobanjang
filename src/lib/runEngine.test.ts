import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { executeRun } from './runEngine';
import type { RunConfig } from '@/mocks/runs';

const APPROVAL_CONFIG: RunConfig = {
  runKey: 'test-approval',
  mode: 'approval',
  title: 't',
  agent: 'a',
  evidenceRef: '#1',
  autonomyLabel: 'x',
  question: 'q',
  altLabel: 'alt',
  steps: [
    { kind: 'tool_call', label: 's1', detail: 'd1' },
    { kind: 'guardrail', label: 's2', detail: 'd2' },
  ],
};

const REPLAY_CONFIG: RunConfig = { ...APPROVAL_CONFIG, mode: 'replay', readOnly: true };

describe('executeRun', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('approval/command 모드는 스텝을 430ms 간격으로 순차 emit한다', () => {
    const onStep = vi.fn();
    const onDone = vi.fn();
    executeRun(APPROVAL_CONFIG, onStep, onDone);

    expect(onStep).not.toHaveBeenCalled();

    vi.advanceTimersByTime(430);
    expect(onStep).toHaveBeenCalledTimes(1);
    expect(onStep).toHaveBeenNthCalledWith(1, APPROVAL_CONFIG.steps[0], 0);
    expect(onDone).not.toHaveBeenCalled();

    vi.advanceTimersByTime(430);
    expect(onStep).toHaveBeenCalledTimes(2);
    expect(onStep).toHaveBeenNthCalledWith(2, APPROVAL_CONFIG.steps[1], 1);
    expect(onDone).toHaveBeenCalledOnce();
  });

  it('cancel() 호출 후에는 남은 스텝이 emit되지 않는다', () => {
    const onStep = vi.fn();
    const onDone = vi.fn();
    const handle = executeRun(APPROVAL_CONFIG, onStep, onDone);

    vi.advanceTimersByTime(430);
    handle.cancel();
    vi.advanceTimersByTime(1000);

    expect(onStep).toHaveBeenCalledTimes(1);
    expect(onDone).not.toHaveBeenCalled();
  });

  it('replay 모드는 지연 없이 전체 스텝을 즉시 emit하고 종료한다', () => {
    const onStep = vi.fn();
    const onDone = vi.fn();
    executeRun(REPLAY_CONFIG, onStep, onDone);

    expect(onStep).toHaveBeenCalledTimes(2);
    expect(onDone).toHaveBeenCalledOnce();
  });
});
