import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRunEngine } from './useRunEngine';
import type { RunConfig } from '@/mocks/runs';

const CONFIG: RunConfig = {
  runKey: 'test',
  mode: 'approval',
  title: 't',
  agent: 'a',
  evidenceRef: '#1',
  autonomyLabel: 'x',
  question: 'q',
  altLabel: 'alt',
  steps: [
    { kind: 'tool_call', label: 's1', detail: 'd1' },
    { kind: 'tool_call', label: 's2', detail: 'd2' },
  ],
};

describe('useRunEngine', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('스트리밍 중에는 status가 streaming이고 emit된 스텝만 누적한다', () => {
    const { result } = renderHook(() => useRunEngine(CONFIG));
    expect(result.current.status).toBe('streaming');
    expect(result.current.steps).toHaveLength(0);

    act(() => {
      vi.advanceTimersByTime(430);
    });
    expect(result.current.steps).toHaveLength(1);
    expect(result.current.status).toBe('streaming');
  });

  it('모든 스텝이 emit되면 status가 done이 된다', () => {
    const { result } = renderHook(() => useRunEngine(CONFIG));
    act(() => {
      vi.advanceTimersByTime(430 * 2);
    });
    expect(result.current.status).toBe('done');
    expect(result.current.steps).toHaveLength(2);
    expect(result.current.currentIndex).toBe(1);
  });

  it('언마운트 시 남은 타이머를 취소한다', () => {
    const { unmount } = renderHook(() => useRunEngine(CONFIG));
    act(() => {
      vi.advanceTimersByTime(430);
    });
    unmount();
    expect(() => act(() => vi.advanceTimersByTime(1000))).not.toThrow();
  });
});
