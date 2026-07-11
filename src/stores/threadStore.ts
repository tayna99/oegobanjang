import { create } from 'zustand';
import type { Interpretation, MessageThread } from '@/types';
import { GuardrailError } from '@/lib/guardrail';

interface ThreadStoreState {
  threads: Record<string, MessageThread>;
  upsert: (thread: MessageThread) => void;
  /**
   * 응답 해석 확인 — pending_review에서만 진행 가능한 담당자 승인 경계.
   * 발송 함수는 여기 두지 않는다. sendMessage/dispatchMessage 등은 이 스토어에
   * 정의되지 않는다 — 승인은 상태(interpretationStatus)를 confirmed로 옮길 뿐,
   * 실제 채널 발송(mock dispatch 경계 포함)은 approvalStore.dispatch의 몫이다.
   */
  confirmInterpretation: (
    threadId: string,
    updateIds: string[],
  ) => Interpretation;
  /** 테스트용 초기화 — evidenceStore.ts의 reset 선례. */
  reset: () => void;
}

export const useThreadStore = create<ThreadStoreState>((set, get) => ({
  threads: {},

  upsert: (thread) =>
    set((s) => ({ threads: { ...s.threads, [thread.threadId]: thread } })),

  // updateIds는 이 단계에서는 시그니처만 확정한다 — caseStore.applyInterpretationUpdates
  // 연동은 페이지 오케스트레이션(RunPage.approve()와 같은 형태) 몫으로 남겨둔다.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- 위 사유로 이 단계는 시그니처만 확정
  confirmInterpretation: (threadId, _updateIds) => {
    const thread = get().threads[threadId];
    if (!thread) {
      throw new GuardrailError(`존재하지 않는 스레드: ${threadId}`);
    }

    // 이미 확인된 해석에 재호출 — 에러 없이 기존 interpretation을 그대로 반환하는 no-op
    // (approvalStore.decide의 idempotency 처리와 같은 정신이되, 여기서는 상태 자체가
    // 멱등성 판단 기준이므로 별도의 idempotencyKey 파라미터가 필요 없다).
    if (thread.interpretationStatus === 'confirmed') {
      if (!thread.interpretation) {
        throw new GuardrailError(`확인할 해석이 없는 스레드: ${threadId}`);
      }
      return thread.interpretation;
    }

    // 'none'(해석 자체가 없음)도 여기서 함께 걸러진다.
    if (thread.interpretationStatus !== 'pending_review' || !thread.interpretation) {
      throw new GuardrailError(
        `pending_review 상태에서만 해석 확인 가능: 현재 ${thread.interpretationStatus}`,
      );
    }

    const interpretation = thread.interpretation;
    set((s) => ({
      threads: {
        ...s.threads,
        [threadId]: {
          ...thread,
          interpretationStatus: 'confirmed',
          preview: interpretation.confirmedSummary ?? thread.preview,
        },
      },
    }));
    return interpretation;
  },

  reset: () => set({ threads: {} }),
}));
