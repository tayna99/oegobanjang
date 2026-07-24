import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// useRunEngine.test.tsx와 동일 관례 — 이 훅은 실 fetch(streamCommandRun)를 소비하므로
// 타이머가 아니라 async generator를 mock한다.
vi.mock('./api/runs', () => ({ streamCommandRun: vi.fn() }));

import { streamCommandRun } from './api/runs';
import type { RunSseFrame } from './api/runs';
import { useLiveRunEngine } from './useLiveRunEngine';
import { useSessionStore } from '@/stores/sessionStore';

const mockStreamCommandRun = vi.mocked(streamCommandRun);

async function* framesOf(frames: RunSseFrame[]): AsyncGenerator<RunSseFrame> {
  for (const frame of frames) yield frame;
}

describe('useLiveRunEngine', () => {
  afterEach(() => {
    mockStreamCommandRun.mockReset();
    useSessionStore.getState().reset();
  });

  it('companyId가 없으면 즉시 error 상태로 안내하고 streamCommandRun을 호출하지 않는다', () => {
    const { result } = renderHook(() => useLiveRunEngine('질문'));
    expect(result.current.status).toBe('error');
    expect(result.current.errorMessage).toBe('로그인이 필요합니다.');
    expect(mockStreamCommandRun).not.toHaveBeenCalled();
  });

  it('step 프레임을 누적하고 structured/done을 거쳐 done 상태로 전환한다', async () => {
    useSessionStore.setState({ companyId: 'cmp1' });
    mockStreamCommandRun.mockReturnValue(
      framesOf([
        { type: 'step', step: { kind: 'tool_call', label: '검색', detail: '근거 검색 중' } },
        {
          type: 'structured',
          data: {
            answer: { final_response: '답변', citations: [], missing_evidence: false, risk_flags: [] },
            approval: null,
          },
        },
        { type: 'done', run_id: 'r1', status: 'completed' },
      ]),
    );

    const { result } = renderHook(() => useLiveRunEngine('질문'));

    await waitFor(() => expect(result.current.status).toBe('done'));
    expect(result.current.steps).toEqual([{ kind: 'tool_call', label: '검색', detail: '근거 검색 중' }]);
    expect(result.current.answer?.final_response).toBe('답변');
    expect(mockStreamCommandRun).toHaveBeenCalledWith({ companyId: 'cmp1', message: '질문' }, expect.anything());
  });

  it('error 프레임이 오면 status를 error로 전환하고 뒤이은 done이 덮어쓰지 않는다', async () => {
    useSessionStore.setState({ companyId: 'cmp1' });
    mockStreamCommandRun.mockReturnValue(framesOf([{ type: 'error', detail: '근거 검색 실패' }]));

    const { result } = renderHook(() => useLiveRunEngine('질문'));
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.errorMessage).toBe('근거 검색 실패');
  });

  it('언마운트 시 전달한 AbortSignal을 abort한다', () => {
    useSessionStore.setState({ companyId: 'cmp1' });
    let capturedSignal: AbortSignal | undefined;
    mockStreamCommandRun.mockImplementation((_params, signal) => {
      capturedSignal = signal;
      return framesOf([]);
    });

    const { unmount } = renderHook(() => useLiveRunEngine('질문'));
    unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });
});
