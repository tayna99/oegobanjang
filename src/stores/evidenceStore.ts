import { create } from 'zustand';
import type { EvidenceEvent } from '@/types';

interface EvidenceStoreState {
  events: readonly EvidenceEvent[];
  /** append-only. 수정·삭제 액션은 존재하지 않는다 (감사 무결성). 정정도 새 이벤트로. */
  append: (event: EvidenceEvent) => void;
  reset: () => void;
}

export const useEvidenceStore = create<EvidenceStoreState>((set) => ({
  events: [],
  append: (event) =>
    // 이벤트를 동결해 사후 변형을 막는다.
    set((s) => ({ events: [...s.events, Object.freeze({ ...event })] })),
  reset: () => set({ events: [] }),
}));
