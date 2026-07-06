import { create } from 'zustand';
import type { Approval } from '@/types';
import { GuardrailError } from '@/lib/guardrail';

export interface DispatchResult {
  dispatched: true;
  actionId: string;
}

interface ApprovalStoreState {
  approvals: Record<string, Approval>;
  seenKeys: Set<string>;
  /** 승인 요청 생성 — 액션의 종착점. 직접 발송 함수는 두지 않는다. */
  requestApproval: (actionId: string) => Approval;
  /** pending → approved|rejected. 같은 idempotencyKey 재호출은 no-op(중복 승인 차단). */
  decide: (
    actionId: string,
    decision: 'approved' | 'rejected',
    idempotencyKey: string,
  ) => Approval;
  /** 승인된 액션만 mock dispatch 경계까지. 미승인이면 가드레일 위반. */
  dispatch: (actionId: string) => DispatchResult;
  reset: () => void;
}

export const useApprovalStore = create<ApprovalStoreState>((set, get) => ({
  approvals: {},
  seenKeys: new Set<string>(),

  requestApproval: (actionId) => {
    const approval: Approval = {
      actionId,
      status: 'pending',
      idempotencyKey: '',
    };
    set((s) => ({ approvals: { ...s.approvals, [actionId]: approval } }));
    return approval;
  },

  decide: (actionId, decision, idempotencyKey) => {
    // 중복 승인 차단: 이미 처리한 키면 상태를 바꾸지 않고 현재값 반환(no-op).
    if (get().seenKeys.has(idempotencyKey)) {
      return get().approvals[actionId];
    }
    const current = get().approvals[actionId];
    if (!current) {
      throw new GuardrailError(`승인 요청이 없는 액션: ${actionId}`);
    }
    if (current.status !== 'pending') {
      throw new GuardrailError(
        `pending 상태에서만 결정 가능: 현재 ${current.status}`,
      );
    }
    const next: Approval = { ...current, status: decision, idempotencyKey };
    set((s) => {
      const seenKeys = new Set(s.seenKeys);
      seenKeys.add(idempotencyKey);
      return { approvals: { ...s.approvals, [actionId]: next }, seenKeys };
    });
    return next;
  },

  dispatch: (actionId) => {
    const current = get().approvals[actionId];
    if (!current || current.status !== 'approved') {
      throw new GuardrailError(
        `승인 없이 dispatch 불가: ${actionId} (현재 ${current?.status ?? '없음'})`,
      );
    }
    // MVP는 여기까지 — 실제 외부 발송 없음(mock 경계).
    return { dispatched: true, actionId };
  },

  reset: () => set({ approvals: {}, seenKeys: new Set<string>() }),
}));
