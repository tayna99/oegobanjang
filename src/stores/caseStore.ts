import { create } from 'zustand';
import type { CaseCard, CaseState } from '@/types';
import { GuardrailError } from '@/lib/guardrail';

// GOTCHAS §2 상태 전이. 이 표 밖의 전이는 버그이므로 거부한다.
// returned(반려)는 승인 대기에서만 진입하고, 보완 후 다시 승인 대기로만 나간다
// (Mobile §2c "반려 시 … 요청이 되돌아갑니다", 블루프린트 §3).
const CASE_TRANSITIONS: Record<CaseState, readonly CaseState[]> = {
  draft: ['risk_review'],
  risk_review: ['approval_pending', 'blocked'],
  approval_pending: ['human_approved', 'returned', 'blocked'],
  returned: ['approval_pending'],
  human_approved: ['completed', 'blocked'],
  completed: [],
  blocked: [],
};

export function canTransition(from: CaseState, to: CaseState): boolean {
  return CASE_TRANSITIONS[from].includes(to);
}

interface CaseStoreState {
  cases: Record<string, CaseCard>;
  upsert: (card: CaseCard) => void;
  transition: (caseId: string, to: CaseState) => void;
  reset: () => void;
}

export const useCaseStore = create<CaseStoreState>((set, get) => ({
  cases: {},
  upsert: (card) =>
    set((s) => ({ cases: { ...s.cases, [card.caseId]: card } })),
  transition: (caseId, to) => {
    const current = get().cases[caseId];
    if (!current) throw new GuardrailError(`존재하지 않는 케이스: ${caseId}`);
    if (!canTransition(current.state, to)) {
      throw new GuardrailError(
        `허용되지 않은 상태 전이: ${current.state} → ${to}`,
      );
    }
    set((s) => ({
      cases: { ...s.cases, [caseId]: { ...current, state: to } },
    }));
  },
  reset: () => set({ cases: {} }),
}));
