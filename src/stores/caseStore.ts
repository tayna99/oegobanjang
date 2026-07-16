import { create } from 'zustand';
import type { CaseCard, CaseState, InterpretationUpdate } from '@/types';
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
  // 해석 확인으로 갱신된 서류 필드값 — caseId → 필드명 → 갱신값. 케이스 원본 서류 데이터가
  // 아직 없으므로(M2.2 시점) 별도 네임스페이스에 쌓아둔다. CaseCard 필드가 아니다.
  docUpdates: Record<string, Record<string, { to: string }>>;
  upsert: (card: CaseCard) => void;
  transition: (caseId: string, to: CaseState) => void;
  /**
   * 해석 확인(ThreadPage.onConfirm, mocks/messages.ts ResponseInterpretation.updates)이
   * 제안한 서류 상태 갱신을 케이스에 반영한다. CASE_TRANSITIONS 표에 이 경로는 없다 —
   * CaseState를 전이시키지 않는다(actionNav.ts의 kind:'confirm' 케이스와 같은 취지:
   * 해석 확인은 케이스 상태 전이가 아니라 문서 갱신이다).
   */
  applyInterpretationUpdates: (
    caseId: string,
    updates: InterpretationUpdate[],
  ) => void;
  reset: () => void;
}

export const useCaseStore = create<CaseStoreState>((set, get) => ({
  cases: {},
  docUpdates: {},
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
  applyInterpretationUpdates: (caseId, updates) => {
    set((s) => {
      const existing = s.docUpdates[caseId] ?? {};
      const merged = { ...existing };
      for (const update of updates) {
        merged[update.field] = { to: update.to };
      }
      return { docUpdates: { ...s.docUpdates, [caseId]: merged } };
    });
  },
  reset: () => set({ cases: {}, docUpdates: {} }),
}));
