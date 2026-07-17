import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useConfirmInterpretation } from './interpretation';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useThreadStore } from '@/stores/threadStore';
import type { Interpretation, MessageThread } from '@/types';

const INTERPRETATION: Interpretation = {
  interpretationId: 'test-interp-1',
  threadId: 't1',
  caseId: 'case1',
  summaryKo: '요약',
  confidence: 'high',
  updates: [{ updateId: 'u1', field: '서류', from: '누락', to: '확인됨', badgeTone: 'warning' }],
  recommendedActions: [],
  isFinal: false,
  confirmedSummary: '확인 완료',
  evidenceRef: '#9001',
};

const THREAD: MessageThread = {
  threadId: 't1',
  workerRef: { displayName: '테스트', nationality: '베트남', maskLevel: 'masked' },
  channel: 'zalo',
  channelLabel: 'Zalo',
  caseId: 'case1',
  messages: [],
  interpretation: INTERPRETATION,
  interpretationStatus: 'pending_review',
  preview: '',
  timeLabel: '',
};

// ThreadPage/MessagesWorkbench가 공유하는 M6 해석확인 오케스트레이션(코드리뷰 reuse
// 지적으로 추출) — 훅 자체를 직접 단위 테스트한다.
describe('useConfirmInterpretation', () => {
  beforeEach(() => {
    useThreadStore.getState().reset();
    useCaseStore.getState().reset();
    useEvidenceStore.getState().reset();
    useThreadStore.getState().upsert(THREAD);
  });

  it('pending_review 스레드를 확인하면 3개 스토어가 모두 갱신된다', () => {
    const { result } = renderHook(() => useConfirmInterpretation());

    act(() => result.current('t1'));

    expect(useThreadStore.getState().threads.t1.interpretationStatus).toBe('confirmed');
    expect(useCaseStore.getState().docUpdates.case1?.['서류']).toEqual({ to: '확인됨' });
    const events = useEvidenceStore.getState().events;
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      type: 'interpretation_confirmed',
      caseId: 'case1',
      evidenceRef: '#9001',
      summary: '확인 완료',
    });
  });

  it('이미 confirmed인 스레드를 다시 호출해도 evidence가 중복 기록되지 않는다(이중 클릭 방지)', () => {
    const { result } = renderHook(() => useConfirmInterpretation());

    act(() => result.current('t1'));
    act(() => result.current('t1'));

    expect(useEvidenceStore.getState().events).toHaveLength(1);
  });

  it('존재하지 않는 스레드 id는 조용히 무시한다', () => {
    const { result } = renderHook(() => useConfirmInterpretation());
    act(() => result.current('no-such-thread'));
    expect(useEvidenceStore.getState().events).toHaveLength(0);
  });
});
