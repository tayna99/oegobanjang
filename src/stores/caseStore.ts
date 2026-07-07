import { create } from 'zustand';
import type { CaseCard, CaseState } from '@/types';
import { GuardrailError } from '@/lib/guardrail';

// GOTCHAS §2 상태 전이. 이 표 밖의 전이는 버그이므로 거부한다.
const CASE_TRANSITIONS: Record<CaseState, readonly CaseState[]> = {
  draft: ['risk_review'],
  risk_review: ['approval_pending', 'blocked'],
  approval_pending: ['human_approved', 'blocked'],
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
